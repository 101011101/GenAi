"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import {
  getRunStatus,
  getAgents,
  getMatrix,
  getTrace,
  sendControl,
  formatElapsed,
  AGENT_COLORS,
  AgentStatus,
  RunStatus,
  TraceEvent,
} from "@/lib/api";
import AgentCard from "./AgentCard";
import CoverageMatrix from "./CoverageMatrix";

// ── Helpers ────────────────────────────────────────────────────────────────────

function agentColor(agentId: string): string {
  return AGENT_COLORS[agentId]?.color ?? "var(--color-muted)";
}

function formatTs(ts: string): string {
  try {
    const d = new Date(ts);
    return d.toLocaleTimeString("en-US", { hour12: false, hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return ts.slice(0, 8);
  }
}

function syntaxHighlightJSON(obj: unknown): string {
  const json = JSON.stringify(obj, null, 2);
  return json
    .replace(/("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")\s*:/g, '<span class="json-key">$1</span>:')
    .replace(/:\s*("(\\u[a-zA-Z0-9]{4}|\\[^u]|[^\\"])*")/g, ': <span class="json-string">$1</span>')
    .replace(/:\s*(\d+\.?\d*)/g, ': <span class="json-number">$1</span>')
    .replace(/:\s*(true|false)/g, ': <span class="json-boolean">$1</span>')
    .replace(/:\s*(null)/g, ': <span class="json-null">$1</span>');
}

// ── Score badge ────────────────────────────────────────────────────────────────

function ScoreBadge({ score }: { score: number | null }) {
  if (score === null) return null;
  const color = score >= 7 ? "var(--color-green)" : "var(--color-red)";
  return (
    <span
      style={{
        fontFamily: "var(--font-mono)",
        fontSize: "0.72rem",
        fontWeight: 700,
        color,
      }}
    >
      {score.toFixed(1)}
    </span>
  );
}

// ── Agent badge chip ───────────────────────────────────────────────────────────

function AgentBadge({ agentId }: { agentId: string }) {
  const c = AGENT_COLORS[agentId] ?? { color: "var(--color-muted)", light: "var(--color-surface2)" };
  return (
    <span
      style={{
        display: "inline-block",
        padding: "0.12rem 0.4rem",
        borderRadius: 4,
        fontSize: "0.6rem",
        fontWeight: 800,
        fontFamily: "var(--font-mono)",
        background: c.color,
        color: "var(--color-bg)",
        flexShrink: 0,
      }}
    >
      {agentId}
    </span>
  );
}

// ── Status badge for variant groups ───────────────────────────────────────────

function VariantStatusBadge({ status }: { status: TraceEvent["status"] }) {
  const cfg =
    status === "done"
      ? { bg: "var(--color-green-light)", color: "var(--color-green)", label: "done" }
      : status === "error"
      ? { bg: "var(--color-red-light)", color: "var(--color-red)", label: "error" }
      : { bg: "var(--color-accent-light)", color: "var(--color-accent)", label: "running" };
  return (
    <span
      style={{
        padding: "0.1rem 0.4rem",
        borderRadius: 999,
        fontSize: "0.62rem",
        fontWeight: 700,
        background: cfg.bg,
        color: cfg.color,
      }}
    >
      {cfg.label}
    </span>
  );
}

// ── Trace Entry ────────────────────────────────────────────────────────────────

function TraceEntryRow({ event }: { event: TraceEvent }) {
  const [expanded, setExpanded] = useState(false);
  const borderColor = agentColor(event.agent_id);

  return (
    <>
      <div
        onClick={() => setExpanded((v) => !v)}
        style={{
          padding: "0.42rem 1.25rem 0.42rem 1rem",
          display: "flex",
          alignItems: "flex-start",
          gap: "0.65rem",
          borderBottom: "1px solid var(--color-border)",
          borderLeft: `3px solid ${borderColor}`,
          cursor: "pointer",
          background: expanded ? "var(--color-surface)" : "var(--color-bg)",
        }}
      >
        {/* Timestamp */}
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.62rem",
            color: "var(--color-faint)",
            whiteSpace: "nowrap",
            paddingTop: "0.1rem",
            flexShrink: 0,
            width: 60,
          }}
        >
          {formatTs(event.ts)}
        </span>

        {/* Agent badge */}
        <div style={{ flexShrink: 0, paddingTop: "0.08rem" }}>
          <AgentBadge agentId={event.agent_id} />
        </div>

        {/* Body */}
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: "0.73rem", fontWeight: 600, color: "var(--color-text)" }}>{event.step_name}</div>
          <div style={{ fontSize: "0.65rem", color: "var(--color-muted)", marginTop: "0.06rem" }}>{event.description}</div>
        </div>

        {/* Right: score + toggle */}
        <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <ScoreBadge score={event.score} />
          <span style={{ fontSize: "0.62rem", color: "var(--color-faint)", width: 10 }}>{expanded ? "▼" : "▶"}</span>
        </div>
      </div>

      {/* Expanded detail */}
      {expanded && event.detail && (
        <div
          style={{
            padding: "0.55rem 1.25rem 0.7rem 3.5rem",
            background: "var(--color-surface)",
            borderBottom: "1px solid var(--color-border)",
          }}
        >
          <div
            style={{
              fontSize: "0.6rem",
              fontWeight: 700,
              color: "var(--color-muted)",
              textTransform: "uppercase",
              letterSpacing: "0.07em",
              marginBottom: "0.3rem",
            }}
          >
            Detail
          </div>
          <div
            style={{
              background: "var(--color-code-bg)",
              borderRadius: 6,
              padding: "0.6rem 0.85rem",
              fontFamily: "var(--font-mono)",
              fontSize: "0.64rem",
              lineHeight: 1.75,
              color: "var(--color-faint)",
              overflowX: "auto",
              whiteSpace: "pre",
            }}
            dangerouslySetInnerHTML={{ __html: syntaxHighlightJSON(event.detail) }}
          />
        </div>
      )}
    </>
  );
}

