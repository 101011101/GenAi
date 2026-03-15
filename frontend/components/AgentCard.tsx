"use client";

import { AgentStatus } from "@/lib/api";

const AGENT_COLORS: Record<string, { color: string; light: string; border: string }> = {
  A1: { color: "var(--color-accent)", light: "var(--color-accent-light)", border: "var(--color-accent-border)" },
  A2: { color: "var(--color-green)", light: "var(--color-green-light)", border: "var(--color-green-border)" },
  A3: { color: "var(--color-purple)", light: "var(--color-purple-light)", border: "var(--color-purple-light)" },
  A4: { color: "var(--color-yellow)", light: "var(--color-yellow-light)", border: "var(--color-yellow-border)" },
  A5: { color: "var(--color-red)", light: "var(--color-red-light)", border: "var(--color-red-border)" },
};

function StatusBadge({ status, attempt, maxAttempts }: { status: AgentStatus["status"]; attempt: number; maxAttempts: number }) {
  if (status === "running") {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.2rem",
          padding: "0.14rem 0.45rem",
          borderRadius: "999px",
          fontSize: "0.63rem",
          fontWeight: 700,
          background: "var(--color-accent-light)",
          color: "var(--color-accent)",
        }}
      >
        <span className="pulse" style={{ display: "inline-block", width: 6, height: 6, borderRadius: "50%", background: "var(--color-accent)" }} />
        running
      </span>
    );
  }
  if (status === "done") {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.2rem",
          padding: "0.14rem 0.45rem",
          borderRadius: "999px",
          fontSize: "0.63rem",
          fontWeight: 700,
          background: "var(--color-green-light)",
          color: "var(--color-green)",
        }}
      >
        ✓ done
      </span>
    );
  }
  if (status === "retry") {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.2rem",
          padding: "0.14rem 0.45rem",
          borderRadius: "999px",
          fontSize: "0.63rem",
          fontWeight: 700,
          background: "var(--color-yellow-light)",
          color: "var(--color-yellow)",
        }}
      >
        ↺ retry {attempt}/{maxAttempts}
      </span>
    );
  }
  if (status === "error") {
    return (
      <span
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "0.2rem",
          padding: "0.14rem 0.45rem",
          borderRadius: "999px",
          fontSize: "0.63rem",
          fontWeight: 700,
          background: "var(--color-red-light)",
          color: "var(--color-red)",
        }}
      >
        ✕ error
      </span>
    );
  }
  // idle
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.2rem",
        padding: "0.14rem 0.45rem",
        borderRadius: "999px",
        fontSize: "0.63rem",
        fontWeight: 700,
        background: "var(--color-surface2)",
        color: "var(--color-muted)",
      }}
    >
      idle
    </span>
  );
}

interface AgentCardProps {
  agent: AgentStatus;
}

export default function AgentCard({ agent }: AgentCardProps) {
  const colors = AGENT_COLORS[agent.agent_id] ?? { color: "var(--color-muted)", light: "var(--color-surface2)", border: "var(--color-border)" };
  const pct = agent.total_steps > 0 ? (agent.current_step / agent.total_steps) * 100 : 0;

  const statusDotColor =
    agent.status === "running" ? "var(--color-accent)" :
    agent.status === "done"    ? "var(--color-green)" :
    agent.status === "retry"   ? "var(--color-yellow)" :
    agent.status === "error"   ? "var(--color-red)" :
    "var(--color-faint)";

  return (
    <div
      style={{
        background: "var(--color-bg)",
        border: `1.5px solid var(--color-border)`,
        borderRadius: 8,
        padding: "0.7rem 0.75rem",
        marginBottom: "0.4rem",
        cursor: "pointer",
        userSelect: "none",
      }}
    >
      {/* Row 1: pill + variant + status badge */}
      <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", marginBottom: "0.4rem" }}>
        {/* Agent pill */}
        <span
          style={{
            fontSize: "0.6rem",
            fontWeight: 800,
            fontFamily: "var(--font-mono)",
            padding: "0.15rem 0.45rem",
            borderRadius: 4,
            background: colors.color,
            color: "var(--color-bg)",
            flexShrink: 0,
          }}
        >
          {agent.agent_id}
        </span>

        {/* Status dot */}
        <span
          className={agent.status === "running" || agent.status === "retry" ? "pulse" : undefined}
          style={{
            display: "inline-block",
            width: 7,
            height: 7,
            borderRadius: "50%",
            background: statusDotColor,
            flexShrink: 0,
          }}
        />

        {/* Variant ID */}
        <span
          style={{
            fontSize: "0.7rem",
            fontWeight: 700,
            color: "var(--color-text)",
            fontFamily: "var(--font-mono)",
            flex: 1,
            minWidth: 0,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {agent.variant_id || "—"}
        </span>

        {/* Status badge */}
        <div style={{ flexShrink: 0 }}>
          <StatusBadge status={agent.status} attempt={agent.attempt} maxAttempts={agent.max_attempts} />
        </div>
      </div>

      {/* Row 2: persona · step summary */}
      <div
        style={{
          fontSize: "0.62rem",
          color: "var(--color-muted)",
          marginBottom: "0.25rem",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {agent.persona_name || "—"}{agent.step_name ? ` · ${agent.step_name}` : ""}
      </div>

      {/* Row 3: step progress */}
      <div style={{ fontSize: "0.65rem", color: "var(--color-text)", marginBottom: "0.25rem" }}>
        <em style={{ color: "var(--color-muted)", fontStyle: "normal" }}>Step {agent.current_step}/{agent.total_steps}:</em>{" "}
        {agent.step_name || "—"}
      </div>

      {/* Row 4: tokens + cost */}
      <div
        style={{
          fontSize: "0.62rem",
          color: "var(--color-faint)",
          fontFamily: "var(--font-mono)",
          marginBottom: "0.3rem",
        }}
      >
        {agent.tokens_used.toLocaleString()} tok · ${agent.cost_usd.toFixed(2)}
      </div>

      {/* Mini progress bar */}
      <div
        style={{
          height: 3,
          background: "var(--color-border)",
          borderRadius: 99,
          overflow: "hidden",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${Math.min(100, pct)}%`,
            background: colors.color,
            borderRadius: 99,
            transition: "width 0.4s ease",
          }}
        />
      </div>
    </div>
  );
}
