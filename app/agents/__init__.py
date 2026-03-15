"""agents/ — one class per agent, each with a single public async run() method."""
from __future__ import annotations

from agents.orchestrator import OrchestratorAgent
from agents.persona_generator import PersonaGeneratorAgent
from agents.fraud_constructor import FraudConstructorAgent
from agents.critic import CriticAgent

__all__ = [
    "OrchestratorAgent",
    "PersonaGeneratorAgent",
    "FraudConstructorAgent",
    "CriticAgent",
]
