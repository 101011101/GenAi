# User Flow & Console Features

**Audience:** UI engineers, demo prep, stakeholder walkthroughs
**Supplements:** `06_api_and_console_draft.md` (technical spec) — this doc is the analyst-facing narrative
**Related:** `03_product_requirements_draft.md` (user stories), `04_mvp_and_scaling_draft.md` (MVP scope)

---

## User Persona

**Fraud Analyst (primary user)**

Investigates fraud patterns at a financial institution. Needs labeled training data to improve the ML models that flag suspicious transactions — but the existing dataset only covers fraud variants the institution has already seen. Doesn't write code. Cares about three things:

1. **Variant diversity** — did the system explore the space, or just generate copies of the same pattern?
2. **Realism** — will this data actually train a better model, or is it obviously synthetic garbage?
3. **Speed to pipeline** — how fast can this get into the next training run?

The console is built around these three concerns. Every control either expands the variant space, improves realism, or reduces the time from "I have an idea" to "data is in the pipeline."

---

## User Flow — 4 Phases

The analyst moves through four phases in a single session: **Input → Tweak → Run → Review**. Each phase is a distinct UI state.

---

### Phase 1: Input

*The analyst describes what kind of fraud they want to explore and how much of it to generate.*

**Fraud description (free text)**
Natural language prompt that seeds the entire run. The orchestrator agent reads this to decompose the fraud type into variable dimensions.

> Example: *"layered mule account network with cross-border hops and burst withdrawal"*

Why this matters: the description is the only creative input the analyst provides. The richer and more specific it is, the more targeted the variant space the system explores. A vague description produces generic variants; a specific one produces structurally diverse variants around a real fraud pattern.

Validation: Run button is disabled if the field is empty or under 20 characters. A character count hint appears below the field.

**Fraud type helper (dropdown)**
Pre-fills the description with a template so the analyst isn't starting from a blank page.

| Template | Pre-fill |
|---|---|
| Mule Network | "layered mule account network with cross-border hops and burst withdrawal" |
| Synthetic Identity | "synthetic identity fraud using fabricated SSNs, slow credit-building phase, bust-out event" |
| Account Takeover | "account takeover via credential stuffing, small test transaction, rapid balance drain" |
| Card Testing | "card testing attack across multiple low-value merchants before large purchase" |

Selecting a template pre-fills the description but leaves it editable. The analyst can customize from the template rather than writing from scratch.

**Variant count (slider, 10–100, default 25)**
How many distinct fraud variants to generate. Each variant is a separate sub-agent run producing a complete transaction sequence.

Shows a real-time estimate that updates as the slider moves:

> *~25 variants · Est. $5.00 · Est. 4 min*

Why this matters: more variants = better coverage of the fraud space, but higher cost and longer wait. The estimate lets the analyst make an informed trade-off before hitting Run.

**Run button**
Primary action. Disabled states:
- Description empty or < 20 chars → tooltip: "Describe the fraud type to continue"
- Previous run results exist in session → modal: "You have results from a previous run. Load them or start a new run?" (Load / Overwrite)

---

### Phase 2: Tweak (Advanced Controls)

*Collapsible panel below the input section. Collapsed by default — the analyst opens this only if they want to steer generation beyond the defaults.*

**Fidelity level (tabs: 2 / 3 / 4)**
Controls how deeply sub-agents model fraudster behavior.

| Level | Label | What it does | Speed |
|---|---|---|---|
| 2 | Fast | Rule-based transaction structure, no persona | Fastest |
| 3 | Default | Persona-seeded transactions with behavioral backstory | Moderate |
| 4 | Deep | Full multi-agent roleplay — persona negotiates with mule, responds to friction | Slowest |

Each tab has a tooltip that shows this table. Why this matters: Level 4 produces the most realistic and structurally diverse variants, but costs 3–4× more than Level 2. For a quick exploratory run, Level 2 is fine. For production training data, Level 3 or 4 is recommended.

