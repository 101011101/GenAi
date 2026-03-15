"use client";

import { useEffect, useState, useCallback } from "react";
import { getRuns, getRunStatus, sendControl, formatElapsed } from "@/lib/api";
import { useTheme } from "@/lib/ThemeContext";
import { THEMES, THEME_KEYS, type ThemeKey } from "@/lib/themes";

type Screen = "input" | "monitor" | "results";

interface AppShellProps {
  screen: Screen;
  runId: string | null;
  children: React.ReactNode;
  onNavigate: (screen: Screen) => void;
}

interface RecentRun {
  run_id: string;
  fraud_description: string;
  status: string;
  variants_total: number;
  variants_completed: number;
  is_complete: boolean;
  total_cost_usd: number;
  elapsed_s: number;
}

interface LiveStats {
  approved: number;
  retry: number;
  failed: number;
  cost: number;
  elapsed: number;
}

function StatusChip({ status }: { status: string }) {
  let bg = "var(--color-surface2)";
  let color = "var(--color-muted)";
  let label = status;

  if (status === "complete" || status === "completed") {
    bg = "var(--color-green-light)"; color = "var(--color-green)"; label = "done";
  } else if (status === "running" || status === "in_progress") {
    bg = "var(--color-accent-light)"; color = "var(--color-accent)"; label = "live";
  } else if (status === "error" || status === "failed") {
    bg = "var(--color-red-light)"; color = "var(--color-red)"; label = "error";
  } else if (status === "paused") {
    bg = "var(--color-yellow-light)"; color = "var(--color-yellow)"; label = "paused";
  }

  return (
    <span
      style={{
        background: bg,
        color,
        fontSize: "0.65rem",
        fontWeight: 700,
        letterSpacing: "0.05em",
        textTransform: "uppercase" as const,
        padding: "0.15rem 0.4rem",
        borderRadius: "3px",
        flexShrink: 0,
      }}
    >
      {label}
    </span>
  );
}

