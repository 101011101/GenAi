# 08 — Execution Plan

**Purpose:** Segment the build into parallel-workable chunks that can be assigned to multiple agents simultaneously. Each chunk has a self-contained scope, a list of files to produce, and a prompt you can hand directly to an agent.

**Reference docs:**
- Architecture + folder structure: `05_architecture_draft.md`
- Agent responsibilities + data contracts: `02_approaches_draft.md`, `05_architecture_draft.md`
- MVP scope (what to build, what to skip): `04_mvp_and_scaling_draft.md`
- Console features + UX: `06_api_and_console_draft.md`, `07_user_flow_and_console.md`
- Agent hierarchy + output schemas: `03_product_requirements_draft.md`

---

## Dependency Map

```
Wave 1 (start here, no dependencies)
  └── Chunk 1: Foundation

Wave 2 (parallel, all depend on Chunk 1)
  ├── Chunk 2A: Orchestrator + Persona Generator
  ├── Chunk 2B: Fraud Constructor + Critic
  └── Chunk 2C: Pipeline Infrastructure

Wave 3 (parallel, depend on Wave 2)
  ├── Chunk 3A: Pipeline Runner      ← needs 2A + 2B + 2C
  └── Chunk 3B: Console UI           ← needs 2C (run_state), 1 (models)

Wave 4 (final integration)
  └── Chunk 4: App Wiring + Demo Mode ← needs 3A + 3B
```

Start Wave 2 agents as soon as Chunk 1 is done. Start Wave 3 agents as their specific dependencies complete. Wave 4 is the integration pass.

---

## Chunk 1 — Foundation

**What it is:** The shared data models, Claude API wrapper, schema validator, grounding data files, and all agent system prompt text files. Every other chunk depends on these. Build this first, alone.

**Files to produce:**

```
models/
  run_config.py          ← RunConfig: settings object from console
  persona.py             ← Persona: criminal profile
  variant.py             ← RawVariant, ValidatedVariant, ScoredVariant
  output_record.py       ← OutputRecord: one transaction row in the final dataset

utils/
  llm_client.py          ← Claude API async wrapper
  schema_validator.py    ← JSON schema validation (pure Python, no LLM)

prompts/
  orchestrator.txt
  persona_generator.txt
  fraud_constructor.txt
  critic.txt

data/
  mcc_stats.json                    ← amount distributions by merchant category
  payment_rail_constraints.json     ← processing windows, limits by rail
  account_balance_distributions.json
  regulatory_thresholds.json
```

**Agent prompt:**

