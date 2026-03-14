"""
Orchestrator controls panel for the fraud data generation console.

Renders advanced run configuration inside a collapsible expander.
Returns a dict of overrides to merge on top of RunConfig defaults.
No LLM calls or agent imports.
"""
from __future__ import annotations

import streamlit as st


def render_orchestrator_controls() -> dict:
    """
    Render the advanced orchestrator controls inside a collapsed expander.

    Returns a dict whose keys match RunConfig field names for any controls
    the analyst has changed from defaults.
    """
    overrides: dict = {}

    with st.expander("Advanced Controls", expanded=False):

        # --- Fidelity level ---
        st.markdown("**Fidelity Level**")
        fidelity_options = ["2 - Fast", "3 - Default (recommended)", "4 - Deep (coming soon)"]
        fidelity_selection = st.radio(
            "Fidelity level",
            options=fidelity_options,
            index=1,
            key="fidelity_radio",
            label_visibility="collapsed",
            help=(
                "Level 2: Single-pass, fast, lower quality.\n"
                "Level 3: Multi-step reasoning, persona-grounded (recommended).\n"
                "Level 4: Full role simulation, highest quality, slowest."
            ),
        )

        if fidelity_selection == fidelity_options[2]:  # Level 4 selected
            st.info("Level 4 coming soon — build the MVP first")
            effective_fidelity = 3
        elif fidelity_selection == fidelity_options[0]:
            effective_fidelity = 2
        else:
            effective_fidelity = 3

        overrides["fidelity_level"] = effective_fidelity

        st.divider()

        # --- Max parallel agents ---
        st.markdown("**Max Parallel Agents**")
        max_parallel = st.slider(
            "Max parallel agents",
            min_value=1,
            max_value=10,
            value=st.session_state.get("max_parallel", 5),
            key="max_parallel_slider",
            label_visibility="collapsed",
            help="Higher values finish faster but may hit API rate limits.",
        )
        st.session_state.max_parallel = max_parallel
        if max_parallel > 8:
            st.warning("High parallelism may hit API rate limits")
        overrides["max_parallel"] = max_parallel

        st.divider()

        # --- Critic score floor ---
        st.markdown("**Critic Score Floor**")
        critic_floor = st.slider(
            "Minimum critic score to pass quality gate",
            min_value=5.0,
            max_value=9.0,
            value=st.session_state.get("critic_floor", 7.0),
            step=0.5,
            key="critic_floor_slider",
            label_visibility="collapsed",
            help="Variants below this score are revised or dropped. Higher = smaller, cleaner dataset.",
        )
        st.session_state.critic_floor = critic_floor
        overrides["critic_floor"] = critic_floor

        st.divider()

        # --- Max revision iterations ---
        st.markdown("**Max Revision Iterations**")
        max_revisions = st.number_input(
            "Max revisions before a variant is discarded",
            min_value=1,
            max_value=5,
            value=st.session_state.get("max_revisions", 2),
            step=1,
            key="max_revisions_input",
            label_visibility="collapsed",
            help="How many times the critic can send a variant back for improvement.",
        )
        st.session_state.max_revisions = int(max_revisions)
        overrides["max_revisions"] = int(max_revisions)

        st.divider()

        # --- Persona count ---
        st.markdown("**Persona Count**")
        persona_count = st.number_input(
            "Number of distinct criminal profiles to generate",
            min_value=1,
            max_value=10,
            value=st.session_state.get("persona_count", 5),
            step=1,
            key="persona_count_input",
            label_visibility="collapsed",
            help="More personas = more behavioral diversity in the generated variants.",
        )
        st.session_state.persona_count = int(persona_count)
        overrides["persona_count"] = int(persona_count)

        st.divider()

        # --- Risk distribution ---
        st.markdown("**Risk Distribution** (must sum to 100)")
        col_h, col_m, col_l = st.columns(3)

        with col_h:
            risk_high = st.slider(
                "High risk %",
                min_value=0,
                max_value=100,
                value=st.session_state.get("risk_high", 33),
                key="risk_high_slider",
            )
            st.session_state.risk_high = risk_high

        with col_m:
            risk_mid = st.slider(
                "Mid risk %",
                min_value=0,
                max_value=100,
                value=st.session_state.get("risk_mid", 34),
                key="risk_mid_slider",
            )
            st.session_state.risk_mid = risk_mid

        with col_l:
            risk_low = st.slider(
                "Low risk %",
                min_value=0,
                max_value=100,
                value=st.session_state.get("risk_low", 33),
                key="risk_low_slider",
            )
            st.session_state.risk_low = risk_low

        risk_total = risk_high + risk_mid + risk_low
        st.caption(f"Total: {risk_total}% (High: {risk_high}%, Mid: {risk_mid}%, Low: {risk_low}%)")

        if risk_total != 100:
            st.error(f"Risk distribution must sum to 100. Currently: {risk_total}%")
        else:
            overrides["risk_distribution"] = {"high": risk_high, "mid": risk_mid, "low": risk_low}

        st.divider()

        # --- Geographic scope ---
        st.markdown("**Geographic Scope**")
        geo_options = ["Domestic", "Cross-border", "SWIFT corridors"]
        geo_scope = st.multiselect(
            "Geographic scope",
            options=geo_options,
            default=st.session_state.get("geo_scope", ["Domestic"]),
            key="geo_scope_multiselect",
            label_visibility="collapsed",
            help="Controls which payment rails and regulatory thresholds are injected into the simulation.",
        )
        st.session_state.geo_scope = geo_scope

        # Map display names to internal values
        _geo_map = {"Domestic": "domestic", "Cross-border": "cross_border", "SWIFT corridors": "swift"}
        overrides["geographic_scope"] = [_geo_map.get(g, g.lower()) for g in geo_scope] or ["domestic"]

        st.divider()

        # --- Mule context depth ---
        st.markdown("**Mule Context Depth**")
        depth_options = ["Shallow", "Medium", "Deep"]
        mule_depth = st.selectbox(
            "How much backstory detail to generate for mule accounts",
            options=depth_options,
            index=st.session_state.get("mule_depth_index", 1),
            key="mule_depth_select",
            label_visibility="collapsed",
            help=(
                "Shallow: job description only — fastest.\n"
                "Medium: adds financial situation and motivation.\n"
                "Deep: full backstory, suspicion level, relationship to criminal org."
            ),
        )
        st.session_state.mule_depth_index = depth_options.index(mule_depth)
        overrides["mule_context_depth"] = mule_depth.lower()

        st.divider()

        # --- Auto second-pass ---
        st.markdown("**Auto Second-Pass**")
        auto_second_pass = st.toggle(
            "Auto second-pass on coverage gaps",
            value=st.session_state.get("auto_second_pass", False),
            key="auto_second_pass_toggle",
            help="After the first run, automatically re-run on underrepresented coverage cells.",
        )
        st.session_state.auto_second_pass = auto_second_pass
        overrides["auto_second_pass"] = auto_second_pass

    return overrides