export default function AppShell({ screen, runId, children, onNavigate }: AppShellProps) {
  const [recentRuns, setRecentRuns] = useState<RecentRun[]>([]);
  const [liveStats, setLiveStats] = useState<LiveStats | null>(null);
  const { theme, setTheme } = useTheme();

  // Poll recent runs every 5s
  const fetchRuns = useCallback(async () => {
    try {
      const runs = await getRuns();
      setRecentRuns(runs.slice(0, 8));
    } catch {
      // API may be unavailable; fail silently
    }
  }, []);

  // Poll live stats during monitor screen
  const fetchLiveStats = useCallback(async () => {
    if (!runId || screen !== "monitor") return;
    try {
      const status = await getRunStatus(runId);
      // Count from variant_log
      const approved = status.variant_log.filter((v) => v.passed).length;
      const failed = status.variant_log.filter((v) => !v.passed && v.status === "rejected").length;
      const retry = status.revisions_count;
      setLiveStats({
        approved,
        retry,
        failed,
        cost: status.total_cost_usd,
        elapsed: status.elapsed_s,
      });
    } catch {
      // fail silently
    }
  }, [runId, screen]);

  useEffect(() => {
    fetchRuns();
    const runsInterval = setInterval(fetchRuns, 5000);
    return () => clearInterval(runsInterval);
  }, [fetchRuns]);

  useEffect(() => {
    if (screen === "monitor" && runId) {
      fetchLiveStats();
      const statsInterval = setInterval(fetchLiveStats, 3000);
      return () => clearInterval(statsInterval);
    }
  }, [screen, runId, fetchLiveStats]);

  // URL bar display
  let urlDisplay = "localhost:8000";
  if (runId && screen === "monitor") urlDisplay = `localhost:8000 · ${runId.slice(0, 8)}`;
  if (runId && screen === "results") urlDisplay = `localhost:8000 · ${runId.slice(0, 8)} · complete`;

  const navItems: { key: Screen; label: string; icon: string }[] = [
    { key: "input", label: "New Run", icon: "+" },
    { key: "monitor", label: "Monitor", icon: "◉" },
    { key: "results", label: "Results", icon: "↓" },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100vh", overflow: "hidden" }}>
      {/* Browser chrome top bar */}
      <div
        style={{
          background: "var(--color-surface2)",
          borderBottom: "1px solid var(--color-border)",
          padding: "0 1rem",
          height: "40px",
          display: "flex",
          alignItems: "center",
          gap: "0.75rem",
          flexShrink: 0,
        }}
      >
        {/* Window dots */}
        <div style={{ display: "flex", gap: "5px", alignItems: "center" }}>
          <span
            style={{
              width: "11px",
              height: "11px",
              borderRadius: "50%",
              background: "#fc605c",
              display: "inline-block",
            }}
          />
          <span
            style={{
              width: "11px",
              height: "11px",
              borderRadius: "50%",
              background: "#fdbc40",
              display: "inline-block",
            }}
          />
          <span
            style={{
              width: "11px",
              height: "11px",
              borderRadius: "50%",
              background: "#35cd4b",
              display: "inline-block",
            }}
          />
        </div>

        {/* URL bar */}
        <div
          style={{
            flex: 1,
            maxWidth: "480px",
            margin: "0 auto",
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "5px",
            padding: "0.2rem 0.75rem",
            fontSize: "0.75rem",
            color: "var(--color-muted)",
            fontFamily: "var(--font-mono, monospace)",
            display: "flex",
            alignItems: "center",
            gap: "0.4rem",
          }}
        >
          <span style={{ color: "var(--color-green)", fontSize: "0.65rem" }}>⬤</span>
          {urlDisplay}
        </div>

        <div style={{ marginLeft: "auto", fontSize: "0.7rem", color: "var(--color-faint)" }}>
          FraudGen Console
        </div>
      </div>

      {/* Main layout: sidebar + content */}
      <div style={{ display: "flex", flex: 1, overflow: "hidden" }}>
        {/* Sidebar */}
        <div
          style={{
            width: "200px",
            flexShrink: 0,
            borderRight: "1px solid var(--color-border)",
            background: "var(--color-surface)",
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Logo */}
          <div
            style={{
              padding: "1.25rem 1rem 0.75rem",
              borderBottom: "1px solid var(--color-border)",
            }}
          >
            <div
              style={{
                fontWeight: 800,
                fontSize: "1.1rem",
                color: "var(--color-accent)",
                letterSpacing: "-0.02em",
                fontFamily: "var(--font-display)",
              }}
            >
              FraudGen
            </div>
            <div style={{ fontSize: "0.65rem", color: "var(--color-faint)", marginTop: "0.1rem" }}>
              Synthetic variant generator
            </div>
          </div>

          {/* Nav items */}
          <nav style={{ padding: "0.75rem 0.5rem" }}>
            {navItems.map((item) => {
              const isActive = screen === item.key;
              const isDisabled =
                (item.key === "monitor" || item.key === "results") && !runId;

              return (
                <button
                  key={item.key}
                  onClick={() => !isDisabled && onNavigate(item.key)}
                  disabled={isDisabled}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.5rem",
                    width: "100%",
                    padding: "0.5rem 0.625rem",
                    borderRadius: "6px",
                    border: "none",
                    cursor: isDisabled ? "not-allowed" : "pointer",
                    background: isActive ? "var(--color-accent-light)" : "transparent",
                    color: isActive ? "var(--color-accent)" : isDisabled ? "var(--color-border)" : "var(--color-text)",
                    fontWeight: isActive ? 700 : 500,
                    fontSize: "0.84rem",
                    textAlign: "left",
                    marginBottom: "0.15rem",
                    transition: "background 0.1s",
                  }}
                  onMouseEnter={(e) => {
                    if (!isActive && !isDisabled) {
                      (e.currentTarget as HTMLButtonElement).style.background = "var(--color-surface2)";
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isActive) {
                      (e.currentTarget as HTMLButtonElement).style.background = "transparent";
                    }
                  }}
                >
                  <span
                    style={{
                      width: "18px",
                      textAlign: "center",
                      fontSize: item.key === "input" ? "1rem" : "0.8rem",
                      lineHeight: 1,
                    }}
                  >
                    {item.icon}
                  </span>
                  {item.label}
                </button>
              );
            })}
          </nav>

          {/* History section */}
          <div style={{ padding: "0 0.5rem", flex: 1, overflowY: "auto" }}>
            <div
              style={{
                fontSize: "0.65rem",
                fontWeight: 700,
                letterSpacing: "0.1em",
                textTransform: "uppercase",
                color: "var(--color-faint)",
                padding: "0.25rem 0.625rem 0.5rem",
                marginTop: "0.25rem",
              }}
            >
              History
            </div>

            {recentRuns.length === 0 && (
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--color-border)",
                  padding: "0.25rem 0.625rem",
                  fontStyle: "italic",
                }}
              >
                No runs yet
              </div>
            )}

            {recentRuns.map((run) => (
              <div
                key={run.run_id}
                style={{
                  padding: "0.4rem 0.625rem",
                  borderRadius: "5px",
                  marginBottom: "0.2rem",
                  cursor: "pointer",
                  background: runId === run.run_id ? "var(--color-accent-light)" : "transparent",
                }}
                onMouseEnter={(e) => {
                  if (runId !== run.run_id) {
                    (e.currentTarget as HTMLDivElement).style.background = "var(--color-surface2)";
                  }
                }}
                onMouseLeave={(e) => {
                  if (runId !== run.run_id) {
                    (e.currentTarget as HTMLDivElement).style.background = "transparent";
                  }
                }}
              >
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    gap: "0.35rem",
                    marginBottom: "0.15rem",
                  }}
                >
                  <span
                    style={{
                      fontFamily: "var(--font-mono, monospace)",
                      fontSize: "0.7rem",
                      color: "var(--color-text)",
                      fontWeight: 600,
                    }}
                  >
                    {run.run_id.slice(0, 8)}
                  </span>
                  <StatusChip status={run.is_complete ? "complete" : run.status} />
                </div>
                <div
                  style={{
                    fontSize: "0.68rem",
                    color: "var(--color-muted)",
                    whiteSpace: "nowrap",
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                  }}
                  title={run.fraud_description}
                >
                  {run.fraud_description.slice(0, 28)}
                  {run.fraud_description.length > 28 ? "…" : ""}
                </div>
              </div>
            ))}
          </div>

          {/* Footer */}
          <div
            style={{
              borderTop: "1px solid var(--color-border)",
              padding: "0.75rem 1rem",
              flexShrink: 0,
            }}
          >
            {/* Live stats during monitor */}
            {screen === "monitor" && liveStats && (
              <div style={{ marginBottom: "0.75rem" }}>
                <div
                  style={{
                    fontSize: "0.65rem",
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "var(--color-faint)",
                    marginBottom: "0.4rem",
                  }}
                >
                  Live Stats
                </div>
                <div
                  style={{
                    display: "flex",
                    gap: "0.5rem",
                    flexWrap: "wrap",
                    marginBottom: "0.35rem",
                  }}
                >
                  <span style={{ fontSize: "0.72rem", color: "var(--color-green)", fontWeight: 600 }}>
                    ✓ {liveStats.approved}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "var(--color-yellow)", fontWeight: 600 }}>
                    ↺ {liveStats.retry}
                  </span>
                  <span style={{ fontSize: "0.72rem", color: "var(--color-red)", fontWeight: 600 }}>
                    ✕ {liveStats.failed}
                  </span>
                </div>
                <div style={{ fontSize: "0.7rem", color: "var(--color-muted)", marginBottom: "0.3rem" }}>
                  <span style={{ color: "var(--color-yellow)", fontWeight: 600 }}>
                    ${liveStats.cost.toFixed(2)}
                  </span>
                  {" "}·{" "}
                  {formatElapsed(liveStats.elapsed)}
                </div>

                {/* Control buttons */}
                {runId && (
                  <div style={{ display: "flex", gap: "0.35rem", marginTop: "0.4rem" }}>
                    <button
                      onClick={() => sendControl(runId, "pause")}
                      style={{
                        flex: 1,
                        padding: "0.3rem 0.4rem",
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        background: "var(--color-yellow-light)",
                        color: "var(--color-yellow)",
                        border: "1px solid var(--color-yellow-border)",
                        borderRadius: "5px",
                        cursor: "pointer",
                      }}
                    >
                      ⏸ Pause
                    </button>
                    <button
                      onClick={() => sendControl(runId, "stop")}
                      style={{
                        flex: 1,
                        padding: "0.3rem 0.4rem",
                        fontSize: "0.7rem",
                        fontWeight: 600,
                        background: "var(--color-red-light)",
                        color: "var(--color-red)",
                        border: "1px solid var(--color-red-border)",
                        borderRadius: "5px",
                        cursor: "pointer",
                      }}
                    >
                      ⏹ Stop
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Mode / Model info */}
            <div style={{ fontSize: "0.7rem", color: "var(--color-faint)", lineHeight: 1.6, marginBottom: "0.6rem" }}>
              <div>
                <span style={{ color: "var(--color-muted)" }}>Mode:</span> Live
              </div>
              <div>
                <span style={{ color: "var(--color-muted)" }}>Model:</span> Sonnet
              </div>
            </div>

            {/* Theme switcher */}
            <div style={{ display: "flex", gap: "0.3rem" }}>
              {THEME_KEYS.map((key: ThemeKey) => {
                const isActive = theme === key;
                return (
                  <button
                    key={key}
                    onClick={() => setTheme(key)}
                    title={THEMES[key].name}
                    style={{
                      flex: 1,
                      padding: "0.25rem 0",
                      fontSize: "0.65rem",
                      fontWeight: isActive ? 700 : 500,
                      borderRadius: "4px",
                      border: isActive
                        ? `1px solid var(--color-accent)`
                        : "1px solid var(--color-border)",
                      background: isActive ? "var(--color-accent-light)" : "transparent",
                      color: isActive ? "var(--color-accent)" : "var(--color-muted)",
                      cursor: "pointer",
                      transition: "all 0.1s",
                    }}
                  >
                    {THEMES[key].name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* Main content */}
        <main
          style={{
            flex: 1,
            overflowY: "auto",
            background: "var(--color-bg)",
          }}
        >
          {children}
        </main>
      </div>
    </div>
  );
}
