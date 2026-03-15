"use client";

import { useMemo } from "react";
import { type ScoredVariant } from "@/lib/api";

interface Props {
  variant: ScoredVariant;
}

interface PositionedNode {
  id: string;
  role: string;
  x: number;
  y: number;
}

interface Edge {
  from: string;
  to: string;
  isFraud: boolean;
}

function nodeStyle(role: string): React.CSSProperties {
  const base: React.CSSProperties = {
    position: "absolute",
    width: "40px",
    height: "28px",
    borderRadius: "5px",
    border: "1.5px solid",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontSize: "0.6rem",
    fontFamily: "var(--font-mono)",
    fontWeight: 700,
    zIndex: 2,
    transform: "translate(-50%, -50%)",
    textAlign: "center",
    lineHeight: 1.2,
    padding: "0 2px",
  };
  if (role === "fraud" || role === "mule" || role === "placement") {
    return { ...base, background: "var(--color-red-light)", borderColor: "var(--color-red-border)", color: "var(--color-red-dark)" };
  }
  if (role === "extraction" || role === "crypto") {
    return { ...base, background: "var(--color-purple-light)", borderColor: "var(--color-purple-light)", color: "var(--color-purple-dark)" };
  }
  // cover / default
  return { ...base, background: "var(--color-surface2)", borderColor: "var(--color-border)", color: "var(--color-muted)" };
}

