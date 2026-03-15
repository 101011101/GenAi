"use client";

import { CellStatus, MatrixData } from "@/lib/api";

interface CoverageMatrixProps {
  cells: CellStatus[];
  dimensions: MatrixData["dimensions"];
}

function cellBg(status: CellStatus["status"]): { background: string; border: string } {
  switch (status) {
    case "completed":  return { background: "var(--color-green-light)", border: "var(--color-green-border)" };
    case "in_progress": return { background: "var(--color-accent-light)", border: "var(--color-accent-border)" };
    case "failed":     return { background: "var(--color-red-light)", border: "var(--color-red-border)" };
    default:           return { background: "var(--color-surface2)", border: "var(--color-border)" };
  }
}

function CellBox({ cell }: { cell: CellStatus }) {
  const colors = cellBg(cell.status);
  const isInProgress = cell.status === "in_progress";

  return (
    <div
      className={isInProgress ? "pulse" : undefined}
      title={`${cell.cell_id}${cell.assigned_persona_name ? ` · ${cell.assigned_persona_name}` : ""}${cell.critic_score != null ? ` · score ${cell.critic_score}` : ""}`}
      style={{
        height: 14,
        borderRadius: 3,
        background: colors.background,
        border: `1px solid ${colors.border}`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        cursor: "default",
      }}
    >
      {cell.critic_score != null && (
        <span
          style={{
            fontSize: "0.5rem",
            fontFamily: "var(--font-mono)",
            color: cell.critic_score >= 7 ? "var(--color-green)" : "var(--color-red)",
            lineHeight: 1,
          }}
        >
          {cell.critic_score.toFixed(0)}
        </span>
      )}
    </div>
  );
}

const LEGEND = [
  { label: "Completed", bg: "var(--color-green-light)", border: "var(--color-green-border)" },
  { label: "In Progress", bg: "var(--color-accent-light)", border: "var(--color-accent-border)" },
  { label: "Failed",    bg: "var(--color-red-light)", border: "var(--color-red-border)" },
  { label: "Empty",     bg: "var(--color-surface2)", border: "var(--color-border)" },
];

function FlatGrid({ cells }: { cells: CellStatus[] }) {
  const cols = Math.min(6, cells.length);
  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${cols}, 1fr)`, gap: 3 }}>
        {cells.map((cell) => <CellBox key={cell.cell_id} cell={cell} />)}
      </div>
      <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
        {LEGEND.map((l) => (
          <div key={l.label} style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.6rem", color: "var(--color-muted)" }}>
            <div style={{ width: 10, height: 10, borderRadius: 3, background: l.bg, border: `1px solid ${l.border}`, flexShrink: 0 }} />
            {l.label}
          </div>
        ))}
      </div>
    </div>
  );
}

export default function CoverageMatrix({ cells, dimensions }: CoverageMatrixProps) {
  if (!cells || cells.length === 0) {
    return (
      <div style={{ fontSize: "0.7rem", color: "var(--color-faint)", padding: "0.5rem 0" }}>
        No coverage data yet.
      </div>
    );
  }

  // 2+ dimensions: render as table
  if (dimensions && dimensions.length >= 2) {
    const rowDim = dimensions[0];
    const colDim = dimensions[1];
    const rowVals = (rowDim.values ?? []) as string[];
    const colVals = (colDim.values ?? []) as string[];

    // Fall back to flat grid if either axis has no values
    if (rowVals.length === 0 || colVals.length === 0) {
      return <FlatGrid cells={cells} />;
    }

    // Build lookup: "rowVal|colVal" -> CellStatus
    const lookup: Record<string, CellStatus> = {};
    for (const cell of cells) {
      const rv = cell.dimension_values[rowDim.name];
      const cv = cell.dimension_values[colDim.name];
      if (rv !== undefined && cv !== undefined) {
        lookup[`${rv}|${cv}`] = cell;
      }
    }

    return (
      <div>
        {/* Table */}
        <div style={{ overflowX: "auto" }}>
          <table style={{ borderCollapse: "collapse", width: "100%", fontSize: "0.58rem" }}>
            <thead>
              <tr>
                <th
                  style={{
                    padding: "0.2rem 0.3rem",
                    color: "var(--color-faint)",
                    fontWeight: 700,
                    textAlign: "left",
                    whiteSpace: "nowrap",
                    borderBottom: "1px solid var(--color-border)",
                  }}
                >
                  {rowDim.name}
                </th>
                {colVals.map((cv) => (
                  <th
                    key={cv}
                    style={{
                      padding: "0.2rem 0.3rem",
                      color: "var(--color-faint)",
                      fontWeight: 700,
                      textAlign: "center",
                      whiteSpace: "nowrap",
                      borderBottom: "1px solid var(--color-border)",
                      maxWidth: 40,
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                    }}
                    title={String(cv)}
                  >
                    {String(cv).slice(0, 5)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rowVals.map((rv) => (
                <tr key={rv}>
                  <td
                    style={{
                      padding: "0.2rem 0.3rem",
                      color: "var(--color-muted)",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                      borderBottom: "1px solid var(--color-border)",
                    }}
                    title={String(rv)}
                  >
                    {String(rv).slice(0, 6)}
                  </td>
                  {colVals.map((cv) => {
                    const cell = lookup[`${rv}|${cv}`];
                    if (!cell) {
                      return (
                        <td key={cv} style={{ padding: "0.15rem 0.3rem", borderBottom: "1px solid var(--color-border)" }}>
                          <div style={{ height: 14, borderRadius: 3, background: "var(--color-surface2)", border: "1px solid var(--color-border)" }} />
                        </td>
                      );
                    }
                    return (
                      <td key={cv} style={{ padding: "0.15rem 0.3rem", borderBottom: "1px solid var(--color-border)" }}>
                        <CellBox cell={cell} />
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div style={{ marginTop: "0.5rem", display: "flex", flexWrap: "wrap", gap: "0.4rem" }}>
          {LEGEND.map((l) => (
            <div key={l.label} style={{ display: "flex", alignItems: "center", gap: "0.3rem", fontSize: "0.6rem", color: "var(--color-muted)" }}>
              <div style={{ width: 10, height: 10, borderRadius: 3, background: l.bg, border: `1px solid ${l.border}`, flexShrink: 0 }} />
              {l.label}
            </div>
          ))}
        </div>
      </div>
    );
  }

  // 1 dimension or no dimensions: flat grid
  return <FlatGrid cells={cells} />;
}
