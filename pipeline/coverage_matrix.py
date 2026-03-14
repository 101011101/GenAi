from __future__ import annotations

import threading
import uuid
from typing import Any


class CoverageMatrix:
    """
    Tracks variant space coverage across a grid of cells.

    Each cell represents one specific combination of variation dimension values,
    e.g. {"hop_count": 3, "topology": "chain", "timing": "same_day"}.

    The orchestrator populates dimension definitions and the initial cell list.
    The runner assigns cells to agents, marks them completed or rejected,
    and queries for underrepresented cells to drive second-pass runs.

    All mutation methods are thread-safe.
    """

    def __init__(
        self,
        variation_dimensions: list[dict],
        cells: list[dict],
    ) -> None:
        """
        Parameters
        ----------
        variation_dimensions:
            List of dimension descriptors returned by the orchestrator, e.g.:
            [
                {"name": "hop_count", "values": [2, 3, 4, 5, 6]},
                {"name": "topology",  "values": ["chain", "fan_out", "hybrid"]},
            ]
        cells:
            List of cell dicts, each with at least:
            {
                "cell_id": str,          # unique identifier for this cell
                "dimension_values": dict  # e.g. {"hop_count": 3, "topology": "chain"}
            }
            Any extra keys are preserved.
        """
        self._lock = threading.Lock()

        self.variation_dimensions: list[dict] = variation_dimensions

        # Internal cell store: cell_id → cell dict.
        # Adds tracking fields if they are not already present.
        self._cells: dict[str, dict] = {}
        for raw_cell in cells:
            cell = dict(raw_cell)  # shallow copy — do not mutate caller's data
            cell_id = cell.get("cell_id") or str(uuid.uuid4())
            cell["cell_id"] = cell_id
            cell.setdefault("status", "unassigned")          # unassigned | in_progress | completed | rejected
            cell.setdefault("assigned_variant_ids", [])
            self._cells[cell_id] = cell

    # ------------------------------------------------------------------
    # Mutation methods
    # ------------------------------------------------------------------

    def assign_cell(self, cell_id: str, agent_id: str) -> dict | None:
        """
        Attempt to claim a cell for an agent.

        Marks the cell "in_progress" and records which agent claimed it.
        Returns the cell dict on success, or None if the cell does not exist
        or is already taken (status is not "unassigned").

        This is the primary concurrency guard — two threads racing to assign
        the same cell will result in exactly one winner.
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                return None
            if cell["status"] != "unassigned":
                return None
            cell["status"] = "in_progress"
            cell["assigned_agent_id"] = agent_id
            return dict(cell)  # return copy so caller cannot mutate internal state

    def complete_cell(self, cell_id: str, variant_id: str) -> None:
        """
        Mark a cell completed and record the variant that filled it.

        Safe to call even if the cell does not exist (no-op).
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                return
            cell["status"] = "completed"
            cell["assigned_variant_ids"].append(variant_id)

    def reject_cell(self, cell_id: str) -> None:
        """
        Return a cell to "unassigned" so the runner can reassign it.

        Called when the critic permanently rejects a variant after all
        revision attempts have been exhausted, or when schema validation fails.
        """
        with self._lock:
            cell = self._cells.get(cell_id)
            if cell is None:
                return
            cell["status"] = "unassigned"
            cell.pop("assigned_agent_id", None)

    def get_next_unassigned(self) -> dict | None:
        """
        Return the first unassigned cell, or None if all cells are assigned.

        Returns a copy of the cell dict so the caller cannot mutate internal state.
        Does NOT claim the cell — callers must call assign_cell() to claim it.
        This separation allows the runner to pass cell_id to an agent before
        claiming, without holding the lock across agent construction.
        """
        with self._lock:
            for cell in self._cells.values():
                if cell["status"] == "unassigned":
                    return dict(cell)
            return None

    # ------------------------------------------------------------------
    # Query methods (read-only — lock still used for consistency)
    # ------------------------------------------------------------------

    def check_saturation(self) -> float:
        """
        Return the fraction of cells that are "completed" (0.0 to 1.0).

        Returns 0.0 if there are no cells.
        """
        with self._lock:
            total = len(self._cells)
            if total == 0:
                return 0.0
            completed = sum(1 for c in self._cells.values() if c["status"] == "completed")
            return completed / total

    def get_underrepresented_cells(self) -> list[dict]:
        """
        Return all cells with zero completed variants.

        Includes cells in any status (unassigned, in_progress, rejected) that
        have an empty assigned_variant_ids list. The runner uses this list to
        drive the second-pass targeting when auto_second_pass is enabled.
        """
        with self._lock:
            return [
                dict(cell)
                for cell in self._cells.values()
                if len(cell["assigned_variant_ids"]) == 0
            ]

    def to_display_dict(self) -> dict:
        """
        Return a serializable dict for console rendering.

        Structure:
        {
            "dimensions": [ {name, values}, ... ],
            "cells": [
                {
                    "cell_id": str,
                    "dimension_values": dict,
                    "status": str,
                    "variant_count": int
                },
                ...
            ]
        }
        """
        with self._lock:
            cells_display = [
                {
                    "cell_id": cell["cell_id"],
                    "dimension_values": cell.get("dimension_values", {}),
                    "status": cell["status"],
                    "variant_count": len(cell["assigned_variant_ids"]),
                }
                for cell in self._cells.values()
            ]
        return {
            "dimensions": self.variation_dimensions,
            "cells": cells_display,
        }

    def get_stats(self) -> dict:
        """
        Return a summary of cell statuses.

        Returns:
        {
            "total": int,
            "unassigned": int,
            "in_progress": int,
            "completed": int,
            "rejected": int
        }
        """
        with self._lock:
            counts: dict[str, int] = {
                "total": len(self._cells),
                "unassigned": 0,
                "in_progress": 0,
                "completed": 0,
                "rejected": 0,
            }
            for cell in self._cells.values():
                status = cell["status"]
                if status in counts:
                    counts[status] += 1
            return counts
