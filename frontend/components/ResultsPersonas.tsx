"use client";

import { type Persona } from "@/lib/api";

interface Props {
  personas: Persona[];
}

function riskColors(risk: string | undefined): { bg: string; border: string; text: string } {
  const r = (risk ?? "").toLowerCase();
  if (r === "high") return { bg: "var(--color-red-light)", border: "var(--color-red-border)", text: "var(--color-red)" };
  if (r === "medium" || r === "mid") return { bg: "var(--color-yellow-light)", border: "var(--color-yellow-border)", text: "var(--color-yellow)" };
  return { bg: "var(--color-green-light)", border: "var(--color-green-border)", text: "var(--color-green)" };
}

function initials(name: string): string {
  return name
    .split(" ")
    .slice(0, 2)
    .map((w) => w[0]?.toUpperCase() ?? "")
    .join("");
}

function riskLabel(risk: string | undefined): string {
  const r = (risk ?? "").toLowerCase();
  if (r === "high") return "High risk";
  if (r === "medium" || r === "mid") return "Medium risk";
  return "Low risk";
}

function Tag({ label }: { label: string }) {
  return (
    <span
      style={{
        display: "inline-block",
        background: "var(--color-surface2)",
        color: "var(--color-muted)",
        border: "1px solid var(--color-border)",
        borderRadius: "4px",
        padding: "0.15rem 0.5rem",
        fontSize: "0.72rem",
        fontFamily: "var(--font-sans)",
        marginRight: "0.35rem",
        marginBottom: "0.35rem",
      }}
    >
      {label}
    </span>
  );
}

export default function ResultsPersonas({ personas }: Props) {
  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      <h2
        style={{
          fontSize: "1.1rem",
          fontWeight: 700,
          color: "var(--color-text)",
          marginBottom: "1.5rem",
          marginTop: 0,
        }}
      >
        Criminal personas — {personas.length} generated
      </h2>

      {personas.length === 0 ? (
        <div style={{ color: "var(--color-faint)", textAlign: "center", padding: "2rem", fontSize: "0.85rem" }}>
          No personas available.
        </div>
      ) : (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(3, 1fr)",
            gap: "1rem",
          }}
        >
          {personas.map((persona, idx) => {
            const { bg, border, text } = riskColors(persona.risk_tolerance);
            const ini = initials(persona.name);
            const risk = persona.risk_tolerance;

            const evasion = persona.evasion_targets ?? [];
            const geo = persona.geographic_scope;
            const desc = persona.resources ?? persona.operational_scale ?? "";

            return (
              <div
                key={persona.persona_id ?? idx}
                style={{
                  background: "var(--color-surface)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "10px",
                  padding: "1.25rem",
                }}
              >
                {/* Top row: avatar + name + risk badge */}
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: "0.75rem",
                    marginBottom: "0.85rem",
                  }}
                >
                  {/* Avatar */}
                  <div
                    style={{
                      width: "32px",
                      height: "32px",
                      borderRadius: "50%",
                      background: bg,
                      border: `1.5px solid ${border}`,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: "0.65rem",
                      fontWeight: 800,
                      color: text,
                      flexShrink: 0,
                      letterSpacing: "0.02em",
                    }}
                  >
                    {ini}
                  </div>

                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontWeight: 600,
                        fontSize: "0.875rem",
                        color: "var(--color-text)",
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {persona.name}
                    </div>
                  </div>

                  {/* Risk badge */}
                  <span
                    style={{
                      background: bg,
                      border: `1px solid ${border}`,
                      color: text,
                      borderRadius: "20px",
                      padding: "0.15rem 0.6rem",
                      fontSize: "0.68rem",
                      fontWeight: 600,
                      whiteSpace: "nowrap",
                      flexShrink: 0,
                    }}
                  >
                    {riskLabel(risk)}
                  </span>
                </div>

                {/* Trait tags */}
                <div style={{ marginBottom: "0.75rem" }}>
                  {evasion.map((ev) => (
                    <Tag key={ev} label={ev} />
                  ))}
                  {geo && <Tag label={geo} />}
                </div>

                {/* Description */}
                {desc && (
                  <div
                    style={{
                      fontSize: "0.8rem",
                      color: "var(--color-muted)",
                      lineHeight: 1.6,
                    }}
                  >
                    {desc}
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
