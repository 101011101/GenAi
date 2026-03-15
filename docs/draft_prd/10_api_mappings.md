# 10 — Console API Mappings

**Purpose:** Maps every wireframe UI element to its backend data source. Flags fields that exist, fields that need to be added, and gaps where new tracking is required.

**Wireframe sources:** `ide_full_console_wireframes.html`, `ide_monitor_trace.html`
**Backend sources:** `RunState`, `RunConfig`, `ScoredVariant`, `OutputRecord`, `Persona`, `LLMClient`

---

## Legend

| Symbol | Meaning |
|---|---|
| ✅ | Data exists today — direct field mapping |
| ⚠️ | Data partially exists — needs reshaping or aggregation |
| ❌ | Gap — data is not stored anywhere, must be added |

---

## Screen 01 — Input

All input fields map directly to `RunConfig`.

| UI Element | Field | Source | Status |
|---|---|---|---|
| Fraud description textarea | `fraud_description` | `RunConfig` | ✅ |
| Variant count slider | `variant_count` | `RunConfig` | ✅ |
| Fidelity selector (L2/L3/L4) | `fidelity_level` | `RunConfig` | ✅ |
| Max parallel agents | `max_parallel` | `RunConfig` | ✅ |
| Critic score floor | `critic_floor` | `RunConfig` | ✅ |
| Max revisions | `max_revisions` | `RunConfig` | ✅ |
| Persona count | `persona_count` | `RunConfig` | ✅ |
| Risk High % | `risk_distribution["high"]` | `RunConfig` | ✅ |
| Risk Mid % | `risk_distribution["mid"]` | `RunConfig` | ✅ |
| Risk Low % | `risk_distribution["low"]` | `RunConfig` | ✅ |
| Geographic scope | `geographic_scope` | `RunConfig` | ✅ |
| Auto second-pass toggle | `auto_second_pass` | `RunConfig` | ✅ |
| Cost cap | `cost_cap_usd` | `RunConfig` | ✅ |
| Live estimate bar (cost) | Computed: `variant_count × avg_cost_per_variant` | Derived | ⚠️ hardcode ~$0.18/variant for estimate |
| Live estimate bar (time) | Computed: `variant_count / max_parallel × avg_seconds` | Derived | ⚠️ hardcode ~12s/variant for estimate |

---

## Screen 02 — Live Monitor

### Global Header

| UI Element | Field | Source | Status |
|---|---|---|---|
| Run ID | `run_id` | `RunState` | ❌ add `run_id: str` to RunState |
| Health badge (Healthy/Warning/Critical) | Computed from failure rate + cost burn | Derived | ❌ add `health_status` property to RunState |
| Progress bar % | `variants_completed / variants_total × 100` | `RunState` | ✅ |
| Variants X/Y | `variants_completed`, `variants_total` | `RunState` | ✅ |
| Elapsed time | `time.time() - run_start_time` | Derived | ❌ add `start_time: float` to RunState |
| Cost so far | `total_cost_usd` | `RunState` | ✅ |
| Cost cap | `cost_cap_usd` | `RunConfig` | ✅ |
| Pause button | `control_signal = "pause"` | `RunState` | ✅ |
| Stop button | `control_signal = "stop"` | `RunState` | ✅ |

### Persona Avatar Cards (left panel)

| UI Element | Field | Source | Status |
|---|---|---|---|
| Persona name | `persona.name` | `Persona` | ✅ |
| Persona initials | First chars of name | Derived | ✅ (compute client-side) |
| Risk badge (High/Mid/Low) | `persona.risk_tolerance` | `Persona` | ✅ |
| Specialization subtitle | `persona.backstory[:80]` | `Persona` | ⚠️ use backstory truncated |
| Cells assigned count | Count of coverage cells where `persona_slot == persona_index` | `CoverageCell` | ❌ add `cells_assigned: int` to Persona or compute from cell list |

### Coverage Matrix Grid (center panel)

