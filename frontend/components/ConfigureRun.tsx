"use client";

import { useState } from "react";
import { startRun } from "@/lib/api";

interface ConfigureRunProps {
  onStart: (runId: string) => void;
}

type FraudType =
  | "Mule Account Network"
  | "Card Skimming Ring"
  | "Business Email Compromise"
  | "Account Takeover";

const FRAUD_PREFILL: Record<FraudType, string> = {
  "Mule Account Network":
    "A layered mule account network where proceeds from online scams are laundered through 3–5 hops of domestic consumer bank accounts. Each hop uses same-day ACH transfers to obscure the money trail. Mule accounts are recruited via social media job posts, with burst transaction patterns on weekday mornings to blend into payroll traffic.",
  "Card Skimming Ring":
    "An organized card skimming operation targeting ATMs and gas station POS terminals in suburban areas. Compromised card data is encoded onto blank cards and used for in-person cash withdrawals across multiple states within a 48-hour window before the victim detects the fraud. Skimmers are retrieved every 3–7 days.",
  "Business Email Compromise":
    "A BEC fraud targeting mid-size companies where attackers spoof the CEO email domain and instruct the CFO to wire funds to a newly opened business account. The account receives a single large wire transfer and immediately disperses to multiple crypto exchanges and international beneficiaries within 6 hours.",
  "Account Takeover":
    "A credential-stuffing account takeover attack where stolen username/password pairs are tested against retail banking login portals. Successful logins trigger profile changes (phone number, email), followed by new payee additions and scheduled transfers to mule accounts over 3–5 days to avoid velocity rules.",
};

