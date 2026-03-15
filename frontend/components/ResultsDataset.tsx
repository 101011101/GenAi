"use client";

import { useEffect, useState, useCallback } from "react";
import { getDataset, type DatasetRow, type ScoredVariant } from "@/lib/api";

interface Props {
  runId: string;
  variants: ScoredVariant[];
}

interface Filters {
  persona: string;
  role: string;
  is_fraud: string; // "all" | "true" | "false"
  variant_id: string;
}

const FRAUD_ROLE_COLORS: Record<string, string> = {
  placement: "var(--color-purple)",
  extraction: "var(--color-red)",
  cover_activity: "var(--color-faint)",
};

function getRoleColor(role: string): string {
  if (role in FRAUD_ROLE_COLORS) return FRAUD_ROLE_COLORS[role];
  if (role.startsWith("hop_")) return "var(--color-accent)";
  return "var(--color-muted)";
}

interface ChipDropdownProps {
  label: string;
  value: string;
  options: string[];
  onChange: (v: string) => void;
  activeColor?: string;
}

function ChipDropdown({ label, value, options, onChange, activeColor }: ChipDropdownProps) {
  const [open, setOpen] = useState(false);
  const isActive = value !== "all" && value !== "";
  const displayLabel = isActive ? `${label}: ${value}` : `${label}: All ▼`;

  return (
    <div style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((o) => !o)}
        style={{
          background: isActive ? (activeColor ?? "var(--color-accent-light)") : "var(--color-surface2)",
          color: isActive ? (activeColor ? "var(--color-bg)" : "var(--color-accent)") : "var(--color-muted)",
          border: `1px solid ${isActive ? "var(--color-accent-border)" : "var(--color-border)"}`,
          borderRadius: "6px",
          padding: "0.3rem 0.75rem",
          fontSize: "0.78rem",
          fontWeight: 500,
          cursor: "pointer",
          fontFamily: "var(--font-sans)",
          whiteSpace: "nowrap",
        }}
      >
        {displayLabel}
      </button>
      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            background: "var(--color-bg)",
            border: "1px solid var(--color-border)",
            borderRadius: "8px",
            boxShadow: "0 8px 24px rgba(0,0,0,0.10)",
            zIndex: 50,
            minWidth: "160px",
            overflow: "hidden",
          }}
        >
          {["all", ...options].map((opt) => (
            <button
              key={opt}
              onClick={() => {
                onChange(opt);
                setOpen(false);
              }}
              style={{
                display: "block",
                width: "100%",
                textAlign: "left",
                background: opt === value ? "var(--color-accent-light)" : "transparent",
                color: opt === value ? "var(--color-accent)" : "var(--color-text)",
                border: "none",
                padding: "0.5rem 1rem",
                fontSize: "0.8rem",
                cursor: "pointer",
                fontFamily: "var(--font-sans)",
                fontWeight: opt === value ? 600 : 400,
              }}
            >
              {opt === "all" ? "All" : opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function ResultsDataset({ runId, variants }: Props) {
  const [rows, setRows] = useState<DatasetRow[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [filters, setFilters] = useState<Filters>({
    persona: "all",
    role: "all",
    is_fraud: "all",
    variant_id: "all",
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const personaOptions = Array.from(
    new Set(variants.map((v) => v.persona_name).filter(Boolean) as string[])
  );
  const variantOptions = variants.map((v) => v.variant_id);
  const roleOptions = [
    "placement",
    "hop_1_of_3",
    "hop_2_of_3",
    "hop_N_of_M",
    "extraction",
    "cover_activity",
  ];

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      setError(null);
      const apiFilters: {
        persona?: string;
        role?: string;
        is_fraud?: boolean;
        variant_id?: string;
      } = {};
      if (filters.persona !== "all") apiFilters.persona = filters.persona;
      if (filters.role !== "all") apiFilters.role = filters.role;
      if (filters.is_fraud === "true") apiFilters.is_fraud = true;
      if (filters.is_fraud === "false") apiFilters.is_fraud = false;
      if (filters.variant_id !== "all") apiFilters.variant_id = filters.variant_id;

      const res = await getDataset(runId, page, pageSize, apiFilters);
      setRows(res.rows);
      setTotal(res.total);
    } catch (e) {
      console.error("Dataset fetch failed:", e);
      setError("Failed to load dataset.");
    } finally {
      setLoading(false);
    }
  }, [runId, page, pageSize, filters]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  function setFilter(key: keyof Filters, val: string) {
    setFilters((f) => ({ ...f, [key]: val }));
    setPage(1);
  }

  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      {/* Filter bar */}
      <div
        style={{
          display: "flex",
          gap: "0.6rem",
          alignItems: "center",
          borderBottom: "1px solid var(--color-border)",
          padding: "0.75rem 0",
          marginBottom: "0",
          flexWrap: "wrap",
        }}
      >
        <ChipDropdown
          label="Persona"
          value={filters.persona}
          options={personaOptions}
          onChange={(v) => setFilter("persona", v)}
        />
        <ChipDropdown
          label="Role"
          value={filters.role}
          options={roleOptions}
          onChange={(v) => setFilter("role", v)}
        />
        <ChipDropdown
          label="is_fraud"
          value={filters.is_fraud}
          options={["true", "false"]}
          onChange={(v) => setFilter("is_fraud", v)}
        />
        <ChipDropdown
          label="Variant"
          value={filters.variant_id}
          options={variantOptions}
          onChange={(v) => setFilter("variant_id", v)}
        />

        <div style={{ marginLeft: "auto", fontSize: "0.75rem", color: "var(--color-muted)", fontFamily: "var(--font-mono)" }}>
          Showing {rows.length} of {total.toLocaleString()} rows
          {loading && " (loading…)"}
        </div>
      </div>

      {/* Error */}
      {error && (
        <p style={{ margin: "0.75rem 0 0", fontSize: "0.85rem", color: "var(--color-red)" }}>{error}</p>
      )}

      {/* Table */}
      <div style={{ overflowX: "auto" }}>
        <table
          style={{
            width: "100%",
            borderCollapse: "collapse",
            fontSize: "0.78rem",
          }}
        >
          <thead>
            <tr
              style={{
                borderBottom: "2px solid var(--color-border)",
                background: "var(--color-surface)",
              }}
            >
              {[
                "transaction_id",
                "timestamp",
                "amount",
                "channel",
                "is_fraud",
                "fraud_role",
                "variant_id",
                "persona_name",
              ].map((col) => (
                <th
                  key={col}
                  style={{
                    textAlign: "left",
                    padding: "0.6rem 0.75rem",
                    fontWeight: 600,
                    color: "var(--color-muted)",
                    fontSize: "0.72rem",
                    textTransform: "uppercase",
                    letterSpacing: "0.06em",
                    whiteSpace: "nowrap",
                  }}
                >
                  {col.replace(/_/g, "_")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const isOdd = idx % 2 === 0;
              return (
                <tr
                  key={`${row.transaction_id}-${idx}`}
                  style={{
                    background: isOdd ? "var(--color-bg)" : "var(--color-surface)",
                    borderBottom: "1px solid var(--color-surface2)",
                    cursor: "default",
                  }}
                  onMouseEnter={(e) => {
                    (e.currentTarget as HTMLTableRowElement).style.background = "var(--color-surface2)";
                  }}
                  onMouseLeave={(e) => {
                    (e.currentTarget as HTMLTableRowElement).style.background = isOdd ? "var(--color-bg)" : "var(--color-surface)";
                  }}
                >
                  {/* transaction_id */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: "var(--color-muted)",
                      maxWidth: "120px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                    title={row.transaction_id}
                  >
                    {row.transaction_id.slice(-8)}
                  </td>

                  {/* timestamp */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.7rem",
                      color: "var(--color-faint)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {row.timestamp?.slice(0, 19).replace("T", " ")}
                  </td>

                  {/* amount */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontWeight: 700,
                      fontSize: "0.78rem",
                      color: "var(--color-text)",
                      whiteSpace: "nowrap",
                    }}
                  >
                    ${parseFloat(row.amount).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </td>

                  {/* channel */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.78rem",
                      color: "var(--color-text)",
                    }}
                  >
                    {row.channel}
                  </td>

                  {/* is_fraud */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontWeight: row.is_fraud === "True" || row.is_fraud === "true" ? 700 : 400,
                      fontSize: "0.78rem",
                      color:
                        row.is_fraud === "True" || row.is_fraud === "true"
                          ? "var(--color-red)"
                          : "var(--color-faint)",
                    }}
                  >
                    {row.is_fraud}
                  </td>

                  {/* fraud_role */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: getRoleColor(row.fraud_role ?? ""),
                      fontWeight: 600,
                    }}
                  >
                    {row.fraud_role}
                  </td>

                  {/* variant_id */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontFamily: "var(--font-mono)",
                      fontSize: "0.72rem",
                      color: "var(--color-accent)",
                    }}
                  >
                    {row.variant_id}
                  </td>

                  {/* persona_name */}
                  <td
                    style={{
                      padding: "0.5rem 0.75rem",
                      fontSize: "0.78rem",
                      color: "var(--color-muted)",
                      maxWidth: "140px",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {row.persona_name}
                  </td>
                </tr>
              );
            })}

            {rows.length === 0 && !loading && (
              <tr>
                <td
                  colSpan={8}
                  style={{
                    padding: "2rem",
                    textAlign: "center",
                    color: "var(--color-faint)",
                    fontSize: "0.85rem",
                  }}
                >
                  No rows match the current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Ellipsis row */}
      {total > rows.length + (page - 1) * pageSize && (
        <div
          style={{
            textAlign: "center",
            color: "var(--color-faint)",
            fontSize: "0.8rem",
            padding: "0.75rem",
            fontFamily: "var(--font-mono)",
          }}
        >
          · · · {(total - rows.length - (page - 1) * pageSize).toLocaleString()} more rows · · ·
        </div>
      )}

      {/* Pagination */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          gap: "0.75rem",
          padding: "1rem 0",
          fontSize: "0.82rem",
          color: "var(--color-text)",
        }}
      >
        <button
          onClick={() => setPage((p) => Math.max(1, p - 1))}
          disabled={page === 1}
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "6px",
            padding: "0.35rem 0.85rem",
            cursor: page === 1 ? "not-allowed" : "pointer",
            color: page === 1 ? "var(--color-faint)" : "var(--color-text)",
            fontSize: "0.8rem",
            fontFamily: "var(--font-sans)",
          }}
        >
          Prev
        </button>
        <span style={{ fontFamily: "var(--font-mono)", fontSize: "0.78rem", color: "var(--color-muted)" }}>
          Page {page} of {totalPages}
        </span>
        <button
          onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
          disabled={page === totalPages}
          style={{
            background: "var(--color-surface)",
            border: "1px solid var(--color-border)",
            borderRadius: "6px",
            padding: "0.35rem 0.85rem",
            cursor: page === totalPages ? "not-allowed" : "pointer",
            color: page === totalPages ? "var(--color-faint)" : "var(--color-text)",
            fontSize: "0.8rem",
            fontFamily: "var(--font-sans)",
          }}
        >
          Next
        </button>
      </div>

      {/* Role legend */}
      <div
        style={{
          borderTop: "1px solid var(--color-border)",
          paddingTop: "0.75rem",
          display: "flex",
          gap: "1.5rem",
          fontSize: "0.72rem",
          flexWrap: "wrap",
        }}
      >
        {[
          { role: "placement", label: "placement — first account receives funds", color: "var(--color-purple)" },
          { role: "hop_N_of_M", label: "hop_N_of_M — layering", color: "var(--color-accent)" },
          { role: "extraction", label: "extraction — final cashout", color: "var(--color-red)" },
          { role: "cover_activity", label: "cover_activity — is_fraud = False", color: "var(--color-faint)" },
        ].map(({ role, label, color }) => (
          <div key={role} style={{ display: "flex", alignItems: "center", gap: "0.35rem" }}>
            <div
              style={{
                width: "10px",
                height: "10px",
                borderRadius: "2px",
                background: color,
                flexShrink: 0,
              }}
            />
            <span style={{ color: "var(--color-muted)" }}>{label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
