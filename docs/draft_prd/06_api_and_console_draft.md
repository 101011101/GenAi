# 06 — API & Console [DRAFT]

---

## Console Features

### Panel 1 — Input Panel

**Components:**

**Fraud Description Text Area**
- Large multi-line text area (~8 rows)
- Placeholder text showing a well-formed example input
- Character count indicator (LLM prompt budget awareness)
- Clear button to reset

**Fraud Type Dropdown (helper)**
- Single-select: Mule Network / Authorized Push Payment / Synthetic Identity / Other
- Pre-fills the text area with a template for the selected type
- Optional — analyst can ignore and type freely

**Target Variant Count**
- Slider: 10 to 100
- Default: 20 for fast demos, 50 for a fuller run
- Helper text updates dynamically: "~X minutes at current fidelity level"

**Estimated Cost Indicator**
- Small text below the run button: "~$X.XX estimated for this run"
- Computed from: variant count × fidelity level × average tokens per agent call
- Helps analysts make informed decisions before starting

**Run Button**
- Disabled if text area is empty
- Changes to "Running..." spinner while pipeline is active
- Grayed out with tooltip if a run is already in progress

**Edge Cases:**
- Empty description → Run button stays disabled
- Description too short (<50 chars) → yellow warning: "Add more detail for better variant diversity"
- Previous run in memory → "Load last run settings" option appears above text area

---

### Panel 2 — Orchestrator Controls

Strategic controls the analyst sets before a run and can adjust during a pause.

| Control | Type | What It Does |
|---|---|---|
| Fidelity level | Tabs (2 / 3 / 4) | Which agents are active, simulation depth. Level 4 shows cost warning badge. |
| Max parallel agents | Slider (1–10) | Speed vs cost tradeoff. Warning shown at 8+ agents. |
| Critic score floor | Slider (5–9, default 7) | Minimum quality to enter dataset |
| Max revision iterations | Number input (1–5, default 2) | Retries before a variant is discarded |
| Persona count | Number input (3–10, default 5) | Distinct criminal profiles to generate |
| Risk distribution | Three-way slider | % high / mid / low risk, must sum to 100 |
| Geographic scope | Multi-select | Domestic / International / EU / North America / APAC |
| Mule context depth | Selector (Shallow / Medium / Deep) | Backstory detail for mule agents |
| Auto second-pass | Toggle (default On) | Re-run on underrepresented coverage cells |
| Pause / Resume / Stop | Buttons | Mid-run pipeline control |

**Fidelity Level Detail:**
- Level 2: "Single-pass, fast, lower quality"
- Level 3: "Multi-step reasoning, persona-grounded (recommended)"
- Level 4: "Full role simulation, highest quality, slowest" — cost warning badge
- For MVP: Level 4 shows "Coming soon" to set up the architecture story without requiring it to be built

**Mule Context Depth Detail:**
- Shallow: job description only — fastest
- Medium: adds financial situation and motivation
- Deep: full backstory, suspicion level, relationship to criminal org — most realistic behavioral variation

**Pause / Resume / Stop Behavior:**
- Pause: waits for current in-flight agents to finish before stopping — does not interrupt mid-generation
- Resume: grayed out unless paused. Analyst can change controls while paused — changes apply on resume.
- Stop: requires confirmation dialog ("Stop now? You will keep N completed variants.") — then calls output_handler with whatever approved variants exist

**Edge Cases:**
- Estimated time warning if settings are extreme (e.g. 1 parallel agent + Level 4 + 50 variants → "~45 minutes at these settings")
- Fidelity changes mid-run: display updates but tooltip explains "applies on next run"

---

### Panel 3 — Live Monitoring Panel

Real-time visibility into what the pipeline is doing. Runs while the pipeline is active.

**Top-Level Progress Bar**
- Full-width: Variants Completed / Target
- Label: "23 / 50 variants complete"
- Estimated time remaining: "46% — ~8 minutes remaining"

**Pipeline Phase Indicator**
- Horizontal step indicator: [Orchestrating] → [Generating] → [Evaluating] → [Complete]
- Current phase highlighted. During Orchestrating: "Building coverage matrix and generating personas..."

**Persona Cards (appear after orchestration)**
- One card per persona: name, risk level badge (High / Mid / Low), geographic scope, operational scale
- Cards animate in as personas are generated
- Clicking a card opens a modal with full persona description

**Variant Feed**
- Scrollable live feed, newest at top
- Each card shows:
  - Persona name and risk badge
  - Variant parameters summary ("6 hops, fan-out, crypto extraction, international")
  - Critic score as colored gauge: green (≥8), yellow (6–7), red (<6)
  - Timestamp of completion
  - Expandable section showing the strategy description the agent wrote
- Rejected variants appear with red border and "Rejected" tag — still shown for transparency

**Coverage Matrix (live)**
- Grid of variation dimensions
- Cell states: Gray (unassigned) / Blue pulsing (agent working) / Green (approved) / Yellow (revised) / Red (rejected, reassigned)
- Mouse hover on cell shows persona and parameters

