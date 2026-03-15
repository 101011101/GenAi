export const API = "http://localhost:8000";

// ── Shared types ──────────────────────────────────────────────────────────────

export interface RunConfig {
  fraud_description: string;
  variant_count?: number;
  demo?: boolean;
  instant?: boolean;
  max_parallel?: number;
  critic_floor?: number;
}

export interface StartRunResponse {
  run_id: string;
}

export interface AgentStatus {
  agent_id: string;         // "A1"–"A5"
  cell_id: string;
  variant_id: string;
  persona_name: string;
  status: "idle" | "running" | "retry" | "done" | "error";
  current_step: number;
  total_steps: number;
  step_name: string;
  attempt: number;
  max_attempts: number;
  tokens_used: number;
  cost_usd: number;
  last_score: number | null;
}

export interface TraceEvent {
  event_id: string;
  ts: string;
  agent_id: string;
  variant_id: string;
  step: number;
  step_name: string;
  attempt: number;
  status: "running" | "done" | "error";
  description: string;
  score: number | null;
  detail: Record<string, unknown> | null;
}

export interface VariantSummary {
  variant_id: string;
  persona_name: string;
  parameters_summary: string;
  critic_score: number;
  status: "approved" | "rejected" | "revised";
  strategy_description: string;
  completed_at: string;
  realism_score: number;
  distinctiveness_score: number;
  attempt_count: number;
  passed: boolean;
}

export interface CellStatus {
  cell_id: string;
  dimension_values: Record<string, string>;
  assigned_persona_id: string;
  assigned_persona_name: string;
  status: "empty" | "in_progress" | "completed" | "failed";
  attempt_count: number;
  critic_score: number | null;
  variant_id: string | null;
}

export interface RunStatus {
  run_id: string;
  start_time: number;
  current_phase: string;
  variants_completed: number;
  variants_total: number;
  active_agent_count: number;
  control_signal: "run" | "pause" | "stop";
  is_complete: boolean;
  total_cost_usd: number;
  cost_cap_usd: number;
  elapsed_s: number;
  health_status: "healthy" | "warning" | "critical";
  revisions_count: number;
  rejections_count: number;
  error_count: number;
  variant_count: number;
  event_log: string[];
  variant_log: VariantSummary[];
  coverage_cells: CellStatus[];
}

export interface MatrixData {
  dimensions: Array<{ name: string; values: unknown[] }>;
  cells: CellStatus[];
}

export interface Persona {
  persona_id?: string;
  name: string;
  risk_tolerance?: string;
  operational_scale?: string;
  resources?: string;
  evasion_targets?: string[];
  geographic_scope?: string;
}

export interface ScoredVariant {
  variant_id: string;
  persona_name?: string;
  variant_parameters?: Record<string, unknown>;
  realism_score?: number;
  distinctiveness_score?: number;
  strategy_description?: string;
  transactions?: Array<{
    txn_id?: string;
    transaction_id?: string;
    timestamp: string;
    amount: number;
    channel: string;
    is_fraud: boolean;
    fraud_role: string;
    sender_account_id?: string;
    receiver_account_id?: string;
  }>;
  accounts?: Array<{ account_id: string; role: string }>;
  passed?: boolean;
}

export interface ResultsData {
  variants: ScoredVariant[];
  stats: {
    variants_generated: number;
    mean_realism: number;
    mean_distinctiveness: number;
    mean_critic_score: number;
    coverage_pct: number;
    total_transactions: number;
  };
}

export interface DatasetRow {
  transaction_id: string;
  timestamp: string;
  amount: string;
  channel: string;
  is_fraud: string;
  fraud_role: string;
  variant_id: string;
  persona_name: string;
  hop_count?: string;
  critic_score?: string;
}

export interface ExportFile {
  filename: string;
  format: string;
  description: string;
  size_bytes: number | null;
  record_count: number | null;
  available: boolean;
}

// ── API calls ─────────────────────────────────────────────────────────────────

export async function startRun(config: RunConfig): Promise<StartRunResponse> {
  const res = await fetch(`${API}/api/runs`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(config),
  });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getRunStatus(runId: string): Promise<RunStatus> {
  const res = await fetch(`${API}/api/runs/${runId}/status`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getAgents(runId: string): Promise<{ agents: AgentStatus[] }> {
  const res = await fetch(`${API}/api/runs/${runId}/agents`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getTrace(runId: string, variantId?: string, agentId?: string): Promise<{ events: TraceEvent[] }> {
  const params = new URLSearchParams();
  if (variantId) params.set("variant_id", variantId);
  if (agentId) params.set("agent_id", agentId);
  const res = await fetch(`${API}/api/runs/${runId}/trace?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getMatrix(runId: string): Promise<MatrixData> {
  const res = await fetch(`${API}/api/runs/${runId}/matrix`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getPersonas(runId: string): Promise<{ personas: Persona[] }> {
  const res = await fetch(`${API}/api/runs/${runId}/personas`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getResults(runId: string): Promise<ResultsData> {
  const res = await fetch(`${API}/api/runs/${runId}/results`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getDataset(
  runId: string,
  page: number = 1,
  pageSize: number = 50,
  filters: { persona?: string; role?: string; is_fraud?: boolean; min_score?: number; variant_id?: string } = {}
): Promise<{ rows: DatasetRow[]; total: number; page: number; page_size: number }> {
  const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
  if (filters.persona) params.set("persona", filters.persona);
  if (filters.role) params.set("role", filters.role);
  if (filters.is_fraud !== undefined) params.set("is_fraud", String(filters.is_fraud));
  if (filters.min_score !== undefined) params.set("min_score", String(filters.min_score));
  if (filters.variant_id) params.set("variant_id", filters.variant_id);
  const res = await fetch(`${API}/api/runs/${runId}/dataset?${params}`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getExportManifest(runId: string): Promise<ExportFile[]> {
  const res = await fetch(`${API}/api/runs/${runId}/export`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function getRuns(): Promise<Array<{
  run_id: string;
  fraud_description: string;
  status: string;
  variants_total: number;
  variants_completed: number;
  is_complete: boolean;
  total_cost_usd: number;
  elapsed_s: number;
}>> {
  const res = await fetch(`${API}/api/runs`);
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function sendControl(runId: string, signal: "run" | "pause" | "stop"): Promise<void> {
  const res = await fetch(`${API}/api/runs/${runId}/control`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ signal }),
  });
  if (!res.ok) throw new Error(await res.text());
}

// ── Helpers ───────────────────────────────────────────────────────────────────

export const AGENT_COLORS: Record<string, { color: string; light: string; border: string }> = {
  A1: { color: "#0f4c8a", light: "#e8f0fa", border: "#bdd4ef" },
  A2: { color: "#059669", light: "#ecfdf5", border: "#a7f3d0" },
  A3: { color: "#7c3aed", light: "#f5f3ff", border: "#ddd6fe" },
  A4: { color: "#d97706", light: "#fffbeb", border: "#fde68a" },
  A5: { color: "#dc2626", light: "#fef2f2", border: "#fecaca" },
};

export function formatElapsed(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s}s`;
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
