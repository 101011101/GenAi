"use client";

import { useState, useEffect } from "react";
import AppShell from "@/components/AppShell";
import ConfigureRun from "@/components/ConfigureRun";
import LiveMonitor from "@/components/LiveMonitor";
import Results from "@/components/Results";
import { getRunStatus } from "@/lib/api";

type Screen = "input" | "monitor" | "results";

function loadState(): { screen: Screen; runId: string | null } {
  if (typeof window === "undefined") return { screen: "input", runId: null };
  const runId = localStorage.getItem("runId");
  const screen = (localStorage.getItem("screen") as Screen) || "input";
  if ((screen === "monitor" || screen === "results") && !runId) {
    return { screen: "input", runId: null };
  }
  return { screen, runId };
}

export default function Home() {
  // Always start with SSR-safe defaults — localStorage is client-only.
  // Don't render screens that need a runId until validation completes.
  const [screen, setScreen] = useState<Screen>("input");
  const [runId, setRunId] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const saved = loadState();
    if (!saved.runId || saved.screen === "input") {
      setReady(true);
      return;
    }
    // Validate the persisted run against the backend before restoring.
    getRunStatus(saved.runId)
      .then(() => {
        setRunId(saved.runId);
        setScreen(saved.screen);
      })
      .catch(() => {
        localStorage.removeItem("runId");
        localStorage.setItem("screen", "input");
      })
      .finally(() => setReady(true));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function persist(newScreen: Screen, newRunId: string | null) {
    if (newRunId) localStorage.setItem("runId", newRunId);
    else localStorage.removeItem("runId");
    localStorage.setItem("screen", newScreen);
  }

  function handleStart(newRunId: string) {
    setRunId(newRunId);
    setScreen("monitor");
    persist("monitor", newRunId);
  }

  function handleComplete() {
    setScreen("results");
    persist("results", runId);
  }

  function handleNavigate(target: Screen) {
    if ((target === "monitor" || target === "results") && !runId) return;
    setScreen(target);
    persist(target, runId);
  }

  if (!ready) return null;

  return (
    <AppShell screen={screen} runId={runId} onNavigate={handleNavigate}>
      {screen === "input" && <ConfigureRun onStart={handleStart} />}
      {screen === "monitor" && runId && (
        <LiveMonitor runId={runId} onComplete={handleComplete} />
      )}
      {screen === "results" && runId && (
        <Results runId={runId} onNewRun={() => { setRunId(null); setScreen("input"); persist("input", null); }} />
      )}
    </AppShell>
  );
}
