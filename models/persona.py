from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class Persona(BaseModel):
    persona_id: str
    name: str
    risk_tolerance: str
    operational_scale: str
    geographic_scope: str
    timeline_pressure: str
    evasion_targets: list[str] = Field(default_factory=list)
    backstory: str
    resources: str

    @field_validator("risk_tolerance")
    @classmethod
    def risk_tolerance_valid(cls, v: str) -> str:
        if v not in ("high", "mid", "low"):
            raise ValueError("risk_tolerance must be 'high', 'mid', or 'low'")
        return v

    @field_validator("operational_scale")
    @classmethod
    def operational_scale_valid(cls, v: str) -> str:
        if v not in ("small", "medium", "large"):
            raise ValueError("operational_scale must be 'small', 'medium', or 'large'")
        return v
