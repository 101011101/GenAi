from __future__ import annotations

import threading
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class VariantSummary:
    variant_id: str
    persona_name: str
    parameters_summary: str  # human-readable one-liner, e.g. "6-hop fan-out, crypto extraction, international"
    critic_score: float
    status: str  # "approved" / "rejected" / "revised"
    strategy_description: str  # first 200 chars of the agent's strategy text
    completed_at: str  # ISO timestamp


class RunState:
    """
    Shared state bridge between the background pipeline thread and the Streamlit console.

    The pipeline writes to this object from a background thread.
    The console reads from it on the main thread via Streamlit's polling loop.

    All mutation methods acquire a threading.Lock before modifying state.
    Reads do not acquire the lock — they are treated as eventually consistent
    for display purposes, which is acceptable for a 1-second polling interval.
    """

    def __init__(self, variants_total: int = 0) -> None:
        self._lock = threading.Lock()

        self.variants_completed: int = 0
        self.variants_total: int = variants_total
        self.active_agent_count: int = 0
        self.variant_log: list[VariantSummary] = []
        self.control_signal: str = "run"  # "run" | "pause" | "stop"
        self.errors: list[str] = []
        self.is_complete: bool = False
        self.current_phase: str = "idle"
        self.total_cost_usd: float = 0.0
        self.revisions_count: int = 0
        self.rejections_count: int = 0

    # ------------------------------------------------------------------
    # Mutation methods — all thread-safe
    # ------------------------------------------------------------------

    def update_variant(self, summary: VariantSummary) -> None:
        """
        Record a completed variant.

        Appends the summary to variant_log, increments variants_completed,
        and decrements active_agent_count. Tracks rejections and revisions
        via the summary status field so callers do not need to update those
        counters separately.
        """
        with self._lock:
            self.variant_log.append(summary)
            self.variants_completed += 1
            self.active_agent_count = max(0, self.active_agent_count - 1)
            if summary.status == "rejected":
                self.rejections_count += 1
            elif summary.status == "revised":
                self.revisions_count += 1

    def increment_active(self) -> None:
        """Increment active_agent_count when a new agent task is spawned."""
        with self._lock:
            self.active_agent_count += 1

    def decrement_active(self) -> None:
        """Decrement active_agent_count when an agent task finishes (without producing a variant)."""
        with self._lock:
            self.active_agent_count = max(0, self.active_agent_count - 1)

    def set_control(self, signal: str) -> None:
        """
        Set the control signal.

        Valid values: "run", "pause", "stop".
        The runner checks this between each parallel batch and acts accordingly.
        """
        if signal not in ("run", "pause", "stop"):
            raise ValueError(f"Invalid control signal: {signal!r}. Must be 'run', 'pause', or 'stop'.")
        with self._lock:
            self.control_signal = signal

    def add_error(self, msg: str) -> None:
        """Append an error message to the error log."""
        with self._lock:
            self.errors.append(msg)

    def set_phase(self, phase: str) -> None:
        """Update the current pipeline phase label (used by the monitoring panel)."""
        with self._lock:
            self.current_phase = phase

    def add_cost(self, usd: float) -> None:
        """Accumulate API cost in USD."""
        with self._lock:
            self.total_cost_usd += usd

    def mark_complete(self) -> None:
        """Mark the run as finished and set phase to 'complete'."""
        with self._lock:
            self.is_complete = True
            self.current_phase = "complete"

    # ------------------------------------------------------------------
    # Convenience read — no lock (eventually consistent is fine for display)
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Return a plain-dict snapshot suitable for serialization or display."""
        return {
            "variants_completed": self.variants_completed,
            "variants_total": self.variants_total,
            "active_agent_count": self.active_agent_count,
            "control_signal": self.control_signal,
            "is_complete": self.is_complete,
            "current_phase": self.current_phase,
            "total_cost_usd": self.total_cost_usd,
            "revisions_count": self.revisions_count,
            "rejections_count": self.rejections_count,
            "error_count": len(self.errors),
            "variant_count": len(self.variant_log),
        }
