# FraudGen — Developer Guide

How to run the system, how each part works, how to test it, and what to look for when something breaks.

---

## Quick Start

```bash
# Install deps
pip install -r requirements.txt

# Add your API key to .env (already set up)
# .env contains: ANTHROPIC_API_KEY=sk-ant-...

# Run the app (real API calls)
streamlit run app.py

# Run with mock data (no API key consumed, instant)
# Uncomment FRAUDGEN_MOCK=1 in .env, then:
streamlit run app.py
```

App opens at `http://localhost:8501`.

To use demo mode, append `?demo=true` to the URL — runs a pre-configured 12-variant mule network in ~60 seconds.

---

## Folder Structure

```
app.py                          ← Streamlit entry point
.env                            ← API key + optional FRAUDGEN_MOCK=1

models/                         ← Pydantic data models (shared language)
  run_config.py                 ← All settings for one run
  persona.py                    ← Criminal profile
  variant.py                    ← Transaction, RawVariant, ValidatedVariant, ScoredVariant
  output_record.py              ← Flat row for final CSV/dataset

utils/
  llm_client.py                 ← Async Claude API wrapper (retries, cost tracking, mock mode)
  schema_validator.py           ← Fast sync validation of agent JSON output

prompts/                        ← Plain text system prompts, one per agent
  orchestrator.txt
  persona_generator.txt
  fraud_constructor.txt
  critic.txt

data/                           ← Static grounding data (no API calls needed)
  mcc_stats.json                ← Amount distributions by merchant category
  payment_rail_constraints.json ← ACH/wire/Zelle/crypto limits and settlement times
  account_balance_distributions.json
  regulatory_thresholds.json    ← CTR/SAR reporting thresholds by jurisdiction

agents/                         ← LLM-powered agents (no imports from pipeline/ or console/)
  orchestrator.py               ← Decomposes fraud type into coverage cells
  persona_generator.py          ← Generates criminal personas
  fraud_constructor.py          ← 5-step reasoning chain → transaction sequence
  critic.py                     ← Quality gate scoring

pipeline/                       ← Pure Python, no LLM calls (except through agents/)
  run_state.py                  ← Thread-safe shared state (pipeline writes, console reads)
  coverage_matrix.py            ← Tracks which variant space cells are filled
  output_handler.py             ← Writes CSV/JSON files to output/runs/
  runner.py                     ← Async coordinator: runs all agents in order

console/                        ← Streamlit UI (no agent imports)
  input_panel.py                ← Fraud description + variant count
  orchestrator_controls.py      ← Advanced settings (collapsed by default)
  monitoring_panel.py           ← Live feed during run
  data_display/
    coverage_matrix_view.py     ← Grid visualization
    network_graph_view.py       ← NetworkX mule network graphs
    stats_panel.py              ← Summary metric cards
    dataset_browser.py          ← Filterable transaction table
    export_panel.py             ← Download buttons

output/runs/                    ← Auto-created per run, gitignored
  run_YYYYMMDD_HHMMSS/
    config.json
    personas.json
    variants.json
    dataset.csv
    dataset.json
    run_summary.json
```

---

## How a Run Works End to End

This is the execution path when you click Run:

```
1. app.py        Builds RunConfig from input panel + advanced controls
2. app.py        Creates RunState, starts background thread
3. runner.py     Calls OrchestratorAgent → gets variation dimensions + coverage cells
4. runner.py     Calls PersonaGeneratorAgent → gets list of Persona objects
5. runner.py     Spawns N parallel async tasks (up to max_parallel at once)

For each task:
  6. runner.py        Claims a coverage cell
  7. fraud_constructor.py  5-step reasoning chain:
       Step 1: Persona analysis (what does this criminal need?)
       Step 2: Network planning (hop count, topology, timing, amounts)
       Step 3: Participant profiles (who are the mule accounts?)
       Step 4: Transaction generation (full sequence, streamed live to console)
       Step 5: Self-review (fix inconsistencies before returning)
  8. schema_validator.py   Fast sync validation → if schema broken, hard fail (no retry)
  9. critic.py             Scores on realism, distinctiveness, persona consistency, labels
       → pass: add to approved_variants, mark cell complete
       → fail: send feedback back to fraud_constructor, retry (max N times)

After all tasks:
  10. runner.py     Check coverage saturation → optional second pass
  11. output_handler.py  Write all 6 output files
  12. run_state.py  mark_complete() → console transitions to results phase
```

