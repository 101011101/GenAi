"""
app.py — Streamlit entry point for FraudGen.

Wires the console UI components to the backend pipeline.
No business logic, no LLM calls — only coordination.
"""
from __future__ import annotations

import atexit
import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")
import os
import threading
import time

# ---------------------------------------------------------------------------
# Page config — MUST be the first Streamlit call
# ---------------------------------------------------------------------------
import streamlit as st

st.set_page_config(
    page_title="FraudGen — Synthetic Fraud Data Generator",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Project root on sys.path so all imports resolve regardless of cwd
# ---------------------------------------------------------------------------
_ROOT = os.path.dirname(os.path.abspath(__file__))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

# ---------------------------------------------------------------------------
# Console components
# ---------------------------------------------------------------------------
from console.input_panel import render_input_panel
from console.orchestrator_controls import render_orchestrator_controls
from console.monitoring_panel import render_monitoring_panel
from console.data_display.stats_panel import render_stats_panel
from console.data_display.network_graph_view import render_network_graphs
from console.data_display.coverage_matrix_view import render_coverage_matrix
from console.data_display.dataset_browser import render_dataset_browser
from console.data_display.export_panel import render_export_panel

# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
from models.run_config import RunConfig
from pipeline.run_state import RunState
from pipeline.runner import PipelineRunner
from pipeline.output_handler import OutputHandler


# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

st.session_state.setdefault("phase", "input")
st.session_state.setdefault("run_state", None)
st.session_state.setdefault("run_folder", None)
st.session_state.setdefault("personas", [])
st.session_state.setdefault("approved_variants", [])
st.session_state.setdefault("demo_mode", False)
st.session_state.setdefault("run_thread", None)

# ---------------------------------------------------------------------------
# Demo mode detection via query params
# ---------------------------------------------------------------------------
params = st.query_params
if params.get("demo") == "true":
    st.session_state.demo_mode = True


# ---------------------------------------------------------------------------
# Helper: start a run in a background thread
# ---------------------------------------------------------------------------

def _start_run(config: RunConfig) -> None:
    """Initialise shared state, spin up the background runner thread, rerun."""
    run_state = RunState()
    personas_out: list = []
    approved_variants: list = []

    st.session_state.run_state = run_state
    st.session_state.personas = personas_out
    st.session_state.approved_variants = approved_variants
    st.session_state.phase = "running"

    runner = PipelineRunner()
    thread = threading.Thread(
        target=asyncio.run,
        args=(
            runner.run(
                config,
                run_state,
                personas_out=personas_out,
                approved_variants_out=approved_variants,
            ),
        ),
        daemon=False,
    )
    thread.start()
    st.session_state.run_thread = thread

    # On process exit, signal the pipeline to stop and wait up to 10s for a
    # clean shutdown so in-flight file writes can complete.
    def _shutdown() -> None:
        run_state.set_control("stop")
        thread.join(timeout=10)

    atexit.register(_shutdown)

    st.rerun()


# ---------------------------------------------------------------------------
# Sidebar — always visible
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("## FraudGen")
    st.caption("v0.1.0 — hackathon build")
    st.caption("Powered by Claude")
    st.divider()

    phase = st.session_state.phase
    run_state: RunState | None = st.session_state.run_state

    if phase == "running" and run_state is not None:
        snap = run_state.snapshot()
        st.markdown("**Run status**")
        st.caption(
            f"{snap['variants_completed']} / {snap['variants_total']} variants  ·  "
            f"Phase: {snap['current_phase']}"
        )
        st.progress(
            snap["variants_completed"] / max(snap["variants_total"], 1)
        )

    st.divider()
    st.caption("PRD docs")
    st.caption("PRD/01_problem_and_solution.md")
    st.caption("PRD/05_architecture_draft.md")
    st.caption("PRD/06_api_and_console_draft.md")
    st.caption("PRD/07_user_flow_and_console.md")


# ---------------------------------------------------------------------------
# Main content — wrapped in try/except for graceful error handling
# ---------------------------------------------------------------------------

try:
    phase = st.session_state.phase

    # -----------------------------------------------------------------------
    # PHASE: input
    # -----------------------------------------------------------------------
    if phase == "input":
        title_col, demo_col = st.columns([4, 1])

        with title_col:
            st.title("FraudGen")
            st.caption("Synthetic fraud variant data for ML training")

        with demo_col:
            st.markdown("")  # vertical spacer to align button
            if st.button("▶ Run Demo", use_container_width=True, type="primary"):
                st.session_state.demo_mode = True
                # Immediately start demo — skip input panel
                demo_config = RunConfig(
                    fraud_description=(
                        "Layered 3-hop mule account network, burst withdrawal pattern, "
                        "domestic transfers only. Criminal organization uses recruited "
                        "account holders to move stolen funds rapidly before extraction."
                    ),
                    variant_count=12,
                    fidelity_level=3,
                    max_parallel=5,
                    demo_mode=True,
                )
                _start_run(demo_config)

        if st.session_state.demo_mode:
            st.info(
                "Demo mode — running a pre-configured 12-variant mule network demo"
            )
            # If demo_mode was set but _start_run hasn't fired (e.g. query param path),
            # auto-start on next render cycle.
            if st.session_state.phase == "input":
                demo_config = RunConfig(
                    fraud_description=(
                        "Layered 3-hop mule account network, burst withdrawal pattern, "
                        "domestic transfers only. Criminal organization uses recruited "
                        "account holders to move stolen funds rapidly before extraction."
                    ),
                    variant_count=12,
                    fidelity_level=3,
                    max_parallel=5,
                    demo_mode=True,
                )
                _start_run(demo_config)

        # Render input panel — returns RunConfig on submit, None otherwise
        base_config = render_input_panel()

        if base_config is not None:
            # Merge orchestrator control overrides
            overrides = render_orchestrator_controls()
            if overrides:
                try:
                    base_config = base_config.model_copy(update=overrides)
                except Exception as exc:
                    st.error(f"Configuration override error: {exc}")
                    base_config = None

            if base_config is not None:
                _start_run(base_config)
        else:
            # Still render the controls panel (collapsed) so it's accessible
            render_orchestrator_controls()

    # -----------------------------------------------------------------------
    # PHASE: running
    # -----------------------------------------------------------------------
    elif phase == "running":
        run_state = st.session_state.run_state

        st.subheader("Generating variants...")

        action = render_monitoring_panel(run_state)

        # Handle control buttons
        if action is not None and run_state is not None:
            action_lower = action.lower()
            if action_lower == "pause":
                run_state.set_control("pause")
            elif action_lower == "resume":
                run_state.set_control("run")
            elif action_lower == "stop":
                run_state.set_control("stop")

        # Check for run completion
        if run_state is not None and run_state.is_complete:
            # Retrieve the run folder from the thread result if possible
            thread: threading.Thread | None = st.session_state.run_thread
            # The folder path is returned by runner.run() but asyncio.run() returns
            # it only if we capture it.  We read it from the output directory by
            # finding the most recent run folder, which OutputHandler just created.
            run_folder = st.session_state.run_folder
            if run_folder is None:
                # Derive from the output/runs directory — most recently modified folder
                runs_dir = os.path.join(_ROOT, "output", "runs")
                if os.path.isdir(runs_dir):
                    try:
                        folders = [
                            os.path.join(runs_dir, d)
                            for d in os.listdir(runs_dir)
                            if os.path.isdir(os.path.join(runs_dir, d))
                        ]
                        if folders:
                            run_folder = max(folders, key=os.path.getmtime)
                    except OSError:
                        run_folder = None

            st.session_state.run_folder = run_folder
            st.session_state.phase = "results"
            st.rerun()
        else:
            # Poll every second while the run is active
            placeholder = st.empty()
            with placeholder:
                time.sleep(1)
            st.rerun()

    # -----------------------------------------------------------------------
    # PHASE: results
    # -----------------------------------------------------------------------
    elif phase == "results":
        run_state = st.session_state.run_state
        run_folder = st.session_state.run_folder
        approved_variants = st.session_state.approved_variants

        # "Start New Run" button at the top
        top_col, btn_col = st.columns([4, 1])
        with top_col:
            st.subheader("Run Complete")
        with btn_col:
            if st.button("Start New Run", use_container_width=True):
                # Clear run-specific session state and go back to input
                for key in ("run_state", "run_folder", "personas", "approved_variants", "run_thread", "demo_mode"):
                    st.session_state[key] = (
                        [] if key in ("personas", "approved_variants") else
                        False if key == "demo_mode" else
                        None
                    )
                st.session_state.phase = "input"
                st.rerun()

        if st.session_state.demo_mode:
            st.success("Demo complete! Click 'Start New Run' to try with your own fraud type.")

        # --- Build output records from approved variants ---
        output_handler = OutputHandler()
        records: list = []
        for variant in approved_variants:
            try:
                records.extend(output_handler._variant_to_output_records(variant))
            except Exception:
                pass

        # 1. Stats panel
        render_stats_panel(run_state, approved_variants)

        st.divider()

        # 2. Network graphs
        with st.expander("Network Graph View", expanded=True):
            render_network_graphs(approved_variants)

        st.divider()

        # 3. Coverage matrix
        # Try to load matrix display dict from the run folder's variants.json,
        # or fall back to a minimal representation derived from run_state.
        matrix_display_dict: dict | None = None
        if run_folder:
            variants_json_path = os.path.join(run_folder, "variants.json")
            if os.path.isfile(variants_json_path):
                try:
                    import json as _json
                    with open(variants_json_path, "r", encoding="utf-8") as f:
                        _variants_data = _json.load(f)
                    # Build a minimal matrix display dict from the saved variants
                    if isinstance(_variants_data, list) and _variants_data:
                        cells = []
                        for v in _variants_data:
                            params = v.get("variant_parameters", {}) or {}
                            cells.append({
                                "cell_id": v.get("variant_id", "?"),
                                "dimension_values": {
                                    "hop_count": str(params.get("hop_count", "?")),
                                    "timing": str(params.get("timing_pattern", params.get("timing", "?"))),
                                },
                                "status": "completed",
                                "variant_count": 1,
                            })
                        matrix_display_dict = {
                            "dimensions": [
                                {"name": "hop_count", "values": sorted({c["dimension_values"]["hop_count"] for c in cells})},
                                {"name": "timing", "values": sorted({c["dimension_values"]["timing"] for c in cells})},
                            ],
                            "cells": cells,
                        }
                except Exception:
                    matrix_display_dict = None

        render_coverage_matrix(matrix_display_dict)

        st.divider()

        # 4. Dataset browser
        render_dataset_browser(records)

        st.divider()

        # 5. Export panel
        render_export_panel(run_folder, records, approved_variants)

except Exception as _exc:
    st.error(f"Unexpected error: {_exc}")
    if st.button("Reset", key="error_reset_btn"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
