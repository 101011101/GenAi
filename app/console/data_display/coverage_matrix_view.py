"""
Coverage matrix visualization for the fraud data generation console.

Renders the coverage matrix as a visual grid using Streamlit columns.
Reads from a CoverageMatrix.to_display_dict() result — no LLM calls.
"""
from __future__ import annotations

from typing import Any

import streamlit as st

# Status → display character + color
_STATUS_CONFIG: dict[str, tuple[str, str]] = {
    "unassigned":  ("░░", "#555555"),
    "in_progress": ("▓▓", "#3498DB"),
    "completed":   ("██", "#2ECC71"),
    "rejected":    ("✗✗", "#E74C3C"),
}


def _cell_html(symbol: str, color: str, tooltip: str) -> str:
    """Render a single coverage matrix cell as an HTML block."""
    return (
        f'<div title="{tooltip}" style="'
        f"display:inline-block;"
        f"font-family:monospace;"
        f"font-size:1.4em;"
        f"color:{color};"
        f"padding:2px 4px;"
        f"border-radius:3px;"
        f'cursor:default;">'
        f"{symbol}"
        f"</div>"
    )


def render_coverage_matrix(matrix_display_dict: dict | None) -> None:
    """
    Render the coverage matrix as a visual grid.

    Parameters
    ----------
    matrix_display_dict : dict | None
        Output of CoverageMatrix.to_display_dict(), or None if not yet available.
        Expected structure:
        {
            "dimensions": [ {"name": str, "values": list}, ... ],
            "cells": [
                {"cell_id": str, "dimension_values": dict, "status": str, "variant_count": int},
                ...
            ]
        }
    """
    st.markdown("**Coverage Matrix**")

    if not matrix_display_dict:
        st.caption("Coverage matrix will appear here once the orchestrator builds the variant space.")
        # Show empty placeholder grid
        st.markdown(
            '<div style="color:#555;font-family:monospace;font-size:1.2em;">'
            + ("░░ " * 8 + "<br>") * 4
            + "</div>",
            unsafe_allow_html=True,
        )
        return

    dimensions: list[dict] = matrix_display_dict.get("dimensions", [])
    cells: list[dict] = matrix_display_dict.get("cells", [])

    if not cells:
        st.caption("No cells defined yet.")
        return

    # --- Saturation stats ---
    total_cells = len(cells)
    completed_cells = sum(1 for c in cells if c.get("status") == "completed")
    pct = int(completed_cells / total_cells * 100) if total_cells > 0 else 0
    st.caption(f"{completed_cells} / {total_cells} cells covered ({pct}%)")

    # --- Legend ---
    legend_cols = st.columns(4)
    legend_items = [
        ("░░", "#555555", "Unassigned"),
        ("▓▓", "#3498DB", "In Progress"),
        ("██", "#2ECC71", "Completed"),
        ("✗✗", "#E74C3C", "Rejected"),
    ]
    for col, (sym, color, label) in zip(legend_cols, legend_items):
        with col:
            st.markdown(
                f'<span style="color:{color};font-family:monospace;">{sym}</span> {label}',
                unsafe_allow_html=True,
            )

    st.markdown("")  # spacer

    # --- Pick the two best dimensions for a 2D grid ---
    # Prefer hop_count and topology as primary axes (most visually meaningful
    # for mule network fraud). Fall back to first two dimensions if not found.
    _PREFERRED_AXES = ["hop_count", "topology"]

    if len(dimensions) >= 2:
        dim_by_name = {d.get("name"): d for d in dimensions}
        if all(n in dim_by_name for n in _PREFERRED_AXES):
            dim_x = dim_by_name[_PREFERRED_AXES[0]]
            dim_y = dim_by_name[_PREFERRED_AXES[1]]
        else:
            dim_x = dimensions[0]
            dim_y = dimensions[1]

        x_values = dim_x.get("values", [])
        y_values = dim_y.get("values", [])
        x_name = dim_x.get("name", "dim_0")
        y_name = dim_y.get("name", "dim_1")

        # Index cells by (x, y) — aggregate when multiple cells map to same slot
        cell_index: dict[tuple, list[dict]] = {}
        for cell in cells:
            dv = cell.get("dimension_values", {})
            key = (str(dv.get(x_name)), str(dv.get(y_name)))
            cell_index.setdefault(key, []).append(cell)

        # Build as a single HTML table for reliable grid layout
        html_rows = []

        # Header row
        header = f'<th style="padding:6px 12px;text-align:left;font-size:0.85em;">{y_name} \\ {x_name}</th>'
        for xv in x_values:
            header += f'<th style="padding:6px 12px;text-align:center;font-size:0.85em;">{xv}</th>'
        html_rows.append(f"<tr>{header}</tr>")

        # Data rows
        for yv in y_values:
            row_html = f'<td style="padding:6px 12px;font-weight:bold;font-size:0.85em;">{yv}</td>'
            for xv in x_values:
                key = (str(xv), str(yv))
                slot_cells = cell_index.get(key, [])
                if slot_cells:
                    # Pick the best status: completed > in_progress > rejected > unassigned
                    priority = {"completed": 3, "in_progress": 2, "rejected": 1, "unassigned": 0}
                    best = max(slot_cells, key=lambda c: priority.get(c.get("status", "unassigned"), 0))
                    status = best.get("status", "unassigned")
                    variant_count = sum(c.get("variant_count", 0) for c in slot_cells)
                    sym, color = _STATUS_CONFIG.get(status, ("░░", "#555555"))
                    tooltip = (
                        f"{x_name}={xv}, {y_name}={yv} | "
                        f"Status: {status} | "
                        f"Variants: {variant_count}"
                    )
                else:
                    sym, color = _STATUS_CONFIG["unassigned"]
                    tooltip = f"{x_name}={xv}, {y_name}={yv} | No cell defined"

                row_html += (
                    f'<td title="{tooltip}" style="'
                    f"text-align:center;padding:6px 12px;"
                    f"font-family:monospace;font-size:1.4em;"
                    f'color:{color};cursor:default;">'
                    f"{sym}</td>"
                )
            html_rows.append(f"<tr>{row_html}</tr>")

        table_html = (
            '<table style="border-collapse:collapse;margin-top:4px;">'
            + "".join(html_rows)
            + "</table>"
        )
        st.markdown(table_html, unsafe_allow_html=True)

    else:
        # Fallback: flat list of cells when dimension structure is unexpected
        flat_html = ""
        for cell in cells:
            status = cell.get("status", "unassigned")
            dv = cell.get("dimension_values", {})
            sym, color = _STATUS_CONFIG.get(status, ("░░", "#555555"))
            tooltip = f"{dv} | {status}"
            flat_html += (
                f'<span title="{tooltip}" style="'
                f"font-family:monospace;font-size:1.4em;"
                f'color:{color};padding:2px 4px;">'
                f"{sym}</span> "
            )
        st.markdown(flat_html, unsafe_allow_html=True)

    # Low-saturation warning
    if total_cells > 0 and pct < 40:
        st.warning(
            f"Coverage saturation: {pct}%. "
            "Consider running a second pass to fill underrepresented cells."
        )
