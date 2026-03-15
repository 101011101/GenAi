"""Fraud Network Constructor Agent — Level 3 multi-step reasoning chain."""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable
from uuid import uuid4

from models.persona import Persona
from models.variant import RawVariant
from utils.label_transactions import label_transactions
from utils.llm_client import LLMClient

# ---------------------------------------------------------------------------
# Grounding data — loaded once at module import time
# ---------------------------------------------------------------------------
_DATA_DIR = Path(__file__).parent.parent / "data"


def _load_json(filename: str) -> dict:
    path = _DATA_DIR / filename
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise RuntimeError(f"Required data file not found: {path}") from None
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Malformed JSON in data file {path}: {e}") from e


_MCC_STATS = _load_json("mcc_stats.json")
_RAIL_CONSTRAINTS = _load_json("payment_rail_constraints.json")
_ACCOUNT_BALANCES = _load_json("account_balance_distributions.json")
_REG_THRESHOLDS = _load_json("regulatory_thresholds.json")

# ---------------------------------------------------------------------------
# System prompt — loaded from prompts/ directory
# ---------------------------------------------------------------------------
_PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

try:
    with open(_PROMPTS_DIR / "fraud_constructor.txt", encoding="utf-8") as _f:
        _BASE_SYSTEM_PROMPT = _f.read()
except FileNotFoundError:
    raise RuntimeError(
        f"Prompt file not found: {_PROMPTS_DIR / 'fraud_constructor.txt'}"
    ) from None

# Inject all four grounding data files into the system prompt as reference context
_GROUNDING_BLOCK = f"""
---

GROUNDING DATA — use these as your authoritative reference when generating transactions.

## MCC Stats (amount distributions by merchant category)
{json.dumps(_MCC_STATS, indent=2)}

## Payment Rail Constraints
{json.dumps(_RAIL_CONSTRAINTS, indent=2)}

## Account Balance Distributions
{json.dumps(_ACCOUNT_BALANCES, indent=2)}

## Regulatory Thresholds by Jurisdiction
{json.dumps(_REG_THRESHOLDS, indent=2)}
"""

_FULL_SYSTEM_PROMPT = _BASE_SYSTEM_PROMPT + _GROUNDING_BLOCK

# ---------------------------------------------------------------------------
# JSON schemas for each intermediate step
# ---------------------------------------------------------------------------

_PERSONA_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "specific_goal": {"type": "string"},
        "deadline_or_pressure": {"type": "string"},
        "available_resources": {
            "type": "object",
            "properties": {
                "mule_count": {"type": "integer"},
                "account_quality": {"type": "string"},
                "payment_rails_accessible": {"type": "array", "items": {"type": "string"}},
                "crypto_capability": {"type": "boolean"},
                "international_reach": {"type": "boolean"},
            },
            "required": [
                "mule_count", "account_quality", "payment_rails_accessible",
                "crypto_capability", "international_reach",
            ],
        },
        "fears_and_known_controls": {"type": "array", "items": {"type": "string"}},
        "non_negotiable_constraints": {"type": "array", "items": {"type": "string"}},
        "structural_differentiators": {"type": "string"},
        "evasion_targets": {"type": "array", "items": {"type": "string"}},
        "constraint_audit": {
            "type": "object",
            "properties": {
                "max_hop_count": {"type": "integer"},
                "allowed_channels": {"type": "array", "items": {"type": "string"}},
                "crypto_allowed": {"type": "boolean"},
                "international_allowed": {"type": "boolean"},
                "min_timing_interval_hrs": {"type": "number"},
                "max_timing_interval_hrs": {"type": "number"},
                "cover_activity_required": {"type": "boolean"},
                "mule_account_age_range": {"type": "string"},
                "mule_account_quality": {"type": "string"},
                "geographic_scope": {"type": "string"},
                "extraction_methods_allowed": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "max_hop_count", "allowed_channels", "crypto_allowed",
                "international_allowed", "min_timing_interval_hrs",
                "max_timing_interval_hrs", "cover_activity_required",
                "mule_account_age_range", "mule_account_quality",
                "geographic_scope", "extraction_methods_allowed",
            ],
        },
    },
    "required": [
        "specific_goal", "deadline_or_pressure", "available_resources",
        "fears_and_known_controls", "non_negotiable_constraints",
        "structural_differentiators", "evasion_targets", "constraint_audit",
    ],
}