**Max parallel agents (slider, 1–10, default 5)**
How many sub-agents run simultaneously.

> *5 agents · Est. 4 min* → *10 agents · Est. 2 min (2× cost)*

Why this matters: parallelism is the main speed lever. Higher values finish faster but burn more API budget simultaneously. Default 5 balances speed and cost for a demo-sized run.

**Critic floor score (slider, 5–9, default 7)**
Minimum quality score a variant must achieve to be included in the output. Variants below this score get one revision pass; if they still fall short, they're dropped.

Why this matters: the analyst is trading quantity for quality. A floor of 5 lets more variants through (bigger dataset, some weak ones). A floor of 9 means only the most realistic variants survive (smaller, cleaner dataset). Default 7 is the recommended balance for training data.

**Persona risk distribution (three-way drag)**
Controls the mix of fraudster risk profiles in the generated personas.

```
Low ←——————→ Medium ←——————→ High
```

Why this matters: risk tolerance determines how aggressively the persona structures transactions — how much layering, how fast the extraction, how much evasion. A high-risk mix generates more aggressive fraud patterns; a low-risk mix generates slower, more patient fraud. The analyst chooses based on what they want the model to learn to detect.

**Geographic scope (multi-select)**
- Domestic only
- Cross-border
- SWIFT corridors

Why this matters: geography determines which transaction rails, regulatory thresholds, and reporting triggers are injected into the simulation. A mule network operating domestically looks different from one using SWIFT correspondent banking. Select all three to get variants that span jurisdictions.

**Mule context depth (dropdown)**
- Basic backstory — name, occupation, risk level
- Full persona — backstory + account history + behavioral quirks
- Deep cover story — full persona + fabricated employment records + plausible transaction history

Why this matters: deeper context makes the generated transaction sequences more internally consistent. A mule with a "deep cover story" will structure their transactions in ways that match their stated occupation and income level. This improves realism scores and makes the synthetic data harder for a model to reject as obviously fake.

**Auto second-pass (toggle, default off)**
After the first run completes, automatically inspect the coverage matrix. If any cells are underrepresented (fewer than 2 variants), trigger a targeted second pass to fill them.

Why this matters: coverage saturation is the goal. Without auto second-pass, the analyst has to manually inspect the matrix and re-run. With it on, the system self-corrects for gaps. Adds ~30–50% to total run time, so it's opt-in.

---

### Phase 3: Live Run

*What the analyst watches while the system runs. The UI transitions into monitoring mode when Run is clicked.*

**Progress bar + phase label**
Top of the screen. Single progress bar with a text label showing the current pipeline phase:

```
Generating personas… ████░░░░░░ 35%
```

Phases in order:
1. Generating personas
2. Building coverage matrix
3. Generating variants
4. Running critic
5. Compiling dataset

Why this matters: the analyst needs to know the system is working and roughly where it is. Without this, a 4-minute wait feels like a hang.

**Persona cards (live, streaming)**
As personas are generated, cards appear in a left-side feed:

```
┌─────────────────────────────┐
│ Marcus Okafor               │
│ Risk: High · Slot: V-07     │
│ "Former bank employee,      │
│  plausible internal access" │
└─────────────────────────────┘
```

Why this matters: persona cards are the most human-readable signal that the system is doing something interesting. They give the analyst (and a demo audience) a sense of the "cast" being assembled. Each card is a fraudster the system is about to simulate.

**Variant feed (live, streaming)**
Each variant appears as its sub-agent completes:

```
V-07  Marcus Okafor  4-hop · burst withdrawal · domestic
      Critic: 8.2 ●green
```

Critic score is color-coded: green (≥7), yellow (5–6.9), red (<5 → will be revised or dropped).

Why this matters: the analyst can see quality in real-time. If critic scores are consistently low, they can stop the run, adjust the fidelity level or description, and restart rather than waiting for the full run to complete with bad data.

