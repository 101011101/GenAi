# 05 — Architecture [DRAFT]

---

## System Overview

The system has three major components. The backend pipeline is where all the real work happens. The console and data display module are thin layers on top.

```
┌─────────────────────────────────────────────────────┐
│                     CONSOLE                         │
│  ┌─────────────────┐   ┌──────────────────────────┐ │
│  │  Input Panel    │   │ Orchestrator Controls    │ │
│  └────────┬────────┘   └──────────┬───────────────┘ │
│           └──────────┬────────────┘                 │
│                      ↓                              │
│           ┌──────────────────────┐                  │
│           │  Live Monitoring     │                  │
│           └──────────────────────┘                  │
└──────────────────────┬──────────────────────────────┘
                       ↓ RunConfig
┌──────────────────────────────────────────────────────┐
│                    BACKEND PIPELINE                  │
│                                                      │
│  runner.py                                           │
│    ├── orchestrator       →  variation_dimensions    │
│    ├── cell_generator     →  coverage cells          │
│    ├── persona_generator  →  List[Persona]           │
│    ├── fraud_constructor  →  RawVariant (per agent)  │
│    ├── schema_validator   →  ValidatedVariant        │
│    ├── critic             →  ScoredVariant           │
│    └── output_handler     →  6 files on disk         │
│                                                      │
│  run_state.py  ← pipeline writes, console reads      │
└──────────────────────┬───────────────────────────────┘
                       ↓ completed run folder
┌──────────────────────────────────────────────────────┐
│               DATA DISPLAY MODULE                    │
│  Coverage Matrix │ Network Graphs │ Dataset Browser  │
│  Stats Panel     │ Export Panel                      │
└──────────────────────────────────────────────────────┘
```

---

## Folder Structure

```
project/
│
├── app.py                              ← Streamlit entry point
├── .streamlit/
│   └── config.toml                     ← dark theme + colors
│
├── console/
│   ├── input_panel.py                  ← fraud description + run settings
│   ├── orchestrator_controls.py        ← strategic controls over pipeline
│   ├── monitoring_panel.py             ← live run updates
│   └── data_display/
│       ├── coverage_matrix_view.py
│       ├── network_graph_view.py
│       ├── stats_panel.py
│       ├── dataset_browser.py
│       └── export_panel.py
│
├── agents/                             ← agent logic
│   ├── orchestrator.py
│   ├── persona_generator.py
│   ├── fraud_constructor.py
│   ├── critic.py
│   └── level4/                         ← next level, build after MVP
│       ├── criminal_agent.py
│       ├── mule_agent.py
│       ├── bank_agent.py
│       └── cover_story_agent.py
│
├── models/
│   ├── run_config.py                   ← settings object from console
│   ├── persona.py                      ← criminal persona
│   ├── variant.py                      ← one fraud variant + transactions
│   └── output_record.py                ← final labeled dataset row
│
├── pipeline/
│   ├── runner.py                       ← async engine
│   ├── coverage_matrix.py              ← variant space tracker
│   ├── cell_generator.py               ← deterministic coverage cell generator (Cartesian product of dimension example_values)
│   ├── variant_validator.py            ← pure Python 8-rule constraint checker; violations → retry
│   ├── run_state.py                    ← shared state: pipeline writes, console reads
│   └── output_handler.py              ← formatters + file writer
│
├── prompts/                            ← system prompts
│   ├── orchestrator.txt
│   ├── persona_generator.txt
│   ├── fraud_constructor.txt
│   └── critic.txt
│
├── utils/
│   ├── llm_client.py                   ← Claude API wrapper
│   ├── schema_validator.py             ← validates agent JSON output
│   └── label_transactions.py           ← deterministic BFS graph labeler; stamps fraud_role + is_fraud
│
└── output/
    └── runs/                           ← runtime generated, gitignored
        └── run_YYYYMMDD_HHMMSS/
            ├── config.json
            ├── personas.json
            ├── variants.json
            ├── dataset.csv
            ├── dataset.json
            └── run_summary.json
```

---

## System 1 — Console

The console is a Streamlit web app. It runs locally at `localhost:8501`. It does not contain any agent logic — it only triggers the pipeline and displays results.