**Active Agent Status**
- Badge row: "Agent 1: Generating transactions (Viktor) | Agent 2: Critic evaluating (James)"
- Shows revision activity in real time — analyst can see when critic is rejecting heavily

**Revision Activity Counter**
- Small stat: "Revisions: 7 | Rejections: 2"
- Spike in revisions signals critic floor may be too high or personas are underconstrained

**Log / Console Output**
- Collapsed by default
- When expanded: raw pipeline log, token usage, timing, errors

**Edge Cases:**

*Run fails mid-way (API error):*
- Red banner: "Pipeline error — run stopped. N variants saved."
- "Save partial dataset" button
- "Retry failed variants" button — regenerates only failed cells

*0 variants pass critic:*
- Warning: "0 variants passed quality gate. Critic floor may be set too high."
- Suggestion to lower floor or reduce fidelity
- Failed variants shown anyway (marked "Not in dataset") for inspection

*Run paused:*
- Progress bar shows "Paused"
- "Resume" button appears prominently
- "Export partial dataset" button appears
- Analyst can adjust Orchestrator Controls — changes apply on resume

*Coverage saturation low (<40%) after completion:*
- Yellow warning: "Coverage saturation: 38%. Consider running a second pass."
- "Run second pass now" button auto-populates input panel with targeted configuration

---

### Panel 4 — Data Display Module

Post-run visualization. Makes three things instantly obvious to a judge:
1. The dataset is large and diverse
2. Fraud variants are structurally different — not the same network with different numbers
3. Output is immediately usable for ML training

**Run Summary Header**
- Large stat bar: [47 Variants] [Mean Score: 8.1/10] [Coverage: 82%] [6 Personas] [~4,200 Transactions]
- Readable from across the room during a demo
- Run timestamp and duration

**1. Coverage Matrix (final state)**
- Full rendered grid with legend
- Downloadable as PNG
- Annotation: "82% of planned variant space covered"

**2. Network Graph View (highest demo impact)**
- 3–4 fraud networks rendered side by side
- Nodes = accounts (colored by role: source / mule / destination)
- Edges = transactions (thickness = amount, direction = money flow)
- Fraud path edges in red, cover activity edges in gray
- Graphs chosen for maximum structural contrast (chain vs fan-out vs hybrid)
- Hover: node shows account details, edge shows amount and timestamp
- "View all networks" button opens paginated gallery

**3. Dataset Browser**
- Full-width interactive `st.dataframe`
- Default columns: `variant_id`, `persona_name`, `timestamp`, `amount`, `fraud_role`, `is_fraud`, `critic_score`
- Filters: persona (multi-select), critic score range, fraud role, topology type, is_fraud (True/False/All)
- "Show variant metadata" toggle: adds `variant_parameters`, `evasion_techniques`, `fraud_indicators_present`
- Row count: "Showing 1,240 of 4,213 transactions"

**4. Persona Gallery**
- Card view of all generated personas, sorted by risk level high to low
- Each card: name, risk level, scale, geography, timeline, evasion targets
- Clicking a card: modal with full persona description, mapped variant IDs, mean critic score, mini network graph of one variant

**5. Critic Score Distribution**
- Histogram of scores across all variants (realism and distinctiveness separately)
- Vertical line at configured score floor
- "N variants rejected" labeled clearly

**6. Variant Comparison View**
- Side-by-side comparison of any two variants selected from dropdowns
- Shows: persona, parameters, strategy description, network graph, transaction count, mean amount
- Purpose: makes structural diversity tangible — point at two completely different graphs and say "same fraud type, same model"

**7. Export Panel**
- Format tabs: CSV / JSON / Graph Adjacency List
- Each format: preview of first 5 rows, `st.download_button`, file size estimate
- Graph format note: "nodes.csv + edges.csv for GNN training"
- "Include metadata" toggle: adds persona and variant parameter columns
- "Export run summary" button: downloads `run_summary.json`

---

### Analyst Workflow — End to End

```
1. Open console → Input Panel active
2. Enter fraud description, set basic controls
3. Optionally expand Orchestrator Controls to adjust fidelity / personas / critic
4. Click Run → Input Panel locks, Monitoring Panel expands
5. Watch live: orchestration → persona cards → variant feed + coverage matrix
6. Optionally Pause → adjust settings → Resume
7. Run completes → Data Display Module unlocks
8. Explore network graphs, coverage matrix, dataset browser
9. Export in chosen format
10. Start a new run or re-run with different settings
```

---

## API Usage

### Claude API — Model Selection

| Agent | Model | Reason |
|---|---|---|
| Orchestrator | Claude Opus with extended thinking | Dimension decomposition determines entire run quality — worth the cost |
| Persona Generator | Claude Sonnet | Creative generation, moderate complexity |
| Fraud Constructor | Claude Sonnet | Core generation agent, best quality/cost ratio |
| Critic | Claude Sonnet | Evaluation reasoning, reliable at this tier |
| Cover Story Agent | Claude Sonnet | Single-turn, moderate complexity |
| Criminal / Mule Agents (L4) | Claude Sonnet | Multi-turn reasoning, cost needs to stay manageable |
| Bank System Agent (L4) | Claude Haiku | Rule application — fast and cheap |
| Dev/test iterations | Claude Haiku | Iterate on prompts cheaply before switching to Sonnet |

