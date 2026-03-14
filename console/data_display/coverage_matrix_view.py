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

    # --- Build 2D grid if exactly 2 dimensions are available ---
    if len(dimensions) >= 2:
        dim_x = dimensions[0]
        dim_y = dimensions[1]
        x_values = dim_x.get("values", [])
        y_values = dim_y.get("values", [])
        x_name = dim_x.get("name", "dim_0")
        y_name = dim_y.get("name", "dim_1")

        # Index cells by dimension values for fast lookup
        cell_index: dict[tuple, dict] = {}
        for cell in cells:
            dv = cell.get("dimension_values", {})
            key = (dv.get(x_name), dv.get(y_name))
            cell_index[key] = cell

        # Header row
        col_widths = [2] + [1] * len(x_values)
        header_cols = st.columns(col_widths)
        with header_cols[0]:
            st.markdown(f"**{y_name}** \\ **{x_name}**")
        for i, xv in enumerate(x_values):
            with header_cols[i + 1]:
                st.markdown(f"**{xv}**")

        # Data rows
        for yv in y_values:
            row_cols = st.columns(col_widths)
            with row_cols[0]:
                st.markdown(f"**{yv}**")
            for i, xv in enumerate(x_values):
                key = (xv, yv)
                cell = cell_index.get(key)
                if cell:
                    status = cell.get("status", "unassigned")
                    variant_count = cell.get("variant_count", 0)
                    sym, color = _STATUS_CONFIG.get(status, ("░░", "#555555"))
                    tooltip = (
                        f"{x_name}={xv}, {y_name}={yv} | "
                        f"Status: {status} | "
                        f"Variants: {variant_count}"
                    )
                else:
                    sym, color = _STATUS_CONFIG["unassigned"]
                    tooltip = f"{x_name}={xv}, {y_name}={yv} | No cell defined"

                with row_cols[i + 1]:
                    st.markdown(
                        _cell_html(sym, color, tooltip),
                        unsafe_allow_html=True,
                    )
    else:
        # Fallback: flat list of cells when dimension structure is unexpected
        st.markdown("**All cells:**")
        cells_per_row = 8
        rows = [cells[i : i + cells_per_row] for i in range(0, len(cells), cells_per_row)]
        for row_cells in rows:
            cols = st.columns(len(row_cells))
            for col, cell in zip(cols, row_cells):
                status = cell.get("status", "unassigned")
                variant_count = cell.get("variant_count", 0)
                dv = cell.get("dimension_values", {})
                sym, color = _STATUS_CONFIG.get(status, ("░░", "#555555"))
                tooltip = f"{dv} | {status} | {variant_count} variants"
                with col:
                    st.markdown(
                        _cell_html(sym, color, tooltip),
                        unsafe_allow_html=True,
                    )

    # Low-saturation warning
    if total_cells > 0 and pct < 40:
        st.warning(
            f"Coverage saturation: {pct}%. "
            "Consider running a second pass to fill underrepresented cells."
        )