> You are building the foundation layer for a synthetic fraud data generation system. Your job is to produce all shared data models, utilities, and reference files that every other part of the system depends on.
>
> Read `PRD/05_architecture_draft.md` for the full folder structure, the "Data Flow — Interface Contracts" section for the exact shapes of each model, and the "Concurrency Model" section for how the async client should behave. Read `PRD/06_api_and_console_draft.md` for the "API Usage" section (model selection, structured output, rate limit handling, error handling) and the "Grounding Data" section for what goes in the static JSON files.
>
> **models/run_config.py** — Pydantic model. Fields: `fraud_description: str`, `variant_count: int`, `fidelity_level: int` (2/3/4), `max_parallel: int`, `critic_floor: float`, `max_revisions: int`, `persona_count: int`, `risk_distribution: dict` (high/mid/low pct), `geographic_scope: list[str]`, `mule_context_depth: str`.
>
> **models/persona.py** — Pydantic model. Fields: `persona_id: str`, `name: str`, `risk_tolerance: str`, `operational_scale: str`, `geographic_scope: str`, `timeline_pressure: str`, `evasion_targets: list[str]`, `backstory: str`.
>
> **models/variant.py** — Three Pydantic models:
> - `RawVariant`: `variant_id`, `fraud_type`, `persona_id`, `strategy_description`, `variant_parameters` (dict), `transactions` (list of transaction dicts), `evasion_techniques` (list), `fraud_indicators_present` (list)
> - `ValidatedVariant`: same as RawVariant, schema-confirmed valid
> - `ScoredVariant`: adds `realism_score: float`, `distinctiveness_score: float`, `persona_consistency: bool`, `label_correctness: bool`, `passed: bool`, `feedback: str`
>
> **models/output_record.py** — Flat Pydantic model representing one transaction row. Fields: all transaction fields plus `is_fraud: bool`, `fraud_role: str`, `variant_id: str`, `persona_id: str`, `fraud_type: str`, `variant_parameters: dict`, `critic_scores: dict`.
>
> **utils/llm_client.py** — Async Claude API wrapper. Requirements: async `call(system_prompt, messages, model, response_format_schema)` method that returns parsed JSON; retry on JSON parse errors (max 3, with modified prompt); exponential backoff with jitter on 429/529; hard timeout (30s constructors, 15s critics); per-call exception catching that never crashes the caller. Use `anthropic` SDK with `AsyncAnthropic`. Support streaming via a separate `call_streaming()` method that yields text chunks and returns full JSON at end.
>
> **utils/schema_validator.py** — Pure Python, no LLM calls. `validate_raw_variant(data: dict) -> ValidatedVariant | ValidationError`. Uses Pydantic model validation. Fast and synchronous — runs before any critic call.
>
> **prompts/*.txt** — Write thoughtful system prompts for each agent based on the agent descriptions in `PRD/02_approaches_draft.md` (Layers 2–4) and `PRD/05_architecture_draft.md` (agents/ section). These are plain text files loaded at runtime. The fraud constructor prompt must include the five-step chain-of-thought structure (persona analysis → network planning → participant profiles → transaction generation → self-review). The critic prompt must specify the four scoring dimensions and their pass/fail criteria.
>
> **data/*.json** — Static grounding files bundled with the system. Populate with realistic values based on public sources described in `PRD/06_api_and_console_draft.md`. Use the Federal Reserve Payment Study for MCC stats, public rail documentation for payment constraints, Federal Reserve Survey of Consumer Finances for balance distributions, and FinCEN/FINTRAC public guidance for reporting thresholds. These do not need to be perfectly accurate — they need to be internally consistent and realistic enough that agents generate plausible transaction amounts.
>
> Output only Python files with complete, working implementations and the JSON data files. Do not produce placeholder stubs.

---

## Chunk 2A — Orchestrator + Persona Generator Agents

**Depends on:** Chunk 1 complete.

**Files to produce:**

```
agents/
  orchestrator.py
  persona_generator.py
```

**Agent prompt:**

> You are building two agents in a synthetic fraud data generation pipeline: the Orchestrator and the Persona Generator. Read `PRD/02_approaches_draft.md` Layer 2 (Orchestrator) for full behavior specification. Read `PRD/05_architecture_draft.md` the agents/ section for implementation pattern. Read `PRD/06_api_and_console_draft.md` for model selection (Orchestrator uses Claude Opus with extended thinking, Persona Generator uses Sonnet).
>
> **agents/orchestrator.py** — Class `OrchestratorAgent`. Single LLM call using Claude Opus with `thinking: { type: "enabled", budget_tokens: 5000 }`. Input: `RunConfig`. Output: `OrchestratorOutput` with fields: `variation_dimensions: list[dict]` (name + range for each dimension), `coverage_cells: list[dict]` (each cell is one sub-agent assignment specifying its position in the variation grid), `persona_count: int`. The orchestrator does NOT spawn agents itself — it returns a plan that `runner.py` executes. Load system prompt from `prompts/orchestrator.txt`. Pass grounding data from `data/` as context in the system prompt.
>
> **agents/persona_generator.py** — Class `PersonaGeneratorAgent`. One LLM call (or N parallel calls for large counts). Input: `fraud_description: str`, `persona_count: int`, `risk_distribution: dict`, `geographic_scope: list[str]`. Output: `list[Persona]`. Enforces the configured risk distribution in the prompt — if 30% high / 40% mid / 30% low is requested, the prompt explicitly states this requirement. Load system prompt from `prompts/persona_generator.txt`. Use `response_format` with JSON schema for reliable parsing. Reference the Viktor and James example personas in `PRD/02_approaches_draft.md` (Layer 2, Persona Seed Generation) when writing the prompt call.
>
> Both agents must be pure classes with a single async `run()` method. They import from `models/` and `utils/llm_client.py`. They do not import or call any other agent. They do not import anything from `pipeline/` or `console/`.

---

## Chunk 2B — Fraud Constructor + Critic Agents

**Depends on:** Chunk 1 complete.

**Files to produce:**

```
agents/
  fraud_constructor.py
  critic.py
```

**Agent prompt:**

> You are building two agents in a synthetic fraud data generation pipeline: the Fraud Network Constructor and the Critic. Read `PRD/02_approaches_draft.md` Layers 3 and 4 for the full behavioral spec. Read `PRD/05_architecture_draft.md` for the agents/ section (Fraud Network Constructor and Critic). Read `PRD/06_api_and_console_draft.md` for model selection (both use Sonnet), structured output, streaming, and the tool use section.
>
> **agents/fraud_constructor.py** — Class `FraudConstructorAgent`. Implements Level 3 simulation fidelity: a five-step reasoning chain where each step's output is context for the next. The five steps are: (1) persona analysis, (2) network planning, (3) participant profiles, (4) transaction generation, (5) self-review. Each step is a separate LLM call. Use the streaming client (`call_streaming()`) on the transaction generation step so the strategy description can be displayed in the console as it arrives. Input: `Persona`, `cell_assignment: dict` (the sub-agent's specific position in the coverage matrix). Output: `RawVariant`. Load system prompt from `prompts/fraud_constructor.txt`. Inject grounding data from `data/` into the prompt context. The agent must respect the variant parameters specified in its cell_assignment — it is not free to choose its own.
>
> **agents/critic.py** — Class `CriticAgent`. Independent LLM agent — no knowledge of the coverage matrix or other variants. Input: `ValidatedVariant`, `Persona`. Output: `ScoredVariant` with all four scoring dimensions (realism 1–10, persona consistency pass/fail, label correctness pass/fail, distinctiveness 1–10) plus `feedback: str` for revision if failed. Default thresholds from `PRD/02_approaches_draft.md`: realism ≥ 7, distinctiveness ≥ 6, persona consistency pass, label correctness pass. The feedback string must be specific enough that the constructor can act on it — not "this failed" but "the mule account behavior contradicts the stated risk tolerance because X". Load system prompt from `prompts/critic.txt`.
>
> Both agents must be pure classes with a single async `run()` method. They import from `models/` and `utils/`. They do not import or call any other agent. They do not import anything from `pipeline/` or `console/`.

---

## Chunk 2C — Pipeline Infrastructure

**Depends on:** Chunk 1 complete.

**Files to produce:**

```
pipeline/
  run_state.py
  coverage_matrix.py
  output_handler.py
```

**Agent prompt:**

> You are building the pipeline infrastructure layer for a synthetic fraud data generation system. This layer is used by both the pipeline runner and the console UI. Read `PRD/05_architecture_draft.md` for the full specification of each file in this chunk (Backend Pipeline section — `run_state.py`, `coverage_matrix.py`, `output_handler.py`).
>
> **pipeline/run_state.py** — `RunState` dataclass (or Pydantic model). Fields: `variants_completed: int`, `variants_total: int`, `active_agent_count: int`, `variant_log: list[VariantSummary]` (lightweight per-variant record for console display: variant_id, persona_name, parameters_summary, critic_score, status), `control_signal: str` (one of "run" / "pause" / "stop"), `errors: list[str]`, `is_complete: bool`, `current_phase: str`. Must be thread-safe — use a `threading.Lock` for writes since the console polls from the main thread while the pipeline writes from a background thread. Provide `update_variant(...)` and `set_control(...)` methods.
>
> **pipeline/coverage_matrix.py** — `CoverageMatrix` class. `build(variation_dimensions: list[dict]) -> list[dict]` creates the assignment grid. Tracks cell states: `unassigned / in_progress / completed / rejected`. `assign_cell(cell_id, agent_id)` marks in_progress. `complete_cell(cell_id, variant_id)` marks complete. `reject_cell(cell_id)` returns it to unassigned for reassignment. `check_saturation() -> float` returns fraction of cells covered. `get_underrepresented_cells() -> list[dict]` returns cells with zero or one variant for second-pass targeting. `cluster_detection()` checks if agents are gravitating to the same region.
>
> **pipeline/output_handler.py** — `OutputHandler` class. `write_run_output(approved_variants: list[ScoredVariant], run_config: RunConfig, run_state: RunState)` writes all output files to `output/runs/run_YYYYMMDD_HHMMSS/`. Produces: `config.json`, `personas.json`, `variants.json`, `dataset.csv` (one row per transaction, flat tabular), `dataset.json` (full nested structure), `run_summary.json` (stats). For large runs (1000+ variants), provide an `append_variant(variant)` method for incremental writes to CSV so memory stays flat. Import from `models/` only.

---

## Chunk 3A — Pipeline Runner

**Depends on:** Chunks 2A, 2B, 2C all complete.

**Files to produce:**

```
pipeline/
  runner.py
```

**Agent prompt:**

> You are building the async pipeline runner — the component that coordinates all agents, manages the revision loop, tracks state, and drives a full run from RunConfig to output files. Read `PRD/05_architecture_draft.md` — the entire "Pipeline Flow" section (Level 3 Pipeline and Revision Loop Detail), the "How Agents Communicate" section, and the "Concurrency Model" section. Read `PRD/06_api_and_console_draft.md` for cost controls and rate limit handling. Read `PRD/04_mvp_and_scaling_draft.md` for MVP scope (Level 3 only for MVP).
>
> **pipeline/runner.py** — `PipelineRunner` class with a single public async method `run(config: RunConfig, run_state: RunState)`. The runner is the only component that calls agents. Agents never call each other.
>
> **Execution sequence:**
> 1. Call `OrchestratorAgent.run(config)` → get `OrchestratorOutput` (dimensions + cell assignments)
> 2. Build `CoverageMatrix` from dimensions
> 3. Call `PersonaGeneratorAgent.run(...)` → get `List[Persona]`
> 4. Write `run_state.current_phase = "Generating variants"`
> 5. Use `asyncio.gather()` to run up to `config.max_parallel` concurrent tasks
> 6. Each task: `FraudConstructorAgent.run(persona, cell)` → `SchemaValidator.validate()` → `CriticAgent.run(variant, persona)`
> 7. On schema failure: discard immediately, reassign cell, log error. Do NOT retry — schema failures indicate broken output structure.
> 8. On critic failure (below threshold): re-call `FraudConstructorAgent` with feedback prepended to prompt. Max `config.max_revisions` attempts. After max, discard variant, reassign cell.
> 9. On critic pass: append to `approved_variants`, call `run_state.update_variant(...)`, call `coverage_matrix.complete_cell(...)`
> 10. After each parallel batch: check `run_state.control_signal` — pause/resume/stop as specified in `PRD/05_architecture_draft.md`
> 11. After full batch: call `coverage_matrix.check_saturation()` — if below threshold and `config.auto_second_pass`, run second pass targeting underrepresented cells
> 12. Call `OutputHandler.write_run_output(approved_variants, config, run_state)`
>
> **Cost cap:** Track cumulative token usage via return values from `llm_client`. If it exceeds `$20` equivalent, stop the run and surface a warning via `run_state.errors`. Default threshold is configurable.
>
> **Error isolation:** Each async task must catch and log its own exceptions. One failed variant must never crash the runner. Use `asyncio.gather(..., return_exceptions=True)`.
>
> The runner runs in a background thread. It does not import from `console/`. It is started from `app.py` using `threading.Thread(target=asyncio.run, args=(runner.run(config, run_state),))`.

---

## Chunk 3B — Console UI

**Depends on:** Chunk 1 (models), Chunk 2C (run_state). Can be built in parallel with Chunk 3A — the console only reads from `run_state`, it does not call agents.

**Files to produce:**

```
console/
  input_panel.py
  orchestrator_controls.py
  monitoring_panel.py
  data_display/
    coverage_matrix_view.py
    network_graph_view.py
    stats_panel.py
    dataset_browser.py
    export_panel.py

.streamlit/
  config.toml
```

**Agent prompt:**

> You are building the Streamlit console UI for a synthetic fraud data generation system. The console does NOT contain any agent logic — it renders input forms, reads from `run_state` for live monitoring, and renders output data after a run. Read `PRD/06_api_and_console_draft.md` for the full component spec of all four panels. Read `PRD/07_user_flow_and_console.md` for the analyst workflow narrative, demo mode spec, and all edge case behaviors. Read `PRD/03_product_requirements_draft.md` for the Console & Controls section. Read `PRD/04_mvp_and_scaling_draft.md` for the MVP console scope.
>
> **Tech stack:** Streamlit. Dark theme via `.streamlit/config.toml`. NetworkX + Matplotlib for network graphs. All imports must be guarded — no import errors if an optional library is not installed.
>
> **console/input_panel.py** — `render_input_panel() -> RunConfig | None`. Returns a `RunConfig` when Run is clicked, `None` otherwise. Components: fraud description text area (8 rows, placeholder, char count), fraud type dropdown pre-fills, variant count slider (10–100, default 25), estimated cost + time indicator (computed from variant count × fidelity), Run button (disabled if description < 20 chars). Edge cases from `PRD/06_api_and_console_draft.md` Input Panel section.
>
> **console/orchestrator_controls.py** — `render_orchestrator_controls() -> dict`. Returns a dict of control overrides. Collapsed `st.expander` by default. All controls from the Orchestrator Controls table in `PRD/06_api_and_console_draft.md`. Fidelity Level 4 shows "Coming soon" badge for MVP. Risk distribution three-way slider must validate that values sum to 100.
>
> **console/monitoring_panel.py** — `render_monitoring_panel(run_state: RunState)`. Called every ~1 second via `st.rerun()` while run is active. Components: full-width progress bar, pipeline phase indicator, persona cards feed (left side), variant feed (scrollable, newest first), live coverage matrix grid, agent status strip (N dots), revision activity counter, collapsible log. All edge cases from `PRD/06_api_and_console_draft.md` Live Monitoring section.
>
> **console/data_display/coverage_matrix_view.py** — `render_coverage_matrix(matrix_data: dict, phase: str)`. Renders as `st.columns` grid. Cell states: unassigned (gray), in_progress (blue pulse — use `st.spinner` or color), completed (green), rejected (red). Hover tooltip via Streamlit or Matplotlib. Downloadable as PNG.
>
> **console/data_display/network_graph_view.py** — `render_network_graphs(variants: list[ScoredVariant])`. Picks 3–4 structurally distinct variants (highest-scoring from different coverage matrix regions). Renders side-by-side using NetworkX + Matplotlib embedded in Streamlit. Node colors: originator=blue, mule=orange, extractor=red. Edge thickness = amount, direction = money flow. Fraud path edges red, cover activity gray. Falls back gracefully if NetworkX not installed.
>
> **console/data_display/stats_panel.py** — `render_stats(run_state: RunState, variants: list)`. Large `st.metric` cards: variants generated, mean critic score, coverage saturation %, persona diversity count, variants rejected. Readable from across the room — large font.
>
> **console/data_display/dataset_browser.py** — `render_dataset_browser(records: list[OutputRecord])`. Full-width `st.dataframe`. Default columns from `PRD/07_user_flow_and_console.md` dataset browser section. Filters: persona multi-select, critic score range slider, fraud role, is_fraud. "Show variant metadata" toggle adds extra columns.
>
> **console/data_display/export_panel.py** — `render_export_panel(run_folder: str)`. Format tabs: CSV / JSON. `st.download_button` for each. File size estimate. "Include metadata" toggle. "Export run summary" button. "Send to pipeline" button — always disabled, tooltip explains it's for API integration (vision CTA per `PRD/07_user_flow_and_console.md`).
>
> **`.streamlit/config.toml`** — Dark theme. Primary color to match the adversarial/security aesthetic.

---

## Chunk 4 — App Wiring + Demo Mode

**Depends on:** Chunks 3A and 3B complete.

**Files to produce:**

```
app.py
```

**Agent prompt:**

> You are writing the Streamlit entry point that wires together the console UI and the backend pipeline. Read `PRD/05_architecture_draft.md` for the Concurrency Model (background thread + asyncio + Streamlit polling pattern). Read `PRD/06_api_and_console_draft.md` for Demo Mode configuration. Read `PRD/07_user_flow_and_console.md` for the 4-phase user flow and Demo Mode section.
>
> **app.py** — Main Streamlit app. Manages the four phases as session state: `input` → `running` → `results`.
>
> **Phase management:**
> - `input` phase: render `input_panel` + `orchestrator_controls` (collapsed). On Run click: build `RunConfig`, create `RunState`, start pipeline in background thread (`threading.Thread(target=asyncio.run, args=(runner.run(config, run_state),))`). Transition to `running` phase.
> - `running` phase: render `monitoring_panel(run_state)`. Poll via `time.sleep(1)` + `st.rerun()`. On completion (`run_state.is_complete`): transition to `results` phase.
> - `results` phase: render data display module (stats, network graphs, coverage matrix, dataset browser, export panel) from the completed run folder.
>
> **Demo mode:** Activated by `?demo=true` URL param or a "Run Demo" button on the input panel. Pre-fills: description = "layered 3-hop mule network, burst withdrawal, domestic only", variant_count = 12, fidelity = 3, model override to Haiku, max_parallel = 5. After run completes, show banner: "Try the real thing →" with CTA to reset to input phase. Target total time: ~60 seconds.
>
> **Pause / Resume / Stop:** Wire the Pause/Resume/Stop buttons in monitoring_panel to `run_state.set_control(signal)`. The runner checks this between batches.
>
> Keep `app.py` thin — no business logic, no agent imports. It only imports from `console/`, `pipeline/run_state.py`, `pipeline/runner.py`, and `models/`.

---

## Interface Contracts Between Chunks

These are the exact data handoffs across chunk boundaries. Build to these shapes and integration will be clean.

**Chunk 1 → all:** Pydantic models are the shared language. If a model shape needs to change, update `models/` and all consumers.

**Chunk 2C → Chunk 3A:**
```python
run_state: RunState          # runner writes, console reads
coverage_matrix: CoverageMatrix
output_handler: OutputHandler
```

**Chunk 2A, 2B → Chunk 3A:**
```python
OrchestratorAgent.run(config: RunConfig) -> OrchestratorOutput
PersonaGeneratorAgent.run(...) -> list[Persona]
FraudConstructorAgent.run(persona: Persona, cell: dict) -> RawVariant
CriticAgent.run(variant: ValidatedVariant, persona: Persona) -> ScoredVariant
```

**Chunk 3A → Chunk 3B:**
```python
run_state: RunState          # shared object, runner writes, console polls
run_folder: str              # path to output/runs/run_YYYYMMDD_HHMMSS/
```

**Chunk 3B → Chunk 4:**
```python
render_input_panel() -> RunConfig | None
render_orchestrator_controls() -> dict
render_monitoring_panel(run_state: RunState)
render_*()                   # all data_display functions
```

---

## What to Build First if Time Is Short

If only one agent is available, follow the build order from `PRD/05_architecture_draft.md` (Build Order section) sequentially. The MVP can be demonstrated with Chunks 1, 2A, 2B (fraud constructor only), 2C, 3A, and a simplified version of 3B. Level 4 agents (criminal, mule, bank system, cover story) are explicitly out of MVP scope.

If running two agents in parallel, assign one agent to Chunks 1 + 2C (foundation + infrastructure) and one to Chunk 2B (fraud constructor + critic) once Chunk 1 is done. The constructor and critic are the most complex and most likely to need iteration.

See `PRD/04_mvp_and_scaling_draft.md` "What Cuts First Under Time Pressure" for what to drop without breaking the demo.
