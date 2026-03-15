"""
api/main.py — FastAPI wrapper around the FraudGen pipeline.

Run with:
    PYTHONPATH=app uvicorn api.main:app --reload --port 8000

The existing Streamlit app (app.py) is untouched and continues to work.
"""
from __future__ import annotations

import asyncio
import csv
import io
import os
import sys
import threading
from dataclasses import asdict
from pathlib import Path
from typing import Any

# ------------------------------------------------------------------
# Add app/ to sys.path so pipeline imports resolve
# ------------------------------------------------------------------
_ROOT = Path(__file__).parent.parent
_APP_DIR = _ROOT / "app"
if str(_APP_DIR) not in sys.path:
    sys.path.insert(0, str(_APP_DIR))

from dotenv import load_dotenv
load_dotenv(_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel

from models.run_config import RunConfig
from pipeline.run_state import RunState
from pipeline.runner import PipelineRunner

# ------------------------------------------------------------------
# App setup
# ------------------------------------------------------------------
app = FastAPI(title="FraudGen API", version="1.0.0")

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:3001,*")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------------------------------------------
# In-memory run store
# ------------------------------------------------------------------
_runs: dict[str, dict[str, Any]] = {}
# structure: { run_id: { run_state, thread, folder_path, config, approved_variants } }


def _get_run(run_id: str) -> dict[str, Any]:
    if run_id not in _runs:
        raise HTTPException(status_code=404, detail=f"Run {run_id!r} not found")
    return _runs[run_id]


# ------------------------------------------------------------------
# Request / response models
# ------------------------------------------------------------------
class StartRunRequest(BaseModel):
    fraud_description: str
    variant_count: int = 7
    fidelity_level: int = 3
    max_parallel: int = 3
    critic_floor: float = 7.0
    max_revisions: int = 2
    persona_count: int = 5
    risk_distribution: dict = {"high": 33, "mid": 34, "low": 33}
    geographic_scope: list[str] = ["domestic"]
    mule_context_depth: str = "medium"
    cost_cap_usd: float = 20.0
    auto_second_pass: bool = False
    demo_mode: bool = True


class ControlRequest(BaseModel):
    signal: str  # "run" | "pause" | "stop"


# ------------------------------------------------------------------
# POST /api/runs — start a new pipeline run
# ------------------------------------------------------------------
@app.post("/api/runs")
def start_run(req: StartRunRequest) -> dict:
    config = RunConfig(
        fraud_description=req.fraud_description,
        variant_count=max(1, min(req.variant_count, 20)),
        fidelity_level=req.fidelity_level,
        max_parallel=req.max_parallel,
        critic_floor=req.critic_floor,
        max_revisions=req.max_revisions,
        persona_count=req.persona_count,
        risk_distribution=req.risk_distribution,
        geographic_scope=req.geographic_scope,
        mule_context_depth=req.mule_context_depth,
        cost_cap_usd=req.cost_cap_usd,
        auto_second_pass=req.auto_second_pass,
        demo_mode=req.demo_mode,
    )
    run_state = RunState()
    approved_variants: list = []
    folder_path: list[str] = [""]  # mutable container so thread can write back

    def _run_thread() -> None:
        async def _run() -> None:
            fp = await PipelineRunner().run(
                config=config,
                run_state=run_state,
                approved_variants_out=approved_variants,
            )
            folder_path[0] = fp

        asyncio.run(_run())

    thread = threading.Thread(target=_run_thread, daemon=True)
    thread.start()

    _runs[run_state.run_id] = {
        "run_state": run_state,
        "thread": thread,
        "folder_path": folder_path,
        "config": config,
        "approved_variants": approved_variants,
    }

    return {"run_id": run_state.run_id}


# ------------------------------------------------------------------
# GET /api/runs/{id}/status
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/status")
def get_status(run_id: str) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    snap = rs.snapshot()
    with rs._lock:
        event_log = list(rs.event_log[-50:])
        variant_log = [asdict(v) for v in rs.variant_log]
        coverage_cells = [asdict(c) for c in rs.coverage_cells.values()]
    snap["event_log"] = event_log
    snap["variant_log"] = variant_log
    snap["coverage_cells"] = coverage_cells
    snap["cost_cap_usd"] = entry["config"].cost_cap_usd
    return snap


# ------------------------------------------------------------------
# POST /api/runs/{id}/control
# ------------------------------------------------------------------
@app.post("/api/runs/{run_id}/control")
def control_run(run_id: str, req: ControlRequest) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    try:
        rs.set_control(req.signal)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True, "signal": req.signal}


