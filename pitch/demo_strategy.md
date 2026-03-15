# FraudGen — Demo Strategy

## TL;DR recommendation

**Use the Streamlit console as the primary demo surface.**
Use the debug pipeline (`debug_pipeline.py`) as the explainer tool — either beforehand to show internal thinking, or as a backup if the API is slow.

The console is what wins the room. The debugger is what convinces the technical judges.

---

## Option A: Streamlit Console (PRIMARY — recommended)

### Why
- Visual. The coverage matrix filling in real time is a story by itself.
- Shows the full pipeline without narrating it — judges see it, not just hear it.
- The output table and network graphs give you a natural closer — "here's what goes into the bank's ML pipeline."

### Demo flow (target: 4–5 min)

**Beat 1 — Input (30 sec)**
- Open the console, show the input panel
- Pre-filled description already loaded (use demo mode: `?demo=true`)
- Point at: fraud description box, variant count slider showing "12 variants · Est. $2.10 · Est. 60s"
- Say: *"A fraud analyst types what they know about a fraud type. That's the only input."*

**Beat 2 — Hit Run, watch the orchestrator (45 sec)**
- Hit Run. Show the live monitoring panel animating.
- Point at: progress bar transitioning from "Decomposing fraud type..." to "Generating personas..."
- Say: *"The orchestrator is using Claude Opus with extended thinking to break this fraud type into every dimension it can vary across — hop count, timing, topology, extraction method, evasion."*
- When dimensions appear: *"These are the axes of the variant space we're going to explore."*

**Beat 3 — Personas stream in (30 sec)**
- Point at persona cards appearing: name, risk badge, backstory snippet
- Say: *"Now it creates criminal personas — Viktor is high-risk, international routing. James is conservative, slow timing, domestic only. Each persona seeds structurally different fraud logic."*

**Beat 4 — Coverage matrix filling (90 sec — the money shot)**
- Point at the matrix: *"Each cell is a specific point in the fraud variant space. Gray = not yet covered. Blue = agent running right now. Green = approved."*
- Watch a variant card appear with a critic score badge (green ≥7)
- If a yellow appears: *"That one came back from the critic for revision — realism score was too low."*
- Say: *"5 parallel agents. Each one is doing 4 LLM reasoning steps — persona analysis, network planning, participant profiles, transaction generation. Then the critic scores it."*

**Beat 5 — Run completes, pivot to output (60 sec)**
- Summary header: "12 variants · Mean score 8.1 · Coverage 83% · 1,140 transactions"
- Switch to Dataset Browser tab — show the table
- Say: *"Every transaction is labeled. is_fraud. fraud_role — placement, hop, extraction, cover activity. variant_id. persona. This is what goes into the bank's XGBoost or GNN training pipeline."*
- Click one fraud role filter to show only extraction transactions: *"Want to see only the extraction layer? One click."*

**Beat 6 — Network graph (45 sec)**
- Switch to Network Graph tab
- Show 2–3 graphs side by side: *"This is a 3-hop chain from Viktor. This is a 5-hop fan-out from James. Structurally different. Not statistical noise around the same pattern — structurally different fraud."*
- Red edges = fraud path. Gray = cover activity.
- Say: *"This is what the all-seeing eye looks like."*

---

## Option B: Debug Pipeline CLI (TECHNICAL DEEP DIVE)

### When to use
- Technical judges who want to see the internals
- After the main demo, as a "let me show you under the hood" moment
- If the Streamlit console is slow or has API issues

### What the debug pipeline shows
`debug_pipeline.py` runs a single variant end-to-end and prints every stage.

### What to point at in the CLI output

