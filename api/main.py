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
from pipeline.run_state import AgentStatus, RunState, TraceEvent
from pipeline.runner import PipelineRunner
from .demo_runner import run_demo

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
    demo: bool = False
    instant: bool = False  # skip delays and write output files immediately
    max_parallel: int = 3
    critic_floor: float = 7.0


class ControlRequest(BaseModel):
    signal: str  # "run" | "pause" | "stop"


# ------------------------------------------------------------------
# GET /api/runs — list all runs
# ------------------------------------------------------------------
@app.get("/api/runs")
def list_runs() -> list:
    result = []
    for run_id, entry in _runs.items():
        rs: RunState = entry["run_state"]
        config = entry["config"]
        snap = rs.snapshot()
        result.append({
            "run_id": run_id,
            "fraud_description": config.fraud_description,
            "status": "complete" if snap["is_complete"] else snap["current_phase"],
            "variants_total": snap["variants_total"],
            "variants_completed": snap["variants_completed"],
            "is_complete": snap["is_complete"],
            "total_cost_usd": snap["total_cost_usd"],
            "elapsed_s": snap["elapsed_s"],
        })
    return result


# ------------------------------------------------------------------
# POST /api/runs — start a new pipeline run
# ------------------------------------------------------------------
@app.post("/api/runs")
def start_run(req: StartRunRequest) -> dict:
    run_state = RunState()
    approved_variants: list = []
    folder_path: list[str] = [""]

    config = RunConfig(
        fraud_description=req.fraud_description,
        variant_count=max(1, min(req.variant_count, 20)),
        demo_mode=req.demo,
        max_parallel=req.max_parallel,
        critic_floor=req.critic_floor,
    )

    if req.demo:
        # Demo mode: stream synthetic data without hitting the Claude API.
        # instant=True also writes all output files so dataset/export endpoints work.
        thread = threading.Thread(
            target=run_demo,
            args=(run_state, config.variant_count),
            kwargs={"instant": req.instant, "folder_path_out": folder_path},
            daemon=True,
        )
    else:
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
    # Issue 1: avoid "0/0" flash during startup — emit None until the pipeline
    # has set variants_total after the orchestration step.
    if snap["variants_total"] == 0 and not snap["is_complete"]:
        snap["variants_total"] = None
    return snap


# ------------------------------------------------------------------
# GET /api/runs/{id}/agents
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/agents")
def get_agents(run_id: str) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    with rs._lock:
        agents = [asdict(a) for a in rs.agent_slots.values()]
    return {"agents": agents}


# ------------------------------------------------------------------
# GET /api/runs/{id}/trace
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/trace")
def get_trace_events(
    run_id: str,
    variant_id: str | None = None,
    agent_id: str | None = None,
) -> dict:
    entry = _get_run(run_id)
    rs: RunState = entry["run_state"]
    with rs._lock:
        events = list(rs.trace_events)
    if variant_id is not None:
        events = [e for e in events if e.variant_id == variant_id]
    if agent_id is not None:
        events = [e for e in events if e.agent_id == agent_id]
    return {"events": [asdict(e) for e in events]}


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
    normalized_dims = []
    for dim in dimensions:
        if isinstance(dim, dict):
            d = dict(dim)
            d["values"] = d.get("example_values", [])
            normalized_dims.append(d)
        else:
            normalized_dims.append(dim)
    return {"dimensions": normalized_dims, "cells": cells}


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
        persona_map: dict[str, str] = {}
        for p in rs.personas:
            try:
                pd = p.model_dump()
            except AttributeError:
                pd = vars(p) if hasattr(p, "__dict__") else {}
            persona_map[pd.get("persona_id", "")] = pd.get("name", "")

    variants_out = []
    total_transactions = 0
    realism_scores = []
    distinctiveness_scores = []

    for sv in scored:
        try:
            d = sv.model_dump()
        except AttributeError:
            d = vars(sv) if hasattr(sv, "__dict__") else {}

        # Inject persona_name from lookup
        d["persona_name"] = persona_map.get(d.get("persona_id", ""), d.get("persona_id", ""))

        # Derive accounts list from transactions
        seen: dict[str, str] = {}
        for txn in d.get("transactions", []):
            role = txn.get("fraud_role", "") if isinstance(txn, dict) else getattr(txn, "fraud_role", "")
            sender = txn.get("sender_account_id", "") if isinstance(txn, dict) else getattr(txn, "sender_account_id", "")
            receiver = txn.get("receiver_account_id", "") if isinstance(txn, dict) else getattr(txn, "receiver_account_id", "")
            if role == "placement":
                if sender: seen[sender] = "placement"
                if receiver: seen.setdefault(receiver, "mule")
            elif role == "extraction":
                if sender: seen.setdefault(sender, "mule")
                if receiver: seen[receiver] = "extraction"
            elif role.startswith("hop_"):
                if sender: seen.setdefault(sender, "mule")
                if receiver: seen.setdefault(receiver, "mule")
            elif role == "cover_activity":
                if sender: seen.setdefault(sender, "cover")
        d["accounts"] = [{"account_id": k, "role": v} for k, v in seen.items()]

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
def get_dataset(
    run_id: str,
    page: int = 1,
    page_size: int = 100,
    persona: str | None = None,
    role: str | None = None,
    is_fraud: bool | None = None,
    min_score: float | None = None,
    variant_id: str | None = None,
) -> dict:
    entry = _get_run(run_id)
    folder_path = entry["folder_path"][0]
    # Issue 3: signal to the frontend that data will arrive after completion.
    if not folder_path:
        return {"rows": [], "total": 0, "page": page, "page_size": page_size, "available": False}

    csv_path = Path(folder_path) / "dataset.csv"
    if not csv_path.exists():
        return {"rows": [], "total": 0, "page": page, "page_size": page_size, "available": False}

    import pandas as pd

    # Issue 2: cache parsed CSV rows on the run entry so repeated paginated
    # requests do not re-read and re-parse the file from disk each time.
    # Invalidate the cache when folder_path changes (run just completed).
    cached_folder = entry.get("dataset_cache_folder", None)
    if cached_folder != folder_path or "dataset_cache" not in entry:
        raw_df = pd.read_csv(csv_path, dtype=str)
        entry["dataset_cache"] = raw_df.to_dict(orient="records")
        entry["dataset_cache_folder"] = folder_path

    all_rows = entry["dataset_cache"]
    df = pd.DataFrame(all_rows)

    if persona is not None:
        df = df[df["persona_name"] == persona]
    if role is not None:
        df = df[df["fraud_role"] == role]
    if is_fraud is not None:
        target = "True" if is_fraud else "False"
        df = df[df["is_fraud"] == target]
    if min_score is not None:
        df = df[pd.to_numeric(df["critic_score"], errors="coerce").fillna(0) >= min_score]
    if variant_id is not None:
        df = df[df["variant_id"] == variant_id]

    total = len(df)
    start = (page - 1) * page_size
    page_df = df.iloc[start : start + page_size]
    rows = page_df.to_dict(orient="records")

    return {"rows": rows, "total": total, "page": page, "page_size": page_size, "available": True}


