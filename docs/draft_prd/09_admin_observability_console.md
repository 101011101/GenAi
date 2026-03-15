> [!NOTE]
> **DRAFT** — This document describes the admin observability console planned for the web app version of FraudGen. Wireframes are in progress. Implementation follows the analyst console MVP.

# 09 — Admin Observability Console


**Audience:** Platform engineers, system administrators, pipeline operators
**Supplements:** `07_user_flow_and_console.md` (analyst-facing console) — this doc is the admin-facing counterpart
**Related:** `05_architecture_draft.md` (pipeline architecture), `06_api_and_console_draft.md` (analyst console spec), `08_execution_plan.md` (build plan)


---


## 1. Purpose & Audience


The admin console provides **deep pipeline observability** — full visibility into every agent's output, reasoning chain, quality outcomes, cost accumulation, and coverage decisions.


**Who uses this:**
- Platform engineers monitoring pipeline health and agent behavior
- System administrators tracking cost efficiency and resource usage
- Pipeline operators debugging quality issues or coverage gaps


**How it differs from the analyst console:**


| | Analyst Console | Admin Console |
|---|---|---|
| Focus | Results — what was generated | Process — how it was generated |
| Depth | Summary stats, dataset browser | Per-agent reasoning, per-step outputs |
| Controls | Run config, pause/stop | Read-only monitoring (no pipeline control) |
| Data | Approved variants only | All variants including rejected, revised, failed |
| Timing | Post-run review | Live during run + post-run forensics |


The analyst sees *what came out*. The admin sees *what happened inside*.


---


## 2. Design Philosophy


The console is organized around **6 views** (not one tab per pipeline stage). Each view answers a specific operational question with a single high-density "hero" visualization supported by reference tables. The goal is *fewer charts that each tell a richer story*, not a dashboard of disconnected metrics.


| View | Question it answers | Hero visualization |
|---|---|---|
| Mission Brief | What did the system plan? | Variant Space Sunburst |
| Coverage | How is execution progressing? | Status Grid with live transitions |
| Constructor | How was this fraud designed? | Money Trail + Heist Storyboard |
| Quality Gate | Did the output pass quality checks? | Quality Battlefield scatter |
| Operations | How did the run perform operationally? | Pipeline Waterfall |
| Journey | What happened to a specific variant? | Lifecycle timeline |


---


## 3. Per-View Specifications


---


### View 1 — Mission Brief


Merges orchestrator decomposition and persona generation into a single "setup" view. Both answer the same question: *what did the system decide to do before generation started?*


**Hero — Variant Space Sunburst (D3)**


A zoomable sunburst diagram showing the full dimensional variant space:


- **Inner ring** = primary dimension (e.g., hop_count: 2, 3, 4, 6)
- **Middle ring** = secondary dimension (e.g., topology: chain, fan_out, hybrid)
- **Outer ring** = tertiary dimension (e.g., timing: burst, staggered, delayed)
- **Leaf segments** = individual coverage cells, colored by assigned persona


One glance reveals: the full plan, dimensional balance, persona workload distribution, and any gaps in coverage. Clicking a segment drills down to show cell details (assigned persona, priority, dimension values). Hovering shows the exact cell ID and parameters.


This single visualization replaces the dimension distribution bar chart, persona allocation pie chart, and coverage cell plan grid — three disconnected charts merged into one interactive view.


**Supporting Data:**


**Variation Dimensions Table**
| Column | Description |
|---|---|
| Dimension name | e.g., "hop_count", "timing_pattern", "topology" |
| Possible values | Enumerated values extracted by the LLM |
| Value count | Number of distinct values per dimension |
| Source | Which part of the fraud description triggered this dimension |


**Persona "Wanted" Cards**


Instead of a flat roster table, each persona is displayed as a styled card resembling a threat profile:


- **Color bar** along the top edge indicating risk level (red = High, amber = Mid, green = Low)
- **Persona name** and ID prominently displayed
- **Key stats as badges:** geographic scope, mule network size, assigned cell count
- **Evasion targets** as inline tags
- **Specialization** as a subtitle