**The key design rule:** Agents never call other agents. `runner.py` is always the intermediary — it calls agent A, takes the output, and passes it to agent B. Agents only import from `models/` and `utils/`.

---

## Data Models — What Flows Between Components

```
RunConfig          → runner.py (all settings for the run)
OrchestratorOutput → runner.py (dimensions + cells + persona count)
List[Persona]      → runner.py → fraud_constructor (behavioral seed)
RawVariant         → schema_validator (unvalidated JSON from agent)
ValidatedVariant   → critic (schema confirmed, ready to score)
ScoredVariant      → approved_variants[] → output_handler
OutputRecord       → dataset.csv (one row per transaction, flat)
VariantSummary     → run_state.variant_log → console display (lightweight)
RunState           → monitoring_panel (pipeline writes, console reads every 1s)
```

---

## The Mock Mode

When `FRAUDGEN_MOCK=1` is set in `.env`, `LLMClient` skips all real API calls and returns instant stub data. The detection works by scanning message content to figure out which agent is calling:

- Message contains "variation_dimensions" or "decompose" → returns orchestrator stub (6 cells)
- Message contains "persona" + "risk" → returns 3 persona stubs (Viktor, James, Maria)
- Message contains "realism" or "persona_consistency" → returns critic score stub (random 6.5–9.2)
- Everything else → returns fraud constructor stub (3-hop chain, 4 transactions)

The full pipeline runs end-to-end in mock mode — all validation, the coverage matrix, the revision loop, and output files. It just uses fake data instead of real LLM responses.

---

## API Cost and Models

| Agent | Model | Why |
|---|---|---|
| Orchestrator | claude-opus-4-6 + extended thinking (5000 tokens) | Dimension decomposition quality determines the whole run |
| Persona Generator | claude-sonnet-4-6 | Creative, moderate complexity |
| Fraud Constructor | claude-sonnet-4-6 | 5 sequential calls per variant |
| Critic | claude-sonnet-4-6 | 1 call per variant |

**Rough cost per 20-variant run at Level 3:** ~$4–6. The default cost cap is $20 — the runner stops and saves whatever it has if this is exceeded.

Token usage is tracked in `LLMClient.total_input_tokens` / `total_output_tokens`. Cost estimate is surfaced live in the monitoring panel.

---

## Running and Testing — Step by Step

### Step 1: Verify it opens

```bash
streamlit run app.py
```

**Expected:** Browser opens at localhost:8501. You see the FraudGen title, a fraud type dropdown, a text area, a variant count slider, and a Run button (disabled until you type something).

**If it doesn't open:** Check `pip install -r requirements.txt` ran successfully. Check `.env` has a valid key (or that `FRAUDGEN_MOCK=1` is uncommented for keyless testing).

---

### Step 2: Mock run (full pipeline, no API cost)

1. Open `.env`, uncomment `FRAUDGEN_MOCK=1`
2. `streamlit run app.py`
3. Select "Mule Network" from the dropdown (auto-fills description)
4. Set variant count to 10
5. Click Run

**Expected results during run:**
- Progress bar starts filling
- Phase label reads: "Generating personas" → "Generating variants" → "Compiling dataset"
- Persona cards appear in the left feed (Viktor Sokolov, James Harlow, Maria Chen)
- Variant cards appear one by one with critic scores (green ≥7, yellow 5–6.9, red <5)
- Coverage matrix cells turn green as variants complete
- Active agent count shows up to 5 simultaneous
- Run completes in ~15–30 seconds (mock data has 0.3s sleep per call)

**Expected results after run:**
- Stats panel shows: ~10 variants, mean score ~7–9, coverage saturation some%, 3 personas, ~40 total transactions
- Network graphs render 3–4 side-by-side directed graphs (nodes = accounts, edges = transactions)
- Dataset browser shows filterable table of transactions with fraud_role and is_fraud columns
- Export panel shows CSV/JSON download buttons with file size estimates
- Output folder created at `output/runs/run_YYYYMMDD_HHMMSS/` with 6 files

