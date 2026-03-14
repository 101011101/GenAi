from __future__ import annotations

import math
from pathlib import Path

from models.persona import Persona
from models.run_config import RunConfig
from utils.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
_PERSONA_GENERATOR_PROMPT_PATH = _PROMPTS_DIR / "persona_generator.txt"


def _load_system_prompt() -> str:
    return _PERSONA_GENERATOR_PROMPT_PATH.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Agent class
# ---------------------------------------------------------------------------

class PersonaGeneratorAgent:
    """Generates a list of criminal personas to seed fraud variant generation.

    Each Persona is a decision-maker whose goals, resources, and constraints
    determine the structural shape of the fraud operations attributed to them.
    The count and risk distribution are driven by RunConfig settings.
    """

    def __init__(self, model: str | None = None) -> None:
        self._client = LLMClient()
        self._model = model or "claude-haiku-4-5-20251001"

    async def run(self, fraud_description: str, config: RunConfig) -> list[Persona]:
        """Generate personas and return them as validated Pydantic objects."""

        system_prompt = _load_system_prompt()
        user_message = _build_user_message(fraud_description, config)
        response_schema = _build_response_schema()

        raw: dict = await self._client.call(
            system_prompt=system_prompt,
            messages=[{"role": "user", "content": user_message}],
            model=self._model,
            response_schema=response_schema,
            timeout=60.0,
        )

        return _parse_personas(raw, config.persona_count)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_risk_counts(persona_count: int, risk_distribution: dict) -> tuple[int, int, int]:
    """Return (high_count, mid_count, low_count) rounding to exactly persona_count total."""
    high_f = persona_count * risk_distribution["high"] / 100.0
    mid_f = persona_count * risk_distribution["mid"] / 100.0
    low_f = persona_count * risk_distribution["low"] / 100.0

    high = round(high_f)
    mid = round(mid_f)
    low = round(low_f)

    # Adjust rounding error so counts sum exactly to persona_count
    diff = persona_count - (high + mid + low)
    if diff > 0:
        # Add remainder to the largest bucket to minimise distortion
        buckets = [("high", high), ("mid", mid), ("low", low)]
        buckets.sort(key=lambda x: -x[1])
        largest = buckets[0][0]
        if largest == "high":
            high += diff
        elif largest == "mid":
            mid += diff
        else:
            low += diff
    elif diff < 0:
        # Remove excess from the largest bucket
        buckets = [("high", high), ("mid", mid), ("low", low)]
        buckets.sort(key=lambda x: -x[1])
        largest = buckets[0][0]
        if largest == "high":
            high += diff  # diff is negative
        elif largest == "mid":
            mid += diff
        else:
            low += diff

    return max(high, 0), max(mid, 0), max(low, 0)


def _build_user_message(fraud_description: str, config: RunConfig) -> str:
    high_count, mid_count, low_count = _compute_risk_counts(
        config.persona_count, config.risk_distribution
    )

    geo_scope_str = ", ".join(config.geographic_scope)

    count_instruction = (
        f"Generate {config.persona_count} personas: "
        f"{high_count} high risk, {mid_count} mid risk, {low_count} low risk."
    )

    return (
        f"FRAUD DESCRIPTION:\n{fraud_description}\n\n"
        f"PERSONA REQUIREMENTS:\n"
        f"{count_instruction}\n"
        f"Geographic scope: {geo_scope_str}\n"
        f"Mule context depth: {config.mule_context_depth}\n\n"
        f"Risk distribution to enforce: "
        f"{config.risk_distribution['high']}% high / "
        f"{config.risk_distribution['mid']}% mid / "
        f"{config.risk_distribution['low']}% low\n\n"
        f"Return the JSON array with exactly {config.persona_count} persona objects. "
        f"Assign sequential persona_ids: P-01, P-02, P-03, etc."
    )


def _build_response_schema() -> dict:
    """Wrap the Persona JSON schema in an array schema for structured output."""
    persona_schema = Persona.model_json_schema()

    # The LLM client injects the schema into the system prompt and pre-fills
    # the assistant turn with `{` — this forces a top-level JSON object.
    # We wrap the array in an object so the pre-fill trick works correctly.
    return {
        "type": "object",
        "properties": {
            "personas": {
                "type": "array",
                "items": persona_schema,
                "description": "Array of generated criminal persona objects.",
            }
        },
        "required": ["personas"],
    }


def _parse_personas(raw: dict, expected_count: int) -> list[Persona]:
    """Validate raw LLM output and return a list of Persona objects with sequential IDs."""

    personas_raw: list[dict] = raw.get("personas", [])

    personas: list[Persona] = []
    for i, persona_dict in enumerate(personas_raw):
        # Override persona_id with sequential format regardless of what the LLM produced
        persona_dict = dict(persona_dict)
        persona_dict["persona_id"] = f"P-{i + 1:02d}"

        # Validate through Pydantic (raises ValidationError on invalid data)
        persona = Persona.model_validate(persona_dict)
        personas.append(persona)

    return personas