export default function NetworkGraph({ variant }: Props) {
  const W = 320;
  const H = 190;

  const { nodes, edges } = useMemo<{ nodes: PositionedNode[]; edges: Edge[] }>(() => {
    const accounts = variant.accounts ?? [];
    const transactions = variant.transactions ?? [];

    if (accounts.length === 0 || transactions.length === 0) {
      return { nodes: [], edges: [] };
    }

    // Categorise accounts
    const fraudAccounts = accounts.filter(
      (a) => a.role === "fraud" || a.role === "mule" || a.role === "placement"
    );
    const extractAccounts = accounts.filter(
      (a) => a.role === "extraction" || a.role === "crypto"
    );
    const coverAccounts = accounts.filter(
      (a) => a.role !== "fraud" && a.role !== "mule" && a.role !== "placement" &&
             a.role !== "extraction" && a.role !== "crypto"
    );

    const allGroups = [fraudAccounts, extractAccounts, coverAccounts];
    const positioned: PositionedNode[] = [];

    // Spread three columns: left=fraud, center=extract, right=cover
    const colXs = [W * 0.18, W * 0.5, W * 0.82];
    allGroups.forEach((group, gi) => {
      group.forEach((acc, i) => {
        const count = group.length;
        const spacing = count > 1 ? (H - 40) / (count - 1) : 0;
        const y = count > 1 ? 20 + i * spacing : H / 2;
        positioned.push({ id: acc.account_id, role: acc.role, x: colXs[gi], y });
      });
    });

    // Build an id -> position map
    const posMap = new Map(positioned.map((n) => [n.id, n]));

    // Build edges from transactions
    const edgeSet: Edge[] = [];
    const seen = new Set<string>();
    for (const txn of transactions) {
      const from = txn.sender_account_id;
      const to = txn.receiver_account_id;
      if (!from || !to) continue;
      const key = `${from}→${to}`;
      if (seen.has(key)) continue;
      seen.add(key);
      if (posMap.has(from) && posMap.has(to)) {
        edgeSet.push({ from, to, isFraud: txn.is_fraud });
      }
    }

    return { nodes: positioned, edges: edgeSet };
  }, [variant]);

  const hasData = nodes.length > 0;

  // Total amount
  const totalIn = (variant.transactions ?? [])
    .filter((t) => t.is_fraud && t.fraud_role === "placement")
    .reduce((s, t) => s + t.amount, 0);
  const totalOut = (variant.transactions ?? [])
    .filter((t) => t.is_fraud && t.fraud_role === "extraction")
    .reduce((s, t) => s + t.amount, 0);

  // Position map for SVG line drawing
  const posMap = new Map(nodes.map((n) => [n.id, n]));

  return (
    <div>
      <div
        style={{
          height: "190px",
          background: "var(--color-surface)",
          border: "1px solid var(--color-border)",
          borderRadius: "8px",
          position: "relative",
          overflow: "hidden",
        }}
      >
        {hasData ? (
          <>
            {/* SVG edges */}
            <svg
              width={W}
              height={H}
              style={{ position: "absolute", top: 0, left: 0, width: "100%", height: "100%" }}
              viewBox={`0 0 ${W} ${H}`}
              preserveAspectRatio="none"
            >
              <defs>
                <marker
                  id={`arrow-fraud-${variant.variant_id}`}
                  markerWidth="8"
                  markerHeight="8"
                  refX="6"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L0,6 L8,3 z" fill="var(--color-red)" />
                </marker>
                <marker
                  id={`arrow-cover-${variant.variant_id}`}
                  markerWidth="8"
                  markerHeight="8"
                  refX="6"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L0,6 L8,3 z" fill="var(--color-faint)" />
                </marker>
              </defs>
              {edges.map((edge, i) => {
                const from = posMap.get(edge.from);
                const to = posMap.get(edge.to);
                if (!from || !to) return null;
                // Scale to SVG space
                const x1 = from.x;
                const y1 = from.y;
                const x2 = to.x;
                const y2 = to.y;
                return edge.isFraud ? (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="var(--color-red)"
                    strokeWidth="1.5"
                    markerEnd={`url(#arrow-fraud-${variant.variant_id})`}
                  />
                ) : (
                  <line
                    key={i}
                    x1={x1}
                    y1={y1}
                    x2={x2}
                    y2={y2}
                    stroke="var(--color-faint)"
                    strokeWidth="1.5"
                    strokeDasharray="4 3"
                    markerEnd={`url(#arrow-cover-${variant.variant_id})`}
                  />
                );
              })}
            </svg>

            {/* Node divs */}
            {nodes.map((node) => (
              <div
                key={node.id}
                style={{
                  ...nodeStyle(node.role),
                  left: `${(node.x / W) * 100}%`,
                  top: `${(node.y / H) * 100}%`,
                }}
                title={`${node.id} (${node.role})`}
              >
                {node.id.slice(-4)}
              </div>
            ))}
          </>
        ) : (
          <>
            {/* Placeholder grid pattern */}
            <svg
              width="100%"
              height="100%"
              style={{ position: "absolute", top: 0, left: 0, opacity: 0.18 }}
            >
              <defs>
                <pattern id={`grid-${variant.variant_id}`} width="20" height="20" patternUnits="userSpaceOnUse">
                  <path d="M 20 0 L 0 0 0 20" fill="none" stroke="var(--color-faint)" strokeWidth="0.5" />
                </pattern>
              </defs>
              <rect width="100%" height="100%" fill={`url(#grid-${variant.variant_id})`} />
            </svg>
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "var(--color-faint)",
                fontSize: "0.78rem",
                fontFamily: "var(--font-sans)",
              }}
            >
              No graph data
            </div>
          </>
        )}
      </div>

      {/* Variant summary line */}
      <div
        style={{
          fontSize: "0.72rem",
          color: "var(--color-muted)",
          marginTop: "0.4rem",
          fontFamily: "var(--font-sans)",
          lineHeight: 1.5,
        }}
      >
        {(variant.transactions ?? []).length} txns
        {totalIn > 0 && (
          <>
            {" · "}${totalIn.toLocaleString(undefined, { maximumFractionDigits: 0 })} in
          </>
        )}
        {totalOut > 0 && (
          <>
            {" → "}${totalOut.toLocaleString(undefined, { maximumFractionDigits: 0 })} extracted
          </>
        )}
        {variant.realism_score !== undefined && (
          <> · critic {variant.realism_score.toFixed(1)}</>
        )}
      </div>
    </div>
  );
}