**Coverage matrix (live, building)**
A grid where axes represent two key dimensions of the fraud variant space (e.g., hop count × timing pattern). Cells fill with color as variants cover them.

```
         Burst  Slow  Random
  2-hop  ████   ░░░░  ████
  3-hop  ████   ████  ░░░░
  5-hop  ░░░░   ░░░░  ░░░░
```

Empty cells (░) = unexplored territory. Filled cells (█) = covered.

Why this matters: this is the core value proposition made visible. The analyst can see the system systematically exploring the fraud space rather than clustering around the same pattern. For a demo, watching this grid fill is the "payoff moment."

**Agent status strip**
A row of N dots, one per configured parallel agent. Each dot shows status:
- ● Running (blue)
- ✓ Done (green)
- ↺ Retrying (orange)

Why this matters: shows the parallelism is actually happening, not just claimed. For a demo, seeing 5 agents simultaneously running makes the system feel like infrastructure, not a toy.

**Pause / Resume / Stop**
- **Pause** — suspends queued sub-agent starts; in-flight agents finish their current variant
- **Resume** — resumes the queue
- **Stop** — halts the run; results so far are kept and shown in Phase 4

Why this matters: if the analyst sees the variant feed producing off-target results (wrong channel, wrong geography), they can stop early rather than burning API budget on a bad run.

**Collapsible log**
Raw pipeline events: agent IDs, LLM call latencies, critic scores before/after revision. Collapsed by default.

Why this matters: the fraud analyst doesn't need this, but a technical stakeholder or developer watching the demo does. One click to expand.

---

### Phase 4: Results & Visualization

*Post-run state. The UI transitions here automatically when the run completes, or when the analyst clicks Stop.*

**Run summary header**
Large, prominent stats at the top:

```
47 variants generated  ·  Mean critic score 7.8  ·  68% coverage saturation  ·  Est. cost $4.20
```

Why this matters: this is the "did it work?" answer in one line. The analyst can tell immediately whether the run produced enough variants at sufficient quality.

**Final coverage matrix**
Same grid from Phase 3, now static. Interactions:
- **Hover a cell** — tooltip showing: which variants cover it, their critic scores, a sample transaction from one variant
- **Click a cell** — expands to show all variants covering that cell with full transaction sequence summaries

Why this matters: the matrix is how the analyst confirms diversity. If all 47 variants cluster in 3 cells, the run failed its primary goal regardless of critic scores.

**Network graph view**
3–4 transaction network graphs displayed side-by-side, one per representative variant (highest-scoring variant from distinct coverage matrix regions).

- Nodes = accounts
- Edges = transactions
- Node colors: originator (blue), mule (orange), extractor (red)
- Edge thickness = transaction amount

Why this matters: this is the most visually compelling view for a non-technical stakeholder. A graph of a 4-hop mule network is instantly legible as "fraud" in a way a table of transaction records is not. This is the demo centerpiece.

**Dataset browser**
Filterable table of all output records. Columns:

| Column | Description |
|---|---|
| variant_id | Which variant this record belongs to |
| persona_id | Which persona executed this transaction |
| transaction_id | Unique record ID |
| amount | Transaction amount |
| channel | ACH / wire / card / etc. |
| timestamp | Simulated datetime |
| hop_position | Position in the layering chain (1 = origin, N = extraction) |
| critic_score | Quality score for the parent variant |
| fraud_label | Always `1` for synthetic fraud data |

Filters: critic score range, channel, persona risk level. Analyst can spot-check rows to verify realism before exporting.

**Persona gallery**
Grid of persona cards (same format as Phase 3 cards), each showing:
- Name, risk profile, backstory
- List of variants assigned to this persona

Why this matters: the analyst can confirm the system generated a diverse cast, not just one persona type repeated across all variants.

**Critic score histogram**
Bar chart of score distribution across all variants (x-axis: score 1–10, y-axis: count).

