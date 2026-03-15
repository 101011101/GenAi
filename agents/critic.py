"""Critic Agent — independent quality gate for generated fraud variants."""
from __future__ import annotations

import json
from pathlib import Path

from models.persona import Persona
from models.variant import ScoredVariant, ValidatedVariant
from utils.llm_client import LLMClient

# ---------------------------------------------------------------------------
# System prompt — loaded from prompts/ directory
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

try:
    with open(_PROMPTS_DIR / "critic.txt", encoding="utf-8") as _f:
        _CRITIC_SYSTEM_PROMPT = _f.read()
except FileNotFoundError:
    raise RuntimeError(f"Prompt file not found: {_PROMPTS_DIR / 'critic.txt'}") from None

# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------
_CRITIC_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "realism_score": {"type": "number", "minimum": 1.0, "maximum": 10.0},
        "distinctiveness_score": {"type": "number", "minimum": 1.0, "maximum": 10.0},
        "persona_consistency": {"type": "boolean"},
        "label_correctness": {"type": "boolean"},
        "feedback": {"type": "string"},
    },
    "required": [
        "realism_score",
        "distinctiveness_score",
        "persona_consistency",
        "label_correctness",
        "feedback",
    ],
}


class CriticAgent:
    """Independent critic agent that scores a ValidatedVariant before dataset entry.

    The critic has NO knowledge of the coverage matrix or other variants.
    It evaluates the variant on its own merits across four dimensions:
      - Realism (score 1–10)
      - Persona consistency (pass/fail)
      - Label correctness (pass/fail)
      - Distinctiveness (score 1–10)
    """

    _MODEL = "claude-sonnet-4-6"

    def __init__(self) -> None:
        self._client = LLMClient()

    async def run(
        self,
        variant: ValidatedVariant,
        persona: Persona,
        critic_floor: float = 7.0,
        distinctiveness_floor: float | None = None,
    ) -> ScoredVariant:
        """Score the variant and return a ScoredVariant.

        Parameters
        ----------
        variant:
            The schema-validated fraud variant to evaluate.
        persona:
            The original persona that generated this variant.
        critic_floor:
            Minimum realism score required to pass (default 7.0).
        distinctiveness_floor:
            Minimum distinctiveness score required to pass. Defaults to
            max(5.0, critic_floor - 1.0) to match the critic prompt semantics.
        """
        if distinctiveness_floor is None:
            distinctiveness_floor = max(5.0, critic_floor - 1.0)

        user_message = (
            f"Critic floor (minimum realism score to pass): {critic_floor}\n"
            f"Distinctiveness floor (minimum distinctiveness score to pass): {distinctiveness_floor}\n\n"
            "VARIANT TO EVALUATE:\n"
            f"{variant.model_dump_json(indent=2)}\n\n"
            "PERSONA THAT GENERATED IT:\n"
            f"{persona.model_dump_json(indent=2)}\n\n"
            "Score this variant on all four dimensions and return only the JSON object."
        )

        messages = [{"role": "user", "content": user_message}]

        raw_scores: dict = await self._client.call(
            system_prompt=_CRITIC_SYSTEM_PROMPT,
            messages=messages,
            model=self._MODEL,
            response_schema=_CRITIC_RESPONSE_SCHEMA,
            timeout=30.0,
        )

        realism_score: float = float(raw_scores["realism_score"])
        distinctiveness_score: float = float(raw_scores["distinctiveness_score"])
        persona_consistency: bool = bool(raw_scores["persona_consistency"])
        label_correctness: bool = bool(raw_scores["label_correctness"])
        feedback: str = str(raw_scores.get("feedback", ""))

        passed: bool = (
            realism_score >= critic_floor
            and distinctiveness_score >= distinctiveness_floor
            and persona_consistency
            and label_correctness
        )

        # Build ScoredVariant by merging the ValidatedVariant fields with critic scores.
        # model_dump() gives us the full variant data; we extend it with critic fields.
        variant_data = variant.model_dump()
        variant_data.update(
            {
                "realism_score": realism_score,
                "distinctiveness_score": distinctiveness_score,
                "persona_consistency": persona_consistency,
                "label_correctness": label_correctness,
                "passed": passed,
                "feedback": feedback,
            }
        )

        return ScoredVariant.model_validate(variant_data)
