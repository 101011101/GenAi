from __future__ import annotations

from pydantic import ValidationError

from models.variant import RawVariant, ValidatedVariant


def validate_raw_variant(data: dict) -> tuple[ValidatedVariant | None, str]:
    """Validate raw agent JSON output against the RawVariant schema.

    This is a pure Python, synchronous function — no LLM calls, no I/O.
    It is intentionally fast so it can run inline in the pipeline without adding latency.

    Returns:
        (ValidatedVariant, "")        — on success
        (None, error_message: str)    — on failure, with a human-readable description
                                        of what was wrong and which field failed.
    """
    try:
        raw = RawVariant.model_validate(data)
    except ValidationError as exc:
        # Build a concise, actionable error message listing each failing field.
        error_lines: list[str] = []
        for error in exc.errors():
            location = " -> ".join(str(loc) for loc in error["loc"])
            message = error["msg"]
            error_lines.append(f"  [{location}] {message}")
        full_message = "RawVariant schema validation failed:\n" + "\n".join(error_lines)
        return None, full_message
    except Exception as exc:
        # Catch unexpected errors (e.g. type coercion issues on non-dict input)
        return None, f"Unexpected validation error: {exc}"

    # Promote to ValidatedVariant (marker type — identical fields, signals schema confirmed)
    validated = ValidatedVariant.model_validate(raw.model_dump())
    return validated, ""