// ── Variant Group ──────────────────────────────────────────────────────────────

function VariantGroup({
  variantId,
  events,
}: {
  variantId: string;
  events: TraceEvent[];
}) {
  const [collapsed, setCollapsed] = useState(false);
  const lastEvent = events[events.length - 1];
  const agentId = lastEvent?.agent_id ?? "";
  const status = lastEvent?.status ?? "running";
  const borderColor = agentColor(agentId);

  return (
    <div style={{ borderBottom: "1px solid var(--color-border)" }}>
      {/* Group header */}
      <div
        onClick={() => setCollapsed((v) => !v)}
        style={{
          padding: "0.38rem 1.25rem",
          background: "var(--color-surface2)",
          display: "flex",
          alignItems: "center",
          gap: "0.6rem",
          cursor: "pointer",
          userSelect: "none",
          borderLeft: `3px solid ${borderColor}`,
        }}
      >
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "0.7rem",
            fontWeight: 700,
            color: "var(--color-text)",
          }}
        >
          {variantId}
        </span>
        <AgentBadge agentId={agentId} />
        <span style={{ fontSize: "0.65rem", color: "var(--color-muted)" }}>{events.length} events</span>
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.35rem" }}>
          <VariantStatusBadge status={status} />
          <span style={{ fontSize: "0.65rem", color: "var(--color-faint)", width: 10 }}>{collapsed ? "▶" : "▼"}</span>
        </div>
      </div>

      {/* Entries */}
      {!collapsed && (
        <div>
          {events.map((ev) => (
            <TraceEntryRow key={ev.event_id} event={ev} />
          ))}
        </div>
      )}
    </div>
  );
}

// ── Variant Detail Tab ─────────────────────────────────────────────────────────

