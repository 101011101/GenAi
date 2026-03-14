from __future__ import annotations

from pydantic import BaseModel, Field, field_validator, model_validator


class RunConfig(BaseModel):
    fraud_description: str
    variant_count: int = 25
    fidelity_level: int = Field(default=3, ge=2, le=4)
    max_parallel: int = 5
    critic_floor: float = 7.0
    max_revisions: int = 2
    persona_count: int = 5
    risk_distribution: dict = Field(
        default_factory=lambda: {"high": 33, "mid": 34, "low": 33}
    )
    geographic_scope: list[str] = Field(default_factory=lambda: ["domestic"])
    mule_context_depth: str = "medium"
    auto_second_pass: bool = False
    demo_mode: bool = False
    cost_cap_usd: float = 20.0

    @field_validator("fidelity_level")
    @classmethod
    def fidelity_must_be_valid(cls, v: int) -> int:
        if v not in (2, 3, 4):
            raise ValueError("fidelity_level must be 2, 3, or 4")
        return v

    @field_validator("mule_context_depth")
    @classmethod
    def mule_depth_must_be_valid(cls, v: str) -> str:
        if v not in ("shallow", "medium", "deep"):
            raise ValueError("mule_context_depth must be 'shallow', 'medium', or 'deep'")
        return v

    @field_validator("critic_floor")
    @classmethod
    def critic_floor_in_range(cls, v: float) -> float:
        if not (1.0 <= v <= 10.0):
            raise ValueError("critic_floor must be between 1.0 and 10.0")
        return v

    @model_validator(mode="after")
    def risk_distribution_sums_to_100(self) -> "RunConfig":
        dist = self.risk_distribution
        required_keys = {"high", "mid", "low"}
        if set(dist.keys()) != required_keys:
            raise ValueError(
                f"risk_distribution must have exactly the keys: {required_keys}"
            )
        total = sum(dist.values())
        if total != 100:
            raise ValueError(
                f"risk_distribution values must sum to 100, got {total}"
            )
        return self
