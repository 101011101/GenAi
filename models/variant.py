from __future__ import annotations

import re

from pydantic import BaseModel, Field, field_validator

_FRAUD_ROLE_PATTERN = re.compile(
    r"^(placement|extraction|cover_activity|hop_\d+_of_\d+)$"
)


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

    @field_validator("fraud_role")
    @classmethod
    def fraud_role_must_match_pattern(cls, v: str) -> str:
        if not _FRAUD_ROLE_PATTERN.match(v):
            raise ValueError(
                f"fraud_role '{v}' does not match allowed pattern: "
                "placement | extraction | cover_activity | hop_N_of_M"
            )
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

    @field_validator("transactions")
    @classmethod
    def validate_label_structure(cls, txns: list) -> list:
        # cover_activity must be is_fraud=False
        for t in txns:
            if t.fraud_role == "cover_activity" and t.is_fraud:
                raise ValueError(
                    f"Transaction {t.transaction_id}: fraud_role='cover_activity' "
                    "but is_fraud=True — cover activity must have is_fraud=False."
                )

        # placement / hop_* / extraction must be is_fraud=True
        for t in txns:
            if t.fraud_role in ("placement", "extraction") and not t.is_fraud:
                raise ValueError(
                    f"Transaction {t.transaction_id}: fraud_role='{t.fraud_role}' "
                    "but is_fraud=False — fraud roles must have is_fraud=True."
                )
            if t.fraud_role.startswith("hop_") and not t.is_fraud:
                raise ValueError(
                    f"Transaction {t.transaction_id}: fraud_role='{t.fraud_role}' "
                    "but is_fraud=False."
                )

        # at least one placement (multi-victim fan-out schemes may have multiple)
        placements = [t for t in txns if t.fraud_role == "placement"]
        if len(placements) == 0:
            raise ValueError("No 'placement' transaction found — at least one is required.")

        # at least one extraction
        if not any(t.fraud_role == "extraction" for t in txns):
            raise ValueError("No 'extraction' transaction found — at least one is required.")

        # hop labels must be sequential (hop_1_of_N, hop_2_of_N, ...)
        hop_txns = [t for t in txns if t.fraud_role.startswith("hop_")]
        if hop_txns:
            parsed = []
            for t in hop_txns:
                m = re.match(r"^hop_(\d+)_of_(\d+)$", t.fraud_role)
                if m:
                    parsed.append((int(m.group(1)), int(m.group(2))))
            if parsed:
                totals = {p[1] for p in parsed}
                if len(totals) > 1:
                    raise ValueError(
                        f"Inconsistent hop total across labels — found M values: {sorted(totals)}"
                    )
                total = next(iter(totals))
                unique_ns = sorted(set(p[0] for p in parsed))
                # Fan-out topologies produce multiple transactions with the same hop index.
                # Validate that every index 1..M appears at least once (no gaps).
                expected = list(range(1, total + 1))
                if unique_ns != expected:
                    raise ValueError(
                        f"Hop indices have gaps — found unique indices {unique_ns}, "
                        f"expected every index in {expected} to appear at least once"
                    )

        return txns


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
