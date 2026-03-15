from __future__ import annotations

import asyncio
import json
import logging
import os
import random
import time
import uuid
from datetime import datetime, timedelta
from typing import Callable

logger = logging.getLogger(__name__)

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
        result = await client.call(system_prompt, messages, model="claude-sonnet-4-6")
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
                if not raw_text.strip():
                    # Model returned no text content — send a clean retry with no
                    # assistant prefill (echoing "(empty)" confuses the model).
                    last_error = ValueError("API returned empty response")
                    current_messages = list(messages) + [
                        {
                            "role": "user",
                            "content": (
                                "You returned an empty response. "
                                "Return only a valid JSON object matching the schema. "
                                "Do not include any text outside the JSON object."
                            ),
                        }
                    ]
                    continue

                try:
                    return json.loads(raw_text)
                except json.JSONDecodeError as parse_err:
                    last_error = parse_err
                    # Reset to original messages + a short preview of the bad response.
                    # Using list(messages) (not current_messages) discards accumulated
                    # correction turns so token cost stays flat across retries.
                    bad_preview = raw_text[:200]
                    current_messages = list(messages) + [
                        {"role": "assistant", "content": bad_preview},
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
                last_error = exc
                await self._backoff(attempt)
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
        timeout: float = 120.0,
    ) -> str:
        """Stream the response, invoke *on_text* for each text chunk, return full text.

        Retries up to 3 times on rate-limit (429), overload (529), and timeout errors.
        """
        if self._mock:
            data = _mock_response(messages)
            text = json.dumps(data)
            if on_text:
                on_text(text)
            await asyncio.sleep(0.3)
            return text

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                return await asyncio.wait_for(
                    self._stream_all(system_prompt, messages, model, on_text),
                    timeout=timeout,
                )
            except asyncio.TimeoutError as exc:
                last_error = exc
                await self._backoff(attempt)
            except anthropic.RateLimitError as exc:
                last_error = exc
                await self._backoff(attempt)
            except anthropic.InternalServerError as exc:
                if hasattr(exc, "status_code") and exc.status_code == 529:
                    last_error = exc
                    await self._backoff(attempt)
                else:
                    raise LLMClientError(f"Streaming call failed: {exc}") from exc
            except Exception as exc:
                raise LLMClientError(f"Streaming call failed: {exc}") from exc

        raise LLMClientError(
            f"Streaming call failed after 3 attempts. Last error: {last_error}"
        ) from last_error

    async def _stream_all(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        on_text: Callable[[str], None] | None,
    ) -> str:
        """Execute one streaming request and return the full text."""
        full_text_parts: list[str] = []
        async with self._client.messages.stream(
            model=model,
            max_tokens=32768,
            system=system_prompt,
            messages=messages,
        ) as stream:
            async for chunk in stream.text_stream:
                full_text_parts.append(chunk)
                if on_text is not None:
                    on_text(chunk)

            final_msg = await stream.get_final_message()
            self.total_input_tokens += final_msg.usage.input_tokens
            self.total_output_tokens += final_msg.usage.output_tokens

        return "".join(full_text_parts)

    async def call_with_thinking(
        self,
        system_prompt: str,
        messages: list[dict],
        model: str,
        budget_tokens: int = 5000,
        timeout: float = 300.0,
    ) -> dict:
        """Call the API with extended thinking enabled (used by the orchestrator).

        Returns the first top-level JSON object found in the response text.
        Extended thinking responses may include a thinking block before the answer block.
        """
        if self._mock:
            await asyncio.sleep(0.5)
            return _mock_response(messages)

        last_error: Exception | None = None
        for attempt in range(3):
            try:
                response = await asyncio.wait_for(
                    self._client.messages.create(
                        model=model,
                        max_tokens=budget_tokens + 8192,
                        thinking={
                            "type": "enabled",
                            "budget_tokens": budget_tokens,
                        },
                        system=system_prompt,
                        messages=messages,
                    ),
                    timeout=timeout,
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
                    extracted = _extract_json_from_text(text_content)
                    if extracted is not None:
                        return extracted
                    raise LLMClientError(
                        f"Could not parse JSON from thinking response. Raw text: {text_content[:500]}"
                    )

            except asyncio.TimeoutError as exc:
                last_error = exc
                await self._backoff(attempt)
            except anthropic.RateLimitError as exc:
                last_error = exc
                await self._backoff(attempt)
            except anthropic.InternalServerError as exc:
                if hasattr(exc, "status_code") and exc.status_code == 529:
                    last_error = exc
                    await self._backoff(attempt)
                else:
                    raise LLMClientError(f"call_with_thinking failed: {exc}") from exc
            except LLMClientError:
                raise
            except Exception as exc:
                raise LLMClientError(f"call_with_thinking failed: {exc}") from exc

        raise LLMClientError(
            f"call_with_thinking failed after 3 attempts. Last error: {last_error}"
        ) from last_error

    async def close(self) -> None:
        """Close the underlying HTTP client and release connections."""
        if self._client is not None:
            await self._client.close()

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
            "max_tokens": 16384,
            "system": system_prompt,
            "messages": messages,
        }

        if response_schema is not None:
            schema_instruction = (
                "\n\nYou MUST respond with a single valid JSON object that strictly "
                f"conforms to this JSON schema:\n{json.dumps(response_schema, indent=2)}\n"
                "Return ONLY the JSON object — no explanation, no markdown fences, no preamble."
            )
            kwargs["system"] = system_prompt + schema_instruction

        response = await asyncio.wait_for(
            self._client.messages.create(**kwargs),
            timeout=timeout,
        )

        self.total_input_tokens += response.usage.input_tokens
        self.total_output_tokens += response.usage.output_tokens

        text = ""
        for block in response.content:
            if block.type == "text":
                text = block.text
                break

        if not text:
            block_types = [getattr(b, "type", "unknown") for b in response.content]
            logger.warning(
                "Empty text response from API. stop_reason=%s blocks=%s",
                response.stop_reason,
                block_types,
            )

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

    Detects which agent is calling based on the LAST user message content only
    (not accumulated history) to avoid misfiring on retry turns.
    """
    # Use only the last user message for reliable branch detection
    last_user_content = ""
    for m in reversed(messages):
        if m.get("role") == "user" and isinstance(m.get("content"), str):
            last_user_content = m["content"].lower()
            break

    content = last_user_content

    # Fraud constructor — check first: its steps have explicit step labels
    if "step 1: persona analysis" in content or "step 4: transaction generation" in content or "step 5: self-review" in content:
        now = datetime.now()
        acct = lambda: f"ACC-{uuid.uuid4().hex[:8].upper()}"
        a1, a2, a3, a4 = acct(), acct(), acct(), acct()
        txns = [
            {"transaction_id": f"T-{uuid.uuid4().hex[:6].upper()}", "timestamp": (now + timedelta(hours=i*8)).isoformat(), "amount": round(random.uniform(3000, 9800), 2), "sender_account_id": [a1,a2,a3][min(i,2)], "receiver_account_id": [a2,a3,a4][min(i,2)], "merchant_category": "wire_transfer", "channel": "wire_domestic", "is_fraud": True, "fraud_role": f"hop_{i+1}_of_3"}
            for i in range(3)
        ] + [
            {"transaction_id": f"T-{uuid.uuid4().hex[:6].upper()}", "timestamp": (now + timedelta(hours=2)).isoformat(), "amount": round(random.uniform(20, 85), 2), "sender_account_id": a2, "receiver_account_id": acct(), "merchant_category": "grocery", "channel": "card_debit", "is_fraud": False, "fraud_role": "cover_activity"}
        ]
        return {
            "variant_id": f"V-{uuid.uuid4().hex[:6].upper()}",
            "fraud_type": "mule_network",
            "persona_id": "P-01",
            "strategy_description": "Mock: 3-hop domestic chain with burst timing. Funds moved via same-day wire transfers structured below $10K CTR threshold. Cover activity via grocery purchases on mule accounts.",
            "variant_parameters": {"hop_count": 3, "timing_interval_hrs": 8, "amount_logic": "structured_below_10k", "cover_activity": "low", "topology": "chain", "extraction_method": "wire", "geographic_spread": "domestic"},
            "transactions": txns,
            "evasion_techniques": ["structuring below CTR threshold", "cover activity transactions"],
            "fraud_indicators_present": ["rapid sequential transfers", "round-trip timing pattern", "new payee relationships"],
        }

    # Orchestrator output
    if "variation_dimensions" in content or "coverage_cells" in content or "decompose" in content:
        cells = []
        for i in range(6):
            cells.append({
                "cell_id": f"C-{i+1:02d}",
                "dimension_values": {
                    "hop_count": random.choice([2, 3, 4, 5, 6]),
                    "timing_interval_hrs": random.choice([1, 8, 24, 72]),
                    "topology": random.choice(["chain", "fan_out", "hybrid"]),
                    "extraction_method": random.choice(["wire", "crypto", "cash"]),
                },
                "persona_slot": i % 3,
            })
        return {
            "variation_dimensions": [
                {"name": "hop_count", "description": "Number of mule hops", "range_low": "2", "range_high": "8", "example_values": ["2", "4", "6"]},
                {"name": "timing_interval_hrs", "description": "Hours between hops", "range_low": "1", "range_high": "168", "example_values": ["1", "24", "72"]},
                {"name": "topology", "description": "Network shape", "range_low": "chain", "range_high": "fan_out", "example_values": ["chain", "fan_out", "hybrid"]},
                {"name": "extraction_method", "description": "Final extraction channel", "range_low": "wire", "range_high": "crypto", "example_values": ["wire", "crypto", "cash"]},
            ],
            "coverage_cells": cells,
            "suggested_persona_count": 3,
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

    # Critic output
    if "realism" in content or "critic" in content or "score this variant" in content:
        score = round(random.uniform(6.5, 9.2), 1)
        return {
            "realism_score": score,
            "distinctiveness_score": round(random.uniform(6.0, 8.5), 1),
            "feedback": "",
        }

    # Fallback — should not normally be reached
    return {}


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