Cards are arranged in a horizontal row. Visual similarity between cards (same color bar, similar tags) immediately reveals when personas lack diversity. This is more scannable than a table and more memorable for a hackathon demo.


**Configured vs Actual Risk Distribution** — a small inline grouped bar (3 groups: High/Mid/Low, two bars each: configured % vs actual %) placed below the persona cards. Compact visual that highlights drift.


---


### View 2 — Coverage


The coverage matrix tracks which cells in the variant space have been assigned, are in progress, or are complete. This is the primary live monitoring view during a run.


**Hero — Coverage Status Grid (2D)**


A heatmap-style grid where:
- Rows = primary dimension (e.g., hop count)
- Columns = secondary dimension (e.g., timing pattern)
- Cell color indicates status: empty (gray), assigned (blue), in progress (yellow), completed (green), failed (red), reassigned (orange)


Each cell is large enough to display: assigned persona ID, current attempt number, and critic score (if completed) as a small badge. Failed cells have a pulsing CSS border animation to draw the eye.


Coverage saturation is shown as an inline stat at the top of the grid (e.g., "11/12 cells — 91.7%") with a colored indicator (green above threshold, red below). This replaces a separate gauge — the number itself is more useful than a circular dial.


**Live Transition Log**


A scrolling monospace feed showing status changes in real time:
```
[14:34:50] cell_001: assigned → in_progress (persona_03, attempt 1)
[14:34:58] cell_002: in_progress → completed (score: 8.1)
[14:35:30] cell_011: in_progress → failed (score: 5.8) → discarded
[14:35:31] cell_011: reassigned → persona_07 (auto second-pass)
```


---


### View 3 — Constructor (Per-Variant Deep Dive)


The fraud constructor is the core generation agent. Each variant goes through a 5-step reasoning chain. This is the deepest view in the console — the admin watches how a fraud scheme was designed.


**Variant Selector** — dropdown to choose any variant by ID, showing key parameters and pass/fail status.


**Hero — Heist Storyboard**


The 5-step reasoning chain is presented as a horizontal sequence of "scene" cards, read left-to-right like a crime narrative:


| Card | Icon | Narrative example |
|---|---|---|
| 1. Motive | Target icon | *"The criminal needs to move $50K through domestic channels before velocity triggers fire..."* |
| 2. Blueprint | Network icon | *"Plans a 3-hop chain topology with burst timing — all transfers within 4 hours..."* |
| 3. Crew | People icon | *"Recruits mule via social media, provides pre-loaded debit card..."* |
| 4. Execution | Clock icon | *"9:34 AM: $9,800 wire from business checking → mule savings..."* |
| 5. Cleanup | Shield icon | *"Self-review catches round-number pattern, adjusts final amounts..."* |


Each card shows a human-readable narrative summary (not raw JSON), plus small stat badges: token count, latency. Each card is expandable — clicking reveals the full raw JSON output for admins who want the detail.


This replaces the collapsible JSON panels. The storyboard is scannable at a glance; the raw data is one click away for those who need it.


**Hero — Money Trail (D3 force-directed graph with animated edges)**


A single combined visualization replacing both the network graph and Sankey diagram:


- **Nodes** = accounts, with distinct shapes per role: circle = source, diamond = mule, square = destination, triangle = cover account
- **Node color** indicates role: source = red, mule tiers = orange gradient (darker per hop), destination = dark red, cover = gray
- **Edges** = transactions, with thickness proportional to amount
- **Edge labels** show amount + timestamp
- **Animated edges** — CSS animated dashed stroke flowing in the direction of money transfer, making the flow direction immediately visible without needing a separate Sankey


The animation makes the money trail visually intuitive: you *see* funds flowing from source through mules to destination, with cover activity flowing in and out of legitimate accounts. Hover on any edge to see full transaction details.