| UI Element | Field | Source | Status |
|---|---|---|---|
| Cell status color | Derived from cell lifecycle | `RunState` | ❌ add `coverage_cells: list[CellStatus]` to RunState |
| Cell persona badge | `cell.assigned_persona_name` | `CellStatus` | ❌ new field |
| Cell attempt number | `cell.attempt_count` | `CellStatus` | ❌ new field |
| Cell critic score | `cell.critic_score` (if completed) | `CellStatus` | ❌ new field |
| Coverage saturation % | `cells_completed / cells_total × 100` | Derived | ❌ needs `CellStatus` list |
| Failed cell pulse animation | `cell.status == "failed"` | `CellStatus` | ❌ |

**New object needed — `CellStatus`:**
```python
@dataclass
class CellStatus:
    cell_id: str
    dimension_values: dict        # e.g. {"hop_count": 3, "timing": "burst"}
    assigned_persona_id: str
    assigned_persona_name: str
    status: str                   # "empty"|"assigned"|"in_progress"|"completed"|"failed"|"reassigned"
    attempt_count: int
    critic_score: float | None    # populated on completion
    variant_id: str | None        # populated on completion
```

Add `coverage_cells: list[CellStatus]` to `RunState`.

### Agent Activity Log (right panel)

| UI Element | Field | Source | Status |
|---|---|---|---|
| Timestamped event entries | `event_log` | `RunState` | ✅ exists, format: `"[HH:MM:SS] message"` |
| Agent status dots (5 agents) | `active_agent_count` | `RunState` | ⚠️ count exists, per-agent status does not |

---

## Screen 02-B through 02-E — Trace Panel (per `ide_monitor_trace.html`)

The trace panel shows per-variant internals when a variant card is clicked. This data is NOT currently stored anywhere — it lives only in-memory during construction and is discarded.

### Orchestrator Sub-Tab

| UI Element | Field | Source | Status |
|---|---|---|---|
| Dimension names + values | `orchestrator_output.variation_dimensions` | `OrchestratorOutput` | ✅ — store in RunState |
| Coverage cell grid | `coverage_cells` | `RunState.coverage_cells` | ❌ (see above) |

**Add to RunState:**
```python
orchestrator_output: OrchestratorOutput | None = None
```

### Persona Sub-Tab

| UI Element | Field | Source | Status |
|---|---|---|---|
| Persona name, risk, backstory | All `Persona` fields | `Persona` | ✅ |
| Resources description | `persona.resources` | `Persona` | ✅ |
| Evasion targets | `persona.evasion_targets` | `Persona` | ✅ |

**Add to RunState:**
```python
personas: list[Persona] = field(default_factory=list)
```

### Constructor Sub-Tab — Heist Storyboard

Each of the 5 step outputs needs to be stored per variant. Currently they are generated and immediately fed to the next step — not saved.

| UI Element | Step | LLM Output Field | Source | Status |
|---|---|---|---|---|
| Step 1 Motive card | Persona Analysis | `specific_goal`, `deadline_or_pressure`, `fears_and_known_controls` | `FraudConstructorAgent` Step 1 | ❌ not stored |
| Step 2 Blueprint card | Network Planning | `hop_count`, `topology`, `timing_interval_hrs`, `rationale` | Step 2 | ❌ not stored |
| Step 3 Crew card | Participant Profiles | `accounts` list (names, roles, recruitment stories) | Step 3 | ❌ not stored |
| Step 4 Execution card | Transaction Generation | `transactions` list (amounts, timestamps, channels) | Step 4 | ❌ not stored |
| Step 5 Cleanup card | Self-review / repair | Repair log from Python constraint fixer | Step 5 | ❌ not stored |
| Token count badge per card | `LLMClient.total_output_tokens` per step | `LLMClient` | ❌ need per-step token counts |
| Latency badge per card | `time.time()` delta per step | Derived | ❌ need per-step timing |

**New object needed — `VariantTrace`:**
```python
@dataclass
class StepTrace:
    step_name: str          # "persona_analysis"|"network_planning"|"profiles"|"transactions"|"self_review"
    input_tokens: int
    output_tokens: int
    latency_s: float
    raw_output: dict        # the full JSON output from the LLM for that step

@dataclass
class VariantTrace:
    variant_id: str
    cell_id: str
    persona_id: str
    attempt_number: int
    steps: list[StepTrace]  # 4-5 entries, one per constructor step
    persona_consistency_ok: bool
    consistency_notes: str
```