function VariantDetailTab({ allEvents }: { allEvents: TraceEvent[] }) {
  const variantIds = Array.from(new Set(allEvents.map((e) => e.variant_id))).filter(Boolean);
  const [selectedVariant, setSelectedVariant] = useState<string>("");
  const [expandedSteps, setExpandedSteps] = useState<Record<number, boolean>>({});

  const activeVariant = selectedVariant || variantIds[0] || "";
  const variantEvents = allEvents.filter((e) => e.variant_id === activeVariant);

  function toggleStep(step: number) {
    setExpandedSteps((prev) => ({ ...prev, [step]: !prev[step] }));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
      {/* Toolbar */}
      <div
        style={{
          padding: "0.55rem 1.25rem",
          borderBottom: "1px solid var(--color-border)",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          flexShrink: 0,
          background: "var(--color-surface)",
        }}
      >
        <span style={{ fontSize: "0.72rem", fontWeight: 600, color: "var(--color-text)" }}>Variant</span>
        <select
          value={activeVariant}
          onChange={(e) => {
            setSelectedVariant(e.target.value);
            setExpandedSteps({});
          }}
          style={{
            border: "1.5px solid var(--color-border)",
            borderRadius: 6,
            padding: "0.3rem 0.6rem",
            fontSize: "0.72rem",
            fontFamily: "var(--font-mono)",
            color: "var(--color-accent)",
            background: "var(--color-bg)",
            cursor: "pointer",
          }}
        >
          {variantIds.length === 0 && <option value="">No variants yet</option>}
          {variantIds.map((vid) => (
            <option key={vid} value={vid}>
              {vid}
            </option>
          ))}
        </select>
      </div>

      {/* Step cards */}
      <div style={{ flex: 1, overflowY: "auto", padding: "1rem 1.25rem" }}>
        {variantEvents.length === 0 && (
          <div style={{ fontSize: "0.72rem", color: "var(--color-faint)" }}>
            {variantIds.length === 0 ? "Waiting for trace events…" : "No events for this variant."}
          </div>
        )}
        {variantEvents.map((ev) => {
          const isOpen = !!expandedSteps[ev.step];
          const tokStr = ev.detail
            ? `${JSON.stringify(ev.detail).length} chars`
            : null;

          return (
            <div
              key={ev.event_id}
              style={{
                border: "1px solid var(--color-border)",
                borderRadius: 9,
                marginBottom: "0.8rem",
                background: "var(--color-bg)",
                overflow: "hidden",
              }}
            >
              {/* Step header */}
              <div
                onClick={() => toggleStep(ev.step)}
                style={{
                  padding: "0.6rem 0.85rem",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.65rem",
                  cursor: "pointer",
                  userSelect: "none",
                  background: isOpen ? "var(--color-surface)" : "var(--color-bg)",
                }}
              >
                {/* Step number */}
                <div
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: "50%",
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "0.62rem",
                    fontWeight: 800,
                    fontFamily: "var(--font-mono)",
                    background: "var(--color-accent)",
                    color: "var(--color-bg)",
                  }}
                >
                  {ev.step}
                </div>

                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--color-text)" }}>{ev.step_name}</div>
                  {ev.description && (
                    <div style={{ fontSize: "0.65rem", color: "var(--color-muted)", marginTop: "0.07rem" }}>{ev.description}</div>
                  )}
                </div>

                <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: "0.5rem" }}>
                  {tokStr && (
                    <span
                      style={{
                        fontSize: "0.62rem",
                        color: "var(--color-faint)",
                        fontFamily: "var(--font-mono)",
                      }}
                    >
                      {tokStr}
                    </span>
                  )}
                  <ScoreBadge score={ev.score} />
                  <span style={{ fontSize: "0.65rem", color: "var(--color-faint)", width: 10 }}>{isOpen ? "▼" : "▶"}</span>
                </div>
              </div>

              {/* Step body */}
              {isOpen && ev.detail && (
                <div
                  style={{
                    padding: "0 0.85rem 0.85rem",
                    borderTop: "1px solid var(--color-border)",
                  }}
                >
                  <div style={{ paddingTop: "0.7rem" }}>
                    <div
                      style={{
                        background: "var(--color-code-bg)",
                        borderRadius: 6,
                        padding: "0.6rem 0.85rem",
                        fontFamily: "var(--font-mono)",
                        fontSize: "0.64rem",
                        lineHeight: 1.75,
                        color: "var(--color-faint)",
                        overflowX: "auto",
                        whiteSpace: "pre",
                      }}
                      dangerouslySetInnerHTML={{ __html: syntaxHighlightJSON(ev.detail) }}
                    />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Right Panel — Live Metrics ─────────────────────────────────────────────────

function CriticSparkline({ criticScores }: { criticScores: number[] }) {
  const last12 = criticScores.slice(-12);
  const maxScore = 10;
  const avg = last12.length > 0 ? last12.reduce((a, b) => a + b, 0) / last12.length : 0;
  const best = last12.length > 0 ? Math.max(...last12) : 0;
  const fails = last12.filter((s) => s < 7).length;

  function barColor(s: number): { bg: string; border: string } {
    if (s >= 8.5) return { bg: "var(--color-green-light)", border: "var(--color-green-border)" };
    if (s >= 7)   return { bg: "var(--color-yellow-light)", border: "var(--color-yellow-border)" };
    return { bg: "var(--color-red-light)", border: "var(--color-red-border)" };
  }

  return (
    <div>
      {/* Sparkline bars */}
      <div style={{ display: "flex", alignItems: "flex-end", gap: 3, height: 38 }}>
        {last12.length === 0 && (
          <div style={{ fontSize: "0.65rem", color: "var(--color-faint)", alignSelf: "center" }}>No scores yet</div>
        )}
        {last12.map((s, i) => {
          const colors = barColor(s);
          const heightPct = (s / maxScore) * 100;
          return (
            <div
              key={i}
              title={`Score: ${s.toFixed(1)}`}
              style={{
                flex: 1,
                height: `${Math.max(10, heightPct)}%`,
                borderRadius: "3px 3px 0 0",
                background: colors.bg,
                border: `1px solid ${colors.border}`,
                minWidth: 5,
                cursor: "default",
              }}
            />
          );
        })}
      </div>

      {/* Labels */}
      {last12.length > 0 && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            fontSize: "0.57rem",
            color: "var(--color-faint)",
            fontFamily: "var(--font-mono)",
            marginTop: "0.2rem",
          }}
        >
          <span>oldest</span>
          <span>latest</span>
        </div>
      )}

      {/* Stats */}
      <div style={{ display: "flex", gap: "0.5rem", marginTop: "0.4rem", fontSize: "0.62rem", color: "var(--color-muted)", fontFamily: "var(--font-mono)" }}>
        <span>avg <strong style={{ color: "var(--color-text)" }}>{avg.toFixed(1)}</strong></span>
        <span>best <strong style={{ color: "var(--color-green)" }}>{best.toFixed(1)}</strong></span>
        <span>fails <strong style={{ color: "var(--color-red)" }}>{fails}</strong></span>
      </div>
    </div>
  );
}