---

### Step 3: Verify output files

After a run (mock or real), check `output/runs/` for the most recent folder:

```bash
ls output/runs/
# → run_20260314_143022/

ls output/runs/run_20260314_143022/
# → config.json  dataset.csv  dataset.json  personas.json  run_summary.json  variants.json
```

**config.json** — Should contain your RunConfig settings (fraud_description, variant_count, etc.)

**personas.json** — List of persona IDs (may be stubs in mock mode — full persona data is carried in variants)

**variants.json** — Array of variant objects. Each should have: variant_id, fraud_type, persona_id, strategy_description, variant_parameters (hop_count, topology, etc.), evasion_techniques, fraud_indicators_present, plus critic scores.

**dataset.csv** — One row per transaction. Open it and check:
- Every row has an `is_fraud` column (True/False)
- Every row has a `fraud_role` column (placement / hop_N_of_M / extraction / cover_activity)
- Cover activity rows should have `is_fraud = False`
- Amounts look realistic (not $0, not $999,999,999)
- Timestamps are valid ISO format

**run_summary.json** — Should show: variant_count, mean_critic_score, total_transactions, total_cost_usd, revisions_count, rejections_count.

---

### Step 4: Real API run (small)

1. Comment out `FRAUDGEN_MOCK=1` in `.env` (key should be active)
2. `streamlit run app.py`
3. Select "Mule Network", set variant count to **5** (minimum cost ~$1–2)
4. Click Run

**Expected:** Same flow as mock but slower (30s–2min for 5 variants at Level 3 with 5 parallel agents). Variants should look meaningfully different from each other — different hop counts, different topologies, different strategies described in the variant card text. Critic scores should vary (not all identical).

**If variants cluster (all look similar):** The orchestrator may be generating similar cells. Check `variants.json` — look at `variant_parameters` across variants. If hop_count is always 3 and topology is always "chain", the orchestrator prompt may need tuning.

**If critic is rejecting everything:** Critic floor may be too high for the fraud type, or the constructor isn't producing realistic outputs. Check `run_summary.json` — if rejections_count is high and variant_count is low, lower the critic floor in Advanced Controls.

---

### Step 5: Test pause/resume/stop

1. Start a 20-variant run
2. Click Pause after ~5 variants complete
3. Verify: progress bar shows "Paused", running variant count stops incrementing
4. Click Resume — run should continue from where it stopped
5. Start another run, click Stop mid-way
6. Verify: results phase shows only the variants that completed before Stop, output files are written with partial data

---

### Step 6: Test demo mode

```
http://localhost:8501?demo=true
```

**Expected:** Blue banner "Demo mode — running pre-configured demo". Run auto-starts with 12 variants, mule network description, Haiku model (fast). Completes in ~60 seconds. After completion: "Demo complete! Click Start New Run to try with your own fraud type."

---

## Common Bugs and Where to Look

### App won't start / import error

Check the terminal for the specific module. Most likely:
- Missing dependency → `pip install -r requirements.txt`
- Pydantic version mismatch → ensure `pydantic>=2.0.0` (the code uses v2 syntax)
- `from dotenv import load_dotenv` failing → `pip install python-dotenv`

### "ANTHROPIC_API_KEY not set" error when clicking Run

`.env` isn't loading. Check:
1. `.env` file exists in project root (same folder as `app.py`)
2. `FRAUDGEN_MOCK=1` is NOT active (commented out)
3. The key in `.env` starts with `sk-ant-`

### Run starts but 0 variants complete

All variants failing schema validation or critic. Check:
- `run_state.errors` — surfaced in the monitoring panel (expand the error section)
- `output/runs/latest/run_summary.json` — check `rejections_count`

Schema failures (hard fail, no retry) mean the agent returned malformed JSON. In mock mode this shouldn't happen — if it does, the mock response detection logic in `_mock_response()` (`utils/llm_client.py`) is returning the wrong stub for some agent call.

In real mode, the LLM may return prose around the JSON. `llm_client.py` retries up to 3 times with a JSON correction prompt — if all 3 fail, the variant is discarded.

### Coverage matrix doesn't appear / shows empty