**Extended thinking on the orchestrator:** use `thinking: { type: "enabled", budget_tokens: 5000 }`. The orchestrator's dimension decomposition directly determines variant diversity for the entire run. Spending extra compute here has outsized downstream effect.

---

### Structured Output

The most critical API feature for this system. The pipeline cannot function on free-text agent outputs — every agent response must be parseable JSON.

Use `response_format` with JSON schema enforcement on every agent call. Define Pydantic models for each output type, use `model.model_json_schema()` to pass the schema to the API. Returns a parse error rather than malformed data.

Key schemas:
- `OrchestratorOutput` — dimension list, coverage cells, persona assignments
- `PersonaList` — array of Persona objects
- `RawVariant` — persona, strategy description, parameters, transaction array
- `CriticScore` — per-dimension scores, pass/fail flags, feedback string

---

### Streaming

Use streaming on the fraud constructor call. Instead of waiting for a full variant to complete, stream the output and display the strategy description as it arrives in the variant card. Makes the demo feel alive — judges see the agent reasoning in real time rather than a spinner.

Implementation: the strategy description appears early in the JSON output (before the transaction array). Parse and display it as it streams. Wait for full JSON completion before running schema validation and the critic.

---

### Tool Use

**Bank System Agent (Level 4):**
Give the bank agent two tools: `flag_transaction` and `reject_transaction`. The criminal mastermind agent receives the flag as an event and must respond with a routing decision. Creates genuine adversarial back-and-forth without requiring the criminal agent to simulate bank behavior itself.

**Grounding data injection:**
Give constructor agents a `lookup_transaction_stats` tool backed by a static lookup table. Agents call it when generating transaction amounts to stay within realistic ranges for a given merchant category. No external API — static JSON file bundled with the system.

---

### Grounding Data — Static Files (No External APIs)

All real-world grounding data is bundled as static JSON files. No external API calls, no latency, no API keys, no demo risk.

| File | Contents | Source |
|---|---|---|
| `mcc_stats.json` | Amount distributions by merchant category (mean, std, range) | Federal Reserve Payment Study |
| `payment_rail_constraints.json` | Processing windows, per-transaction limits per rail (ACH, Interac, SWIFT, Zelle) | Public rail documentation |
| `account_balance_distributions.json` | Balance ranges by demographic and account type | Federal Reserve Survey of Consumer Finances |
| `regulatory_thresholds.json` | Reporting thresholds by jurisdiction (US $10K CTR, CA $10K LCTR, etc.) | FinCEN / FINTRAC public guidance |

These files are loaded at startup and passed as reference context to agent prompts.

---

### Token Budget Estimates

**Per 20-variant run at Level 3, 5 personas:**

| Agent | Calls | Avg Input | Avg Output | Subtotal |
|---|---|---|---|---|
| Orchestrator (+ thinking) | 1 | 2,000 | 4,000 + 5,000 thinking | ~11K |
| Persona Generator | 1 | 1,000 | 2,000 | ~3K |
| Fraud Constructors | ~25 | 3,500 | 7,000 | ~262K |
| Critic | ~25 | 6,000 | 800 | ~170K |
| **Total** | | | | **~446K tokens** |

**Cost estimates at Sonnet pricing (~$3/$15 per million input/output tokens):**

| Variants | Estimated Cost | Run Time (5 parallel) |
|---|---|---|
| 20 | ~$4–6 | ~5–7 min |
| 50 | ~$10–15 | ~12–15 min |
| 100 | ~$20–30 | ~25–30 min |

---

### Rate Limits

Anthropic Sonnet defaults:
- 1,000 RPM (requests per minute)
- ~160K TPM (tokens per minute)

At 10 parallel constructor agents generating ~7K output tokens each, peak output token rate approaches the TPM limit. Practical recommendations:
- **Default max_parallel to 5** — stays safely within limits with buffer
- Exponential backoff with jitter on 429 and 529 responses in `llm_client.py`
- Hard timeout per agent call: 30 seconds for constructors, 15 seconds for critics

---

### Cost Controls

**Hard cost cap in `runner.py`:**
Track cumulative token usage in `RunState`. Stop the run and surface a warning if it exceeds a configured dollar threshold (default $20). Prevents runaway costs from revision loop bugs.

**Confirmation before expensive runs:**
If UI estimates >$10, show a confirmation dialog before starting.

**Demo mode flag:**
Hidden configuration flag that runs 5 variants at Haiku, skips revision loop, completes in under 60 seconds. Shows the console mechanics working live without waiting 30 minutes. Useful for quick judge demonstrations.

---

### Error Handling in `llm_client.py`

- Retry up to 3 times on JSON parse errors with a modified prompt ("Your previous response was not valid JSON. Return only valid JSON matching this schema...")
- Exponential backoff with jitter on 429 (rate limit) and 529 (overloaded) responses
- Hard timeout per call (30s constructors, 15s critics)
- Per-task exception catching in asyncio gather — one failed agent call must never crash the entire run