export default function ConfigureRun({ onStart }: ConfigureRunProps) {
  const [fraudType, setFraudType] = useState<FraudType>("Mule Account Network");
  const [description, setDescription] = useState("");
  const [variantCount, setVariantCount] = useState(5);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [maxParallelAgents, setMaxParallelAgents] = useState(5);
  const [criticScoreFloor, setCriticScoreFloor] = useState(7.0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const estimatedCost = (0.2 * variantCount).toFixed(2);
  const estimatedTime = variantCount * 9.6;
  const estimatedMinutes = Math.floor(estimatedTime / 60);
  const estimatedSeconds = Math.round(estimatedTime % 60);
  const descriptionValid = description.trim().length >= 20;

  function handlePrefill() {
    setDescription(FRAUD_PREFILL[fraudType]);
  }

  async function handleSubmit() {
    if (!descriptionValid || isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await startRun({
        fraud_description: description.trim(),
        variant_count: variantCount,
        max_parallel: maxParallelAgents,
        critic_floor: criticScoreFloor,
      });
      onStart(result.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start run. Is the API server running?");
      setIsSubmitting(false);
    }
  }

  async function handleDemo() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    const demoDesc = description.trim().length >= 20
      ? description.trim()
      : FRAUD_PREFILL["Mule Account Network"];
    try {
      const result = await startRun({
        fraud_description: demoDesc,
        variant_count: Math.min(variantCount, 7),
        demo: true,
        max_parallel: maxParallelAgents,
        critic_floor: criticScoreFloor,
      });
      onStart(result.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start demo. Is the API server running?");
      setIsSubmitting(false);
    }
  }

  async function handleLoadData() {
    if (isSubmitting) return;
    setIsSubmitting(true);
    setError(null);
    try {
      const result = await startRun({
        fraud_description: FRAUD_PREFILL["Mule Account Network"],
        variant_count: 7,
        demo: true,
        instant: true,
      });
      onStart(result.run_id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data. Is the API server running?");
      setIsSubmitting(false);
    }
  }

  return (
    <div
      style={{
        maxWidth: "672px",
        margin: "0 auto",
        padding: "2.5rem",
      }}
    >
      {/* Header */}
      <div style={{ marginBottom: "2rem" }}>
        <div className="section-tag" style={{ marginBottom: "0.875rem" }}>
          NEW RUN
        </div>
        <h1
          style={{
            fontSize: "clamp(1.5rem, 3vw, 2rem)",
            fontWeight: 800,
            color: "var(--color-text)",
            letterSpacing: "-0.03em",
            lineHeight: 1.15,
            marginBottom: "0.625rem",
          }}
        >
          Configure Run
        </h1>
        <p style={{ color: "var(--color-muted)", fontSize: "0.9rem", lineHeight: 1.6 }}>
          Describe a fraud type to generate synthetic variants across the full attack space.
        </p>
      </div>

      {/* Main card */}
      <div
        style={{
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "12px",
          padding: "1.5rem",
          display: "flex",
          flexDirection: "column",
          gap: "1.25rem",
        }}
      >
        {/* Fraud type dropdown */}
        <div>
          <label
            style={{
              display: "block",
              fontSize: "0.82rem",
              fontWeight: 600,
              color: "var(--color-text)",
              marginBottom: "0.4rem",
            }}
          >
            Fraud type
          </label>
          <div style={{ display: "flex", gap: "0.625rem", alignItems: "center" }}>
            <select
              value={fraudType}
              onChange={(e) => setFraudType(e.target.value as FraudType)}
              style={{
                flex: 1,
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
                padding: "0.5rem 0.75rem",
                fontSize: "0.875rem",
                color: "var(--color-text)",
                background: "var(--color-bg)",
                cursor: "pointer",
                appearance: "none",
                backgroundImage: `url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8' fill='none' viewBox='0 0 12 8'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%23999999' stroke-width='1.5' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E")`,
                backgroundRepeat: "no-repeat",
                backgroundPosition: "right 0.75rem center",
                paddingRight: "2.25rem",
              }}
            >
              <option>Mule Account Network</option>
              <option>Card Skimming Ring</option>
              <option>Business Email Compromise</option>
              <option>Account Takeover</option>
            </select>
            <button
              onClick={handlePrefill}
              style={{
                padding: "0.5rem 0.875rem",
                fontSize: "0.8rem",
                fontWeight: 600,
                color: "var(--color-accent)",
                background: "transparent",
                border: "1.5px solid var(--color-border)",
                borderRadius: "8px",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "border-color 0.1s, background 0.1s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "var(--color-accent-light)";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-accent-border)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-border)";
              }}
            >
              Pre-fill
            </button>
          </div>
        </div>

        {/* Description textarea */}
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "0.5rem",
              marginBottom: "0.4rem",
            }}
          >
            <label
              style={{
                fontSize: "0.82rem",
                fontWeight: 600,
                color: "var(--color-text)",
              }}
            >
              Fraud description
            </label>
            <span
              style={{
                fontSize: "0.72rem",
                color: "var(--color-accent)",
                fontWeight: 500,
              }}
            >
              required · min 20 chars
            </span>
          </div>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder="Describe the fraud pattern in plain English..."
            rows={4}
            style={{
              width: "100%",
              minHeight: "88px",
              border: `1.5px solid ${
                description.length > 0 && !descriptionValid ? "var(--color-red-border)" : "var(--color-border)"
              }`,
              borderRadius: "8px",
              padding: "0.625rem 0.75rem",
              fontSize: "0.875rem",
              color: "var(--color-text)",
              background: "var(--color-bg)",
              resize: "vertical",
              fontFamily: "var(--font-sans)",
              lineHeight: 1.6,
              outline: "none",
              transition: "border-color 0.1s",
            }}
            onFocus={(e) => {
              (e.target as HTMLTextAreaElement).style.borderColor = "var(--color-accent)";
            }}
            onBlur={(e) => {
              (e.target as HTMLTextAreaElement).style.borderColor =
                description.length > 0 && !descriptionValid ? "var(--color-red-border)" : "var(--color-border)";
            }}
          />
          <p
            style={{
              fontSize: "0.75rem",
              color: "var(--color-muted)",
              marginTop: "0.35rem",
            }}
          >
            The richer and more specific, the more targeted the variant space.
          </p>
        </div>

        {/* Variant count slider */}
        <div>
          <div
            style={{
              display: "flex",
              alignItems: "baseline",
              gap: "0.5rem",
              marginBottom: "0.6rem",
            }}
          >
            <label
              style={{
                fontSize: "0.82rem",
                fontWeight: 600,
                color: "var(--color-text)",
              }}
            >
              Variant count
            </label>
            <span
              style={{
                fontFamily: "var(--font-mono, monospace)",
                fontSize: "0.95rem",
                fontWeight: 700,
                color: "var(--color-accent)",
              }}
            >
              {variantCount}
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--color-faint)" }}>
              Est. ${estimatedCost} ·{" "}
              {estimatedMinutes > 0 ? `${estimatedMinutes}m ` : ""}
              {estimatedSeconds}s
            </span>
          </div>
          <input
            type="range"
            min={1}
            max={20}
            value={variantCount}
            onChange={(e) => setVariantCount(Number(e.target.value))}
            style={{
              width: "100%",
              accentColor: "var(--color-accent)",
              cursor: "pointer",
              height: "4px",
            }}
          />
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              fontSize: "0.7rem",
              color: "var(--color-faint)",
              marginTop: "0.3rem",
            }}
          >
            <span>1</span>
            <span>20</span>
          </div>
        </div>

        {/* Advanced controls (collapsible) */}
        <div>
          <button
            onClick={() => setAdvancedOpen((v) => !v)}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "0.35rem",
              fontSize: "0.8rem",
              fontWeight: 600,
              color: "var(--color-muted)",
              background: "transparent",
              border: "none",
              cursor: "pointer",
              padding: 0,
            }}
          >
            <span style={{ fontSize: "0.65rem", transition: "transform 0.15s", display: "inline-block", transform: advancedOpen ? "rotate(90deg)" : "rotate(0deg)" }}>
              ▸
            </span>
            Advanced controls
          </button>

          {advancedOpen && (
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: "1rem",
                marginTop: "0.875rem",
                padding: "1rem",
                background: "var(--color-bg)",
                border: "1px solid var(--color-border)",
                borderRadius: "8px",
              }}
            >
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "var(--color-text)",
                    marginBottom: "0.35rem",
                  }}
                >
                  Max parallel agents
                </label>
                <input
                  type="number"
                  min={1}
                  max={10}
                  value={maxParallelAgents}
                  onChange={(e) => setMaxParallelAgents(Number(e.target.value))}
                  style={{
                    width: "100%",
                    border: "1px solid var(--color-border)",
                    borderRadius: "6px",
                    padding: "0.4rem 0.6rem",
                    fontSize: "0.875rem",
                    color: "var(--color-text)",
                    background: "var(--color-surface)",
                  }}
                />
              </div>
              <div>
                <label
                  style={{
                    display: "block",
                    fontSize: "0.78rem",
                    fontWeight: 600,
                    color: "var(--color-text)",
                    marginBottom: "0.35rem",
                  }}
                >
                  Critic score floor
                </label>
                <input
                  type="number"
                  min={0}
                  max={10}
                  step={0.5}
                  value={criticScoreFloor}
                  onChange={(e) => setCriticScoreFloor(Number(e.target.value))}
                  style={{
                    width: "100%",
                    border: "1px solid var(--color-border)",
                    borderRadius: "6px",
                    padding: "0.4rem 0.6rem",
                    fontSize: "0.875rem",
                    color: "var(--color-text)",
                    background: "var(--color-surface)",
                  }}
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Error message */}
      {error && (
        <div
          style={{
            marginTop: "1rem",
            padding: "0.75rem 1rem",
            background: "var(--color-red-light)",
            border: "1px solid var(--color-red-border)",
            borderRadius: "8px",
            fontSize: "0.8rem",
            color: "var(--color-red)",
          }}
        >
          {error}
        </div>
      )}

      {/* Action row */}
      <div
        style={{
          display: "flex",
          gap: "0.75rem",
          marginTop: "1.25rem",
          alignItems: "center",
        }}
      >
        <button
          onClick={handleSubmit}
          disabled={!descriptionValid || isSubmitting}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "0.5rem",
            padding: "0.7rem 1.5rem",
            background: !descriptionValid || isSubmitting ? "var(--color-accent-border)" : "var(--color-accent)",
            color: "var(--color-bg)",
            fontWeight: 700,
            fontSize: "0.9rem",
            border: "none",
            borderRadius: "8px",
            cursor: !descriptionValid || isSubmitting ? "not-allowed" : "pointer",
            transition: "background 0.15s",
          }}
          onMouseEnter={(e) => {
            if (descriptionValid && !isSubmitting) {
              (e.currentTarget as HTMLButtonElement).style.background = "var(--color-accent-dark)";
            }
          }}
          onMouseLeave={(e) => {
            if (descriptionValid && !isSubmitting) {
              (e.currentTarget as HTMLButtonElement).style.background = "var(--color-accent)";
            }
          }}
        >
          {isSubmitting ? (
            <>
              <span
                style={{
                  display: "inline-block",
                  width: "12px",
                  height: "12px",
                  border: "2px solid rgba(255,255,255,0.3)",
                  borderTopColor: "var(--color-bg)",
                  borderRadius: "50%",
                  animation: "spin 0.7s linear infinite",
                }}
              />
              Starting…
            </>
          ) : (
            <>▶ Run</>
          )}
        </button>

        <button
          style={{
            padding: "0.7rem 1.25rem",
            background: "transparent",
            color: "var(--color-text)",
            fontWeight: 600,
            fontSize: "0.875rem",
            border: "1.5px solid var(--color-border)",
            borderRadius: "8px",
            cursor: "pointer",
            transition: "border-color 0.1s, background 0.1s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = "transparent";
          }}
        >
          Save config
        </button>

        <button
          onClick={handleDemo}
          disabled={isSubmitting}
          title="Watch the pipeline run live with synthetic data — no API key needed"
          style={{
            padding: "0.7rem 1.25rem",
            background: isSubmitting ? "var(--color-surface2)" : "transparent",
            color: "var(--color-purple)",
            fontWeight: 600,
            fontSize: "0.875rem",
            border: "1.5px solid var(--color-purple-light)",
            borderRadius: "8px",
            cursor: isSubmitting ? "not-allowed" : "pointer",
            transition: "border-color 0.1s, background 0.1s",
            whiteSpace: "nowrap",
          }}
          onMouseEnter={(e) => {
            if (!isSubmitting) {
              (e.currentTarget as HTMLButtonElement).style.background = "var(--color-purple-light)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-purple-light)";
            }
          }}
          onMouseLeave={(e) => {
            if (!isSubmitting) {
              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-purple-light)";
            }
          }}
        >
          Demo
        </button>

        <button
          onClick={handleLoadData}
          disabled={isSubmitting}
          title="Instantly populate all views with a complete synthetic dataset"
          style={{
            padding: "0.7rem 1.25rem",
            background: isSubmitting ? "var(--color-info-light)" : "transparent",
            color: "var(--color-info)",
            fontWeight: 600,
            fontSize: "0.875rem",
            border: "1.5px solid var(--color-info-border)",
            borderRadius: "8px",
            cursor: isSubmitting ? "not-allowed" : "pointer",
            transition: "border-color 0.1s, background 0.1s",
            whiteSpace: "nowrap",
          }}
          onMouseEnter={(e) => {
            if (!isSubmitting) {
              (e.currentTarget as HTMLButtonElement).style.background = "var(--color-info-light)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-info-border)";
            }
          }}
          onMouseLeave={(e) => {
            if (!isSubmitting) {
              (e.currentTarget as HTMLButtonElement).style.background = "transparent";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "var(--color-info-border)";
            }
          }}
        >
          Load with data
        </button>

        {!descriptionValid && description.length > 0 && (
          <span style={{ fontSize: "0.75rem", color: "var(--color-red)" }}>
            {20 - description.trim().length} more chars needed
          </span>
        )}
      </div>

      {/* Spin keyframes via a style tag */}
      <style>{`
        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