The coverage matrix view (`console/data_display/coverage_matrix_view.py`) expects `CoverageMatrix.to_display_dict()` output. If `matrix_display_dict` is None (run ended before matrix was built), it shows a fallback message. This usually means the orchestrator failed before building the matrix — check `run_state.errors`.

### Network graphs don't render

NetworkX or Matplotlib may not be installed. The view fails gracefully and shows an info message. Fix: `pip install networkx matplotlib`.

If installed but graphs look wrong (all nodes same color, no edges): the variant transactions may not have `sender_account_id` / `receiver_account_id` populated, or all transactions are `cover_activity`. Check `dataset.csv` — are there fraud_role values like "hop_1_of_3", "hop_2_of_3"?

### Critic scores are all the same (mock mode)

Expected — mock mode returns a random score between 6.5 and 9.2 for every critic call. In real mode, scores will vary meaningfully across variants.

### Run hangs after "Generating personas" phase

The orchestrator call uses extended thinking (`claude-opus-4-6`) and can take 30–60 seconds. This is normal. If it hangs >2 minutes, the API call probably timed out — check the terminal for `call_with_thinking timed out after 120s`. If this happens repeatedly, the Opus API may be under load — try again or switch orchestrator to Sonnet in `agents/orchestrator.py`.

### "Cost cap reached" error

Default cap is $20. For a demo this shouldn't trigger — if it does, either `max_parallel` is very high or there are many revision loops burning tokens. Check `run_summary.json` for `total_cost_usd` and `revisions_count`.

---

## Adjusting Agent Behavior Without Touching Code

All agent prompts are plain text in `prompts/`. Edit them directly — no Python changes needed. The agents reload the prompt file on every `run()` call.

**To make variants more diverse:** In `prompts/fraud_constructor.txt`, strengthen the instruction in Step 2 (Network Planning) to pick more extreme positions on each dimension.

**To make the critic less strict:** In `prompts/critic.txt`, lower the realism threshold language or soften the persona consistency check. Alternatively, lower the `critic_floor` slider in Advanced Controls.

**To add a new fraud type:** The system works on any fraud description — no code changes needed. Just type a new description in the input panel. The orchestrator will decompose it into dimensions regardless of type.

**To add more variation dimensions:** In `prompts/orchestrator.txt`, add examples of dimensions you want it to consider (e.g. "account age", "network jurisdiction count"). The orchestrator's output structure is flexible.

---

## Output Format Reference

### dataset.csv columns

| Column | Type | Description |
|---|---|---|
| transaction_id | str | Unique ID per transaction |
| timestamp | str (ISO) | Simulated datetime |
| amount | float | Transaction amount |
| sender_account_id | str | Source account |
| receiver_account_id | str | Destination account |
| merchant_category | str | e.g. wire_transfer, grocery |
| channel | str | ACH / wire / Zelle / card / crypto |
| is_fraud | bool | True for fraud transactions |
| fraud_role | str | placement / hop_N_of_M / extraction / cover_activity |
| variant_id | str | Which variant this belongs to (e.g. V-A3F7B2) |
| persona_id | str | Which persona generated it (e.g. P-01) |
| persona_name | str | Human-readable persona name |
| fraud_type | str | mule_network (or other fraud type) |
| variant_parameters | dict | {hop_count, topology, timing_interval_hrs, ...} |
| critic_scores | dict | {realism, distinctiveness, passed} |

### run_summary.json fields

```json
{
  "variant_count": 20,
  "mean_critic_score": 7.8,
  "coverage_saturation_pct": 68.0,
  "persona_count": 3,
  "total_transactions": 186,
  "run_duration_seconds": 312,
  "total_cost_usd": 4.21,
  "revisions_count": 3,
  "rejections_count": 1,
  "timestamp": "2026-03-14T14:30:22"
}
```

---

## Environment Variables

| Variable | Value | Effect |
|---|---|---|
| `ANTHROPIC_API_KEY` | `sk-ant-...` | Required for real runs |
| `FRAUDGEN_MOCK` | `1` | Skip all API calls, return stub data |

Both are set in `.env` at project root. `app.py` loads `.env` automatically on startup via `python-dotenv`.