**Attempt History Table**


For variants that went through revision loops:


| Attempt | Realism | Distinctiveness | Passed | Feedback summary |
|---|---|---|---|---|
| 1 | 4 | 7 | No | "Timing too uniform, no cover activity" |
| 2 | 6 | 7 | No | "Amounts are round numbers, unrealistic" |
| 3 | 8 | 7 | Yes | — |


---


### View 4 — Quality Gate


Merges schema validation and critic scoring into a single quality assessment view. Both are quality checkpoints — one automated (Python schema check), one AI-driven (critic agent). The admin's question is the same for both: *did the output pass?*


**Hero — Quality Battlefield (scatter plot with revision trails)**


Realism (x-axis) vs distinctiveness (y-axis) scatter plot, reimagined:


- **Pass zone** — a shaded green rectangle where both scores exceed the critic floor (e.g., 7.0). Subtle glow effect on the zone boundary.
- **Final scores** — solid dots positioned by their final realism/distinctiveness scores. Green = passed, red = failed.
- **Revision trails** — for variants that went through revision loops, ghost dots show previous attempt scores connected by thin lines to the final position. The trail shows the variant's *journey toward quality* — moving from the red zone into the green zone across attempts.
- **Hover** on any dot shows: variant ID, persona, attempt count, and critic feedback for failed attempts.


This single chart tells the complete quality story: overall score distribution, pass/fail ratio, how effective revision was, which variants struggled, and whether there are systematic quality problems (clustering in one quadrant).


**Supporting Data:**


**Pass/Fail/Revised Donut** — three segments: passed on first attempt, passed after revision, permanently failed. Shows how much rework the pipeline is doing.


**Quality Issues Table** — a unified table merging schema failures and critic feedback:


| Column | Description |
|---|---|
| Variant ID | Which variant was affected |
| Gate | Schema or Critic |
| Issue | Field path (schema) or feedback category (critic) |
| Detail | Failure type or full feedback text |
| Severity | Error (permanent fail) or Warning (revised and passed) |
| Resolution | Auto-corrected, revised, or discarded |


Sorted by severity then variant ID. Replaces the separate schema failure table and critic feedback bar chart — one unified view of all quality problems.


---


### View 5 — Operations


Merges run metrics, final output summary, and pipeline Gantt into a single operational health view. All answer: *how did the run perform?*


**Hero — Pipeline Waterfall (D3 horizontal bar chart)**


Inspired by CPU flame charts. Unlike the stage-level Gantt chart (which shows 7 bars), the waterfall operates at the **variant level**:


- **Each row** = one variant, labeled by ID
- **X-axis** = wall clock time from run start
- **Colored segments** within each row show which pipeline phase the variant is in at each moment: persona analysis (purple), network planning (blue), profiles (cyan), transaction generation (orange), self-review (yellow), schema validation (green), critic scoring (red)
- **Segment width** = duration of that phase for that variant
- **Vertical stacking** shows parallelism naturally — 5 variants running simultaneously appear as 5 active rows
- **Failed variants** end with a red marker; revised variants show a gap (wait time) then a second pass of segments


This single chart replaces **four separate charts**: the stage Gantt, progress-over-time line, active agent area chart, and phase duration stacked bar. It's far more information-dense — you see throughput, parallelism, bottlenecks, phase breakdowns, and failures all at once.


**Summary Metric Cards** (large number + label, 6 cards in a row):
- Total variants generated
- Mean realism score
- Mean distinctiveness score
- Coverage saturation %
- Total cost ($)
- Total run duration


**Cost Accumulation Sparkline** — a compact line chart showing cumulative cost over time with a horizontal dashed line at the cost cap threshold. Small but always visible.


**Error Log** — scrollable table:


| Column | Description |
|---|---|
| Timestamp | When the error occurred |
| Stage | Which pipeline stage |
| Variant ID | Which variant was affected |
| Severity | Error / Warning / Info |
| Message | Error description |
| Resolution | How the pipeline handled it (retry, discard, reassign) |