Add to RunState:
```python
variant_traces: dict[str, list[VariantTrace]] = field(default_factory=dict)
# keyed by variant_id, value is list of attempts
```

### Labeling Sub-Tab

| UI Element | Field | Source | Status |
|---|---|---|---|
| Fraud account ID chips | `variant.fraud_account_ids` | `RawVariant` | ⚠️ available during construction, removed from final output — preserve it |
| Before-labeling transactions | `transactions` before labeling step | `FraudConstructorAgent` internal | ❌ not stored (labeling is in-place) |
| After-labeling transactions | `variant.transactions` with `fraud_role` + `is_fraud` | `RawVariant` | ✅ |
| BFS traversal summary | Graph walk result | `label_transactions.py` | ❌ not stored |
| Mini network graph nodes/edges | `variant.accounts` + `variant.transactions` | `RawVariant` | ✅ accounts + transactions available |

### Validator Sub-Tab

| UI Element | Field | Source | Status |
|---|---|---|---|
| 8-rule checklist (pass/fail per rule) | Validation result per rule | `variant_validator.py` | ❌ not stored — only pass/fail overall |

**Add to `VariantTrace`:**
```python
validation_results: list[dict]  # [{"rule": "amount_floor", "passed": True, "detail": "..."}, ...]
```

### Critic Sub-Tab

| UI Element | Field | Source | Status |
|---|---|---|---|
| Verdict (PASS/FAIL) | `scored_variant.passed` | `ScoredVariant` | ✅ |
| Realism score | `scored_variant.realism_score` | `ScoredVariant` | ✅ |
| Distinctiveness score | `scored_variant.distinctiveness_score` | `ScoredVariant` | ✅ |
| Persona consistency | `scored_variant.persona_consistency` | `ScoredVariant` | ✅ |
| Critic feedback text | `scored_variant.feedback` | `ScoredVariant` | ✅ |

---

## Screen 03 — Results: Summary

### Stat Cards

| UI Element | Field | Source | Status |
|---|---|---|---|
| Total variants approved | `len([v for v in variant_log if v.status == "approved"])` | `RunState.variant_log` | ✅ |
| Mean realism score | `mean([v.critic_score for v in variant_log])` | `RunState.variant_log` | ⚠️ `critic_score` is a single float — need to store realism + distinctiveness separately in `VariantSummary` |
| Mean distinctiveness | Same as above | `RunState.variant_log` | ⚠️ |
| Coverage saturation % | `cells_completed / cells_total` | `RunState.coverage_cells` | ❌ needs CellStatus |
| Total cost | `total_cost_usd` | `RunState` | ✅ |
| Run duration | `time.time() - start_time` | Derived | ❌ needs `start_time` in RunState |

**Update `VariantSummary`** to split critic score:
```python
realism_score: float       # was: critic_score (composite)
distinctiveness_score: float
passed: bool
```

### Persona Wanted Cards

| UI Element | Field | Source | Status |
|---|---|---|---|
| Color bar (risk level) | `persona.risk_tolerance` | `Persona` | ✅ |
| Persona name | `persona.name` | `Persona` | ✅ |
| Persona ID | `persona.persona_id` | `Persona` | ✅ |
| Specialization subtitle | `persona.backstory[:100]` | `Persona` | ⚠️ |
| Evasion target tags | `persona.evasion_targets` | `Persona` | ✅ |
| Geographic scope stat | `persona.geographic_scope` | `Persona` | ✅ |
| Cells assigned count | Computed from `coverage_cells` | `RunState.coverage_cells` | ❌ needs CellStatus |
| Hop range stat | Not in Persona model | — | ❌ add `hop_range: str` to Persona or derive from assigned cells |

### Risk Distribution Chart

| UI Element | Field | Source | Status |
|---|---|---|---|
| Configured H/M/L % | `risk_distribution` | `RunConfig` | ✅ |
| Actual H/M/L % | Count personas by risk_tolerance | `Persona` list | ✅ compute client-side |

---

## Screen 04 — Results: Quality Gate

### Quality Battlefield Scatter