### input_panel.py
- Fraud description text area
- Variant count slider (10–50 for demo)
- Submit → builds `RunConfig` object → hands to `runner.py`

### orchestrator_controls.py
Strategic controls the analyst can set before a run and adjust mid-run:

| Control | Type | What It Does |
|---|---|---|
| Fidelity level | Selector (2 / 3 / 4) | Which agents are active, how deep simulation goes |
| Variant count | Slider | Target number of variants |
| Max parallel agents | Slider | Cost / speed tradeoff |
| Critic score floor | Slider (5–9) | Minimum quality to enter dataset |
| Max revision iterations | Number input | How many retries before variant is discarded |
| Persona count | Number input | How many distinct criminal profiles to generate |
| Risk distribution | Multi-slider | % high / mid / low risk personas |
| Geographic scope | Multiselect | Domestic / international / specific regions |
| Mule context depth | Selector | Shallow / medium / deep backstory |
| Auto second-pass | Toggle | Re-run on underrepresented coverage cells |
| Pause / Resume / Stop | Buttons | Sends control signal to pipeline mid-run |

### monitoring_panel.py
Polls `run_state` every ~1 second while pipeline is running:
- Progress bar (variants completed / target)
- Live variant feed — each variant card appears as it completes, showing persona name, parameters, and critic score
- Active agent count
- Revision loop activity (how many retries are happening)
- Any errors or rejected variants

---

## System 2 — Backend Pipeline

The pipeline is pure Python. No Streamlit imports anywhere in this system. It runs in a background thread so the console UI stays responsive.

### runner.py
The coordinator. Sequence of operations:
1. Receive `RunConfig` from console
2. Call `OrchestratorAgent` → get `variation_dimensions` + `suggested_persona_count`
3. Call `cell_generator.generate_cells()` → coverage cells (deterministic Cartesian product of dimension `example_values`)
4. Initialize `CoverageMatrix` with dimensions + cells
5. Call `PersonaGeneratorAgent` → get `List[Persona]`
6. Spawn variant tasks using `asyncio` up to `max_parallel`
7. Each task: `fraud_constructor` → `variant_validator` → `critic`
8. On critic fail: re-queue with feedback (up to `max_revisions` iterations)
9. Optional second pass if `coverage_saturation < 60%` and `auto_second_pass=True`
10. On completion: call `output_handler` to write all 6 files

### coverage_matrix.py
`CoverageMatrix` class:
- Initialized with variation dimensions extracted by orchestrator
- Tracks which cells are assigned, in progress, completed
- Detects clustering (agents gravitating to same cells)
- Returns underrepresented cells for second pass targeting

### run_state.py
`RunState` class — the bridge between pipeline and console:
```
variants_completed    int
variants_total        int
active_agent_count    int
variant_log           List[VariantSummary]   ← one entry per completed variant
control_signal        str                    ← "run" | "pause" | "stop"
errors                List[str]
is_complete           bool
current_phase         str                    ← "idle" | "Orchestrating" | "Generating personas" | "Generating variants" | "Compiling dataset" | "complete"
total_cost_usd        float                  ← accumulated API cost across all agent calls
revisions_count       int                    ← variants that passed on a retry attempt
rejections_count      int                    ← variants that failed all attempts and were discarded
event_log             List[str]              ← real-time timestamped agent activity (capped at 200 entries)
```
Pipeline writes to it. Console reads from it every second.
Pause/stop: console sets `control_signal`, runner checks it between agent batches.

### output_handler.py
Takes approved `List[ScoredVariant]` and writes 6 files per run:
- `config.json` — the `RunConfig` settings for this run
- `personas.json` — personas used in this run
- `variants.json` — all approved variants (metadata only, no transaction list)
- `dataset.csv` — one row per transaction, flat tabular
- `dataset.json` — full nested structure with variant + persona metadata + transactions
- `run_summary.json` — stats (variant count, mean critic score, coverage %, timing, cost, revision/rejection counts)

### agents/

Each agent is a Python class with a `run()` method. It takes a context object, builds a prompt, calls the Claude API, parses the response, and returns a typed Pydantic object. No agent imports or calls another agent directly — the runner always mediates.

**Orchestrator**
One LLM call with extended thinking. Decomposes the fraud description into `variation_dimensions` (list of dimension objects with `example_values`) and returns `suggested_persona_count`. Does NOT coordinate anything downstream — the runner handles all of that.

