from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from models.run_config import RunConfig
from utils.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Output dataclass
# ---------------------------------------------------------------------------

@dataclass
class OrchestratorOutput:
    """Plan returned by the Orchestrator. Does NOT spawn agents — that is the runner's job."""

    variation_dimensions: list[dict] = field(default_factory=list)
    """Each dict: name, description, range_low, range_high, example_values."""

    coverage_cells: list[dict] = field(default_factory=list)
    """Each dict: cell_id, dimension_values (dict), persona_slot (int index into personas list)."""

    suggested_persona_count: int = 5


# ---------------------------------------------------------------------------
# Grounding data paths
# ---------------------------------------------------------------------------

_DATA_DIR = Path(__file__).parent.parent / "data"
_REGULATORY_THRESHOLDS_PATH = _DATA_DIR / "regulatory_thresholds.json"
_PAYMENT_RAIL_CONSTRAINTS_PATH = _DATA_DIR / "payment_rail_constraints.json"

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_ORCHESTRATOR_PROMPT_PATH = _PROMPTS_DIR / "orchestrator.txt"


def _load_system_prompt() -> str:
    base_prompt = _ORCHESTRATOR_PROMPT_PATH.read_text(encoding="utf-8")

    # Load grounding data and inject as reference context
    regulatory_thresholds = json.load(open(_REGULATORY_THRESHOLDS_PATH))
    payment_rail_constraints = json.load(open(_PAYMENT_RAIL_CONSTRAINTS_PATH))

    grounding_block = (
        "\n\n--- REGULATORY THRESHOLDS REFERENCE ---\n"
        "Use this data to ensure coverage cells reflect real jurisdictional reporting thresholds "
        "when assigning amount-structuring dimension values.\n"
        f"{json.dumps(regulatory_thresholds, indent=2)}"
        "\n\n--- PAYMENT RAIL CONSTRAINTS REFERENCE ---\n"
        "Use this data to ensure coverage cells assign only payment rails that exist and have "
        "realistic processing windows and per-transaction limits.\n"
        f"{json.dumps(payment_rail_constraints, indent=2)}"
    )

    return base_prompt + grounding_block


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class OrchestratorAgent:
    """Decomposes a fraud description into a structured variation plan.

    Returns an OrchestratorOutput containing:
    - variation_dimensions  — axes along which this fraud type varies
    - coverage_cells        — one sub-agent assignment per planned variant
    - suggested_persona_count — how many distinct criminal profiles to generate

    Does NOT spawn sub-agents. The pipeline runner handles that.
    """

    def __init__(self) -> None:
        self._client = LLMClient()

    async def run(self, config: RunConfig) -> OrchestratorOutput:
        """Run the orchestrator against the given RunConfig and return a plan."""

        system_prompt = _load_system_prompt()

        user_message = _build_user_message(config)

        raw: dict = await self._client.call_with_thinking(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            model="claude-opus-4-6",
            budget_tokens=5000,
        )

        return _parse_output(raw, config)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_user_message(config: RunConfig) -> str:
    geo_scope_str = ", ".join(config.geographic_scope)
    risk_dist = config.risk_distribution
    risk_str = (
        f"{risk_dist['high']}% high risk / "
        f"{risk_dist['mid']}% mid risk / "
        f"{risk_dist['low']}% low risk"
    )

    return (
        f"FRAUD DESCRIPTION:\n{config.fraud_description}\n\n"
        f"RUN SETTINGS:\n"
        f"- Target variant count: {config.variant_count} "
        f"(generate exactly {config.variant_count} coverage cells)\n"
        f"- Fidelity level: {config.fidelity_level}\n"
        f"- Geographic scope: {geo_scope_str}\n"
        f"- Risk distribution for personas: {risk_str}\n"
        f"- Persona count: {config.persona_count}\n"
        f"- Mule context depth: {config.mule_context_depth}\n\n"
        f"Generate the variation dimensions, coverage cells, and suggested persona count. "
        f"The coverage_cells array MUST contain exactly {config.variant_count} cells. "
        f"Distribute cells to maximize structural diversity across the variation space."
    )


def _parse_output(raw: dict, config: RunConfig) -> OrchestratorOutput:
    """Parse the raw JSON dict returned by the LLM into an OrchestratorOutput."""

    variation_dimensions: list[dict] = raw.get("variation_dimensions", [])
    coverage_cells_raw: list[dict] = raw.get("coverage_cells", [])
    suggested_persona_count: int = int(raw.get("suggested_persona_count", config.persona_count))

    # Normalise coverage cells: convert persona_slot to int index if the LLM
    # returned a descriptive string instead of an index.  We map each unique
    # persona_slot label to a sequential integer so downstream code always
    # receives an integer.
    persona_slot_map: dict[str, int] = {}
    next_index = 0

    coverage_cells: list[dict] = []
    for cell in coverage_cells_raw:
        raw_slot = cell.get("persona_slot", 0)

        if isinstance(raw_slot, int):
            normalised_slot = raw_slot
        else:
            # LLM returned a descriptive label — map it to an int
            slot_str = str(raw_slot)
            if slot_str not in persona_slot_map:
                persona_slot_map[slot_str] = next_index
                next_index += 1
            normalised_slot = persona_slot_map[slot_str]

        # Clamp to [0, suggested_persona_count - 1] so indices stay valid
        max_idx = max(suggested_persona_count - 1, 0)
        normalised_slot = min(normalised_slot % max(suggested_persona_count, 1), max_idx)

        coverage_cells.append(
            {
                "cell_id": cell.get("cell_id", f"cell_{len(coverage_cells) + 1:03d}"),
                "dimension_values": cell.get("dimension_values", {}),
                "persona_slot": normalised_slot,
            }
        )

    return OrchestratorOutput(
        variation_dimensions=variation_dimensions,
        coverage_cells=coverage_cells,
        suggested_persona_count=suggested_persona_count,
    )
