"""
Dataset browser for the fraud data generation console.

Filterable dataframe view of all output records.
No LLM calls or agent imports.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

try:
    import pandas as pd
    _PANDAS_AVAILABLE = True
except ImportError:
    _PANDAS_AVAILABLE = False


# Default columns always shown
_DEFAULT_COLUMNS = [
    "variant_id",
    "persona_name",
    "timestamp",
    "amount",
    "fraud_role",
    "is_fraud",
    "critic_score",
]

# Extra columns revealed by "Show variant metadata" toggle
_METADATA_COLUMNS = [
    "variant_parameters",
    "critic_scores",
]


def _record_to_dict(record: Any) -> dict:
    """Convert an OutputRecord object or dict to a flat dict."""
    if isinstance(record, dict):
        base = dict(record)
    elif hasattr(record, "model_dump"):
        base = record.model_dump()
    elif hasattr(record, "__dict__"):
        base = dict(record.__dict__)
    else:
        return {}

    # Flatten critic_scores into a single score field for display
    critic = base.get("critic_scores", {})
    if isinstance(critic, dict):
        base["critic_score"] = critic.get("realism", None)
    else:
        base["critic_score"] = None

    return base


def render_dataset_browser(records: list | None) -> None:
    """
    Render a filterable dataframe view of all output records.

    Parameters
    ----------
    records : list | None
        List of OutputRecord objects or dicts. Handles None/empty gracefully.
    """
    st.markdown("**Dataset Browser**")

    if not _PANDAS_AVAILABLE:
        st.warning("Install pandas for the dataset browser: `pip install pandas`")
        return

    if not records:
        st.caption("No records yet. Run the pipeline to generate data.")
        return

    # Build DataFrame
    rows = [_record_to_dict(r) for r in records]
    df = pd.DataFrame(rows)

    if df.empty:
        st.caption("No records to display.")
        return

    # Ensure expected columns exist (add with None if missing)
    for col in _DEFAULT_COLUMNS + _METADATA_COLUMNS:
        if col not in df.columns:
            df[col] = None

    # --- Filters ---
    filter_col1, filter_col2, filter_col3, filter_col4 = st.columns(4)

    with filter_col1:
        all_personas = sorted(df["persona_name"].dropna().unique().tolist())
        selected_personas = st.multiselect(
            "Persona",
            options=all_personas,
            default=[],
            key="browser_persona_filter",
        )

    with filter_col2:
        min_score = float(df["critic_score"].dropna().min()) if df["critic_score"].notna().any() else 0.0
        max_score = float(df["critic_score"].dropna().max()) if df["critic_score"].notna().any() else 10.0
        min_score = min(min_score, max_score)
        score_range = st.slider(
            "Critic score range",
            min_value=0.0,
            max_value=10.0,
            value=(min_score, max_score),
            step=0.1,
            key="browser_score_filter",
        )

    with filter_col3:
        all_roles = sorted(df["fraud_role"].dropna().unique().tolist())
        selected_roles = st.multiselect(
            "Fraud role",
            options=all_roles,
            default=[],
            key="browser_role_filter",
        )

    with filter_col4:
        fraud_filter = st.selectbox(
            "is_fraud",
            options=["All", "Fraud only", "Legit only"],
            key="browser_fraud_filter",
        )

    # Apply filters
    filtered = df.copy()

    if selected_personas:
        filtered = filtered[filtered["persona_name"].isin(selected_personas)]

    if df["critic_score"].notna().any():
        filtered = filtered[
            (filtered["critic_score"].isna())
            | (
                (filtered["critic_score"] >= score_range[0])
                & (filtered["critic_score"] <= score_range[1])
            )
        ]

    if selected_roles:
        filtered = filtered[filtered["fraud_role"].isin(selected_roles)]

    if fraud_filter == "Fraud only":
        filtered = filtered[filtered["is_fraud"] == True]
    elif fraud_filter == "Legit only":
        filtered = filtered[filtered["is_fraud"] == False]

    st.caption(f"Showing {len(filtered):,} of {len(df):,} transactions")

    # --- Metadata toggle ---
    show_metadata = st.toggle(
        "Show variant metadata",
        value=False,
        key="browser_metadata_toggle",
        help="Adds variant_parameters and critic_scores columns.",
    )

    display_cols = [c for c in _DEFAULT_COLUMNS if c in filtered.columns]
    if show_metadata:
        display_cols += [c for c in _METADATA_COLUMNS if c in filtered.columns]

    st.dataframe(
        filtered[display_cols],
        use_container_width=True,
        hide_index=True,
    )