```
[ORCHESTRATOR]
  Input: "layered 3-hop mule network..."
  Extended thinking: 4,892 tokens
  Dimensions identified: {hop_count: [2,3,5], timing: [same-day, delayed...], ...}
  Coverage cells generated: 6

[PERSONA GENERATOR]
  Persona 1: Viktor Sokolov
    risk_tolerance: high
    resources: international banking access, crypto wallets
    backstory: ...

[FRAUD CONSTRUCTOR — V-001 · 3-hop chain · same-day · Viktor]
  Step 1 — Persona analysis:
    "Viktor needs speed. He knows ACH same-day is traceable but it
     maximizes velocity before freeze. He'll use Zelle for internal hops."
  Step 2 — Network planning:
    hop_count: 3, topology: chain, timing_interval_hrs: 2.5
    extraction: wire_international
  Step 3 — Participant profiles:
    ACC-001: Viktor's shell LLC (originating)
    ACC-002: Mule 1 — recruited via job posting, believes it's freelance pay
    ACC-003: Mule 2 — crypto exchange account, knows partial intent
    ACC-004: Offshore destination
  Step 4 — Transactions generated: 5 (4 fraud + 1 cover)

[VALIDATOR]
  ✓ Amount floors: pass
  ✓ Channel constraints: pass (Zelle domestic only — pass)
  ✓ Timestamp ordering: pass
  ✓ Regulatory threshold check: $4,800 < $10,000 CTR — deliberate structuring

[LABELER]
  BFS traversal from source node ACC-001
  TXN-001: placement (ACC-001 → ACC-002)
  TXN-002: hop_1_of_3 (ACC-002 → ACC-003)
  TXN-003: hop_2_of_3 (ACC-003 → ACC-004)
  TXN-004: extraction (ACC-004 → OFFSHORE)
  TXN-005: cover_activity (ACC-001 → GROCERY)

[CRITIC]
  Realism: 8.4/10 — "Amount structuring below CTR threshold is deliberate
    and realistic. Zelle→wire transition is a known escalation pattern."
  Distinctiveness: 7.8/10 — "Same-day timing with chain topology is
    structurally distinct from the delayed fan-out variants."
  Persona consistency: True
  → APPROVED
```

**What to say:** *"The agent literally reasons about why Viktor chose these specific amounts — structuring below the $10,000 reporting threshold. That's evasion logic. No statistical tool can generate that."*

---

## Option C: Hybrid (IDEAL for a panel with mixed audience)

1. Start with the Streamlit console — win the room visually (3–4 min)
2. Flip to the debug CLI for one variant — show the thinking chain (1–2 min)
3. Come back to the output table to close

---

## Console elements to highlight — priority order

| Element | Why it's compelling | What to say |
|---|---|---|
| Coverage matrix filling | Visual proof of systematic exploration, not random generation | "Every cell is a unique structural variant. We guarantee coverage, not clustering." |
| Persona cards | Makes the agents feel real and purposeful | "Each criminal profile seeds structurally different fraud logic." |
| Variant feed with critic scores | Shows quality gate in action — not all variants pass | "The critic rejects weak variants. Only realistic, distinct data enters the dataset." |
| Retry/revision visible | Shows the system is rigorous | "If a variant scores below 7, it gets specific feedback and tries again." |
| Dataset browser table | The actual ML artifact — tangible | "This is what goes into your XGBoost. One row per transaction, fully labeled." |
| Network graph side-by-side | Visual proof of structural diversity | "Not statistical noise — structurally different attack topologies." |
| Run summary stats | Credibility numbers | "23/25 approved, 82% coverage, 2,140 transactions, cost $4.21." |

---

## Output table — what makes it land

The table needs to show two things at a glance:
1. **The fraud structure is realistic** — amounts below CTR threshold, correct channels per rail, timestamps that make sense
2. **The labels are machine-ready** — is_fraud, fraud_role, variant_id are the columns an ML engineer immediately recognizes

### Columns to keep visible in demo (hide the rest)

| transaction_id | timestamp | amount | channel | is_fraud | fraud_role | variant_id | persona_name |
|---|---|---|---|---|---|---|---|

Show ~6–8 rows — enough to see one full fraud chain (placement → hop_1 → hop_2 → extraction) plus one cover_activity row.

**Color code fraud_role:**
- `placement` → purple
- `hop_N_of_M` → blue
- `extraction` → red
- `cover_activity` → gray

This makes the layered structure readable at a glance without needing to explain it.

---

## What NOT to demo

- Don't show the advanced controls panel unless asked — it's a distraction
- Don't try to run a real 25-variant run live (7 min is too long) — use demo mode (60 sec) or a pre-run result
- Don't read the persona backstories aloud — just gesture at them as "behavioral seeds"
- Don't spend time on the export panel — just say "CSV, JSON, GNN adjacency list, one click"

---

## Backup plan

If the API is slow or something fails during live demo:
- Have a pre-run output folder ready in `output/runs/` with a completed mock run
- The console's data display works off completed run files — you can navigate it without running a new job
- Use `FRAUDGEN_MOCK=1` for instant pipeline runs if you need to show the process but not real output
