"use client";

import { type ExportFile, formatBytes, API } from "@/lib/api";
import { useState } from "react";

interface Props {
  runId: string;
  exportFiles: ExportFile[];
}

export default function ResultsExport({ runId, exportFiles }: Props) {
  const [hovered, setHovered] = useState<string | null>(null);

  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      {/* Heading */}
      <div style={{ marginBottom: "1.5rem" }}>
        <h2
          style={{
            fontSize: "1.1rem",
            fontWeight: 700,
            color: "var(--color-text)",
            margin: "0 0 0.35rem 0",
          }}
        >
          Export dataset
        </h2>
        <p style={{ fontSize: "0.85rem", color: "var(--color-muted)", margin: 0 }}>
          Download generated files for ML training pipelines
        </p>
      </div>

      {/* File manifest list */}
      {exportFiles.length === 0 ? (
        <div
          style={{
            padding: "2rem",
            textAlign: "center",
            color: "var(--color-faint)",
            fontSize: "0.85rem",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
          }}
        >
          No export files available yet.
        </div>
      ) : (
        <div>
          {exportFiles.map((file) => {
            const downloadUrl = `${API}/api/runs/${runId}/export/${file.format}`;
            const isHovered = hovered === file.filename;

            return (
              <div
                key={file.filename}
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "8px",
                  padding: "1rem 1.25rem",
                  marginBottom: "0.5rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "1rem",
                  opacity: file.available ? 1 : 0.55,
                }}
              >
                {/* Left: filename + description */}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div
                    style={{
                      fontFamily: "var(--font-mono)",
                      fontWeight: 600,
                      fontSize: "0.82rem",
                      color: "var(--color-accent)",
                      marginBottom: "0.2rem",
                    }}
                  >
                    {file.filename}
                  </div>
                  <div
                    style={{
                      fontSize: "0.78rem",
                      color: "var(--color-muted)",
                    }}
                  >
                    {file.description}
                  </div>
                </div>

                {/* Middle: size + record count */}
                <div
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "0.75rem",
                    color: "var(--color-muted)",
                    textAlign: "right",
                    flexShrink: 0,
                  }}
                >
                  <div>{formatBytes(file.size_bytes)}</div>
                  {file.record_count !== null && (
                    <div style={{ color: "var(--color-faint)", marginTop: "0.1rem" }}>
                      {file.record_count.toLocaleString()} records
                    </div>
                  )}
                </div>

                {/* Right: Download button */}
                {file.available ? (
                  <a
                    href={downloadUrl}
                    download={file.filename}
                    onMouseEnter={() => setHovered(file.filename)}
                    onMouseLeave={() => setHovered(null)}
                    style={{
                      display: "inline-block",
                      border: `1px solid ${isHovered ? "var(--color-accent)" : "var(--color-border)"}`,
                      color: isHovered ? "var(--color-accent)" : "var(--color-text)",
                      background: "transparent",
                      borderRadius: "8px",
                      padding: "0.45rem 1rem",
                      fontSize: "0.8rem",
                      fontWeight: 500,
                      textDecoration: "none",
                      whiteSpace: "nowrap",
                      transition: "border-color 0.15s, color 0.15s",
                      fontFamily: "var(--font-sans)",
                      flexShrink: 0,
                    }}
                  >
                    ↓ Download
                  </a>
                ) : (
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "0.2rem", flexShrink: 0 }}>
                    <button
                      disabled
                      style={{
                        border: "1px solid var(--color-border)",
                        color: "var(--color-faint)",
                        background: "transparent",
                        borderRadius: "8px",
                        padding: "0.45rem 1rem",
                        fontSize: "0.8rem",
                        fontWeight: 500,
                        cursor: "not-allowed",
                        whiteSpace: "nowrap",
                        fontFamily: "var(--font-sans)",
                        width: "100%",
                      }}
                    >
                      ↓ Download
                    </button>
                    <span
                      style={{
                        fontSize: "0.68rem",
                        color: "var(--color-faint)",
                        fontFamily: "var(--font-sans)",
                        whiteSpace: "nowrap",
                      }}
                    >
                      not yet available
                    </span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