# ------------------------------------------------------------------
# GET /api/runs/{id}/matrix
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/matrix")
def get_matrix(run_id: str) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    with rs._lock:
        orch = rs.orchestrator_output
        cells = [asdict(c) for c in rs.coverage_cells.values()]
    dimensions = []
    if orch is not None:
        try:
            dimensions = orch.variation_dimensions
        except AttributeError:
            pass
    return {"dimensions": dimensions, "cells": cells}


# ------------------------------------------------------------------
# GET /api/runs/{id}/personas
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/personas")
def get_personas(run_id: str) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    with rs._lock:
        personas = list(rs.personas)
    result = []
    for p in personas:
        try:
            result.append(p.model_dump())
        except AttributeError:
            result.append(vars(p) if hasattr(p, "__dict__") else str(p))
    return {"personas": result}


# ------------------------------------------------------------------
# GET /api/runs/{id}/results
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/results")
def get_results(run_id: str) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    with rs._lock:
        scored = list(rs.scored_variants)
        cells = list(rs.coverage_cells.values())

    variants_out = []
    total_transactions = 0
    realism_scores = []
    distinctiveness_scores = []

    for sv in scored:
        try:
            d = sv.model_dump()
        except AttributeError:
            d = vars(sv) if hasattr(sv, "__dict__") else {}
        variants_out.append(d)
        txns = d.get("transactions", [])
        total_transactions += len(txns)
        if d.get("realism_score"):
            realism_scores.append(d["realism_score"])
        if d.get("distinctiveness_score"):
            distinctiveness_scores.append(d["distinctiveness_score"])

    completed_cells = sum(1 for c in cells if c.status == "completed")
    total_cells = len(cells) if cells else 1
    coverage_pct = round(completed_cells / total_cells * 100, 1)

    mean_realism = round(sum(realism_scores) / len(realism_scores), 2) if realism_scores else 0.0
    mean_distinctiveness = round(sum(distinctiveness_scores) / len(distinctiveness_scores), 2) if distinctiveness_scores else 0.0

    return {
        "variants": variants_out,
        "stats": {
            "variants_generated": len(variants_out),
            "mean_realism": mean_realism,
            "mean_distinctiveness": mean_distinctiveness,
            "mean_critic_score": round((mean_realism + mean_distinctiveness) / 2, 2) if realism_scores else 0.0,
            "coverage_pct": coverage_pct,
            "total_transactions": total_transactions,
        },
    }


# ------------------------------------------------------------------
# GET /api/runs/{id}/trace/{variant_id}  — P2 stub
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/trace/{variant_id}")
def get_trace(run_id: str, variant_id: str) -> dict:
    _get_run(run_id)
    return {"variant_id": variant_id, "steps": [], "note": "trace not yet implemented"}


# ------------------------------------------------------------------
# GET /api/runs/{id}/dataset
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/dataset")
def get_dataset(run_id: str, page: int = 1, page_size: int = 100) -> dict:
    entry = _get_run(run_id)
    folder_path = entry["folder_path"][0]
    if not folder_path:
        return {"rows": [], "total": 0, "page": page, "page_size": page_size}

    csv_path = Path(folder_path) / "dataset.csv"
    if not csv_path.exists():
        return {"rows": [], "total": 0, "page": page, "page_size": page_size}

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    total = len(all_rows)
    start = (page - 1) * page_size
    end = start + page_size
    return {"rows": all_rows[start:end], "total": total, "page": page, "page_size": page_size}


# ------------------------------------------------------------------
# GET /api/runs/{id}/operations  — P2 stub
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/operations")
def get_operations(run_id: str) -> dict:
    _get_run(run_id)
    return {"cost_timeline": [], "errors": [], "note": "operations not yet implemented"}


# ------------------------------------------------------------------
# GET /api/runs/{id}/export/{format}
# ------------------------------------------------------------------
_EXPORT_FILES = {
    "csv": "dataset.csv",
    "json": "dataset.json",
    "graph": "graph_adjacency.json",
    "summary": "run_summary.json",
}


@app.get("/api/runs/{run_id}/export/{format}")
def export_file(run_id: str, format: str) -> FileResponse:
    entry = _get_run(run_id)
    folder_path = entry["folder_path"][0]

    if format not in _EXPORT_FILES:
        raise HTTPException(status_code=400, detail=f"Unknown format {format!r}. Use: {list(_EXPORT_FILES)}")

    if not folder_path:
        raise HTTPException(status_code=404, detail="Run output not ready yet")

    file_path = Path(folder_path) / _EXPORT_FILES[format]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"{_EXPORT_FILES[format]} not found")

    _mime = {
        "csv": "text/csv",
        "json": "application/json",
        "graph": "application/json",
        "summary": "application/json",
    }
    return FileResponse(
        path=str(file_path),
        filename=_EXPORT_FILES[format],
        media_type=_mime[format],
    )