**Persona Generator**
Single LLM call (or N parallel calls for large counts). Receives the fraud description and persona settings (count, risk distribution, geographic scope). Returns `List[Persona]`. Enforces the configured risk distribution — if the analyst set 30% high / 40% mid / 30% low, the prompt enforces that spread explicitly.

**Fraud Network Constructor (Level 3)**
The core generation agent. Runs as a four-step LLM reasoning chain followed by two deterministic Python steps:
1. **Persona analysis** [LLM] — what does this criminal actually need? What are their constraints and fears?
2. **Network planning** [LLM] — decide hop count, topology (chain vs fan-out), timing, amount logic, cover activity
3. **Participant profiles** [LLM] — for each account in the network, who are they, how were they recruited, what do they think they're doing
4. **Transaction generation** [LLM] — full transaction sequence grounded in real-world constraints. Transactions do NOT include `is_fraud` or `fraud_role` fields. The LLM emits a `fraud_account_ids` list — the internal mule/layering account IDs only.
5. **Constraint repair + validation** [Python] — `_repair_constraint_violations()` auto-fixes common LLM errors (channel substitution, timestamp re-spacing, ACH floor enforcement, Zelle cap enforcement). Then `check_variant_constraints()` in `pipeline/variant_validator.py` checks 8 hard rules deterministically; any violations → raises exception → triggers retry. No LLM call.
6. **Deterministic labeling** [Python/BFS] — `label_transactions()` in `utils/label_transactions.py` receives the transaction list and `fraud_account_ids` set. Performs a BFS traversal of the transfer graph and stamps `fraud_role` and `is_fraud` on every transaction: placement (external→fraud), hop_N_of_M (fraud→fraud, BFS depth N of M), extraction (fraud→external), cover_activity (external→external).

Returns `RawVariant` JSON with all transactions fully labeled.

**Critic**
Independent LLM agent. Receives `ValidatedVariant` + original `Persona` + `persona_consistency` boolean (from the deterministic check in step 5 above). Has no knowledge of the coverage matrix or other variants. Scores two dimensions via LLM:

| Dimension | Type | Question |
|---|---|---|
| Realism | Score 1–10 | Would a fraud analyst believe this happened? |
| Variant distinctiveness | Score 1–10 | Is this structurally different from the batch average? |

Persona consistency is checked deterministically by `FraudConstructorAgent._check_persona_consistency()` and passed in as a boolean. A variant fails immediately if `persona_consistency=False`, regardless of LLM scores.

On fail: returns specific feedback string → passed back to constructor for revision.

**Level 4 Agents** [TENTATIVE — next level]

*Criminal Mastermind* — knows the full operation plan, generates compartmentalized instructions per mule (each mule only gets what they need to know), receives bank flags and decides how to respond (reroute / wait / proceed).

*Mule Agents (one per hop)* — limited context only. Personal profile includes financial situation, why they took the job, and suspicion level. Suspicion level changes behavior: fully compliant executes immediately; uneasy introduces delays and asks questions; suspicious may forward less than instructed.

*Cover Story Agent* — sub-agent of the criminal mastermind. When a mule asks a question, the runner calls this agent to generate a plausible response from the criminal's perspective. Response feeds back into the mule's conversation history.

*Bank System Agent* — evaluates each transaction against a rule set (velocity limits, reporting thresholds, new-payee flags). Returns approve / flag / reject. When it flags, the criminal mastermind receives the signal and adapts — producing organic evasion behavior.

### How Agents Communicate

Agents do not call each other. The runner is always the intermediary. "Agent communication" is the runner passing one agent's output as input to the next.

For Level 3, this is simple sequential handoff:
```
runner calls fraud_constructor(persona, assignment) → RawVariant
runner calls critic(raw_variant, persona)           → ScoredVariant
```

For Level 4, multi-turn conversation between criminal and mule is handled via a **growing message list** — the standard Claude multi-turn pattern. Each turn is a new API call with the full conversation history as context:
```
conversation = [criminal_instructions]
mule_response = claude.call(system=mule_prompt, messages=conversation)
conversation.append(mule_response)

if mule_response.has_question:
    cover_story = cover_story_agent.run(mule_response.question)
    conversation.append(cover_story)
    mule_final = claude.call(system=mule_prompt, messages=conversation)
```