function TokenBurnBars({ agents }: { agents: AgentStatus[] }) {
  const totalTokens = agents.reduce((acc, a) => acc + a.tokens_used, 0);
  const maxTokens = Math.max(1, ...agents.map((a) => a.tokens_used));

  return (
    <div>
      {agents.map((agent) => {
        const c = AGENT_COLORS[agent.agent_id] ?? { color: "var(--color-muted)" };
        const pct = (agent.tokens_used / maxTokens) * 100;
        return (
          <div key={agent.agent_id} style={{ display: "flex", alignItems: "center", gap: "0.45rem", marginBottom: "0.32rem" }}>
            <span
              style={{
                fontSize: "0.62rem",
                width: 20,
                fontFamily: "var(--font-mono)",
                fontWeight: 700,
                color: c.color,
                flexShrink: 0,
              }}
            >
              {agent.agent_id}
            </span>
            <div
              style={{
                flex: 1,
                height: 5,
                background: "var(--color-border)",
                borderRadius: 99,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${pct}%`,
                  background: c.color,
                  borderRadius: 99,
                  transition: "width 0.4s ease",
                }}
              />
            </div>
            <span
              style={{
                fontSize: "0.59rem",
                fontFamily: "var(--font-mono)",
                color: "var(--color-faint)",
                flexShrink: 0,
                width: 40,
                textAlign: "right",
              }}
            >
              {agent.tokens_used.toLocaleString()}
            </span>
          </div>
        );
      })}
      <div
        style={{
          marginTop: "0.3rem",
          fontSize: "0.62rem",
          color: "var(--color-muted)",
          fontFamily: "var(--font-mono)",
        }}
      >
        Total: <strong style={{ color: "var(--color-text)" }}>{totalTokens.toLocaleString()}</strong>
      </div>
    </div>
  );
}

// ── Main LiveMonitor component ─────────────────────────────────────────────────

interface LiveMonitorProps {
  runId: string;
  onComplete: () => void;
}

type TraceFilter = "all" | "done" | "running" | "error";
type CenterTab = "trace" | "detail";

export default function LiveMonitor({ runId, onComplete }: LiveMonitorProps) {
  const [status, setStatus] = useState<RunStatus | null>(null);
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [traceEvents, setTraceEvents] = useState<TraceEvent[]>([]);
  const [centerTab, setCenterTab] = useState<CenterTab>("trace");
  const [traceFilter, setTraceFilter] = useState<TraceFilter>("all");
  const [isPaused, setIsPaused] = useState(false);
  const [matrixDimensions, setMatrixDimensions] = useState<Array<{ name: string; values: unknown[] }>>([]);
  const completedRef = useRef(false);
  // True once we've seen the run in a non-complete state — prevents
  // auto-redirecting when the user navigates back to an already-finished run.
  const wasRunningRef = useRef(false);
  const consecutiveErrors = useRef(0);
  const [pollingError, setPollingError] = useState(false);

  // Poll status + agents at 1500ms
  useEffect(() => {
    let cancelled = false;

    // Issue 1: reset completedRef on each mount so navigating back to a
    // finished run doesn't leave it permanently true from a prior render.
    completedRef.current = false;

    async function poll() {
      try {
        const [st, ag, mx] = await Promise.all([
          getRunStatus(runId),
          getAgents(runId),
          getMatrix(runId),
        ]);
        if (cancelled) return;

        // Issue 3: reset consecutive error counter on success
        consecutiveErrors.current = 0;
        setPollingError(false);

        setStatus(st);
        setAgents(ag.agents);
        setMatrixDimensions(mx.dimensions);

        if (!st.is_complete) wasRunningRef.current = true;

        // Only auto-advance to Results if we watched the run go from running → complete
        // in this session. If the run is already complete on first poll, stay on the
        // monitor so the user can browse the trace before moving on.
        if (st.is_complete && wasRunningRef.current && !completedRef.current) {
          completedRef.current = true;
          setTimeout(() => {
            if (!cancelled) onComplete();
          }, 1200);
        }
      } catch {
        // Issue 3: track consecutive failures and surface an error banner
        consecutiveErrors.current += 1;
        if (consecutiveErrors.current >= 3) {
          setPollingError(true);
        }
      }
    }

    poll();
    const id = setInterval(poll, 1500);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [runId, onComplete]);

  // Poll trace at 3000ms
  useEffect(() => {
    let cancelled = false;

    async function pollTrace() {
      try {
        const { events } = await getTrace(runId);
        if (!cancelled) setTraceEvents(events);
      } catch {
        // ignore
      }
    }

    pollTrace();
    const id = setInterval(pollTrace, 3000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [runId]);

  // Pause/resume animations
  useEffect(() => {
    if (typeof document !== "undefined") {
      if (isPaused) {
        document.body.classList.add("animation-paused");
      } else {
        document.body.classList.remove("animation-paused");
      }
    }
  }, [isPaused]);

  const handlePause = useCallback(async () => {
    const next = !isPaused;
    setIsPaused(next);
    await sendControl(runId, next ? "pause" : "run").catch(() => {});
  }, [isPaused, runId]);

  const handleStop = useCallback(async () => {
    if (confirm("Stop this run? In-progress variants will be lost.")) {
      await sendControl(runId, "stop").catch(() => {});
    }
  }, [runId]);

  // Derived values
  const completed = status?.variants_completed ?? 0;
  const total = status?.variants_total ?? 0;
  const pct = total > 0 ? Math.round((completed / total) * 100) : 0;
  const cost = status?.total_cost_usd ?? 0;
  const elapsed = status?.elapsed_s ?? 0;
  const approved = status?.variant_log.filter((v) => v.passed).length ?? 0;
  const failed = status?.variant_log.filter((v) => !v.passed && v.status === "rejected").length ?? 0;
  const retry = status?.revisions_count ?? 0;

  // Critic scores from variant_log
  const criticScores = (status?.variant_log ?? [])
    .map((v) => v.critic_score)
    .filter((s): s is number => s != null);

  // Coverage cells
  const coverageCells = status?.coverage_cells ?? [];

  // Fleet stats
  const activeCount = agents.filter((a) => a.status === "running").length;
  const doneCount = agents.filter((a) => a.status === "done").length;
  const retryCount = agents.filter((a) => a.status === "retry").length;

  // Filtered trace events
  const filteredEvents =
    traceFilter === "all"
      ? traceEvents
      : traceEvents.filter((e) => e.status === traceFilter);

  // Group trace events by variant_id
  const variantGroups: Record<string, TraceEvent[]> = {};
  for (const ev of filteredEvents) {
    const vid = ev.variant_id || "unknown";
    if (!variantGroups[vid]) variantGroups[vid] = [];
    variantGroups[vid].push(ev);
  }
  const variantGroupEntries = Object.entries(variantGroups);

  return (
    <div style={{ display: "flex", flexDirection: "column", minHeight: "100vh", background: "var(--color-bg)", color: "var(--color-text)" }}>

      {/* ── Monitor Top Bar ── */}
      <div
        style={{
          position: "sticky",
          top: 0,
          zIndex: 50,
          background: "var(--color-bg)",
          borderBottom: "2px solid var(--color-border)",
          padding: "0.6rem 1.25rem",
          display: "flex",
          flexDirection: "column",
          gap: "0.35rem",
        }}
      >
        {/* Row 1 */}
        <div style={{ display: "flex", alignItems: "center", gap: "1.25rem", flexWrap: "wrap" }}>
          {/* Run ID */}
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.82rem",
              fontWeight: 800,
              color: "var(--color-accent)",
              whiteSpace: "nowrap",
            }}
          >
            {runId}
          </span>

          {/* Progress */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.6rem" }}>
            <span style={{ fontSize: "0.72rem", fontWeight: 700, color: "var(--color-text)", whiteSpace: "nowrap" }}>
              {completed} / {total}
            </span>
            <div
              style={{
                width: 120,
                height: 5,
                background: "var(--color-surface2)",
                borderRadius: 99,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  height: "100%",
                  width: `${pct}%`,
                  background: "var(--color-accent)",
                  borderRadius: 99,
                  transition: "width 0.5s ease",
                }}
              />
            </div>
            <span style={{ fontSize: "0.65rem", color: "var(--color-muted)" }}>{pct}%</span>
          </div>

          {/* Cost */}
          <span
            className="pulse"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "var(--color-yellow)",
              whiteSpace: "nowrap",
            }}
          >
            ${cost.toFixed(2)}
          </span>

          {/* Time */}
          <span
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: "0.75rem",
              fontWeight: 700,
              color: "var(--color-muted)",
              whiteSpace: "nowrap",
            }}
          >
            {formatElapsed(elapsed)}
          </span>

          {/* Spacer */}
          <div style={{ flex: 1 }} />

          {/* Controls */}
          <div style={{ display: "flex", gap: "0.4rem", flexShrink: 0 }}>
            <button
              onClick={handlePause}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
                borderRadius: 7,
                fontWeight: 600,
                fontSize: "0.75rem",
                padding: "0.4rem 0.85rem",
                cursor: "pointer",
                border: "1px solid var(--color-border)",
                background: "var(--color-surface)",
                color: "var(--color-muted)",
                fontFamily: "var(--font-sans)",
                whiteSpace: "nowrap",
              }}
            >
              {isPaused ? "▶ Resume" : "⏸ Pause"}
            </button>
            <button
              onClick={handleStop}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "0.35rem",
                borderRadius: 7,
                fontWeight: 600,
                fontSize: "0.75rem",
                padding: "0.4rem 0.85rem",
                cursor: "pointer",
                border: "1px solid var(--color-red-border)",
                background: "var(--color-red-light)",
                color: "var(--color-red)",
                fontFamily: "var(--font-sans)",
                whiteSpace: "nowrap",
              }}
            >
              ⏹ Stop
            </button>
          </div>
        </div>

        {/* Row 2 */}
        <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
          {/* Fraud description */}
          <span
            style={{
              fontSize: "0.68rem",
              color: "var(--color-muted)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
              maxWidth: 380,
              flex: 1,
            }}
          >
            {status?.current_phase ? `Phase: ${status.current_phase}` : "Initializing…"}
          </span>

          {/* Status counts */}
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontSize: "0.65rem", flexShrink: 0 }}>
            <span>
              Approved:{" "}
              <strong style={{ color: "var(--color-green)" }}>{approved}</strong>
            </span>
            <span style={{ color: "var(--color-faint)" }}>·</span>
            <span>
              Retry:{" "}
              <strong style={{ color: "var(--color-yellow)" }}>{retry}</strong>
            </span>
            <span style={{ color: "var(--color-faint)" }}>·</span>
            <span>
              Failed:{" "}
              <strong style={{ color: "var(--color-red)" }}>{failed}</strong>
            </span>
          </div>
        </div>
      </div>

      {/* ── Polling Error Banner ── */}
      {pollingError && (
        <div
          style={{
            background: "var(--color-red-light)",
            borderBottom: "1px solid var(--color-red-border)",
            color: "var(--color-red)",
            padding: "0.45rem 1.25rem",
            fontSize: "0.72rem",
            fontWeight: 600,
          }}
        >
          Connection to server lost. Retrying...
        </div>
      )}

      {/* ── Three-Column Body ── */}
      <div
        style={{
          flex: 1,
          display: "grid",
          gridTemplateColumns: "240px 1fr 220px",
          borderTop: "1px solid var(--color-border)",
          overflow: "hidden",
          minHeight: 0,
          height: "calc(100vh - 90px)",
        }}
      >

        {/* ── Left Column — Agent Fleet ── */}
        <div
          style={{
            borderRight: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Header */}
          <div
            style={{
              padding: "0.65rem 0.85rem",
              borderBottom: "1px solid var(--color-border)",
              flexShrink: 0,
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <span
              style={{
                fontSize: "0.65rem",
                fontWeight: 700,
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "var(--color-faint)",
              }}
            >
              Agent Fleet
            </span>
            <div style={{ display: "flex", alignItems: "center", gap: "0.35rem", fontSize: "0.65rem", color: "var(--color-green)", fontWeight: 700 }}>
              <span className="pulse" style={{ display: "inline-block", width: 7, height: 7, borderRadius: "50%", background: "var(--color-green)" }} />
              Live
            </div>
          </div>

          {/* Agent list */}
          <div style={{ flex: 1, overflowY: "auto", padding: "0.5rem" }}>
            {agents.length === 0 && (
              <div style={{ fontSize: "0.7rem", color: "var(--color-faint)", padding: "0.5rem 0.25rem" }}>
                Waiting for agents…
              </div>
            )}
            {agents.map((agent) => (
              <AgentCard key={agent.agent_id} agent={agent} />
            ))}
          </div>

          {/* Footer */}
          <div
            style={{
              flexShrink: 0,
              padding: "0.65rem 0.85rem",
              borderTop: "1px solid var(--color-border)",
              display: "flex",
              gap: "1rem",
            }}
          >
            <div style={{ fontSize: "0.65rem", color: "var(--color-muted)" }}>
              Active <strong style={{ color: "var(--color-text)", fontSize: "0.72rem" }}>{activeCount}</strong>
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--color-muted)" }}>
              Done <strong style={{ color: "var(--color-text)", fontSize: "0.72rem" }}>{doneCount}</strong>
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--color-muted)" }}>
              Retry <strong style={{ color: "var(--color-text)", fontSize: "0.72rem" }}>{retryCount}</strong>
            </div>
          </div>
        </div>

        {/* ── Center Column — Trace / Detail ── */}
        <div
          style={{
            borderRight: "1px solid var(--color-border)",
            background: "var(--color-bg)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Tab bar */}
          <div
            style={{
              display: "flex",
              borderBottom: "1px solid var(--color-border)",
              padding: "0 1.25rem",
              flexShrink: 0,
              background: "var(--color-bg)",
            }}
          >
            {(["trace", "detail"] as CenterTab[]).map((tab) => {
              const label = tab === "trace" ? "Execution Trace" : "Variant Detail";
              const isActive = centerTab === tab;
              return (
                <button
                  key={tab}
                  onClick={() => setCenterTab(tab)}
                  style={{
                    padding: "0.6rem 1rem",
                    fontSize: "0.78rem",
                    color: isActive ? "var(--color-accent)" : "var(--color-muted)",
                    fontWeight: isActive ? 600 : 400,
                    borderTop: "none",
                    borderLeft: "none",
                    borderRight: "none",
                    borderBottom: isActive ? "2px solid var(--color-accent)" : "2px solid transparent",
                    background: "none",
                    cursor: "pointer",
                    fontFamily: "var(--font-sans)",
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {/* Trace tab */}
          {centerTab === "trace" && (
            <div style={{ display: "flex", flexDirection: "column", flex: 1, overflow: "hidden" }}>
              {/* Filter toolbar */}
              <div
                style={{
                  padding: "0.55rem 1.25rem",
                  borderBottom: "1px solid var(--color-border)",
                  display: "flex",
                  alignItems: "center",
                  gap: "0.5rem",
                  flexShrink: 0,
                  background: "var(--color-surface)",
                  flexWrap: "wrap",
                }}
              >
                {(["all", "done", "running", "error"] as TraceFilter[]).map((f) => {
                  const isActive = traceFilter === f;
                  return (
                    <button
                      key={f}
                      onClick={() => setTraceFilter(f)}
                      style={{
                        padding: "0.2rem 0.6rem",
                        borderRadius: 5,
                        fontSize: "0.67rem",
                        fontWeight: 600,
                        border: `1px solid ${isActive ? "var(--color-accent-border)" : "var(--color-border)"}`,
                        color: isActive ? "var(--color-accent)" : "var(--color-muted)",
                        background: isActive ? "var(--color-accent-light)" : "var(--color-bg)",
                        cursor: "pointer",
                        fontFamily: "var(--font-sans)",
                        textTransform: "capitalize",
                      }}
                    >
                      {f}
                    </button>
                  );
                })}
                <span
                  style={{
                    marginLeft: "auto",
                    fontSize: "0.65rem",
                    color: "var(--color-faint)",
                    fontFamily: "var(--font-mono)",
                  }}
                >
                  {filteredEvents.length} entries
                </span>
              </div>

              {/* Scrollable trace list */}
              <div style={{ flex: 1, overflowY: "auto" }}>
                {variantGroupEntries.length === 0 && (
                  <div style={{ padding: "1rem 1.25rem", fontSize: "0.72rem", color: "var(--color-faint)" }}>
                    Waiting for trace events…
                  </div>
                )}
                {variantGroupEntries.map(([vid, events]) => (
                  <VariantGroup key={vid} variantId={vid} events={events} />
                ))}
              </div>
            </div>
          )}

          {/* Variant Detail tab */}
          {centerTab === "detail" && (
            <VariantDetailTab allEvents={traceEvents} />
          )}
        </div>

        {/* ── Right Column — Live Metrics ── */}
        <div
          style={{
            background: "var(--color-surface)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          <div style={{ flex: 1, overflowY: "auto" }}>

            {/* Section 1: Critic Scores */}
            <div style={{ padding: "0.8rem", borderBottom: "1px solid var(--color-border)" }}>
              <div
                style={{
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--color-faint)",
                  marginBottom: "0.55rem",
                }}
              >
                Critic Scores
              </div>
              <CriticSparkline criticScores={criticScores} />
            </div>

            {/* Section 2: Token Burn by Agent */}
            <div style={{ padding: "0.8rem", borderBottom: "1px solid var(--color-border)" }}>
              <div
                style={{
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--color-faint)",
                  marginBottom: "0.55rem",
                }}
              >
                Token Burn
              </div>
              {agents.length === 0 ? (
                <div style={{ fontSize: "0.65rem", color: "var(--color-faint)" }}>No agents yet</div>
              ) : (
                <TokenBurnBars agents={agents} />
              )}
            </div>

            {/* Section 3: Coverage Matrix Mini */}
            <div style={{ padding: "0.8rem" }}>
              <div
                style={{
                  fontSize: "0.62rem",
                  fontWeight: 700,
                  letterSpacing: "0.08em",
                  textTransform: "uppercase",
                  color: "var(--color-faint)",
                  marginBottom: "0.55rem",
                }}
              >
                Coverage Matrix
              </div>
              <CoverageMatrix
                cells={coverageCells}
                dimensions={matrixDimensions}
              />
            </div>

          </div>
        </div>

      </div>
    </div>
  );
}
