"""Deterministic coverage cell generator.

Replaces LLM-based cell enumeration in the orchestrator.
Takes the variation_dimensions the orchestrator discovered and produces
exactly target_count cells via Cartesian product + shuffle.
"""
from __future__ import annotations

import random
from itertools import product


def generate_cells(
    dimensions: list[dict],
    target_count: int,
    suggested_persona_count: int,
    seed: int | None = None,
) -> list[dict]:
    """Generate coverage cells from orchestrator dimensions.

    Parameters
    ----------
    dimensions:
        variation_dimensions from OrchestratorOutput. Each dict must have
        "name" and "example_values" keys.
    target_count:
        Exact number of cells to return.
    suggested_persona_count:
        Number of personas available; used for round-robin persona_slot assignment.
    seed:
        Optional random seed for reproducibility.

    Returns
    -------
    list[dict]
        Exactly target_count cell dicts, each with cell_id, dimension_values,
        and persona_slot. Guaranteed to include extreme values because the full
        Cartesian product is enumerated before sampling.
    """
    rng = random.Random(seed)

    # Extract name + example_values; skip dimensions with no values
    dim_names: list[str] = []
    dim_values: list[list] = []
    for dim in dimensions:
        values = dim.get("example_values") or []
        if values:
            dim_names.append(dim["name"])
            dim_values.append(list(values))

    # Degenerate: no usable dimensions
    if not dim_names:
        persona_count = max(suggested_persona_count, 1)
        return [
            {
                "cell_id": f"cell_{i + 1:03d}",
                "dimension_values": {},
                "persona_slot": i % persona_count,
            }
            for i in range(target_count)
        ]

    # Full Cartesian product, then shuffle (preserves all extreme values)
    all_combos: list[tuple] = list(product(*dim_values))
    rng.shuffle(all_combos)

    persona_count = max(suggested_persona_count, 1)
    cells: list[dict] = []
    for i in range(target_count):
        combo = all_combos[i % len(all_combos)]
        cells.append(
            {
                "cell_id": f"cell_{i + 1:03d}",
                "dimension_values": dict(zip(dim_names, combo)),
                "persona_slot": i % persona_count,
            }
        )

    return cells