_NETWORK_PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "hop_count": {"type": "integer"},
        "topology": {"type": "string"},
        "timing_interval_hrs": {"type": "number"},
        "amount_logic": {"type": "string"},
        "cover_activity": {"type": "string"},
        "extraction_method": {"type": "string"},
        "geographic_spread": {"type": "string"},
        "rationale": {"type": "string"},
    },
    "required": [
        "hop_count", "topology", "timing_interval_hrs", "amount_logic",
        "cover_activity", "extraction_method", "geographic_spread", "rationale",
    ],
}

_PARTICIPANT_PROFILES_SCHEMA = {
    "type": "object",
    "properties": {
        "accounts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "role": {"type": "string"},
                    "owner_description": {"type": "string"},
                    "recruitment_story": {"type": "string"},
                    "what_they_think_is_happening": {"type": "string"},
                    "account_type": {"type": "string"},
                    "typical_balance_range": {"type": "string"},
                    "response_time_hrs": {"type": "number"},
                },
                "required": [
                    "account_id", "role", "owner_description",
                    "recruitment_story", "what_they_think_is_happening",
                    "account_type",
                ],
            },
        }
    },
    "required": ["accounts"],
}

_SELF_REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "variant_id": {"type": "string"},
        "fraud_type": {"type": "string"},
        "persona_id": {"type": "string"},
        "strategy_description": {"type": "string"},
        "variant_parameters": {
            "type": "object",
            "properties": {
                "hop_count": {"type": "integer"},
                "timing_interval_hrs": {"type": "number"},
                "amount_logic": {"type": "string"},
                "cover_activity": {"type": "string"},
                "topology": {"type": "string"},
                "extraction_method": {"type": "string"},
                "geographic_spread": {"type": "string"},
            },
            "required": [
                "hop_count", "timing_interval_hrs", "amount_logic",
                "cover_activity", "topology", "extraction_method", "geographic_spread",
            ],
        },
        "transactions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "transaction_id": {"type": "string"},
                    "timestamp": {"type": "string"},
                    "amount": {"type": "number"},
                    "sender_account_id": {"type": "string"},
                    "receiver_account_id": {"type": "string"},
                    "merchant_category": {"type": "string"},
                    "channel": {"type": "string"},
                },
                "required": [
                    "transaction_id", "timestamp", "amount",
                    "sender_account_id", "receiver_account_id",
                    "merchant_category", "channel",
                ],
            },
        },
        "evasion_techniques": {"type": "array", "items": {"type": "string"}},
        "fraud_indicators_present": {"type": "array", "items": {"type": "string"}},
        "fraud_account_ids": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "variant_id", "fraud_type", "persona_id", "strategy_description",
        "variant_parameters", "transactions", "evasion_techniques",
        "fraud_indicators_present", "fraud_account_ids",
    ],
}


