"use client";

import { useEffect, useState } from "react";
import { getMatrix, type ResultsData, type MatrixData, type CellStatus } from "@/lib/api";
import CoverageMatrix from "./CoverageMatrix";

interface Props {
  runId: string;
  results: ResultsData;
}

function CellTooltip({ cell }: { cell: CellStatus }) {
  const dims = Object.entries(cell.dimension_values)
    .map(([k, v]) => `${k}: ${v}`)
    .join(", ");
  return (
    <div
      style={{
        position: "absolute",
        bottom: "calc(100% + 6px)",
        left: "50%",
        transform: "translateX(-50%)",
        background: "var(--color-text)",
        color: "var(--color-surface)",
        borderRadius: "6px",
        padding: "0.5rem 0.75rem",
        fontSize: "0.72rem",
        whiteSpace: "nowrap",
        zIndex: 10,
        pointerEvents: "none",
        fontFamily: "var(--font-sans)",
        boxShadow: "0 4px 12px rgba(0,0,0,0.25)",
        lineHeight: 1.6,
      }}
    >
      <div style={{ fontWeight: 700, marginBottom: "0.2rem" }}>{cell.cell_id}</div>
      <div style={{ color: "var(--color-faint)" }}>{dims}</div>
      {cell.assigned_persona_name && (
        <div style={{ color: "var(--color-info)", marginTop: "0.15rem" }}>{cell.assigned_persona_name}</div>
      )}
      <div style={{ marginTop: "0.15rem" }}>
        Status:{" "}
        <span
          style={{
            color:
              cell.status === "completed"
                ? "var(--color-green)"
                : cell.status === "failed"
                ? "var(--color-red)"
                : cell.status === "in_progress"
                ? "var(--color-yellow)"
                : "var(--color-faint)",
          }}
        >
          {cell.status}
        </span>
        {cell.critic_score !== null && (
          <span style={{ color: "var(--color-border)" }}> · Score {cell.critic_score.toFixed(1)}</span>
        )}
      </div>
    </div>
  );
}

export default function ResultsCoverage({ runId, results }: Props) {
  const [matrix, setMatrix] = useState<MatrixData | null>(null);
  const [hoveredCell, setHoveredCell] = useState<string | null>(null);
  const [matrixError, setMatrixError] = useState<string | null>(null);

  useEffect(() => {
    getMatrix(runId)
      .then(setMatrix)
      .catch((e: unknown) => setMatrixError(e instanceof Error ? e.message : String(e)));
  }, [runId]);

  const stats = results.stats;

  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      {/* Matrix label */}
      <div
        style={{
          fontSize: "0.72rem",
          fontWeight: 600,
          color: "var(--color-muted)",
          textTransform: "uppercase",
          letterSpacing: "0.08em",
          marginBottom: "1rem",
        }}
      >
        Fraud variant space — hover any cell to see covering variants
      </div>

      {/* Coverage matrix */}
      {matrixError ? (
        <div style={{ color: "var(--color-red)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Could not load matrix: {matrixError}
        </div>
      ) : matrix ? (
        <CoverageMatrix cells={matrix.cells} dimensions={matrix.dimensions} />
      ) : (
        <div style={{ color: "var(--color-muted)", fontSize: "0.85rem", marginBottom: "1.5rem" }}>
          Loading coverage matrix…
        </div>
      )}

      {/* Inline fallback heatmap when CoverageMatrix renders nothing */}
      {matrix && matrix.cells.length > 0 && (
        <div style={{ marginTop: "1.5rem" }}>
          {/* Fallback grid — renders cells directly */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(8, 1fr)",
              gap: "4px",
              marginBottom: "1rem",
            }}
          >
            {matrix.cells.map((cell) => {
              const label = Object.values(cell.dimension_values)
                .slice(0, 2)
                .join("·");

              const cellStyle: React.CSSProperties = {
                position: "relative",
                borderRadius: "6px",
                padding: "0.4rem 0.3rem",
                fontSize: "0.65rem",
                fontFamily: "var(--font-mono)",
                textAlign: "center",
                cursor: "pointer",
                border: "1px solid",
                lineHeight: 1.3,
                minHeight: "42px",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                ...(cell.status === "completed"
                  ? { background: "var(--color-green-light)", borderColor: "var(--color-green-border)", color: "var(--color-green)" }
                  : cell.status === "failed"
                  ? { background: "var(--color-red-light)", borderColor: "var(--color-red-border)", color: "var(--color-red)" }
                  : cell.status === "in_progress"
                  ? { background: "var(--color-yellow-light)", borderColor: "var(--color-yellow-border)", color: "var(--color-yellow)" }
                  : { background: "var(--color-surface2)", borderColor: "var(--color-border)", color: "var(--color-faint)" }),
              };

              return (
                <div
                  key={cell.cell_id}
                  style={cellStyle}
                  onMouseEnter={() => setHoveredCell(cell.cell_id)}
                  onMouseLeave={() => setHoveredCell(null)}
                >
                  {label || cell.cell_id}
                  {hoveredCell === cell.cell_id && <CellTooltip cell={cell} />}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Legend */}
      <div
        style={{
          display: "flex",
          gap: "1.5rem",
          alignItems: "center",
          fontSize: "0.75rem",
          color: "var(--color-muted)",
          marginTop: "1rem",
        }}
      >
        {[
          { bg: "var(--color-green-light)", border: "var(--color-green-border)", text: "var(--color-green)", label: "Approved" },
          { bg: "var(--color-yellow-light)", border: "var(--color-yellow-border)", text: "var(--color-yellow)", label: "Revised & Approved" },
          { bg: "var(--color-red-light)", border: "var(--color-red-border)", text: "var(--color-red)", label: "Failed" },
          { bg: "var(--color-surface2)", border: "var(--color-border)", text: "var(--color-faint)", label: "Uncovered" },
        ].map(({ bg, border, text, label }) => (
          <div key={label} style={{ display: "flex", alignItems: "center", gap: "0.4rem" }}>
            <div
              style={{
                width: "14px",
                height: "14px",
                borderRadius: "3px",
                background: bg,
                border: `1px solid ${border}`,
                flexShrink: 0,
              }}
            />
            <span style={{ color: text }}>{label}</span>
          </div>
        ))}
      </div>

      {/* Field hint */}
      <div style={{ fontSize: "0.78rem", color: "var(--color-faint)", marginTop: "0.75rem" }}>
        Axes: hop count × topology × timing · click any cell to see which variants cover it
      </div>

      {/* Extra stats */}
      <div
        style={{
          marginTop: "1.5rem",
          padding: "1rem 1.25rem",
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "8px",
          display: "flex",
          gap: "2rem",
          fontSize: "0.82rem",
          color: "var(--color-muted)",
        }}
      >
        <span>
          Mean realism:{" "}
          <strong style={{ color: "var(--color-text)" }}>{stats.mean_realism.toFixed(1)}</strong>
        </span>
        <span>
          Mean distinctiveness:{" "}
          <strong style={{ color: "var(--color-text)" }}>{stats.mean_distinctiveness.toFixed(1)}</strong>
        </span>
        <span>
          Total transactions:{" "}
          <strong style={{ color: "var(--color-text)" }}>{stats.total_transactions.toLocaleString()}</strong>
        </span>
      </div>
    </div>
  );
}
