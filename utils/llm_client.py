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
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMClientError(
                "ANTHROPIC_API_KEY environment variable is not set. "
                "Export it before starting the application: "
                "export ANTHROPIC_API_KEY='sk-ant-...'"
            )
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0

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
                timeout=120.0,  # thinking calls can take longer
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