class FraudConstructorAgent:
    """Level 3 Fraud Network Constructor.

    Runs a five-step sequential reasoning chain:
      1. Persona analysis
      2. Network planning
      3. Participant profiles
      4. Transaction generation (streaming)
      5. Self-review

    Each step's output is passed as context to the next.
    """

    _MODEL = "claude-sonnet-4-6"

    def __init__(self) -> None:
        self._client = LLMClient()

    async def run(
        self,
        persona: Persona,
        cell_assignment: dict,
        critic_feedback: str = "",
        on_strategy_text: Callable[[str], None] | None = None,
        on_step: Callable[[str], None] | None = None,
    ) -> RawVariant:
        """Execute the five-step reasoning chain and return a RawVariant.

        Parameters
        ----------
        persona:
            The criminal persona seeding this variant.
        cell_assignment:
            Specific parameter values this variant must implement (from coverage matrix).
        critic_feedback:
            Non-empty string if this is a revision attempt — prepended to the system prompt.
        on_strategy_text:
            Optional streaming callback for step 4. Called with each text chunk as it
            arrives. Lets the console surface live reasoning to the monitoring panel.
        """
        system_prompt = self._build_system_prompt(critic_feedback)
        variant_id = f"V-{uuid4().hex[:6].upper()}"

        persona_json = persona.model_dump_json(indent=2)
        cell_json = json.dumps(cell_assignment, indent=2)

        # ------------------------------------------------------------------
        # Step 1 — Persona analysis
        # ------------------------------------------------------------------
        if on_step:
            on_step("Step 1/5: Persona analysis — running…")
        step1_messages = [
            {
                "role": "user",
                "content": (
                    "STEP 1: PERSONA ANALYSIS\n\n"
                    f"Persona:\n{persona_json}\n\n"
                    f"Cell assignment (target parameters for this variant):\n{cell_json}\n\n"
                    "Analyze this persona deeply. Return a JSON object describing their "
                    "goals, resources, fears, non-negotiable constraints, structural "
                    "differentiators, and specific evasion targets."
                ),
            }
        ]
        _t0 = time.perf_counter()
        persona_analysis: dict = await self._client.call(
            system_prompt=system_prompt,
            messages=step1_messages,
            model=self._MODEL,
            response_schema=_PERSONA_ANALYSIS_SCHEMA,
            timeout=None,
        )
        if on_step:
            on_step(f"Step 1/5: Persona analysis — done ({time.perf_counter() - _t0:.1f}s)")

        # ------------------------------------------------------------------
        # Step 2 — Network planning
        # ------------------------------------------------------------------
        if on_step:
            on_step(
                f"Step 2/5: Network planning — running… "
                f"(evasion targets: {', '.join(persona_analysis.get('evasion_targets', [])[:2])})"
            )
        step2_messages = step1_messages + [
            {"role": "assistant", "content": json.dumps(persona_analysis)},
            {
                "role": "user",
                "content": (
                    "STEP 2: NETWORK PLANNING\n\n"
                    "Your constraint_audit from Step 1 defines hard limits — do not violate any of them when selecting parameters.\n\n"
                    "CONFLICT RESOLUTION RULE: The cell assignment defines MANDATORY structural "
                    "parameters (hop_count, topology, extraction_method, etc.). The persona defines "
                    "BEHAVIORAL constraints (risk tolerance, resources, timeline). When they conflict:\n"
                    "- For HARD persona constraints (persona has no crypto access, no international reach, "
                    "limited mule count): the PERSONA wins. Override the cell parameter and note the "
                    "conflict in the rationale field.\n"
                    "- For SOFT quantitative choices (cell says hop_count=5, persona prefers 3): "
                    "use the CELL value and adapt the persona's behavior to make it plausible.\n"
                    "Never silently ignore either constraint — always document any conflict in rationale.\n\n"
                    "Using the persona analysis above and the cell assignment, decide the "
                    "specific operational parameters for this fraud network. Every decision "
                    "must follow logically from the persona's constraints and fears — not be "
                    "arbitrary. Return a JSON object with hop_count, topology, "
                    "timing_interval_hrs, amount_logic, cover_activity, "
                    "extraction_method, geographic_spread, and rationale."
                ),
            },
        ]
        _t0 = time.perf_counter()
        network_plan: dict = await self._client.call(
            system_prompt=system_prompt,
            messages=step2_messages,
            model=self._MODEL,
            response_schema=_NETWORK_PLAN_SCHEMA,
            timeout=None,
        )
        if on_step:
            on_step(f"Step 2/5: Network planning — done ({time.perf_counter() - _t0:.1f}s)")

        # ------------------------------------------------------------------
        # Step 3 — Participant profiles
        # ------------------------------------------------------------------
        if on_step:
            on_step(
                f"Step 3/5: Participant profiles — running… "
                f"({network_plan.get('hop_count', '?')}-hop {network_plan.get('topology', '?')}, "
                f"{network_plan.get('extraction_method', '?')} extraction)"
            )
        step3_messages = step2_messages + [
            {"role": "assistant", "content": json.dumps(network_plan)},
            {
                "role": "user",
                "content": (
                    "STEP 3: PARTICIPANT PROFILES\n\n"
                    "For each account node that will appear in the transaction sequence, "
                    "establish a profile: account_id (unique string like 'ACC-001'), role "
                    "(source, mule_hop_N, destination), owner_description, recruitment_story, "
                    "what_they_think_is_happening, account_type (from the grounding data "
                    "account types), typical_balance_range, and response_time_hrs.\n\n"
                    "The number of accounts must match the topology and hop_count from "
                    "Step 2. Return a JSON object with an 'accounts' array."
                ),
            },
        ]
        _t0 = time.perf_counter()
        participant_profiles: dict = await self._client.call(
            system_prompt=system_prompt,
            messages=step3_messages,
            model=self._MODEL,
            response_schema=_PARTICIPANT_PROFILES_SCHEMA,
            timeout=None,
        )
        if on_step:
            on_step(f"Step 3/5: Participant profiles — done ({time.perf_counter() - _t0:.1f}s)")

        # ------------------------------------------------------------------
        # Step 4 — Transaction generation (streaming)
        # ------------------------------------------------------------------
        step4_prompt = (
            "STEP 4: TRANSACTION GENERATION\n\n"
            f"Variant ID to use: {variant_id}\n\n"
            "Using the persona analysis, network plan, participant profiles, and the "
            "grounding data in the system prompt, generate the complete transaction "
            "sequence.\n\n"
            "Return a JSON object with exactly this structure:\n"
            "{\n"
            f'  "variant_id": "{variant_id}",\n'
            '  "fraud_type": "<string>",\n'
            f'  "persona_id": "{persona.persona_id}",\n'
            '  "strategy_description": "<3-5 sentences describing what makes this variant distinctive — written for a fraud analyst>",\n'
            '  "variant_parameters": {\n'
            '    "hop_count": <integer>,\n'
            '    "timing_interval_hrs": <number>,\n'
            '    "amount_logic": "<string>",\n'
            '    "cover_activity": "<none|low|high>",\n'
            '    "topology": "<chain|fan_out|hybrid>",\n'
            '    "extraction_method": "<string>",\n'
            '    "geographic_spread": "<string>"\n'
            '  },\n'
            '  "transactions": [\n'
            '    {\n'
            '      "transaction_id": "<string — txn_{variant_id}_{seq}>",\n'
            '      "timestamp": "<ISO 8601>",\n'
            '      "amount": <positive number>,\n'
            '      "sender_account_id": "<string>",\n'
            '      "receiver_account_id": "<string>",\n'
            '      "merchant_category": "<string>",\n'
            '      "channel": "<string>"\n'
            '    }\n'
            '  ],\n'
            '  "evasion_techniques": ["<string>"],\n'
            '  "fraud_indicators_present": ["<string>"],\n'
            '  "fraud_account_ids": ["<account_ids of the internal mule/layering accounts ONLY — '
            'the accounts that receive and forward funds between placement and extraction. '
            'Do NOT include the victim/source accounts that originate the funds (they are external senders). '
            'Do NOT include the final attacker/destination accounts that receive extracted funds (they are external receivers). '
            'Do NOT include cover activity accounts>"]\n'
            "}\n\n"
            "Generate at minimum hop_count + 2 fraud transactions (placement → hops → extraction) "
            "plus cover activity proportional to the cover_activity_level. "
            "IMPORTANT: cover activity transactions must use accounts that are NOT in fraud_account_ids — "
            "any transaction involving a mule account will be labeled as fraud by the pipeline regardless of intent. "
            "Do NOT add fraud_role or is_fraud fields to transactions — those are assigned automatically.\n"
            "Return ONLY the JSON object."
        )

        step4_messages = step3_messages + [
            {"role": "assistant", "content": json.dumps(participant_profiles)},
            {"role": "user", "content": step4_prompt},
        ]

        if on_step:
            acct_count = len(participant_profiles.get("accounts", []))
            on_step(f"Step 4/5: Transaction generation — running… ({acct_count} accounts)")
        _t0 = time.perf_counter()
        step4_data: dict = await self._client.call(
            system_prompt=system_prompt,
            messages=step4_messages,
            model=self._MODEL,
            response_schema=_SELF_REVIEW_SCHEMA,
            timeout=None,
        )
        if on_strategy_text:
            on_strategy_text(step4_data.get("strategy_description", ""))
        if on_step:
            on_step(f"Step 4/5: Transaction generation — done ({time.perf_counter() - _t0:.1f}s)")

        # ------------------------------------------------------------------
        # Step 5 — Self-review
        # ------------------------------------------------------------------
        if on_step:
            txn_count = len(step4_data.get("transactions", []))
            on_step(f"Step 5/5: Self-review — running… ({txn_count} transactions)")
        step5_messages = step4_messages + [
            {"role": "assistant", "content": json.dumps(step4_data)},
            {
                "role": "user",
                "content": (
                    "STEP 5: SELF-REVIEW\n\n"
                    "Review the transaction sequence you just generated against these checks:\n\n"
                    "1. Do timestamps between fraud hops match the timing_interval_hrs "
                    "from the network plan? Calculate actual hours between hops.\n"
                    "2. Are all amounts within realistic ranges per the grounding data?\n"
                    "3. Does the topology (chain/fan_out/hybrid) match the "
                    "sender→receiver flow in the transactions? Also verify that the "
                    "fraud_type string is consistent with that topology — if you generated "
                    "a fan_out topology, fraud_type must not describe a chain structure, "
                    "and vice versa. Fix fraud_type if it contradicts variant_parameters.topology.\n"
                    "3b. Using your fraud_account_ids list, count transactions where BOTH "
                    "sender_account_id AND receiver_account_id are NOT in fraud_account_ids — "
                    "these are the cover activity transactions. Does that count match "
                    "variant_parameters.cover_activity? (none → 0, low → 1–3, high → 4+). "
                    "Correct the field value if the count does not match.\n"
                    "3c. Verify fraud_account_ids is present in your output and contains only "
                    "internal mule accounts — not victim accounts, not extraction destination "
                    "accounts, not cover activity accounts.\n"
                    "4. PERSONA CONSTRAINT AUDIT — check every field in the constraint_audit "
                    "from Step 1 against your output. For each field, state ✓ (compliant) or "
                    "✗ (violation + what you will fix), then apply all fixes:\n"
                    "   - constraint_audit.crypto_allowed=false → no transaction channel may be "
                    "'crypto', extraction_method must not be 'crypto'\n"
                    "   - constraint_audit.international_allowed=false → geographic_spread must "
                    "be domestic only, no cross-border routing\n"
                    "   - constraint_audit.max_hop_count → hop_count in variant_parameters must "
                    "be ≤ this value\n"
                    "   - constraint_audit.min_timing_interval_hrs → all inter-hop timestamp "
                    "gaps must be ≥ this value\n"
                    "   - constraint_audit.max_timing_interval_hrs → all inter-hop timestamp "
                    "gaps must be ≤ this value\n"
                    "   - constraint_audit.cover_activity_required=true → cover_activity must "
                    "not be 'none'\n"
                    "   - constraint_audit.mule_account_age_range → participant account ages in "
                    "profiles must reflect this range\n"
                    "   - constraint_audit.allowed_channels → every transaction.channel must "
                    "appear in this list\n"
                    "   - constraint_audit.extraction_methods_allowed → extraction_method must "
                    "be one of these values\n"
                    "   Fix all violations before returning.\n"
                    "5. Are there any payment rail violations? "
                    "(ACH cannot settle in <1 hour; Zelle >$2,500/transaction is over limit)\n\n"
                    "Fix any inconsistencies and return the corrected full JSON object "
                    "using the same schema as Step 4. Return ONLY the corrected JSON."
                ),
            },
        ]
        _t0 = time.perf_counter()
        final_data: dict = await self._client.call(
            system_prompt=system_prompt,
            messages=step5_messages,
            model=self._MODEL,
            response_schema=_SELF_REVIEW_SCHEMA,
            timeout=None,
        )
        if on_step:
            on_step(f"Step 5/5: Self-review — done ({time.perf_counter() - _t0:.1f}s)")

        # Ensure the variant_id is the one we generated (model may have changed it)
        final_data["variant_id"] = variant_id
        final_data["persona_id"] = persona.persona_id

        # Deterministically assign fraud_role and is_fraud from the declared fraud network
        fraud_account_ids = set(final_data.pop("fraud_account_ids", []))
        final_data["transactions"] = label_transactions(
            final_data["transactions"], fraud_account_ids
        )

        return RawVariant.model_validate(final_data)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _build_system_prompt(critic_feedback: str) -> str:
        """Prepend critic feedback to the system prompt when this is a revision attempt."""
        if not critic_feedback:
            return _FULL_SYSTEM_PROMPT
        feedback_prefix = (
            f"Your previous attempt was rejected. Reason: {critic_feedback}. "
            "Generate a new variant that addresses this specific issue.\n\n"
        )
        return feedback_prefix + _FULL_SYSTEM_PROMPT
