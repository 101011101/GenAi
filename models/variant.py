from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Transaction(BaseModel):
    transaction_id: str
    timestamp: str  # ISO 8601 format, e.g. "2025-03-14T09:32:00Z"
    amount: float
    sender_account_id: str
    receiver_account_id: str
    merchant_category: str
    channel: str  # ACH / wire / card / Zelle / Interac / crypto / cash / etc.
    is_fraud: bool
    fraud_role: str  # e.g. "placement", "hop_2_of_5", "extraction", "cover_activity"

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Transaction amount must be positive")
        return v

    @field_validator("timestamp")
    @classmethod
    def timestamp_must_be_nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Transaction timestamp must not be empty")
        return v


class RawVariant(BaseModel):
    variant_id: str
    fraud_type: str
    persona_id: str
    strategy_description: str
    variant_parameters: dict = Field(
        description=(
            "Operational parameters: hop_count, timing_interval_hrs, amount_logic, "
            "cover_activity, topology, extraction_method, geographic_spread"
        )
    )
    transactions: list[Transaction] = Field(default_factory=list)
    evasion_techniques: list[str] = Field(default_factory=list)
    fraud_indicators_present: list[str] = Field(default_factory=list)

    @field_validator("transactions")
    @classmethod
    def must_have_at_least_one_transaction(cls, v: list) -> list:
        if len(v) == 0:
            raise ValueError("A variant must contain at least one transaction")
        return v


# Marker model — structurally identical to RawVariant; signals schema has been confirmed valid.
class ValidatedVariant(RawVariant):
    pass


class ScoredVariant(RawVariant):
    realism_score: float = Field(ge=1.0, le=10.0)
    distinctiveness_score: float = Field(ge=1.0, le=10.0)
    persona_consistency: bool
    label_correctness: bool
    passed: bool
    feedback: str
