"""
Live monitoring panel for the fraud data generation console.

Renders progress, variant feed, stats, and pipeline controls.
Reads from a RunState object or snapshot dict — no LLM calls or agent imports.
"""
from __future__ import annotations

from typing import Any

import streamlit as st


# ---------------------------------------------------------------------------
# Score color helpers
# ---------------------------------------------------------------------------

def _score_color_emoji(score: float) -> str:
    """Return a colored circle emoji based on critic score."""
    if score >= 7.0:
        return "🟢"
    elif score >= 5.0:
        return "🟡"
    else:
        return "🔴"


def _score_color_hex(score: float) -> str:
    if score >= 7.0:
        return "#2ECC71"
    elif score >= 5.0:
        return "#F39C12"
    else:
        return "#E74C3C"


# ---------------------------------------------------------------------------
# Main render function
# ---------------------------------------------------------------------------

def render_monitoring_panel(run_state: Any) -> str | None:
    """
    Render the live monitoring panel.

    Parameters
    ----------
    run_state : RunState instance or snapshot dict.
        The panel handles both types gracefully.

    Returns
    -------
    str | None
        The name of the control button clicked ("Pause", "Resume", "Stop"),
        or None if no button was clicked this render cycle.
    """
    if run_state is None:
        st.info("No active run. Start a run to see live monitoring.")
        return None

    # Normalise: accept both RunState objects and plain dicts
    if isinstance(run_state, dict):
        snap = run_state
        variant_log = snap.get("variant_log", [])
        errors = snap.get("errors", [])
        event_log = snap.get("event_log", [])
    else:
        snap = run_state.snapshot()
        variant_log = getattr(run_state, "variant_log", [])
        errors = getattr(run_state, "errors", [])
        event_log = getattr(run_state, "event_log", [])

    variants_completed = snap.get("variants_completed", 0)
    variants_total = max(snap.get("variants_total", 1), 1)
    current_phase = snap.get("current_phase", "idle")
    active_agents = snap.get("active_agent_count", 0)
    revisions = snap.get("revisions_count", 0)
    rejections = snap.get("rejections_count", 0)
    total_cost = snap.get("total_cost_usd", 0.0)

    # --- Progress bar ---
    progress_frac = variants_completed / variants_total
    st.progress(progress_frac)
    st.caption(
        f"Phase: {current_phase}  ·  "
        f"{variants_completed} / {variants_total} variants complete  ·  "
        f"{int(progress_frac * 100)}%"
    )

    # --- Main two-column layout ---
    col_feed, col_stats = st.columns([2, 1])

    # ---- Left: variant feed ----
    with col_feed:
        st.markdown("**Variant Feed** (newest first)")

        recent_log = list(reversed(variant_log[-20:])) if variant_log else []

        if not recent_log:
            st.caption("Waiting for first variant to complete...")
        else:
            feed_container = st.container()
            with feed_container:
                for entry in recent_log:
                    # Support both VariantSummary dataclass and dict
                    if isinstance(entry, dict):
                        vid = entry.get("variant_id", "?")
                        persona = entry.get("persona_name", "Unknown")
                        params = entry.get("parameters_summary", "")
                        score = float(entry.get("critic_score", 0.0))
                        status = entry.get("status", "approved")
                        completed_at = entry.get("completed_at", "")
                    else:
                        vid = getattr(entry, "variant_id", "?")
                        persona = getattr(entry, "persona_name", "Unknown")
                        params = getattr(entry, "parameters_summary", "")
                        score = float(getattr(entry, "critic_score", 0.0))
                        status = getattr(entry, "status", "approved")
                        completed_at = getattr(entry, "completed_at", "")

                    is_rejected = status == "rejected"
                    color = _score_color_hex(score)
                    circle = _score_color_emoji(score)

                    border_color = "#E74C3C" if is_rejected else "#2C3E50"
                    rejected_badge = (
                        ' <span style="background:#E74C3C;color:white;padding:1px 6px;'
                        'border-radius:3px;font-size:0.7em;">REJECTED</span>'
                        if is_rejected
                        else ""
                    )

                    st.markdown(
                        f"""
                        <div style="
                            border: 1px solid {border_color};
                            border-radius: 6px;
                            padding: 8px 12px;
                            margin-bottom: 6px;
                            background-color: #1A1F2E;
                        ">
                            <div style="display:flex;justify-content:space-between;align-items:center;">
                                <strong>{vid}</strong> — {persona}{rejected_badge}
                            </div>
                            <div style="color:#AAAAAA;font-size:0.85em;">{params}</div>
                            <div>
                                {circle}
                                <span style="color:{color};font-weight:bold;">{score:.1f}</span>
                                <span style="color:#666;font-size:0.8em;margin-left:8px;">{completed_at}</span>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

    # ---- Right: stats column ----
    with col_stats:
        st.markdown("**Stats**")
        st.metric("Active Agents", active_agents)
        st.metric("Completed", variants_completed)
        st.metric("Revisions", revisions)
        st.metric("Rejections", rejections)
        est_cost_display = f"${total_cost:.2f}"
        st.metric("Est. Cost", est_cost_display)

    # --- Cost caption ---
    st.caption(f"Est. cost so far: ${total_cost:.2f}")

    # --- Agent activity log ---
    if event_log:
        with st.expander("Agent Activity Log", expanded=True):
            recent_events = list(reversed(event_log[-30:]))
            log_text = "\n".join(recent_events)
            st.code(log_text, language=None)

    # --- Errors ---
    if errors:
        recent_errors = errors[-3:]
        for err in recent_errors:
            st.error(str(err))

    st.divider()

    # --- Pause / Resume / Stop controls ---
    if "is_paused" not in st.session_state:
        st.session_state.is_paused = False

    btn_col1, btn_col2, btn_col3 = st.columns(3)
    clicked_action: str | None = None

    with btn_col1:
        pause_label = "Resume" if st.session_state.is_paused else "Pause"
        if st.button(pause_label, use_container_width=True, key="pause_resume_btn"):
            st.session_state.is_paused = not st.session_state.is_paused
            # After toggling: is_paused=True means we just paused → send "pause"
            clicked_action = "pause" if st.session_state.is_paused else "resume"

    with btn_col2:
        # Resume is a no-op slot when not paused (grayed via disabled)
        st.button(
            "Resume",
            disabled=not st.session_state.is_paused,
            use_container_width=True,
            key="resume_btn_secondary",
            help="Grayed out unless paused.",
        )

    with btn_col3:
        if st.button("Stop", use_container_width=True, key="stop_btn", type="secondary"):
            clicked_action = "Stop"

    return clicked_action