# ------------------------------------------------------------------
# GET /api/runs/{id}/operations  — P2 stub
# ------------------------------------------------------------------
@app.get("/api/runs/{run_id}/operations")
def get_operations(run_id: str) -> dict:
    _get_run(run_id)
    return {"cost_timeline": [], "errors": [], "note": "operations not yet implemented"}


# ------------------------------------------------------------------
# GET /api/runs/{id}/export — manifest
# ------------------------------------------------------------------
_EXPORT_MANIFEST = [
    {"filename": "config.json",      "format": "config",   "description": "Run configuration snapshot",                "count_key": None},
    {"filename": "personas.json",    "format": "personas", "description": "Full persona profiles",                     "count_key": "personas"},
    {"filename": "variants.json",    "format": "variants", "description": "Complete variant data with metadata",        "count_key": "variants"},
    {"filename": "dataset.csv",      "format": "csv",      "description": "Flat tabular dataset for ML training",       "count_key": "csv"},
    {"filename": "dataset.json",     "format": "json",     "description": "Nested dataset with variant metadata",       "count_key": None},
    {"filename": "run_summary.json", "format": "summary",  "description": "Aggregate stats and quality metrics",        "count_key": None},
]

@app.get("/api/runs/{run_id}/export")
def get_export_manifest(run_id: str) -> list:
    entry = _get_run(run_id)
    folder_path = entry["folder_path"][0]
    result = []
    for item in _EXPORT_MANIFEST:
        file_path = Path(folder_path) / item["filename"] if folder_path else None
        size_bytes = file_path.stat().st_size if file_path and file_path.exists() else None
        record_count = None
        if file_path and file_path.exists():
            if item["count_key"] == "csv":
                # count lines minus header
                with open(file_path) as f:
                    record_count = max(0, sum(1 for _ in f) - 1)
            elif item["count_key"] in ("personas", "variants"):
                import json as _json
                try:
                    with open(file_path) as f:
                        data = _json.load(f)
                    record_count = len(data) if isinstance(data, list) else None
                except Exception:
                    pass
        result.append({
            "filename": item["filename"],
            "format": item["format"],
            "description": item["description"],
            "size_bytes": size_bytes,
            "record_count": record_count,
            "available": file_path.exists() if file_path else False,
        })
    return result


# ------------------------------------------------------------------
# GET /api/runs/{id}/export/{format}
# ------------------------------------------------------------------
_EXPORT_FILES = {
    "csv": "dataset.csv",
    "json": "dataset.json",
    "graph": "graph_adjacency.json",
    "summary": "run_summary.json",
    "config": "config.json",
    "personas": "personas.json",
    "variants": "variants.json",
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
        "config": "application/json",
        "personas": "application/json",
        "variants": "application/json",
    }
    return FileResponse(
        path=str(file_path),
        filename=_EXPORT_FILES[format],
        media_type=_mime[format],
    )