| UI Element | Field | Source | Status |
|---|---|---|---|
| Each dot position (realism, distinctiveness) | `scored_variant.realism_score`, `scored_variant.distinctiveness_score` | `ScoredVariant` | ✅ — but need to store all approved ScoredVariants, not just VariantSummary |
| Dot color (pass/fail) | `scored_variant.passed` | `ScoredVariant` | ✅ |
| Revision trails (ghost dots) | Per-attempt scores for multi-attempt variants | `VariantTrace` | ❌ needs VariantTrace with per-attempt critic scores |
| Pass zone threshold lines | `critic_floor` | `RunConfig` | ✅ |
| Hover tooltip (variant ID, persona, attempts) | All available if VariantTrace exists | Various | ❌ needs VariantTrace |

**Add to RunState:**
```python
scored_variants: list[ScoredVariant] = field(default_factory=list)  # final approved variants
```

### Pass/Fail/Revised Donut

| UI Element | Field | Source | Status |
|---|---|---|---|
| Passed first attempt | `len([v for v in variant_log if v.status == "approved" and attempt == 1])` | ❌ attempt count not in VariantSummary | ❌ |
| Passed after revision | `len([v for v in variant_log if v.status == "approved" and attempt > 1])` | ❌ | ❌ |
| Permanently failed | `rejections_count` | `RunState` | ✅ |

**Update `VariantSummary`:** add `attempt_count: int`

### Quality Issues Table

| UI Element | Field | Source | Status |
|---|---|---|---|
| Variant ID | `variant_id` | `VariantTrace` | ✅ |
| Gate (Schema/Critic) | Type of failure | `VariantTrace.validation_results` / `ScoredVariant.feedback` | ❌ needs VariantTrace |
| Issue detail | Failure message | Same | ❌ |
| Severity | Error vs Warning | Derived from resolution | ❌ |
| Resolution | Auto-corrected / revised / discarded | `VariantTrace` | ❌ |

---

## Screen 05 — Results: Operations

### Pipeline Waterfall (flame chart)

This is the largest gap in the current data model. The waterfall requires per-phase timing per variant — **none of this is currently tracked**.

| UI Element | Field | Source | Status |
|---|---|---|---|
| Each variant row | `variant_id` | `VariantTrace` | ✅ if VariantTrace exists |
| Phase segment start time | `StepTrace.start_time` | `StepTrace` | ❌ add `start_time: float` to StepTrace |
| Phase segment width (duration) | `StepTrace.latency_s` | `StepTrace` | ❌ add `latency_s` to StepTrace |
| Parallelism (overlapping rows) | Global wall-clock times per step | `StepTrace.start_time` relative to `RunState.start_time` | ❌ |
| Failed variant marker | `scored_variant.passed == False` on final attempt | `VariantTrace` | ❌ |
| Revised variant gap + second pass | Multi-attempt VariantTrace entries | `VariantTrace` | ❌ |

### Cost Accumulation Sparkline

| UI Element | Field | Source | Status |
|---|---|---|---|
| Cost over time line | Cost snapshots at regular intervals | `RunState` | ❌ add `cost_timeline: list[tuple[float, float]]` (timestamp, cumulative_cost) to RunState |
| Cap threshold | `cost_cap_usd` | `RunConfig` | ✅ |

**Add to RunState:**
```python
cost_timeline: list[tuple[float, float]] = field(default_factory=list)
# append (time.time(), total_cost_usd) whenever cost changes
```

### Error Log Table

| UI Element | Field | Source | Status |
|---|---|---|---|
| Timestamp | Timestamp from event_log | `RunState.event_log` | ⚠️ event_log is unstructured strings |
| Stage | Which pipeline stage errored | ❌ | ❌ needs structured error log |
| Variant ID | Which variant | ❌ | ❌ |
| Severity | Error/Warning/Info | ❌ | ❌ |
| Message | Error text | `RunState.errors` | ⚠️ exists but unstructured |
| Resolution | Retry/discard/auto-correct | ❌ | ❌ |

**Add to RunState:**
```python
@dataclass
class ErrorRecord:
    timestamp: str
    stage: str        # "orchestrator"|"constructor"|"validator"|"critic"
    variant_id: str | None
    severity: str     # "error"|"warning"|"info"
    message: str
    resolution: str   # "retried"|"discarded"|"auto-corrected"|"reassigned"

structured_errors: list[ErrorRecord] = field(default_factory=list)
```

### Summary Metric Cards