The mule agent doesn't know it's talking to a cover story agent — it just sees the next message in its conversation history. The runner orchestrates the entire exchange invisibly.

### prompts/
One `.txt` file per agent containing the system prompt. Stored as plain text files so they can be edited without touching Python code. Loaded at runtime by `llm_client.py`. During the hackathon, prompts will be iterated constantly — keeping them in text files means no Python changes needed to adjust agent behavior.

---

## System 3 — Data Display Module

Renders after a run completes from the output folder. Independent of the live monitoring panel.

### coverage_matrix_view.py
Visual grid of the variant space. Cells colored:
- Empty — not yet assigned
- In progress — agent running
- Filled — variant completed and approved
- Rejected — variant failed critic, cell reassigned

### network_graph_view.py
Renders 3–4 sample mule networks as actual node graphs side by side using NetworkX + Matplotlib. Each account is a node, each transaction is a directed edge. Colors distinguish fraud hops from cover activity. Shows structural diversity visually — a 3-hop chain next to a fan-out tree makes the diversity argument without any explanation.

### stats_panel.py
`st.metric` cards:
- Variants generated
- Mean critic score
- Coverage matrix saturation %
- Persona diversity (how many distinct profiles)
- Variants rejected / revised

### dataset_browser.py
Filterable `st.dataframe` of the full dataset. Filter by:
- Persona name / risk profile
- Critic score range
- Fraud role (placement / hop / extraction)
- Variant parameters (hop count, timing, topology)

### export_panel.py
- Format selector: CSV / JSON / Graph adjacency list
- `st.download_button` for each format
- Dataset summary stats shown before download

---

## Pipeline Flow

### Level 3 Pipeline

```
RunConfig (from console)
    ↓
OrchestratorAgent LLM call (extended thinking) → variation_dimensions + suggested_persona_count
    ↓
cell_generator.generate_cells() [Python] → coverage cells (Cartesian product)
CoverageMatrix initialized with dimensions + cells
PersonaGeneratorAgent LLM call → List[Persona]
    ↓
[PARALLEL — up to max_parallel]
  For each (Persona, cell_assignment):
    FraudConstructor
      Step 1: persona analysis            [LLM]
      Step 2: network planning            [LLM]
      Step 3: participant profiles        [LLM]
      Step 4: transaction generation      [LLM] → transactions (unlabeled) + fraud_account_ids list
      Step 5: constraint repair + validation [Python] → _repair_constraint_violations() auto-fixes channel/timestamp/ACH/Zelle issues; check_variant_constraints() checks 8 hard rules → violations trigger retry
      Step 6: label_transactions()        [Python/BFS] → stamps fraud_role + is_fraud on all txns
      → RawVariant JSON (fully labeled)
    ↓
    SchemaValidator (pure Python)
      → fail: discard, reassign cell
      → pass: ValidatedVariant
    ↓
    Critic (LLM) — scores Realism (1–10) + Distinctiveness (1–10)
      persona_consistency bool passed in from constructor (deterministic)
      → fail (score below floor OR persona_consistency=False): feedback → FraudConstructor again (max max_revisions+1 attempts)
      → pass: ScoredVariant → approved_variants[]
    ↓
    run_state.update()  ← console reads for live display
[END PARALLEL BATCH]
    ↓
CoverageMatrix.check_saturation()
  → below threshold: second pass targeting underrepresented cells
  → sufficient: proceed
    ↓
OutputHandler(approved_variants) → CSV / JSON / files
```

### Level 4 Pipeline [TENTATIVE — next level]

Same outer structure, FraudConstructor replaced by multi-agent simulation:

```
[PARALLEL — per variant]
  CriminalMasermindAgent(Persona, cell_assignment)
    → operation plan
    → compartmentalized instructions per mule
  ↓
  [SEQUENTIAL — per hop]
    MuleAgent(instructions, personal_context)
      → execution decision based on suspicion level
      → if has_question → CoverStoryAgent → response → back to MuleAgent
      → generates transaction
      ↓
      BankSystemAgent(transaction)
        → approve  → MuleAgent proceeds
        → flag     → CriminalMastermind adapts → reroutes next hop
        → reject   → transaction fails, criminal adjusts
  ↓
  Full sequence assembled → RawVariant
  → SchemaValidator → Critic → revision loop (same as L3)
```

