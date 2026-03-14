# 04 — MVP and Scaling [DRAFT]

---

## MVP — Minimum Viable Demo

The MVP is the minimum the system needs to do to make a compelling, complete demonstration to hackathon judges. Every component listed here must work end to end before anything in the next level is touched.

### What the MVP Delivers

- Fraud analyst enters a mule network description into a console
- Orchestrator decomposes it into variation dimensions and generates personas
- Sub-agents generate 20–50 synthetic fraud variants at Level 3 fidelity
- Critic evaluates each variant and filters below-threshold outputs
- Coverage matrix shows the variant space was explored, not just clustered
- Output exports as a labeled dataset in CSV and JSON
- Judge can see the pipeline run live and the output make sense

---

### MVP Agent Stack

| Agent | In MVP? | Notes |
|---|---|---|
| Orchestrator | Yes | Core — must work |
| Persona Generator | Yes | Core — drives diversity |
| Coverage Matrix Manager | Yes | Needed to show spread |
| Fraud Network Constructor | Yes | Level 3 — multi-step reasoning, single agent per variant |
| Criminal Mastermind Agent | No | Level 4 — next level |
| Mule Agents | No | Level 4 — next level |
| Cover Story Agent | No | Level 4 — next level |
| Bank System Agent | No | Level 4 — next level |
| Schema Validator | Yes | Cheap, must have |
| Critic Agent | Yes | Core quality gate |
| Data Handler | Yes | Output must be usable |

### MVP Console

Built in Streamlit. Functional over polished.

- Input panel — fraud description text box, fidelity locked to Level 3, variant count slider (10–50)
- Run button — triggers orchestrator
- Live feed — variants completing with critic scores as they arrive
- Coverage matrix — simple grid filling in as cells are covered
- Output panel — sample records, export button (CSV / JSON)

### MVP Fraud Case

**Mule network only.** One fraud type, well-executed, is more convincing than two fraud types half-working.

### MVP Quality Bar

- 20+ variants generated
- Mean critic score ≥ 7/10
- ≥ 50% coverage matrix saturation
- All output records contain required fields
- CSV export works without errors

### MVP Tech Stack

| Component | Choice | Reason |
|---|---|---|
| LLM | Claude Sonnet | Best reasoning quality per cost, structured output reliable |
| Agent framework | Claude API with raw prompt chaining | Keeps control simple, no framework overhead |
| Console | Streamlit | Fastest functional UI in hackathon timeframe |
| Output format | CSV + JSON | Universal, no dependencies |
| Language | Python | Fastest iteration, best LLM SDK support |

---

## Next Level — If Time Permits

Once MVP is end-to-end and stable, add in this order. Each item is independent — do whichever fits the remaining time.

---

### Next Level 1 — Graph Visualization

**What it adds:** Instead of showing raw records in the output panel, render generated mule networks as actual node graphs. Each account is a node, each transaction is an edge. Show 3–4 networks side by side so structural diversity is visually obvious.

**Why this first:** Highest demo impact per build time. Judges see the difference between a 3-hop chain and a fan-out tree instantly. Makes the "structural diversity" argument concrete without requiring any explanation.

**Tool:** NetworkX + Matplotlib or Pyvis for interactive graphs inside Streamlit.

---

### Next Level 2 — Fidelity Level Control

**What it adds:** Unlock the fidelity selector in the console. Allow the analyst to switch between Level 2, 3, and 4. Show the quality and time difference between levels.

**Why this second:** Enables the best demo moment — run Level 2 (fast, cheap, shallower), then run Level 4 on the same input (slower, richer), show the output side by side. Makes the architecture argument tangible.

**Dependency:** Requires Level 4 agent stack to be built (see Next Level 3).

---

### Next Level 3 — Level 4 Agent Stack

**What it adds:** Full multi-agent role simulation. Criminal mastermind agent, mule agents per hop, cover story agent, bank system agent. Information asymmetry between agents produces emergent evasion behavior that no single-agent approach generates.

**Why this third:** Most architecturally impressive component, but also the most complex and most likely to break under demo conditions. Build it after the MVP is solid so a bug here doesn't take down the whole demo.

**What it unlocks:** Mule agents that don't know they're committing fraud. Criminal agent routing around bank system flags in real time. Cover stories generated on demand. These details show up in the output metadata and make for a compelling walkthrough.

---

### Next Level 4 — Additional Fraud Type

**What it adds:** A second fraud case — either Authorized Push Payment (APP) fraud or Synthetic Identity bust-out fraud — to demonstrate the system generalizes beyond mule networks.

**Why this fourth:** Proves the system isn't a mule network simulator — it's a general fraud data generation platform. This is the argument for the product beyond the hackathon. But it requires the orchestrator to handle a structurally different fraud type cleanly, which is non-trivial.

**Recommended choice if attempted:** APP fraud. Structurally simpler than synthetic identity (no long time horizon), and timely — fastest growing fraud category in North America right now.

---

### Next Level 5 — Before/After ML Comparison

**What it adds:** Train a simple fraud classifier (logistic regression or lightweight XGBoost) on real-ish baseline data, then retrain with synthetic data added, show the precision/recall improvement.

**Why this last:** Most convincing proof that the output actually works — but requires a baseline dataset to compare against, which means either finding a public fraud dataset (e.g. Kaggle credit card fraud dataset) or generating a synthetic baseline separately. Most time-intensive next level item and most dependent on things outside the core system.

---

## Build Priority Order

```
1. Orchestrator + Persona Generator          → MVP foundation
2. Fraud Network Constructor (Level 3)       → MVP core agent
3. Schema Validator + Critic Agent           → MVP quality gate
4. Data Handler + CSV/JSON export            → MVP output
5. Streamlit console (basic)                 → MVP interface
6. Coverage matrix visualization             → MVP completeness
---- MVP complete ----
7. Graph visualization (NetworkX)            → Next Level 1
8. Fidelity selector (Level 2/3 toggle)      → Next Level 2
9. Level 4 agent stack                       → Next Level 3
10. Second fraud type (APP)                  → Next Level 4
11. Before/after ML comparison               → Next Level 5
```

---

## What Cuts First Under Time Pressure

If time runs short, cut in this order without breaking the demo:

| Cut | Impact |
|---|---|
| Coverage matrix visualization | Console still works, just no grid view |
| JSON export (keep CSV only) | Output still usable |
| Persona controls in console | Hard-code sensible defaults |
| Second diversity pass | First pass output is still valid |
| Parquet export | CSV covers the use case |