| UI Element | Field | Source | Status |
|---|---|---|---|
| Total variants | `variants_completed` | `RunState` | ✅ |
| Mean realism | `mean(realism_score for all ScoredVariants)` | `RunState.scored_variants` | ❌ needs scored_variants stored |
| Mean distinctiveness | Same | Same | ❌ |
| Coverage % | `cells_completed / cells_total` | `RunState.coverage_cells` | ❌ |
| Total cost | `total_cost_usd` | `RunState` | ✅ |
| Duration | `time.time() - start_time` | Derived | ❌ needs `start_time` |

---

## Screen 06 — Results: Variants

### 2D Coverage Heatmap

| UI Element | Field | Source | Status |
|---|---|---|---|
| Row/column axes | Dimension names from `variation_dimensions` | `OrchestratorOutput` | ❌ needs to be stored in RunState |
| Cell color + status | `CellStatus.status` | `RunState.coverage_cells` | ❌ |
| Cell persona + score | `CellStatus.assigned_persona_name`, `CellStatus.critic_score` | `RunState.coverage_cells` | ❌ |

### Heist Storyboard (5 cards)

| UI Element | Field | Source | Status |
|---|---|---|---|
| Step 1 Motive narrative | `persona_analysis.specific_goal` + `deadline_or_pressure` | `VariantTrace.steps[0].raw_output` | ❌ |
| Step 2 Blueprint narrative | `network_plan.rationale` + hop/topology summary | `VariantTrace.steps[1].raw_output` | ❌ |
| Step 3 Crew narrative | `accounts[].owner_description` + `recruitment_story` | `VariantTrace.steps[2].raw_output` | ❌ |
| Step 4 Execution narrative | First 2-3 transactions formatted as prose | `VariantTrace.steps[3].raw_output` | ❌ |
| Step 5 Cleanup narrative | Repair log from constraint fixer | `VariantTrace.steps[4].raw_output` | ❌ |
| Token count badge | `StepTrace.input_tokens + output_tokens` | `StepTrace` | ❌ |
| Latency badge | `StepTrace.latency_s` | `StepTrace` | ❌ |

### Money Trail Graph

| UI Element | Field | Source | Status |
|---|---|---|---|
| Nodes (accounts) | `variant.accounts` (account_id, role, account_type) | `ScoredVariant.accounts` | ⚠️ accounts exist in RawVariant but may not be in ScoredVariant — verify |
| Node shape by role | `account.role` (source/mule/destination/cover) | `accounts` | ✅ if accounts stored |
| Edges (transactions) | `variant.transactions` (sender, receiver, amount, timestamp) | `ScoredVariant.transactions` | ✅ |
| Edge thickness | `transaction.amount` | `Transaction` | ✅ |
| Edge label | `transaction.amount` + `transaction.timestamp` | `Transaction` | ✅ |

### Attempt History Table

| UI Element | Field | Source | Status |
|---|---|---|---|
| Attempt number | `VariantTrace.attempt_number` | `VariantTrace` | ❌ |
| Realism per attempt | Per-attempt `ScoredVariant.realism_score` | `VariantTrace` | ❌ |
| Distinctiveness per attempt | Per-attempt `ScoredVariant.distinctiveness_score` | `VariantTrace` | ❌ |
| Passed? | Per-attempt `ScoredVariant.passed` | `VariantTrace` | ❌ |
| Critic feedback per attempt | Per-attempt `ScoredVariant.feedback` | `VariantTrace` | ❌ |

**All attempt history requires `VariantTrace` with per-attempt critic scores appended to each `StepTrace` entry.**

---

## Screen 07 — Results: Dataset

| UI Element | Field | Source | Status |
|---|---|---|---|
| transaction_id | `OutputRecord.transaction_id` | `OutputRecord` | ✅ |
| timestamp | `OutputRecord.timestamp` | `OutputRecord` | ✅ |
| amount | `OutputRecord.amount` | `OutputRecord` | ✅ |
| channel | `OutputRecord.channel` | `OutputRecord` | ✅ |
| is_fraud | `OutputRecord.is_fraud` | `OutputRecord` | ✅ |
| fraud_role | `OutputRecord.fraud_role` | `OutputRecord` | ✅ |
| variant_id | `OutputRecord.variant_id` | `OutputRecord` | ✅ |
| persona_name | `OutputRecord.persona_name` | `OutputRecord` | ✅ |
| Filter by fraud_role | Client-side filter on `fraud_role` | Client | ✅ |
| Filter by variant | Client-side filter on `variant_id` | Client | ✅ |
| Filter by persona | Client-side filter on `persona_name` | Client | ✅ |