### Revision Loop Detail

Schema failures (malformed JSON) are hard failures — discarded immediately, cell reassigned. Not worth retrying, as the output structure is broken.

Critic failures are soft failures — the feedback string is prepended to the constructor's next prompt: *"Your previous attempt was rejected because: [reason]. Generate a new variant addressing this."* Max 3 iterations. After 3 failures the cell is discarded and reassigned to a fresh agent.

Pause/stop: runner checks `run_state.control_signal` between each parallel batch. If "pause" — waits. If "stop" — calls output_handler with whatever is approved so far and exits cleanly.

---

## Storage & File System

### Automatic Directory Creation

Every run creates its own timestamped folder automatically — no manual setup needed:

```python
folder = f"output/runs/run_{timestamp}"
os.makedirs(folder, exist_ok=True)  # creates full path automatically
```

### File Tree After Multiple Runs

```
output/
    runs/
        run_20260314_143022/    ← 6 files, ~2 MB
        run_20260314_161045/    ← 6 files, ~2 MB
        run_20260314_184230/    ← 6 files, ~2 MB
```

Always exactly 6 files per run. Folder is gitignored.

### Size Estimates

| Variants | Disk | RAM | API Cost | Time (10 parallel) |
|---|---|---|---|---|
| 50 (live demo) | ~1 MB | ~200 MB | ~$2 | ~7 min |
| 100 (standard) | ~2 MB | ~250 MB | ~$5 | ~15 min |
| 1,000 (production) | ~20 MB | ~800 MB | ~$40 | ~1.5 hr |

For 100 variants, output_handler writes all files at the end. For 1,000+ variants, output_handler should write **incrementally** — appending to CSV as each variant completes — so memory stays flat regardless of variant count.

---

## Data Flow — Interface Contracts

```
console → RunConfig → runner.py

runner.py → (fraud_description, settings) → persona_generator → List[Persona]

runner.py → (Persona, cell_assignment) → fraud_constructor → RawVariant JSON
  [internally: LLM emits transactions (unlabeled) + fraud_account_ids list;
   label_transactions() stamps fraud_role/is_fraud via BFS graph traversal before RawVariant is returned]

RawVariant → schema_validator → ValidatedVariant | ValidationError

ValidatedVariant → critic → ScoredVariant {
    scores: { realism, distinctiveness },
    passed: bool,
    feedback: str   ← returned to constructor on failure
}

ScoredVariant (fail) → fraud_constructor (revision loop, max 2-3x)
ScoredVariant (pass) → run_state.variant_log + approved_variants[]

approved_variants[] → output_handler → files on disk
```

---

## Concurrency Model

```
Main thread:     Streamlit UI (polls run_state, re-renders)
                        ↓ st.rerun() every 1 second
Background thread:  runner.py
                        ↓ asyncio event loop
Async tasks:     agent calls (up to max_parallel simultaneous Claude API calls)
```

Revision loops run within the same async task — the failed variant re-calls the constructor and critic before the task returns. This means a revision does not block other agents running in parallel.

---

## Build Order

```
1.  models/                      ← foundation, everything depends on these
2.  utils/llm_client.py          ← Claude API wrapper
3.  utils/schema_validator.py    ← validation logic
4.  utils/label_transactions.py  ← BFS labeler; depends only on stdlib
5.  pipeline/cell_generator.py   ← deterministic Cartesian product cell builder; depends only on models
6.  prompts/                     ← plain text, no code dependencies
7.  pipeline/run_state.py        ← needed by both pipeline and console
8.  agents/                      ← depends on models + utils + prompts
9.  pipeline/variant_validator.py ← pure Python 8-rule constraint checker; depends on models
10. pipeline/coverage_matrix.py
11. pipeline/runner.py           ← depends on agents + coverage_matrix + cell_generator + run_state
12. pipeline/output_handler.py
13. console/data_display/        ← depends on models (knows the output schema)
14. console/monitoring_panel.py  ← depends on run_state
15. console/orchestrator_controls.py
16. console/input_panel.py
17. app.py                       ← wires everything, built last
```
