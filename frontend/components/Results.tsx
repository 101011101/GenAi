"use client";

import { useEffect, useState } from "react";
import {
  getResults,
  getPersonas,
  getExportManifest,
  type ResultsData,
  type Persona,
  type ExportFile,
} from "@/lib/api";
import ResultsCoverage from "./ResultsCoverage";
import ResultsDataset from "./ResultsDataset";
import ResultsPersonas from "./ResultsPersonas";
import ResultsExport from "./ResultsExport";
import NetworkGraph from "./NetworkGraph";

type Tab = "coverage" | "networks" | "dataset" | "personas" | "export";

interface Props {
  runId: string;
  onNewRun: () => void;
}

export default function Results({ runId, onNewRun }: Props) {
  const [activeTab, setActiveTab] = useState<Tab>("coverage");
  const [results, setResults] = useState<ResultsData | null>(null);
  const [personas, setPersonas] = useState<Persona[]>([]);
  const [exportFiles, setExportFiles] = useState<ExportFile[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const [res, per, exp] = await Promise.all([
          getResults(runId),
          getPersonas(runId),
          getExportManifest(runId),
        ]);
        setResults(res);
        setPersonas(per.personas);
        setExportFiles(exp);
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : String(e));
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  const tabs: { key: Tab; label: string }[] = [
    { key: "coverage", label: "Coverage" },
    { key: "networks", label: "Network Graphs" },
    { key: "dataset", label: "Dataset" },
    { key: "personas", label: "Personas" },
    { key: "export", label: "Export" },
  ];

  if (loading) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--color-muted)", fontFamily: "var(--font-sans)" }}>
        Loading results…
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: "3rem", textAlign: "center", color: "var(--color-red)", fontFamily: "var(--font-sans)" }}>
        Error loading results: {error}
      </div>
    );
  }

  const stats = results?.stats;
  const variants = results?.variants ?? [];

  return (
    <div style={{ fontFamily: "var(--font-sans)", color: "var(--color-text)", minHeight: "100vh", background: "var(--color-bg)" }}>
      {/* Summary Banner */}
      {stats && (
        <div
          style={{
            background: "var(--color-green-light)",
            border: "1px solid var(--color-green-border)",
            borderRadius: "8px",
            padding: "1rem 1.5rem",
            margin: "1.5rem",
            fontSize: "0.9rem",
            color: "#065f46",
            fontWeight: 500,
          }}
        >
          Run complete &nbsp;·&nbsp;{" "}
          <strong>{stats.variants_generated}</strong> variants approved &nbsp;·&nbsp; Mean score{" "}
          <strong>{stats.mean_critic_score.toFixed(1)}</strong>/10 &nbsp;·&nbsp; Coverage{" "}
          <strong>{stats.coverage_pct.toFixed(0)}%</strong> &nbsp;·&nbsp;{" "}
          <strong>{stats.total_transactions.toLocaleString()}</strong> transactions
        </div>
      )}

      {/* Stat Cards */}
      {stats && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(5, 1fr)",
            gap: "1rem",
            padding: "0 1.5rem",
            marginBottom: "1.5rem",
          }}
        >
          {[
            { label: "Variants", value: String(stats.variants_generated) },
            { label: "Coverage", value: `${stats.coverage_pct.toFixed(0)}%` },
            { label: "Avg Score", value: stats.mean_critic_score.toFixed(1) },
            { label: "Transactions", value: stats.total_transactions.toLocaleString() },
            { label: "API Cost", value: "—" },
          ].map(({ label, value }) => (
            <div
              key={label}
              style={{
                background: "var(--color-surface)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                padding: "1.25rem",
                textAlign: "center",
              }}
            >
              <div
                style={{
                  fontSize: "1.5rem",
                  fontWeight: 800,
                  color: "var(--color-accent)",
                  fontFamily: "var(--font-mono)",
                  letterSpacing: "-0.02em",
                }}
              >
                {value}
              </div>
              <div
                style={{
                  fontSize: "0.72rem",
                  fontWeight: 600,
                  color: "var(--color-muted)",
                  textTransform: "uppercase",
                  letterSpacing: "0.08em",
                  marginTop: "0.25rem",
                }}
              >
                {label}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Tab Bar */}
      <div
        style={{
          display: "flex",
          gap: 0,
          borderBottom: "2px solid var(--color-border)",
          padding: "0 1.5rem",
          marginBottom: 0,
        }}
      >
        {tabs.map(({ key, label }) => (
          <button
            key={key}
            onClick={() => setActiveTab(key)}
            style={{
              background: "none",
              border: "none",
              borderBottom: activeTab === key ? "2px solid var(--color-accent)" : "2px solid transparent",
              marginBottom: "-2px",
              padding: "0.75rem 1.25rem",
              fontSize: "0.875rem",
              fontWeight: activeTab === key ? 700 : 400,
              color: activeTab === key ? "var(--color-accent)" : "var(--color-muted)",
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
              transition: "color 0.15s",
            }}
          >
            {label}
          </button>
        ))}

        {/* New Run button pushed to right */}
        <div style={{ flex: 1 }} />
        <div style={{ display: "flex", alignItems: "center" }}>
          <button
            onClick={onNewRun}
            style={{
              background: "var(--color-accent)",
              color: "var(--color-bg)",
              border: "none",
              borderRadius: "8px",
              padding: "0.45rem 1rem",
              fontSize: "0.8rem",
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            + New Run
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div style={{ padding: "1.5rem" }}>
        {activeTab === "coverage" && results && (
          <ResultsCoverage runId={runId} results={results} />
        )}

        {activeTab === "networks" && (
          <div>
            <div
              style={{
                fontSize: "0.75rem",
                color: "var(--color-muted)",
                marginBottom: "1rem",
                fontWeight: 500,
              }}
            >
              Showing {variants.length} variant{variants.length !== 1 ? "s" : ""}
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: "1rem",
              }}
            >
              {variants.map((v) => (
                <div key={v.variant_id}>
                  <div
                    style={{
                      background: "var(--color-surface)",
                      border: "1px solid var(--color-border)",
                      borderRadius: "8px",
                      padding: "0.75rem 1rem",
                      marginBottom: "0.5rem",
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: "0.85rem", color: "var(--color-text)" }}>
                      <span style={{ fontFamily: "var(--font-mono)", color: "var(--color-accent)" }}>
                        {v.variant_id}
                      </span>
                    </div>
                    {v.persona_name && (
                      <div style={{ fontSize: "0.75rem", color: "var(--color-muted)", marginTop: "0.15rem" }}>
                        {v.persona_name}
                        {v.strategy_description ? ` · ${v.strategy_description.slice(0, 40)}` : ""}
                      </div>
                    )}
                  </div>
                  <NetworkGraph variant={v} />
                </div>
              ))}
              {variants.length === 0 && (
                <div style={{ gridColumn: "1 / -1", color: "var(--color-muted)", textAlign: "center", padding: "2rem" }}>
                  No variant data available.
                </div>
              )}
            </div>
            {/* Legend */}
            <div
              style={{
                display: "flex",
                gap: "1.5rem",
                marginTop: "1.5rem",
                fontSize: "0.75rem",
                color: "var(--color-muted)",
                alignItems: "center",
              }}
            >
              <span>
                <span style={{ color: "var(--color-red)", fontWeight: 700 }}>●</span> Fraud path
              </span>
              <span>
                <span style={{ color: "var(--color-purple)", fontWeight: 700 }}>●</span> Crypto extraction
              </span>
              <span>
                <span style={{ color: "var(--color-faint)", fontWeight: 700 }}>●</span> Cover activity
              </span>
              <span style={{ marginLeft: "auto", fontStyle: "italic" }}>
                Structurally diverse — not statistical noise around the same pattern
              </span>
            </div>
          </div>
        )}

        {activeTab === "dataset" && (
          <ResultsDataset runId={runId} variants={variants} />
        )}

        {activeTab === "personas" && (
          <ResultsPersonas personas={personas} />
        )}

        {activeTab === "export" && (
          <ResultsExport runId={runId} exportFiles={exportFiles} />
        )}
      </div>
    </div>
  );
}
