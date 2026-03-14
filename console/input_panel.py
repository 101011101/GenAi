"""
Input panel for the fraud data generation console.

Renders fraud description input, variant count slider, and run controls.
Returns a RunConfig when the user clicks Run and input is valid, None otherwise.
No LLM calls or agent imports.
"""
from __future__ import annotations

import sys
import os

import streamlit as st

# Make project root importable regardless of working directory
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from models.run_config import RunConfig

TEMPLATES: dict[str, str] = {
    "Mule Network": (
        "Layered mule account network with cross-border hops and burst withdrawal. "
        "Criminal organization recruits individuals to receive stolen funds and forward "
        "through chain of accounts before final extraction."
    ),
    "Synthetic Identity": (
        "Synthetic identity fraud using fabricated credentials, slow credit-building phase "
        "over 6-18 months, followed by bust-out event draining all available credit."
    ),
    "Account Takeover": (
        "Account takeover via credential stuffing, small test transaction to verify access, "
        "followed by rapid balance drain through multiple channels."
    ),
    "Card Testing": (
        "Card testing attack across multiple low-value merchants to validate stolen card "
        "numbers before high-value purchase attempt."
    ),
}

# Cost and time estimates (per variant at L3 default)
_COST_PER_VARIANT_L3 = 0.20  # USD
_MINS_PER_VARIANT_L3_BASE = 0.15  # minutes per variant at 5 parallel agents


def _estimate_cost_and_time(variant_count: int, fidelity: int = 3) -> tuple[float, float]:
    """Return (estimated_cost_usd, estimated_minutes) for a given variant count and fidelity."""
    fidelity_multiplier = {2: 0.4, 3: 1.0, 4: 3.5}.get(fidelity, 1.0)
    cost = variant_count * _COST_PER_VARIANT_L3 * fidelity_multiplier
    mins = variant_count * _MINS_PER_VARIANT_L3_BASE * fidelity_multiplier
    return cost, mins


def render_input_panel() -> RunConfig | None:
    """
    Render the input panel.

    Returns a RunConfig when the Run button is clicked and all validation passes.
    Returns None otherwise (most renders).
    """
    st.subheader("Fraud Description")

    # --- Fraud type helper dropdown ---
    fraud_type_options = ["(Choose a template...)"] + list(TEMPLATES.keys())

    if "selected_fraud_type" not in st.session_state:
        st.session_state.selected_fraud_type = fraud_type_options[0]

    if "fraud_description" not in st.session_state:
        st.session_state.fraud_description = ""

    selected_type = st.selectbox(
        "Fraud type helper",
        options=fraud_type_options,
        index=fraud_type_options.index(st.session_state.selected_fraud_type),
        help="Select a template to pre-fill the description below. You can edit freely after.",
        key="fraud_type_selector",
    )

    # Pre-fill description when template is chosen (only if changed and not the placeholder)
    if (
        selected_type != fraud_type_options[0]
        and selected_type != st.session_state.selected_fraud_type
    ):
        st.session_state.fraud_description = TEMPLATES[selected_type]
    st.session_state.selected_fraud_type = selected_type

    # --- Fraud description text area ---
    description = st.text_area(
        "Fraud description",
        value=st.session_state.fraud_description,
        height=200,
        placeholder=(
            "Describe the fraud type you want to explore. Example: "
            "\"layered mule account network with cross-border hops and burst withdrawal\""
        ),
        label_visibility="collapsed",
        key="fraud_description_area",
    )
    # Keep session state in sync
    st.session_state.fraud_description = description

    char_count = len(description)
    st.caption(f"{char_count} characters")

    # Validation warnings
    if 0 < char_count < 50:
        st.warning("Add more detail for better variant diversity")

    # --- Variant count slider ---
    st.subheader("Variant Count")
    variant_count = st.slider(
        "Number of variants to generate",
        min_value=10,
        max_value=100,
        value=st.session_state.get("variant_count", 25),
        step=1,
        key="variant_count_slider",
    )
    st.session_state.variant_count = variant_count

    # Dynamic estimate text
    cost_usd, mins = _estimate_cost_and_time(variant_count, fidelity=3)
    st.caption(f"~{variant_count} variants · Est. ${cost_usd:.2f} · Est. {mins:.0f} min")

    # Expensive run confirmation hint
    if cost_usd > 10:
        st.info(f"Estimated cost ${cost_usd:.2f} exceeds $10. You will be asked to confirm before the run starts.")

    # --- Run button ---
    st.divider()

    run_disabled = char_count < 20
    run_tooltip = "Describe the fraud type to continue" if run_disabled else "Start generating synthetic fraud variants"

    clicked = st.button(
        "Run",
        disabled=run_disabled,
        help=run_tooltip,
        type="primary",
        use_container_width=True,
    )

    if run_disabled and char_count > 0:
        st.caption("Minimum 20 characters required to enable Run.")

    if not clicked:
        return None

    # Build and return RunConfig
    try:
        config = RunConfig(
            fraud_description=description.strip(),
            variant_count=variant_count,
        )
        return config
    except Exception as exc:
        st.error(f"Configuration error: {exc}")
        return None
