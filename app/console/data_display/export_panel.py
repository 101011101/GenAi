"""
Export panel for the fraud data generation console.

Provides download buttons for CSV, JSON, and run summary.
No LLM calls or agent imports.
"""
from __future__ import annotations

import io
import json
import os
from typing import Any

import streamlit as st

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _record_to_dict(record: Any) -> dict:
    if isinstance(record, dict):
        return dict(record)
    if hasattr(record, "model_dump"):
        return record.model_dump()
    if hasattr(record, "__dict__"):
        return dict(record.__dict__)
    return {}


def _variant_to_dict(variant: Any) -> dict:
    if isinstance(variant, dict):
        return dict(variant)
    if hasattr(variant, "model_dump"):
        d = variant.model_dump()
    elif hasattr(variant, "__dict__"):
        d = dict(variant.__dict__)
    else:
        return {}
    # Ensure transactions are serialisable
    txns = d.get("transactions", [])
    serialised_txns = []
    for t in txns:
        if isinstance(t, dict):
            serialised_txns.append(t)
        elif hasattr(t, "model_dump"):
            serialised_txns.append(t.model_dump())
        elif hasattr(t, "__dict__"):
            serialised_txns.append(dict(t.__dict__))
        else:
            serialised_txns.append(str(t))
    d["transactions"] = serialised_txns
    return d


def _bytes_label(n_bytes: int) -> str:
    """Human-readable file size."""
    if n_bytes < 1024:
        return f"{n_bytes} B"
    elif n_bytes < 1024 ** 2:
        return f"{n_bytes / 1024:.1f} KB"
    else:
        return f"{n_bytes / 1024 ** 2:.1f} MB"


# ---------------------------------------------------------------------------
# Public render function
# ---------------------------------------------------------------------------

def render_export_panel(
    run_folder: str | None,
    records: list | None,
    variants: list | None,
) -> None:
    """
    Render the export panel with download buttons.

    Parameters
    ----------
    run_folder : str | None
        Absolute path to the run output folder. Used to read run_summary.json.
    records : list | None
        List of OutputRecord objects or dicts for CSV export.
    variants : list | None
        List of ScoredVariant / RawVariant objects or dicts for JSON export.
    """
    st.markdown("**Export**")

    records = records or []
    variants = variants or []

    # --- CSV download ---
    st.markdown("**Download CSV** — full dataset, one row per transaction")

    if _PANDAS_AVAILABLE and records:
        rows = [_record_to_dict(r) for r in records]
        df = pd.DataFrame(rows)
        csv_bytes = df.to_csv(index=False).encode("utf-8")
        csv_size = _bytes_label(len(csv_bytes))
        col_csv, col_csv_info = st.columns([3, 1])
        with col_csv:
            st.download_button(
                label="Download CSV",
                data=csv_bytes,
                file_name="fraud_variants.csv",
                mime="text/csv",
                key="export_csv_btn",
            )
        with col_csv_info:
            st.caption(csv_size)
    elif not _PANDAS_AVAILABLE:
        st.warning("Install pandas to enable CSV export: `pip install pandas`")
    else:
        st.caption("No records to export.")

    # --- JSON download ---
    st.markdown("**Download JSON** — structured output with variant metadata")

    if variants:
        payload = {
            "variants": [_variant_to_dict(v) for v in variants],
        }
        json_str = json.dumps(payload, indent=2, default=str)
        json_bytes = json_str.encode("utf-8")
        json_size = _bytes_label(len(json_bytes))
        col_json, col_json_info = st.columns([3, 1])
        with col_json:
            st.download_button(
                label="Download JSON",
                data=json_bytes,
                file_name="fraud_variants.json",
                mime="application/json",
                key="export_json_btn",
            )
        with col_json_info:
            st.caption(json_size)
    else:
        st.caption("No variants to export.")

    # --- Run summary download ---
    st.markdown("**Download Run Summary** — run_summary.json")

    summary_bytes: bytes | None = None
    if run_folder:
        summary_path = os.path.join(run_folder, "run_summary.json")
        if os.path.isfile(summary_path):
            try:
                with open(summary_path, "rb") as f:
                    summary_bytes = f.read()
            except OSError:
                summary_bytes = None

    if summary_bytes:
        summary_size = _bytes_label(len(summary_bytes))
        col_sum, col_sum_info = st.columns([3, 1])
        with col_sum:
            st.download_button(
                label="Download Run Summary",
                data=summary_bytes,
                file_name="run_summary.json",
                mime="application/json",
                key="export_summary_btn",
            )
        with col_sum_info:
            st.caption(summary_size)
    else:
        # Generate a minimal summary on the fly from available data
        minimal_summary: dict = {
            "variants_count": len(variants),
            "records_count": len(records),
            "run_folder": run_folder or "unknown",
        }
        minimal_bytes = json.dumps(minimal_summary, indent=2).encode("utf-8")
        minimal_size = _bytes_label(len(minimal_bytes))
        col_sum, col_sum_info = st.columns([3, 1])
        with col_sum:
            st.download_button(
                label="Download Run Summary",
                data=minimal_bytes,
                file_name="run_summary.json",
                mime="application/json",
                key="export_summary_minimal_btn",
                help="Full summary not found — downloading a minimal version.",
            )
        with col_sum_info:
            st.caption(minimal_size)

    # --- Send to pipeline (always disabled) ---
    st.markdown("**Send to Pipeline**")
    st.button(
        "Send to pipeline",
        disabled=True,
        key="export_pipeline_btn",
        help=(
            "Connect your ML pipeline to enable this — "
            "ask your platform team about the API integration."
        ),
    )
    st.caption(
        "Disabled — connect your ML pipeline to enable. "
        "Ask your platform team about the API integration."
    )