**Export Manifest** — table listing output files:


| File | Format | Size | Record Count | Description |
|---|---|---|---|---|
| `config.json` | JSON | ~2 KB | — | Run configuration snapshot |
| `personas.json` | JSON | ~15 KB | N personas | Full persona profiles |
| `variants.json` | JSON | ~500 KB | N variants | Complete variant data with metadata |
| `dataset.csv` | CSV | ~800 KB | M transactions | Flat tabular dataset for ML training |
| `dataset.json` | JSON | ~1.2 MB | M transactions | Nested dataset with variant metadata |
| `run_summary.json` | JSON | ~5 KB | — | Aggregate stats and quality metrics |


---


### View 6 — Variant Journey


Select any variant by ID and see its complete lifecycle as a vertical timeline:


```
variant_042
 ├── 00:00  Assigned to cell (hop_count=3, timing=burst, topology=chain)
 ├── 00:00  Persona: persona_03 ("Viktor Semenov")
 ├── 00:12  Constructor Step 1: Persona analysis (1,200 tokens, 3.2s)
 ├── 00:15  Constructor Step 2: Network planning (800 tokens, 2.1s)
 ├── 00:18  Constructor Step 3: Participant profiles (2,100 tokens, 5.4s)
 ├── 00:23  Constructor Step 4: Transaction generation (3,400 tokens, 8.7s)
 ├── 00:32  Constructor Step 5: Self-review (600 tokens, 1.8s)
 ├── 00:34  Schema validation: PASS
 ├── 00:34  Critic scoring: realism=4, distinctiveness=7 → FAIL
 │          Feedback: "Timing too uniform, no cover activity"
 ├── 00:35  Revision attempt 2
 ├── 00:47  Constructor (revised): 5 steps (4,800 tokens, 12.1s)
 ├── 00:47  Schema validation: PASS
 ├── 00:48  Critic scoring: realism=8, distinctiveness=7 → PASS
 └── 00:48  Final cost: $0.04 | Total tokens: 12,900 | Attempts: 2
```


Each node is expandable to show the raw LLM output for that step.


**Enhancements over a plain timeline:**
- **Inline score badges** — green/red pills at critic scoring nodes showing scores at a glance
- **Network thumbnail** — a tiny inline version of the money trail graph at the transaction generation node, linking to the full view in the Constructor tab
- **Running cost total** — each step node shows cumulative cost up to that point, making it visible where the money went


---


## 4. Layout


### Navigation


**Tab-based navigation** — one tab per view:


```
[ Mission Brief | Coverage | Constructor | Quality Gate | Operations | Journey ]
```


Active tab is highlighted. Each tab shows a **stage status chip** instead of a colored dot:
- Completed stages show duration (e.g., "4.2s")
- In-progress stages show an animated spinner
- Stages with errors show a red badge with error count


### Global Header


Persistent header bar visible across all tabs:


```
┌──────────────────────────────────────────────────────────────────────────┐
│  Run: run_20260314_143022  │  ● Healthy  │  ██████░░ 64%               │
│  Cost: $1.42 / $5.00 cap  │  Variants: 32/50  │  Elapsed: 4m 12s      │
└──────────────────────────────────────────────────────────────────────────┘
```


The **run health indicator** ("Healthy" / "Warning" / "Critical") is a single color-coded badge computed from: failure rate, cost burn rate, and coverage saturation. The admin's first glance answers: *"Do I need to worry?"*


Updates live during a run. After run completion, shows final values.


### Sidebar


Collapsible left sidebar showing the run configuration summary:


- Fraud description (truncated, expandable)
- Target variant count
- Fidelity level
- Max parallel agents
- Critic score floor
- Max revision iterations
- Persona count
- Risk distribution (H/M/L %)
- Geographic scope
- Auto second-pass: on/off


The sidebar is read-only — the admin cannot modify run config. Configuration changes happen in the analyst console.
