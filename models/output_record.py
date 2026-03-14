from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class OutputRecord(BaseModel):
    """Flat row for the final labeled dataset — one record per transaction."""

    # Transaction fields
    transaction_id: str
    timestamp: str
    amount: float
    sender_account_id: str
    receiver_account_id: str
    merchant_category: str
    channel: str
    is_fraud: bool
    fraud_role: str

    # Variant / persona metadata
    variant_id: str
    persona_id: str
    persona_name: str
    fraud_type: str
    variant_parameters: dict = Field(
        description=(
            "Operational parameters: hop_count, timing_interval_hrs, amount_logic, "
            "cover_activity, topology, extraction_method, geographic_spread"
        )
    )

    # Critic evaluation summary
    critic_scores: dict = Field(
        description=(
            "Keys: realism (float 1–10), distinctiveness (float 1–10), passed (bool)"
        )
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Transaction amount must be positive")
        return v

    @field_validator("critic_scores")
    @classmethod
    def critic_scores_must_have_required_keys(cls, v: dict) -> dict:
        required = {"realism", "distinctiveness", "passed"}
        missing = required - set(v.keys())
        if missing:
            raise ValueError(f"critic_scores is missing required keys: {missing}")
        return v