Screen 07 is **fully mappable today**. No gaps.

---

## Screen 08 — Results: Export

| UI Element | Field | Source | Status |
|---|---|---|---|
| CSV download | `dataset.csv` file from `OutputHandler` | File on disk | ✅ |
| JSON download | `dataset.json` file from `OutputHandler` | File on disk | ✅ |
| Graph adjacency download | `graph_adjacency.json` from `OutputHandler` | File on disk | ✅ |
| Export manifest (file sizes, record counts) | Computed from output files | `os.path.getsize()` | ✅ |
| run_summary.json preview | `run_summary.json` from `OutputHandler` | File on disk | ✅ |

Screen 08 is **fully mappable today**. No gaps.

---

## Gap Summary — New Data Structures Required

| New Object | Added To | Unlocks |
|---|---|---|
| `run_id: str` | `RunState` | Header run ID |
| `start_time: float` | `RunState` | Elapsed time, waterfall chart |
| `health_status: str` | `RunState` (computed property) | Global header health badge |
| `CellStatus` (dataclass) | `RunState.coverage_cells: list[CellStatus]` | Coverage grid, saturation %, persona cell count |
| `orchestrator_output: OrchestratorOutput` | `RunState` | Dimension axes for heatmap |
| `personas: list[Persona]` | `RunState` | Persona wanted cards, trace panel |
| `scored_variants: list[ScoredVariant]` | `RunState` | Quality Battlefield, mean scores |
| `StepTrace` (dataclass) | New | Per-step token count + latency |
| `VariantTrace` (dataclass) | `RunState.variant_traces: dict[str, list[VariantTrace]]` | Heist Storyboard, Attempt History, Quality issues |
| `cost_timeline: list[tuple[float, float]]` | `RunState` | Cost sparkline |
| `ErrorRecord` (dataclass) | `RunState.structured_errors: list[ErrorRecord]` | Operations error log |
| `realism_score` + `distinctiveness_score` split | `VariantSummary` (replaces `critic_score`) | Mean scores, donut chart |
| `attempt_count: int` | `VariantSummary` | Donut (passed first vs revised) |

---

## Callback Hooks Required in `FraudConstructorAgent`

To populate `VariantTrace`, the constructor needs to fire callbacks after each step:

```python
# In FraudConstructorAgent.run():

# After Step 1
on_step("persona_analysis", raw_output=step1_json, tokens=..., latency_s=...)

# After Step 2
on_step("network_planning", raw_output=step2_json, tokens=..., latency_s=...)

# After Step 3
on_step("participant_profiles", raw_output=step3_json, tokens=..., latency_s=...)

# After Step 4
on_step("transaction_generation", raw_output=step4_json, tokens=..., latency_s=...)

# After Step 5 (repair/label)
on_step("self_review", raw_output=repair_log_dict, tokens=0, latency_s=...)
```

The `on_step` callback already exists — it needs to be extended to capture `raw_output`, `tokens`, and `latency_s`.

---

## Priority Order for Implementation

| Priority | Item | Screens unlocked |
|---|---|---|
| P0 | `CellStatus` + `RunState.coverage_cells` | Monitor coverage grid |
| P0 | `run_id`, `start_time` in RunState | All headers |
| P1 | `VariantSummary` split scores + attempt_count | Summary, Quality donut |
| P1 | `RunState.scored_variants` | Quality Battlefield |
| P1 | `RunState.personas` + `RunState.orchestrator_output` | Summary persona cards, heatmap axes |
| P2 | `StepTrace` + `VariantTrace` + `RunState.variant_traces` | Heist Storyboard, Attempt History |
| P2 | `cost_timeline` | Operations sparkline |
| P2 | `ErrorRecord` + `RunState.structured_errors` | Operations error log |
| P3 | `health_status` computed property | Header badge |
| P3 | Full Pipeline Waterfall timing | Operations waterfall |