Why this matters: the mean score is misleading if half the variants scored 9 and half scored 5. The distribution tells the analyst whether quality is consistent or bimodal.

**Variant comparison view**
Multi-select up to 3 variants. Shows them side-by-side:
- Key dimensions (hop count, timing, extraction method, channel)
- Transaction sequence summary (step-by-step)
- Critic notes (why the variant scored what it scored)

Why this matters: structural diversity is hard to see in a table. Side-by-side comparison lets the analyst confirm that V-07 and V-23 are genuinely different fraud patterns, not just different amounts on the same structure.

---

## Export / Send

*Always-visible bottom panel after the run completes.*

**Download CSV**
Full dataset, one row per transaction. All columns from the dataset browser. Ready to drop into a training pipeline.

**Download JSON**
Structured output with variant metadata and transactions nested under each variant. Format:

```json
{
  "run_id": "run_abc123",
  "variants": [
    {
      "variant_id": "V-07",
      "persona_id": "P-03",
      "critic_score": 8.2,
      "dimensions": { "hop_count": 4, "timing": "burst", ... },
      "transactions": [ { ... }, { ... } ]
    }
  ]
}
```

**Download run summary PDF** *(nice-to-have, not MVP)*
1-page PDF with: run stats, coverage matrix image, 3 network graph images, and a brief methodology note. For sharing with stakeholders who won't open a CSV.

**Copy shareable link**
If the app is hosted, generates a read-only URL for this run's results. Allows the analyst to share the full Phase 4 view with a colleague or manager without them needing an account.

**Send to pipeline**
Greyed out / disabled button. Tooltip: *"Connect your ML pipeline to enable this — ask your platform team about the API integration."*

Why it appears even when disabled: this button tells the story of where the product goes. A demo viewer who sees "Send to pipeline" immediately understands that the output is meant to flow into real infrastructure — not sit in a CSV on someone's desktop. The disabled state is intentional. It's a vision CTA, not a broken feature.

---

## Demo Mode

A quick-start path designed for a live demo with an audience. Accessible via:
- Prominent "Run Demo" button on the landing page
- Hidden URL flag: `?demo=true`

**Demo configuration (pre-set, not editable):**
- Description: *"layered 3-hop mule network, burst withdrawal, domestic only"*
- Variant count: 12
- Fidelity: Level 3
- Model: Claude Haiku (speed-optimized)
- Max parallel agents: 5

**Demo behavior:**
- Total run time: ~60 seconds
- Produces enough variants to show: coverage matrix with 8+ filled cells, 3 network graphs, a full persona gallery
- Critic scores intentionally varied (mix of green/yellow) so the quality-control story is visible
- After run completes, a banner appears: **"Try the real thing →"** with a CTA to start a full run with the analyst's own fraud type

**Why this matters for the demo:**
60 seconds is the window where a demo audience stays engaged. The demo mode is tuned to hit all four visual payoffs — persona cards streaming in, coverage matrix filling, network graphs appearing, dataset browser populating — within that window, using a description that's immediately legible to a non-fraud-expert audience ("3-hop mule network" is self-explanatory).

---

## Control Summary

| Control | Phase | Default | Why it exists |
|---|---|---|---|
| Fraud description | Input | — | Seeds the variant space |
| Fraud type helper | Input | None | Reduces blank-page friction |
| Variant count | Input | 25 | Trade-off: coverage vs. cost |
| Fidelity level | Tweak | 3 | Trade-off: realism vs. speed |
| Max parallel agents | Tweak | 5 | Trade-off: speed vs. API cost |
| Critic floor score | Tweak | 7 | Trade-off: quality vs. quantity |
| Persona risk distribution | Tweak | Balanced | Steer the fraudster behavior mix |
| Geographic scope | Tweak | Domestic | Affects rails and thresholds |
| Mule context depth | Tweak | Full persona | Affects internal consistency |
| Auto second-pass | Tweak | Off | Coverage gap self-correction |
