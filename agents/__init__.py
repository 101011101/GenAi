"""agents/ — one class per agent, each with a single public async run() method."""
from __future__ import annotations

try:
    from agents.orchestrator import OrchestratorAgent
except ImportError:
    OrchestratorAgent = None  # type: ignore[assignment,misc]

try:
    from agents.persona_generator import PersonaGeneratorAgent
except ImportError:
    PersonaGeneratorAgent = None  # type: ignore[assignment,misc]

from agents.fraud_constructor import FraudConstructorAgent
from agents.critic import CriticAgent

__all__ = [
    "OrchestratorAgent",
    "PersonaGeneratorAgent",
    "FraudConstructorAgent",
    "CriticAgent",
]
