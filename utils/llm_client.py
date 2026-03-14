from __future__ import annotations

import asyncio
import json
import os
import random
import time
from typing import Callable

import anthropic

# ---------------------------------------------------------------------------
# Pricing constants — Sonnet as of March 2026
# ---------------------------------------------------------------------------
_SONNET_INPUT_COST_PER_M = 3.0   # USD per million input tokens
_SONNET_OUTPUT_COST_PER_M = 15.0  # USD per million output tokens


class LLMClientError(Exception):
    """All errors from LLMClient are wrapped in this exception type."""


class LLMClient:
    """Async Claude API wrapper.

    Usage:
        client = LLMClient()
        result = await client.call(system_prompt, messages, model="claude-sonnet-4-5")
    """

    def __init__(self) -> None:
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self._mock = os.environ.get("FRAUDGEN_MOCK") == "1"
        if self._mock:
            self._client = None
            return
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMClientError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it before starting the application: "
                "export ANTHROPIC_API_KEY='sk-ant-...'"
            )
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def call(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        response_schema: dict | None = None,
        timeout: float = 30.0,
    ) -> dict:
        """Make one API call and return parsed JSON.

        If *response_schema* is provided, structured output mode is used.
        Retries up to 3 times on JSON parse errors.
        Applies exponential backoff on 429/529 status codes.
        """
        if self._mock:
            await asyncio.sleep(0.3)
            return _mock_response(messages)

        last_error: Exception | None = None
        current_messages = list(messages)

        for attempt in range(3):
            try:
                raw_text = await self._call_raw(
                    system_prompt=system_prompt,
                    messages=current_messages,
                    model=model,
                    response_schema=response_schema,
                    timeout=timeout,
                )
                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError as parse_err:
                    last_error = parse_err
                    # Append a correction turn and retry
                    current_messages = list(current_messages) + [
                        {"role": "assistant", "content": raw_text},
                        {
                            "role": "user",
                            "content": (
                                "Your previous response was not valid JSON. "
                                "Return only valid JSON matching this schema exactly. "
                                "Do not include any text outside the JSON object."
                            ),
                        },
                    ]

            except anthropic.RateLimitError as exc:
                last_error = exc
                await self._backoff(attempt)
            except anthropic.InternalServerError as exc:
                # 529 overloaded maps to InternalServerError with status 529
                if hasattr(exc, "status_code") and exc.status_code == 529:
                    last_error = exc
                    await self._backoff(attempt)
                else:
                    raise LLMClientError(f"Anthropic internal server error: {exc}") from exc
            except asyncio.TimeoutError as exc:
                raise LLMClientError(
                    f"API call timed out after {timeout}s on attempt {attempt + 1}"
                ) from exc
            except Exception as exc:
                raise LLMClientError(f"Unexpected error during API call: {exc}") from exc

        raise LLMClientError(
            f"API call failed after 3 attempts. Last error: {last_error}"
        ) from last_error

    async def call_streaming(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        on_text: Callable[[str], None] | None = None,
    ) -> str:
        """Stream the response, invoke *on_text* for each text chunk, return full text."""
        if self._mock:
            mock_data = _mock_response(messages)
            text = json.dumps(mock_data)
            # Stream in small chunks to simulate real streaming
            chunk_size = 80
            for i in range(0, len(text), chunk_size):
                chunk = text[i : i + chunk_size]
                await asyncio.sleep(0.05)
                if on_text:
                    on_text(chunk)
            return text

        try:
            full_text_parts: list[str] = []
            async with self._client.messages.stream(
                model=model,
                max_tokens=8192,
                system=system_prompt,
                messages=messages,
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text_parts.append(chunk)
                    if on_text is not None:
                        on_text(chunk)

                # Capture final message for token accounting
                final_msg = await stream.get_final_message()
                self.total_input_tokens += final_msg.usage.input_tokens
                self.total_output_tokens += final_msg.usage.output_tokens

            return "".join(full_text_parts)

        except anthropic.RateLimitError as exc:
            raise LLMClientError(f"Rate limit hit during streaming: {exc}") from exc
        except Exception as exc:
            raise LLMClientError(f"Streaming call failed: {exc}") from exc

    async def call_with_thinking(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        budget_tokens: int = 5000,
    ) -> dict:
        """Call the API with extended thinking enabled (used by the orchestrator).

        Returns the first top-level JSON object found in the response text.
        Extended thinking responses may include a thinking block before the answer block.
        """
        if self._mock:
            await asyncio.sleep(0.5)
            return _mock_response(messages)

        try:
            response = await asyncio.wait_for(
                self._client.messages.create(
                    model=model,
                    max_tokens=budget_tokens + 8192,
                    thinking={"type": "adaptive"},
                    system=system_prompt,
                    messages=messages,
                ),
                timeout=180.0,  # thinking calls can take longer
            )
            self.total_input_tokens += response.usage.input_tokens
            self.total_output_tokens += response.usage.output_tokens

            # Extract text blocks (skip thinking blocks)
            text_content = ""
            for block in response.content:
                if block.type == "text":
                    text_content += block.text

            try:
                return json.loads(text_content)
            except json.JSONDecodeError:
                # Try to extract JSON from within the text (agent may add preamble)
                extracted = _extract_json_from_text(text_content)
                if extracted is not None:
                    return extracted
                raise LLMClientError(
                    f"Could not parse JSON from thinking response. Raw text: {text_content[:500]}"
                )

        except asyncio.TimeoutError as exc:
            raise LLMClientError("call_with_thinking timed out after 120s") from exc
        except LLMClientError:
            raise
        except Exception as exc:
            raise LLMClientError(
                f"call_with_thinking failed: {exc}"
            ) from exc

    @property
    def cost_usd(self) -> float:
        """Estimated cost in USD based on Sonnet pricing."""
        input_cost = (self.total_input_tokens / 1_000_000) * _SONNET_INPUT_COST_PER_M
        output_cost = (self.total_output_tokens / 1_000_000) * _SONNET_OUTPUT_COST_PER_M
        return round(input_cost + output_cost, 4)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _call_raw(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        response_schema: dict | None,
        timeout: float,
    ) -> str:
        """Low-level call. Returns raw response text string."""
        kwargs: dict = {
            "model": model,
            "max_tokens": 8192,
            "system": system_prompt,
            "messages": messages,
        }

        if response_schema is not None:
            # Structured output: tell the model to return JSON matching the schema.
            # We inject the schema into the system prompt and pre-fill the assistant turn
            # with `{` to force JSON output. The Anthropic API does not yet support
            # native JSON schema enforcement on all models, so this is the robust approach.
            schema_instruction = (
                "\n\nYou MUST respond with a single valid JSON object that strictly "
                f"conforms to this JSON schema:\n{json.dumps(response_schema, indent=2)}\n"
                "Return ONLY the JSON object — no explanation, no markdown fences, no preamble."
            )
            kwargs["system"] = system_prompt + schema_instruction
            # Pre-fill assistant response to force JSON
            kwargs["messages"] = list(messages) + [{"role": "assistant", "content": "{"}]

        response = await asyncio.wait_for(
            self._client.messages.create(**kwargs),
            timeout=timeout,
        )

        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        text = response.content[0].text if response.content else ""

        # If we pre-filled with `{`, re-attach the opening brace
        if response_schema is not None:
            text = "{" + text

        return text

    @staticmethod
    async def _backoff(attempt: int) -> None:
        """Exponential backoff with jitter. Base 2s, max 30s."""
        base = 2.0
        cap = 30.0
        delay = min(cap, base * (2 ** attempt)) + random.uniform(0.0, 1.0)
        await asyncio.sleep(delay)


def _mock_response(messages: list[dict]) -> dict:
    """Return a plausible stub response for mock mode.

    Detects which agent is calling based on message content and returns
    a schema-matching response so the full pipeline can run end-to-end.
    """
    import uuid, random
    from datetime import datetime, timedelta

    content = " ".join(
        m.get("content", "") if isinstance(m.get("content"), str) else ""
        for m in messages
    ).lower()

    # Critic output — check FIRST because critic messages contain the full variant
    # JSON (which includes "step" keywords and "persona" text from prior agents).
    if "critic floor" in content or "score this variant" in content:
        # ~25% chance of a yellow score (5.5-6.8) to show quality-control story
        if random.random() < 0.25:
            realism = round(random.uniform(5.5, 6.8), 1)
            distinct = round(random.uniform(5.0, 6.5), 1)
        else:
            realism = round(random.uniform(6.5, 9.2), 1)
            distinct = round(random.uniform(6.0, 8.5), 1)
        return {
            "realism_score": realism,
            "distinctiveness_score": distinct,
            "persona_consistency": True,
            "label_correctness": True,
            "feedback": "Improve structural diversity and add more realistic cover activity."
            if (realism + distinct) / 2 < 7.0
            else "",
        }

    # Orchestrator output
    if "variation_dimensions" in content or "coverage_cells" in content or "decompose" in content:
        # Fixed dimension values — used for both cells and grid rendering
        hop_counts = [2, 3, 4, 6]
        topologies = ["chain", "fan_out", "hybrid"]
        extraction_methods = ["wire", "crypto", "cash"]
        timing_values = [1, 8, 24, 72]

        # Build 12 cells with diverse parameter combos across the grid
        cell_configs = [
            {"hop_count": 2, "timing_interval_hrs": 1,  "topology": "chain",   "extraction_method": "wire"},
            {"hop_count": 2, "timing_interval_hrs": 24, "topology": "fan_out", "extraction_method": "crypto"},
            {"hop_count": 2, "timing_interval_hrs": 72, "topology": "hybrid",  "extraction_method": "cash"},
            {"hop_count": 3, "timing_interval_hrs": 8,  "topology": "chain",   "extraction_method": "wire"},
            {"hop_count": 3, "timing_interval_hrs": 24, "topology": "fan_out", "extraction_method": "crypto"},
            {"hop_count": 3, "timing_interval_hrs": 72, "topology": "hybrid",  "extraction_method": "cash"},
            {"hop_count": 4, "timing_interval_hrs": 1,  "topology": "fan_out", "extraction_method": "wire"},
            {"hop_count": 4, "timing_interval_hrs": 8,  "topology": "hybrid",  "extraction_method": "crypto"},
            {"hop_count": 4, "timing_interval_hrs": 72, "topology": "chain",   "extraction_method": "cash"},
            {"hop_count": 6, "timing_interval_hrs": 1,  "topology": "hybrid",  "extraction_method": "wire"},
            {"hop_count": 6, "timing_interval_hrs": 24, "topology": "chain",   "extraction_method": "crypto"},
            {"hop_count": 6, "timing_interval_hrs": 72, "topology": "fan_out", "extraction_method": "cash"},
        ]

        cells = []
        for i, cfg in enumerate(cell_configs):
            cells.append({
                "cell_id": f"C-{i+1:02d}",
                "dimension_values": cfg,
                "persona_slot": i % 3,
            })

        return {
            "variation_dimensions": [
                {"name": "hop_count", "description": "Number of mule hops", "values": hop_counts},
                {"name": "topology", "description": "Network shape", "values": topologies},
                {"name": "extraction_method", "description": "Final extraction channel", "values": extraction_methods},
                {"name": "timing_interval_hrs", "description": "Hours between hops", "values": timing_values},
            ],
            "coverage_cells": cells,
            "suggested_persona_count": 3,
        }

    # Fraud constructor steps — check BEFORE persona generator because
    # constructor messages also contain "persona" and "generate" keywords.
    if "step 1" in content or "step 2" in content or "step 3" in content or "step 4" in content or "step 5" in content:
        now = datetime.now()
        acct = lambda: f"ACC-{uuid.uuid4().hex[:8].upper()}"

        # --- Extract cell assignment params from message content ---
        cell_hop_count = 3
        cell_topology = "chain"
        cell_timing = 8
        cell_extraction = "wire"
        # Parse dimension_values from the cell assignment JSON in the message
        import re
        hop_match = re.search(r'"hop_count"\s*:\s*(\d+)', content)
        if hop_match:
            cell_hop_count = int(hop_match.group(1))
        topo_match = re.search(r'"topology"\s*:\s*"(\w+)"', content)
        if topo_match:
            cell_topology = topo_match.group(1)
        timing_match = re.search(r'"timing_interval_hrs"\s*:\s*(\d+)', content)
        if timing_match:
            cell_timing = int(timing_match.group(1))
        extract_match = re.search(r'"extraction_method"\s*:\s*"(\w+)"', content)
        if extract_match:
            cell_extraction = extract_match.group(1)

        # Build accounts for the given hop count
        accounts = [acct() for _ in range(cell_hop_count + 1)]

        # Step 1 — persona analysis
        if "step 2" not in content:
            return {
                "specific_goal": "Move $150K through mule network within 72 hours",
                "deadline_or_pressure": "Funds must be extracted before Monday freeze review",
                "available_resources": {
                    "mule_count": cell_hop_count + 1,
                    "account_quality": "aged_checking",
                    "payment_rails_accessible": ["wire_domestic", "ach", "zelle"],
                    "crypto_capability": cell_extraction == "crypto",
                    "international_reach": False,
                },
                "fears_and_known_controls": ["velocity flags", "CTR reporting", "new-payee alerts"],
                "non_negotiable_constraints": ["All transactions below $10K", "No international wires"],
                "structural_differentiators": f"Uses {cell_topology} topology with {cell_timing}h timing intervals",
                "evasion_targets": ["structuring detection", "rapid-movement flags"],
            }

        # Step 2 — network planning
        if "step 3" not in content:
            cover_level = "high" if cell_hop_count >= 4 else "low"
            return {
                "hop_count": cell_hop_count,
                "topology": cell_topology,
                "timing_interval_hrs": cell_timing,
                "amount_logic": "structured_below_10k",
                "cover_activity_level": cover_level,
                "extraction_method": cell_extraction,
                "geographic_spread": "domestic",
                "rationale": f"{cell_topology.replace('_', '-')} topology with {cell_hop_count} hops; "
                             f"{cell_timing}h intervals to evade velocity flags.",
            }

        # Step 3 — participant profiles
        if "step 4" not in content:
            roles = ["source"] + [f"mule_hop_{j+1}" for j in range(cell_hop_count - 1)] + ["destination"]
            acct_profiles = []
            for j, role in enumerate(roles):
                acct_profiles.append({
                    "account_id": accounts[j],
                    "role": role,
                    "owner_description": ["Primary fraud operator", "College student recruited online", "Unemployed individual", "Extraction account", "Gig worker", "Retired individual", "Small business owner"][j % 7],
                    "recruitment_story": "Account owner" if j == 0 else "Recruited via social media ad",
                    "what_they_think_is_happening": "Moving own funds" if j == 0 else "Freelance payment processing",
                    "account_type": "business_checking" if role == "destination" else "checking",
                    "typical_balance_range": "$10K-$50K" if role == "destination" else "$500-$15K",
                    "response_time_hrs": round(random.uniform(0.5, 4.0), 1),
                })
            return {"accounts": acct_profiles}

        # Steps 4 & 5 — transaction generation / self-review: return full variant
        # Fraud hop transactions
        txns = []
        for i in range(cell_hop_count):
            txns.append({
                "transaction_id": f"T-{uuid.uuid4().hex[:6].upper()}",
                "timestamp": (now + timedelta(hours=i * cell_timing)).isoformat(),
                "amount": round(random.uniform(3000, 9800), 2),
                "sender_account_id": accounts[i],
                "receiver_account_id": accounts[i + 1],
                "merchant_category": "wire_transfer" if cell_extraction == "wire" else ("crypto_exchange" if cell_extraction == "crypto" else "atm_withdrawal"),
                "channel": {"wire": "wire_domestic", "crypto": "crypto_transfer", "cash": "atm"}[cell_extraction],
                "is_fraud": True,
                "fraud_role": f"hop_{i+1}_of_{cell_hop_count}",
            })

        # Cover activity transactions (more for deeper networks)
        cover_count = 2 if cell_hop_count >= 4 else 1
        for c in range(cover_count):
            mule_idx = min(c + 1, len(accounts) - 2)
            txns.append({
                "transaction_id": f"T-{uuid.uuid4().hex[:6].upper()}",
                "timestamp": (now + timedelta(hours=c * 3 + 2)).isoformat(),
                "amount": round(random.uniform(15, 120), 2),
                "sender_account_id": accounts[mule_idx],
                "receiver_account_id": acct(),
                "merchant_category": random.choice(["grocery", "gas_station", "restaurant", "retail"]),
                "channel": "card_debit",
                "is_fraud": False,
                "fraud_role": "cover_activity",
            })

        strategy_templates = {
            "chain": f"Mock: {cell_hop_count}-hop chain with {cell_timing}h intervals. Sequential fund movement via {cell_extraction} with cover purchases on mule accounts.",
            "fan_out": f"Mock: {cell_hop_count}-hop fan-out tree. Source splits funds to {cell_hop_count - 1} mules simultaneously, converging at extraction point via {cell_extraction}.",
            "hybrid": f"Mock: {cell_hop_count}-hop hybrid network. Initial chain splits into parallel paths before {cell_extraction} extraction. {cell_timing}h timing intervals.",
        }

        return {
            "variant_id": f"V-{uuid.uuid4().hex[:6].upper()}",
            "fraud_type": "mule_network",
            "persona_id": "P-01",
            "strategy_description": strategy_templates.get(cell_topology, strategy_templates["chain"]),
            "variant_parameters": {
                "hop_count": cell_hop_count,
                "timing_interval_hrs": cell_timing,
                "amount_logic": "structured_below_10k",
                "cover_activity": "high" if cell_hop_count >= 4 else "low",
                "topology": cell_topology,
                "extraction_method": cell_extraction,
                "geographic_spread": "domestic",
            },
            "transactions": txns,
            "evasion_techniques": ["structuring below CTR threshold", "cover activity transactions", f"{cell_topology} topology obfuscation"],
            "fraud_indicators_present": ["rapid sequential transfers", "round-trip timing pattern", "new payee relationships"],
        }

    # Persona generator output
    if "persona" in content and ("risk" in content or "generate" in content):
        return {
            "personas": [
                {"persona_id": "P-01", "name": "Viktor Sokolov", "risk_tolerance": "high", "operational_scale": "large", "geographic_scope": "international", "timeline_pressure": "72 hours", "evasion_targets": ["DE", "NL"], "backstory": "Organized crime network, Eastern European operation with 200+ mule accounts.", "resources": "Crypto infrastructure, professional money mules, multiple jurisdictions"},
                {"persona_id": "P-02", "name": "James Harlow", "risk_tolerance": "low", "operational_scale": "small", "geographic_scope": "domestic", "timeline_pressure": "3 weeks", "evasion_targets": ["velocity checks"], "backstory": "Small-scale domestic operation, previously caught, highly cautious.", "resources": "8 recruited mules, no crypto, single city"},
                {"persona_id": "P-03", "name": "Maria Chen", "risk_tolerance": "mid", "operational_scale": "medium", "geographic_scope": "cross-border", "timeline_pressure": "1 week", "evasion_targets": ["CTR thresholds", "new-payee flags"], "backstory": "Mid-level operation using business accounts as cover for layering.", "resources": "Business accounts, 30 mules, partial crypto access"},
            ]
        }

    # Fallback — return a generic fraud constructor variant response
    return _mock_variant_fallback()


def _mock_variant_fallback() -> dict:
    """Fallback mock variant when no agent pattern is detected."""
    import uuid, random
    from datetime import datetime, timedelta

    now = datetime.now()
    acct = lambda: f"ACC-{uuid.uuid4().hex[:8].upper()}"
    a1, a2, a3, a4 = acct(), acct(), acct(), acct()
    txns = [
        {"transaction_id": f"T-{uuid.uuid4().hex[:6].upper()}", "timestamp": (now + timedelta(hours=i * 8)).isoformat(), "amount": round(random.uniform(3000, 9800), 2), "sender_account_id": [a1, a2, a3][min(i, 2)], "receiver_account_id": [a2, a3, a4][min(i, 2)], "merchant_category": "wire_transfer", "channel": "wire_domestic", "is_fraud": True, "fraud_role": f"hop_{i+1}_of_3"}
        for i in range(3)
    ] + [
        {"transaction_id": f"T-{uuid.uuid4().hex[:6].upper()}", "timestamp": (now + timedelta(hours=2)).isoformat(), "amount": round(random.uniform(20, 85), 2), "sender_account_id": a2, "receiver_account_id": acct(), "merchant_category": "grocery", "channel": "card_debit", "is_fraud": False, "fraud_role": "cover_activity"}
    ]
    return {
        "variant_id": f"V-{uuid.uuid4().hex[:6].upper()}",
        "fraud_type": "mule_network",
        "persona_id": "P-01",
        "strategy_description": "Mock: 3-hop domestic chain with burst timing.",
        "variant_parameters": {"hop_count": 3, "timing_interval_hrs": 8, "amount_logic": "structured_below_10k", "cover_activity": "low", "topology": "chain", "extraction_method": "wire", "geographic_spread": "domestic"},
        "transactions": txns,
        "evasion_techniques": ["structuring below CTR threshold", "cover activity transactions"],
        "fraud_indicators_present": ["rapid sequential transfers", "round-trip timing pattern", "new payee relationships"],
    }


def _extract_json_from_text(text: str) -> dict | None:
    """Best-effort extraction of a JSON object from a text that may contain prose."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None
