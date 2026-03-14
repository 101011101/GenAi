"""
Stats panel for the fraud data generation console.

Renders large metric cards readable from across the room.
No LLM calls or agent imports.
"""
from __future__ import annotations

from typing import Any

import streamlit as st


def _safe_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def render_stats_panel(run_state: Any, variants: list | None) -> None:
    """
    Render the run summary stats panel with large metric cards.

    Parameters
    ----------
    run_state : RunState | dict | None
        Used for coverage saturation, cost, and timestamp.
    variants : list | None
        List of ScoredVariant / RawVariant objects or dicts from the completed run.
    """
    variants = variants or []

    # --- Derive metrics from variants ---
    passed_variants = [v for v in variants if _variant_passed(v)]
    variants_generated = len(passed_variants)

    realism_scores = [_get_realism_score(v) for v in passed_variants]
    mean_score = _safe_mean(realism_scores)
    mean_score_str = f"{mean_score:.1f} / 10" if realism_scores else "—"

    persona_ids = {_get_persona_id(v) for v in passed_variants if _get_persona_id(v)}
    persona_count = len(persona_ids)

    total_transactions = sum(_get_transaction_count(v) for v in passed_variants)

    # Coverage saturation from run_state
    coverage_pct = _get_coverage_pct(run_state, variants)
    coverage_str = f"{coverage_pct}%" if coverage_pct is not None else "—"

    # --- Render five metric columns ---
    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("Variants Generated", variants_generated)

    with col2:
        st.metric("Mean Critic Score", mean_score_str)

    with col3:
        st.metric("Coverage Saturation", coverage_str)

    with col4:
        st.metric("Personas", persona_count)

    with col5:
        st.metric("Total Transactions", f"{total_transactions:,}")

    # --- Caption: timestamp + cost ---
    timestamp_str = _get_run_timestamp(run_state)
    cost_str = _get_cost_str(run_state)
    caption_parts = []
    if timestamp_str:
        caption_parts.append(f"Run completed: {timestamp_str}")
    if cost_str:
        caption_parts.append(f"Est. cost: {cost_str}")
    if caption_parts:
        st.caption("  ·  ".join(caption_parts))


# ---------------------------------------------------------------------------
# Extraction helpers — handle both pydantic objects and dicts defensively
# ---------------------------------------------------------------------------

def _variant_passed(v: Any) -> bool:
    if isinstance(v, dict):
        # Check critic_scores.passed or top-level passed field
        critic = v.get("critic_scores", {})
        if isinstance(critic, dict):
            return bool(critic.get("passed", True))
        return bool(v.get("passed", True))
    passed = getattr(v, "passed", None)
    if passed is not None:
        return bool(passed)
    # ScoredVariant has a .passed field; RawVariant does not — treat as passed
    return True


def _get_realism_score(v: Any) -> float:
    if isinstance(v, dict):
        critic = v.get("critic_scores", {})
        if isinstance(critic, dict):
            return float(critic.get("realism", 0.0))
        return float(v.get("realism_score", 0.0))
    return float(getattr(v, "realism_score", 0.0))


def _get_persona_id(v: Any) -> str:
    if isinstance(v, dict):
        return str(v.get("persona_id", ""))
    return str(getattr(v, "persona_id", ""))


def _get_transaction_count(v: Any) -> int:
    if isinstance(v, dict):
        return len(v.get("transactions", []))
    return len(getattr(v, "transactions", []) or [])


def _get_coverage_pct(run_state: Any, variants: list) -> int | None:
    """Try to derive coverage percentage from run_state or variant count heuristic."""
    if run_state is None:
        return None
    if isinstance(run_state, dict):
        sat = run_state.get("coverage_saturation")
        if sat is not None:
            return int(sat * 100) if sat <= 1.0 else int(sat)
        # Heuristic: completed / total
        total = run_state.get("variants_total", 0)
        completed = run_state.get("variants_completed", 0)
        if total > 0:
            return int(completed / total * 100)
        return None
    sat = getattr(run_state, "coverage_saturation", None)
    if sat is not None:
        return int(sat * 100) if sat <= 1.0 else int(sat)
    total = getattr(run_state, "variants_total", 0)
    completed = getattr(run_state, "variants_completed", 0)
    if total > 0:
        return int(completed / total * 100)
    return None


def _get_run_timestamp(run_state: Any) -> str:
    if run_state is None:
        return ""
    if isinstance(run_state, dict):
        return str(run_state.get("completed_at", run_state.get("run_timestamp", "")))
    return str(
        getattr(run_state, "completed_at", None)
        or getattr(run_state, "run_timestamp", None)
        or ""
    )


def _get_cost_str(run_state: Any) -> str:
    if run_state is None:
        return ""
    if isinstance(run_state, dict):
        cost = run_state.get("total_cost_usd")
    else:
        cost = getattr(run_state, "total_cost_usd", None)
    if cost is None:
        return ""
    return f"${float(cost):.2f}"
