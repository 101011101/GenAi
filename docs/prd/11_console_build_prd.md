# 11 — Console Build PRD

**Status:** Implementation-ready spec
**Design sources** (all in `.superdesign/design_iterations/`):
- `ide_landing_clean_2.html` — **canonical theme/design system** (tokens, typography, spacing, component patterns)
- `ide_console_wireframes.html` — Input, Monitor (simple), Results screens layout
- `ide_monitor_trace.html` — Full live monitor (Execution Trace + Variant Detail) layout

The landing page is the style authority. The console wireframes define layout and component structure. Where they conflict, the landing page wins on visual style; the wireframes win on layout/interaction.

---

## 1. Overview

The FraudGen console is a single-page web application running at `localhost:8501` (Streamlit or equivalent). It provides three top-level screens navigated via a persistent left sidebar:

| Screen | Nav label | Purpose |
|---|---|---|
| Configure Run | New Run | Define fraud type, variant count, and run parameters |
| Live Monitor | Monitor | Watch agents execute in real time |
| Results | Results | Review generated variants, coverage, dataset, personas, and export |

---

## 2. Design Tokens

Defined in `ide_landing_clean_2.html` `:root`. Console wireframes extend this base with `surface2`, `purple`, `faint`, and agent colors.

### 2.1 Base tokens (from landing page — canonical)

```css
--bg:           #ffffff;   /* page background */
--surface:      #f8fafc;   /* panel/card/section background */
--border:       #e2e8f0;   /* all dividers and borders */
--accent:       #0f4c8a;   /* primary blue — CTAs, active states, charts, logo */
--accent-light: #e8f0fa;   /* blue tint for badges, active nav bg, chip bg */
--red:          #dc2626;   /* errors, fraud paths, failed states, high-risk */
--red-light:    #fef2f2;
--green:        #059669;   /* approved, passing scores, success */
--green-light:  #ecfdf5;
--yellow:       #d97706;   /* warnings, retries, cost, mid-risk */
--yellow-light: #fffbeb;
--text:         #0f172a;   /* primary text */
--muted:        #64748b;   /* secondary text, labels, descriptions */
--mono:         'JetBrains Mono', 'Fira Code', monospace;
--sans:         'Inter', system-ui, sans-serif;
```

### 2.2 Console extensions (added in wireframes)

```css
--surface2:      #f1f5f9;  /* deeper surface — input backgrounds, cell hover */
--purple:        #7c3aed;  /* placement role, crypto extraction nodes */
--purple-light:  #f5f3ff;
--faint:         #94a3b8;  /* timestamps, tertiary text, empty states */
```

### 2.3 Agent color palette

One color per agent slot (consistent across all views):

```
A1: #0f4c8a  (accent blue)     light: #e8f0fa   border: #bdd4ef
A2: #059669  (green)           light: #ecfdf5   border: #a7f3d0
A3: #7c3aed  (purple)          light: #f5f3ff   border: #ddd6fe
A4: #d97706  (yellow)          light: #fffbeb   border: #fde68a
A5: #dc2626  (red)             light: #fef2f2   border: #fecaca
```

### 2.4 Border radius scale

```
4px   — tags, small labels (section-tag, hero-label, role badges)
6px   — nav CTAs, small buttons, filter chips, url-bar, code blocks
7px   — monitor controls
8px   — primary/outline buttons, inputs, stat boxes, agent cards, step cards
9–10px — variant cards, persona cards, export rows
12px  — pipeline steps
16px  — prominent cards (matrix card, hero visual card)
```

### 2.5 Shadow

Elevated cards (matrix card, hero visual): `box-shadow: 0 20px 50px rgba(0,0,0,0.08)`
All other surfaces: no shadow — borders only.

### 2.6 Typography scale

```
Logo:          0.875–1.2rem, weight 800, accent color, letter-spacing -0.02em
Hero h1:       clamp(2rem, 3.5vw, 3rem), weight 800, letter-spacing -0.03em
Section h2:    clamp(1.75rem, 3vw, 2.5rem), weight 800, letter-spacing -0.02em
Section tag:   0.7rem, weight 700, uppercase, letter-spacing 0.1em, accent-light bg
Body copy:     0.875rem–0.95rem, muted color, line-height 1.6–1.7
UI labels:     0.72–0.78rem, weight 600
Mono values:   0.62–0.75rem, var(--mono)
Stat number:   1.4–1.6rem, weight 800, accent color
```

### 2.7 Component patterns (from landing page)

**Section tag / hero label:**
```css
background: var(--accent-light); color: var(--accent);
font-size: 0.7rem; font-weight: 700; letter-spacing: 0.1em; text-transform: uppercase;
padding: 0.3rem 0.75rem; border-radius: 4px;
```

**Primary button:**
```css
background: var(--accent); color: #fff; font-weight: 700;
padding: 0.8rem 1.75rem; border-radius: 8px; font-size: 0.9rem;
```

**Outline button:**
```css
border: 1.5px solid var(--border); color: var(--text);
padding: 0.8rem 1.75rem; border-radius: 8px; font-size: 0.9rem; font-weight: 500;
```

**Sticky nav:**
```css
position: sticky; top: 0; background: rgba(255,255,255,0.96);
backdrop-filter: blur(8px); z-index: 99;
```

**Pulse animation (live indicators, in-progress cells):**
```css
@keyframes pulse { 0%,100%{opacity:1;} 50%{opacity:0.3;} }
/* duration: 1.5–1.8s ease-in-out infinite */
```

---

## 3. App Shell

### 3.1 Browser Chrome

Wrap the entire app in a simulated browser chrome:

```
┌ ● ● ●  [url-bar: localhost:8501 · run_id · status]          ┐
│                                                               │
│   [sidebar 200px] │ [main content area flex-1]              │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

The URL bar updates dynamically: `localhost:8501` on the input screen, `localhost:8501 · run_20260315_142201` on monitor, `localhost:8501 · run_20260315_142201 · complete` on results.

### 3.2 Left Sidebar (200px, persistent)

```
FraudGen                        ← Logo: bold, accent color

  New Run                       ← nav item
  Monitor                       ← nav item
  Results                       ← nav item

  HISTORY                       ← section label

  [run history entries]

  ──────────────────────
  Mode: Live
  Model: Sonnet
```

Nav items:
- Default: muted text, transparent bg
- Hover: surface2 bg
- Active: accent-light bg, accent text, bold

The sidebar footer shows persistent global state. During a run, the Monitor nav item sidebar footer switches to show live stats:
```
  LIVE STATS
  Approved: 18 (green)
  Rejected: 1  (red)
  Revising: 1  (yellow)

  AGENTS (5)
  [5 colored dots: done=green, running=blue pulse, retry=yellow]

  ──────────────────────
  Cost: $2.14 (yellow)
  Time: 3m 22s

  [⏸ Pause]  [⏹ Stop]
```

---

## 4. Screen 1 — Configure Run

**Route/State:** `screen = "input"`

### 4.1 Top Bar

```
Configure Run
Describe a fraud type to generate synthetic variants across the full attack space
```

### 4.2 Content Layout

**Fraud type + pre-fill row** (2-column grid)

Left: `Fraud type` dropdown with options:
- Mule Account Network
- Card Skimming Ring
- Business Email Compromise
- Account Takeover

Right: `Pre-fill template` ghost button — populates the description textarea with a default description for the selected type.

---

**Fraud description textarea**

Label: `Fraud description` + inline hint `required · min 20 chars` (accent, light weight)

Textarea: 88px height, placeholder text explaining the fraud in plain English.

Field hint below: "The richer and more specific this description, the more targeted the variant space the system will explore."

Run button is **disabled** until textarea has ≥ 20 characters.

---

**Variant count slider**

Row: `Variant count` label + `[number]` (accent monospace, live-updates) + `· Est. $X.XX · Est. N min` (muted, live-updates)

Slider: range 10–100, default 25. Labels "10" and "100" below. Accent-colored thumb.

Cost formula: `$0.20 × count`. Time formula: `count × 9.6s`.

---

**Divider**

---

**Advanced controls** (collapsible, collapsed by default)

Toggle header: `Advanced controls ▸ expand / ▾ collapse`

When expanded, shows an `adv-box` (surface bg, border, border-radius) with two rows of 3 fields each:

Row 1:
- `Fidelity level` — segmented toggle: L2 | **L3** (active) | L4 (disabled)
- `Max parallel agents` — number input, default `5`
- `Critic score floor` — number input, default `7.0`

Row 2:
- `Persona count` — number input, default `5`
- `Risk distribution` — dropdown: Balanced | High-skew | Low-skew
- `Geographic scope` — dropdown: Domestic | International | Mixed

---

**Action row**

```
[▶ Run]  [Save config]
```

- Run: primary (accent bg) — disabled until description filled
- Save config: outline

---

## 5. Screen 2 — Live Monitor

**Route/State:** `screen = "monitor"`

This screen uses a **full-width 3-column layout** with its own top bar. The sidebar is visible but shows the live stats version described in §3.2.

### 5.1 Monitor Top Bar

```
run_20260315_142201            18 / 25  [=====>    ] 72%   $2.14●  3m 22s
Mule Account Network · 25 variants · L3 · 5 agents

Approved: 18  ·  Retry: 1  ·  Failed: 1          [⏸ Pause]  [⏹ Stop]
```

Components:
- `run-title`: bold mono, run ID
- `run-sub`: muted, fraud type · variant count · fidelity · agent count
- Progress: `18 / 25` label + 120px progress track + `72%`
- Cost ticker: mono, yellow, pulse animation
- Time ticker: mono, muted
- Status summary: approved (green), retry (yellow), failed (red)
- Controls: Pause (ghost), Stop (danger)

Pause toggles all pulse animations via `animation-paused` class on body. Stop shows a confirmation before halting.

### 5.2 Three-Column Body

```
[Left 240px] | [Center flex-1] | [Right 220px]
```

---

#### Left Panel — Agent Fleet

Header: `AGENT FLEET` + `● Live` (green, pulse)

Scrollable list of agent cards. One card per active agent (up to `max_parallel_agents`).

**Agent Card anatomy:**

```
┌─────────────────────────────────┐
│ [A1●] ● V-006          ● running│
│ Viktor Sokolov · 3-hop chain    │
│ Step 2/4: Persona assignment    │
│ 1,840 tok · $0.21               │
│ [████████░░░░░░░░░░░░] 50%      │
└─────────────────────────────────┘
```

- `agent-pill`: colored badge with agent ID (A1 = blue, A2 = green, A3 = purple, A4 = yellow, A5 = red)
- `status-dot`: 7px circle, color matches status (run=blue pulse, done=green, retry=yellow, idle=gray)
- `variant-id`: mono bold, e.g. "V-006"
- Status badge top-right: `● running` (blue) / `✓ done` (green) / `↺ retry 1/2` (yellow)
- `agent-persona`: persona name + variant summary
- `agent-step`: `Step N/4: [step name]` — with optional red score annotation if failed
- `agent-tokens`: token count + cost (mono, faint)
- Mini progress bar: 3px height, fill color matches agent color

Clicking a card filters the Execution Trace (center) to show only that agent's entries.

Footer: `Active 4  Done 18  Retry 1`

---

#### Center Panel — Execution Trace / Variant Detail

Two tabs: **Execution Trace** (default) | **Variant Detail**

##### Tab A: Execution Trace

Toolbar: filter chips `All` | `Done` | `Running` | `Error / Retry` + optional `Agent filter ✕` chip (appears when agent card is clicked) + count `15 entries` (right-aligned, mono)

Scrollable list. Grouped by variant:

**Variant group header:**
```
V-003   Maria Chen · A3              ↺ retry 1/2    ▼
```
- Clicking collapses/expands the group's entries
- Group badge matches overall status

**Trace entry (within a group):**
```
12:45:22  [A3]  Step 3 — Transaction Synthesis [attempt 1]     ✕ 4.2  ▶
                Critic rejected — amount floor violation, timing too tight
```

Columns:
- Timestamp: mono, faint, `HH:MM:SS`, fixed width
- Agent badge: colored to match agent (`bg: agent-light, border: agent-light-border, color: agent`)
- Body: step title (bold) + description (muted, below)
- Right: status/score badge + expand toggle `▶`/`▼`

Left border of each row colored to match agent (3px, solid).

Clicking a row expands an **inline detail block** below it:

```
┌──────────────────────────────────────────────────────────┐
│ CRITIC FEEDBACK                                          │
│                                                          │
│ "critic_score": 4.2                                     │
│ "failures": [                                            │
│   "TXN-003: $9,800 exceeds ACH same-day floor $7,500",  │
│   "timing spread 4 min — too tight for 2-hop chain"     │
│ ]                                                        │
│ "action": "retry with corrected constraints"            │
└──────────────────────────────────────────────────────────┘
```

The code block uses a dark-mode style (`bg: #0f172a`, syntax highlighting: keys=`#7dd3fc`, values=`#86efac`, strings=`#fde68a`, numbers=`#c084fc`).

##### Tab B: Variant Detail

Toolbar: `Variant [dropdown selector]` + summary `4 steps · 4,120 tok · $0.47` + status badge

The dropdown lists all variants with their status: `V-001 — Viktor · 3-hop chain · ✓ 8.4`.

Scrollable list of **step cards** (one per pipeline step):

**Step card anatomy:**
```
┌───────────────────────────────────────────────────────────┐
│ ① Orchestrator Decomposition                 ✓ done · 310 tok  ▼ │
│   Variant axes selected — defines the attack shape            │
├───────────────────────────────────────────────────────────┤
│ [Expanded body]                                            │
└───────────────────────────────────────────────────────────┘
```

- Step number circle: blue bg, white text, 22px
- Title: bold, 0.78rem
- Subtitle: muted description
- Right: token badge + expand toggle
- Click header to toggle body

**Step 1 — Orchestrator Decomposition**
Body: short prose description + dark-mode JSON code block showing variant axes.

**Step 2 — Persona Assignment**
Body: persona avatar (initials) + name + risk badge + description. Below: code block showing match score and assignment.

**Step 3 — Transaction Sequence Generation**
Body: mini transaction table (columns: txn_id, timestamp, amount, channel, is_fraud, role). Roles color-coded: placement=purple, hop_N_of_M=blue, extraction=red, cover_activity=faint. Below table: summary `$X in → $Y extracted · Z% wash · cover ratio W ✓`.

**Step 4 — Critic Evaluation**
Body: horizontal score bars for each dimension (Realism, Diversity, Evasion quality, Completeness, Overall). Each row: label (96px fixed) + track + fill bar + numeric value. Fill color: accent for individual dims, green for overall. Below bars: critic note in a green-tinted box if approved, red-tinted if failed.

---

#### Right Panel — Live Metrics

Fixed 220px. Scrollable. Divided into sections by borders.

**Section 1: Critic scores — last 12**

Sparkline bar chart. 12 bars, each proportional to score (0–10 scale). Bar color:
- Accent-light (default)
- Yellow-light if score 7.0–7.5
- Green-light if score ≥ 8.5

Hover on bar shows a tooltip with exact score.

Below bars: `[first score]    avg X.X    [last score]`

Stats row: `Floor: 7.0  Best: X.X  Fails: N`

**Section 2: Token burn by agent**

Horizontal bar per agent (A1–A5). Bar color matches agent color. Right-aligned token count. Separator line + total below.

**Section 3: Coverage matrix — N%**

Mini version of the coverage grid. Small cells (14px height), no labels. Same color states as main grid: green/blue/yellow/red/gray. Below: legend row.

---

## 6. Screen 3 — Results

**Route/State:** `screen = "results"`

### 6.1 Sidebar — Results mode

Shows run summary section:
```
RUN SUMMARY
Variants: 23 / 25 (green)
Score:    8.1 / 10 (green)
Coverage: 82% (green)
Transactions: 2,140
Cost: $4.21 (yellow)
Runtime: 6m 12s
```

When Dataset tab is active, the run summary is replaced by:
```
QUICK FILTER
  All roles
  placement (active, purple)
  hop_N_of_M
  extraction
  cover_activity
```

And the footer shows dataset stats:
```
2,140 total rows
312 fraud txns (red)
1,828 cover txns
```

Footer always shows `[+ New run]` primary button.

### 6.2 Tab Bar

```
[ Coverage | Network Graphs | Dataset | Personas | Export ]
```

---

### Tab: Coverage

**Summary banner** (green-tinted):
`Run complete · 23 variants approved · Mean score 8.1 / 10 · Coverage 82% · 5 personas · 2,140 transactions`

**Stat cards row** (5 cards):
| Variants | Coverage | Avg Score | Transactions | API Cost |
|---|---|---|---|---|
| 23 | 82% | 8.1 | 2,140 | $4.21 |

Cards: surface bg, accent value (large mono), muted uppercase label.

**Coverage Matrix**

Label: `Fraud variant space — hover any cell to see covering variants`

8-column heatmap grid. Each cell label shows encoded dimension values (e.g., `3h·ch·sd` = 3-hop, chain, same-day). Cell states:
- `mx-green` — approved (green-light bg, green border)
- `mx-yellow` — revised & approved (yellow-light bg)
- `mx-red` — failed all attempts (red-light bg, pulsing border)
- `mx-gray` — uncovered (surface2 bg)

Legend below: Approved / Revised & approved / Failed all attempts / Uncovered

Field hint: `Axes: hop count × topology × timing · click any cell to see which variants cover it`

---

### Tab: Network Graphs

Toolbar row: `Showing N variants` + `Compare any two...` dropdown

3-column grid of network graph cards. Each card:
- Header: `V-001 · 3-hop chain`
- Sub: `Viktor · same-day · ACH→Zelle→wire`
- Graph box: 190px height, surface bg

Graph renders as SVG with positioned div nodes overlaid:

Node types:
- `g-fraud` (red-light bg, red border): SRC and hop accounts (M1, M2…)
- `g-extract` (purple-light bg, purple border): DST / crypto extraction node
- `g-cover` (surface2 bg, border): cover activity accounts

SVG edges: red solid lines with arrowhead markers for fraud flow; gray dashed lines for cover activity.

Below each graph: `N txns · $X → $Y · [description] · critic N.N`

Legend row at bottom: `● Fraud path  ● Crypto extraction  ● Cover activity`
Right-aligned note: `Structurally diverse — not statistical noise around the same pattern`

---

### Tab: Dataset

**Filter bar:**
- Chips: `Persona: All ▼` | `Role: [role] ▼` | `is_fraud: All ▼` | `Score ≥ 7 ▼` | `Variant ▼`
- Right: `Showing N of 2,140 rows`

Active chips: accent-light bg (or role-specific color: purple for placement).

**Transaction table:**

Columns: `transaction_id`, `timestamp`, `amount`, `channel`, `is_fraud`, `fraud_role`, `variant_id`, `persona`, `hop_count`, `critic_score`

Formatting:
- `fraud_role`: colored mono by role — `placement` purple, `hop_N_of_M` blue, `extraction` red, `cover_activity` faint
- `is_fraud`: True=red bold, False=faint
- `variant_id`: mono, accent
- `amount`: mono, bold
- `critic_score`: green if ≥ 7
- Alternating row shading (bg / surface)
- Hover: surface bg on all cells in row
- Ellipsis row at bottom: `· · · N more rows · · ·`

**Role legend:**
```
■ placement — first account receives funds
■ hop_N_of_M — layering
■ extraction — final cashout
■ cover_activity — is_fraud = False
```

---

### Tab: Personas

Heading: `Criminal personas — N generated`

3-column grid of persona cards:

**Persona card:**
```
┌───────────────────────────────┐
│ [VS]  Viktor Sokolov          │
│       ● High risk             │
│                               │
│ International routing · crypto│
│ -capable · speed-first ·      │
│ Eastern European network      │
└───────────────────────────────┘
```

- Avatar: 32px circle with initials, bg/border matches risk level (red=high, green=low, yellow=mid)
- Risk badge: colored pill (badge-red, badge-green, badge-yellow)
- Description: muted, small, line-height 1.6

---

### Tab: Export

File manifest. Each file as a row:

```
┌──────────────────────────────────────────────────────────┐
│ dataset.csv                              [↓ Download]    │
│ Flat tabular dataset for ML training                     │
│ ~800 KB · 2,140 records                                  │
└──────────────────────────────────────────────────────────┘
```

Files:
| File | Format | Size | Records | Description |
|---|---|---|---|---|
| `config.json` | JSON | ~2 KB | — | Run configuration snapshot |
| `personas.json` | JSON | ~15 KB | 5 personas | Full persona profiles |
| `variants.json` | JSON | ~500 KB | 23 variants | Complete variant data with metadata |
| `dataset.csv` | CSV | ~800 KB | 2,140 txns | Flat tabular dataset for ML training |
| `dataset.json` | JSON | ~1.2 MB | 2,140 txns | Nested dataset with variant metadata |
| `run_summary.json` | JSON | ~5 KB | — | Aggregate stats and quality metrics |

---

## 7. State Management

The app transitions through these states:

```
idle → configuring → running → complete
                ↓
            error (run failed entirely)
```

### Run state object

```json
{
  "run_id": "run_20260315_142201",
  "status": "running",              // idle | running | complete | error
  "fraud_type": "Mule Account Network",
  "fraud_description": "...",
  "config": {
    "variant_count": 25,
    "fidelity": "L3",
    "max_parallel": 5,
    "critic_floor": 7.0,
    "persona_count": 5,
    "risk_distribution": "balanced",
    "geographic_scope": "domestic"
  },
  "progress": {
    "total": 25,
    "approved": 18,
    "rejected": 1,
    "retry": 1,
    "pending": 5
  },
  "cost_usd": 2.14,
  "elapsed_seconds": 202,
  "agents": [...],
  "variants": [...],
  "personas": [...],
  "trace": [...]
}
```

### Agent object

```json
{
  "agent_id": "A3",
  "color": "#7c3aed",
  "status": "retry",                // idle | running | retry | done | error
  "current_variant": "V-003",
  "current_step": 3,
  "total_steps": 4,
  "step_name": "Transaction Synthesis",
  "attempt": 1,
  "max_attempts": 2,
  "persona_name": "Maria Chen",
  "variant_summary": "burst timing",
  "tokens_used": 3210,
  "cost_usd": 0.37,
  "last_score": 4.2
}
```

### Variant object

```json
{
  "variant_id": "V-001",
  "status": "approved",             // pending | running | retry | approved | failed
  "axes": {
    "hop_count": 3,
    "topology": "chain",
    "timing_mode": "same_day",
    "channel_seq": ["ACH", "Zelle", "wire"],
    "evasion": "cover_activity",
    "cover_ratio": 0.40
  },
  "persona": {
    "id": "viktor_sokolov_001",
    "name": "Viktor Sokolov",
    "risk": "high",
    "description": "International routing · crypto-capable · speed-first"
  },
  "attempts": [
    {
      "attempt": 1,
      "steps": [
        { "step": 1, "name": "Orchestrator Decomposition", "tokens": 310, "latency_ms": 1200, "output": {...} },
        { "step": 2, "name": "Persona Assignment", "tokens": 480, "latency_ms": 1800, "output": {...} },
        { "step": 3, "name": "Transaction Generation", "tokens": 1820, "latency_ms": 7400, "output": {...} },
        { "step": 4, "name": "Critic Evaluation", "tokens": 1510, "latency_ms": 4100, "output": {...} }
      ],
      "critic_scores": {
        "realism": 8.2,
        "diversity": 9.0,
        "evasion": 8.1,
        "completeness": 8.3,
        "overall": 8.4
      },
      "approved": true
    }
  ],
  "transactions": [
    {
      "txn_id": "TXN-0041",
      "timestamp": "2026-03-10T09:14:02",
      "amount": 4800.00,
      "channel": "ACH",
      "is_fraud": true,
      "fraud_role": "placement"
    }
  ],
  "final_score": 8.4,
  "total_tokens": 4120,
  "total_cost_usd": 0.47
}
```

### Trace event object

```json
{
  "event_id": "evt_012",
  "ts": "12:45:22",
  "agent_id": "A3",
  "variant_id": "V-003",
  "step": 3,
  "step_name": "Transaction Synthesis",
  "attempt": 1,
  "status": "error",               // running | done | error
  "description": "Critic rejected — amount floor violation",
  "score": 4.2,
  "detail": {
    "type": "critic_feedback",
    "content": {...}
  }
}
```

---

## 8. Data Flow

```
[User submits config]
        ↓
[POST /api/run] → returns run_id
        ↓
[GET /api/run/{id}/stream] — SSE stream
        ↓
Console subscribes to SSE events:
  - agent_update: update left panel agent card
  - trace_event:  append to execution trace
  - variant_complete: update coverage matrix + variant feed
  - run_complete: switch to results screen, populate all tabs
```

### SSE event types

```json
{ "type": "agent_update", "agent": {...} }
{ "type": "trace_event",  "event": {...} }
{ "type": "variant_complete", "variant": {...} }
{ "type": "cost_update",  "cost_usd": 2.14, "elapsed": 202 }
{ "type": "run_complete", "summary": {...} }
{ "type": "run_error",    "message": "..." }
```

---

## 9. API Audit

All APIs are in `api/main.py`. The pipeline runs in `app/`. Output files are written by `app/pipeline/output_handler.py`.

### 9.1 Built and working ✅

| Endpoint | What it returns | Console use |
|---|---|---|
| `POST /api/runs` | `{run_id}` | Input panel → Run button |
| `GET /api/runs/{id}/status` | Snapshot + last 50 `event_log` strings + `variant_log` + `coverage_cells` | Polling fallback for monitor |
| `POST /api/runs/{id}/control` | `{ok, signal}` — accepts `"pause"`, `"run"`, `"stop"` | Pause/Resume/Stop buttons |
| `GET /api/runs/{id}/matrix` | Dimension definitions + per-cell status objects | Coverage matrix (Results tab) |
| `GET /api/runs/{id}/personas` | List of persona objects | Personas tab |
| `GET /api/runs/{id}/results` | Variants list + aggregate stats (mean_realism, mean_distinctiveness, coverage_pct, total_transactions) | Results stats + Coverage banner |
| `GET /api/runs/{id}/dataset` | Paginated rows from `dataset.csv` (`page`, `page_size` params) | Dataset tab |
| `GET /api/runs/{id}/export/{format}` | File download — formats: `csv`, `json`, `graph`, `summary` | Export tab (partial) |

Output files written to disk per run (all 6 exist):
`config.json`, `personas.json`, `variants.json`, `dataset.csv`, `dataset.json`, `run_summary.json`

---

### 9.2 Stubs — endpoint exists, returns empty ⚠️

| Endpoint | Current state | Console need |
|---|---|---|
| `GET /api/runs/{id}/trace/{variant_id}` | Returns `{"steps": [], "note": "trace not yet implemented"}` | Variant Detail tab — step cards |
| `GET /api/runs/{id}/operations` | Returns `{"cost_timeline": [], "errors": [], "note": "operations not yet implemented"}` | Not directly needed by wireframe console but referenced in PRD §8 |

---

### 9.3 Missing — not built ❌

> **Key insight:** `trace_pipeline.py` is already the reference implementation for everything in this section. Every gap below is solved there — it prints the exact data to terminal that the API needs to return. The work is purely **re-routing** those outputs from `print()` calls into `RunState` fields, then surfacing them via HTTP. No new LLM calls, no new business logic.

#### A. SSE stream `GET /api/runs/{id}/stream`

The PRD's data flow (§8) requires a Server-Sent Events stream pushing typed events to the browser. Currently the only live update mechanism is polling `/status` every N seconds.

**What the console needs:**
```json
{ "type": "agent_update",      "agent": { agent_id, status, current_variant, current_step, step_name, attempt, persona_name, tokens_used, cost_usd, last_score } }
{ "type": "trace_event",       "event": { event_id, ts, agent_id, variant_id, step, step_name, attempt, status, description, score, detail } }
{ "type": "variant_complete",  "variant": { variant_id, status, score, persona_name, parameters_summary } }
{ "type": "cost_update",       "cost_usd": 2.14, "elapsed": 202 }
{ "type": "run_complete",      "summary": { ... } }
{ "type": "run_error",         "message": "..." }
```

**trace_pipeline.py equivalent:** Every print statement in `main()` is an SSE event. `_ok(f"Critic: PASS score={avg}")` → `trace_event`. `_section("STAGE 3...")` → `agent_update`. The SSE endpoint is just a loop that reads from `RunState` and emits whatever has been added since the last poll.

**Workaround (no SSE):** Poll `/status` every 1–2 seconds. `event_log` gives a text feed, `variant_log` gives variant completion events, `coverage_cells` gives matrix state. This is enough for a functional console without the real-time trace.

---

#### B. Per-agent state tracking

The Agent Fleet left panel (§5.2) needs per-agent cards showing: current variant, current step, persona, token count, cost, attempt. `RunState` tracks none of this — only `active_agent_count`.

**trace_pipeline.py equivalent:** The `_section(f"STAGE 3 / 4 — FraudConstructorAgent [{cell_id}]")` header and the `_info(f"Persona: {persona.name}")` line together are exactly one `AgentStatus` entry. In the tracer, cells run serially so there's only ever one "active agent" printed at a time; in the parallel runner the same data exists per-cell but isn't collected.

**What needs to be added to `RunState`:**
```python
@dataclass
class AgentStatus:
    agent_id: str           # "A1"–"A5" (slot index, assigned in runner)
    cell_id: str
    variant_id: str
    persona_name: str
    status: str             # "running" | "retry" | "done" | "idle"
    current_step: int       # 1–4
    total_steps: int        # 4
    step_name: str
    attempt: int
    max_attempts: int
    tokens_used: int
    cost_usd: float
    last_score: float | None

# add to RunState:
self.agent_slots: dict[str, AgentStatus] = {}  # agent_id → AgentStatus
```

`_process_cell` in `runner.py` writes to this the same way the trace pipeline writes to terminal at each step boundary.

---

#### C. Structured trace data

The Execution Trace tab (§5.2) needs structured events. The current `event_log` strings look like:
```
[12:45:22] V-003: Critic FAIL score=4.2 — amount floor violation, timing too tight
```

**trace_pipeline.py equivalent:** This is exactly what the tracer prints — `_err(f"Variant {scored.variant_id} rejected by critic.")` + `_info(f"Feedback: {scored.feedback[:200]}")`. The tracer also prints the full `_dump(raw_variant)` (raw JSON output per step) via `_section("STAGE 3.5 — Labeling Stage")` etc. All of it is structured data that's been pretty-printed to terminal.

The `on_step` callback passed to `FraudConstructorAgent().run()` already fires at each step boundary with a label string (see `make_on_step()` in the tracer). The runner already passes an `on_step` lambda to `constructor.run()` that calls `run_state.log_event()`. Changing that lambda to emit a structured `TraceEvent` instead of a plain string is the entire change needed.

**What needs to be added to `RunState`:**
```python
@dataclass
class TraceEvent:
    event_id: str
    ts: str
    agent_id: str
    variant_id: str
    step: int
    step_name: str
    attempt: int
    status: str       # "running" | "done" | "error"
    description: str
    score: float | None
    detail: dict | None   # e.g. critic JSON, step output JSON

# add to RunState:
self.trace_events: list[TraceEvent] = []

def add_trace_event(self, event: TraceEvent) -> None:
    with self._lock:
        self.trace_events.append(event)
        if len(self.trace_events) > 500:
            self.trace_events = self.trace_events[-500:]
```

New endpoint `GET /api/runs/{id}/trace` returns the list, filtered by `?variant_id=` or `?agent_id=`.

---

#### D. Variant detail step breakdown

The Variant Detail tab (§5.2) needs per-step token counts, latencies, and raw output JSON per attempt.

**trace_pipeline.py equivalent:** This is `_dump(raw_variant)` and `_dump(orchestrator_output.__dict__)` — the tracer already pretty-prints the full JSON for every step output. The `make_on_step()` callback receives the label `"Step 3 — Transaction generation — done (8.7s)"`, and the tracer shows the full scored variant dump after the critic.

`ScoredVariant` currently has `realism_score`, `distinctiveness_score`, `passed`, `feedback`, `transactions`, `variant_parameters`, `strategy_description` — no per-step data. The step outputs and timings already flow through the `on_step` callback; they just need to be captured into `TraceEvent.detail` (§C above) rather than printed. The Variant Detail tab can then reconstruct step cards by filtering `trace_events` by `variant_id`.

---

#### E. Dataset filtering

`GET /api/runs/{id}/dataset` supports pagination only. The PRD's Dataset tab filter chips need:

```
GET /api/runs/{id}/dataset
  ?persona=Viktor+Sokolov
  &role=placement
  &is_fraud=true
  &min_score=7.0
  &variant_id=V-A3F7B2
  &page=1
  &page_size=100
```

Implementation: read the CSV into a DataFrame, apply filters, paginate.

---

#### F. Export manifest `GET /api/runs/{id}/export`

The Export tab (§6.2) needs to list all available files with sizes and record counts before downloading. Currently only individual file downloads exist via `/export/{format}`.

Also, the export endpoint only supports 4 formats (`csv`, `json`, `graph`, `summary`). The PRD's Export tab lists 6 files. Missing from the download endpoint:
- `config.json` → add format `"config"`
- `personas.json` → add format `"personas"`
- `variants.json` → add format `"variants"`

All three files are already written to disk by `OutputHandler` — just need to be added to `_EXPORT_FILES`.

---

#### G. Run history `GET /api/runs`

The sidebar shows run history. No list endpoint exists. The in-memory `_runs` dict in `api/main.py` already holds all runs for the process lifetime — just needs a list endpoint:

```
GET /api/runs
→ [{ run_id, fraud_description, status, variants_total, is_complete, total_cost_usd, elapsed_s }]
```

---

### 9.4 Gap summary

| # | Gap | Severity | trace_pipeline.py analogue | Workaround |
|---|---|---|---|---|
| A | SSE stream | High | Every `print()` in `main()` is an SSE event | Poll `/status` at 1–2s |
| B | Per-agent state in `RunState` | High | `_section("STAGE 3... [{cell_id}]")` + `_info("Persona: ...")` per cell | Partial — parse `event_log` text |
| C | Structured `TraceEvent` in `RunState` | High | `on_step` callback + `_ok`/`_err` calls at each step | Partial — parse `event_log` text |
| D | Variant detail step breakdown | Medium | `_dump(raw_variant)` + `_dump(orchestrator_output)` per step | Reconstruct from trace events (§C) |
| E | Dataset filtering | Medium | Not in trace pipeline — CSV post-processing | No shortcut |
| F | Export manifest + 3 missing formats | Low | `config.json`, `personas.json`, `variants.json` already on disk | Link to known file paths |
| G | Run history list | Low | Not in trace pipeline | `_runs` dict already in memory |

**Implementation pattern for B, C, D:** In `runner.py`'s `_process_cell`, replace each `run_state.log_event(f"...")` string with a `run_state.add_trace_event(TraceEvent(...))` call. The trace pipeline already shows exactly what data is available at each point — it's a direct translation from `print()` to `RunState` mutation. No new LLM calls needed.

**Minimum to ship the console without backend changes:** Poll `/status` for live updates, `/results` for Results screen, `/dataset` for rows (unfiltered), `/export/{format}` for 4 of 6 files. Agent Fleet and Execution Trace tabs show degraded views using `event_log` text.

**To fully match the wireframe:** Implement A (SSE), B+C (AgentStatus + TraceEvent in RunState), E (dataset filter params), F (3 missing export formats + manifest).

---

## 10. Tech Stack

### Option A — Streamlit (fastest for hackathon)

```
streamlit==1.35+
streamlit-extras  (for additional components)
```

Use `st.session_state` for run state. Use `st.empty()` + loop for live updates. Coverage matrix via `st.columns()` grid with color-coded `st.markdown()` tiles. Network graphs via `streamlit-agraph` or embedded SVG in `st.components.v1.html()`.

Limitation: Streamlit's rendering model makes a true 3-column live monitor difficult. Work around with `st.components.v1.html()` to embed the full HTML wireframe as a component for the monitor screen.

### Option B — FastAPI + Vanilla JS (recommended for fidelity)

```
Backend: FastAPI + uvicorn
Frontend: Single HTML file (matches wireframe approach)
Transport: SSE via FastAPI StreamingResponse
```

This matches the wireframe approach exactly. The wireframes are already production-quality HTML. The build plan:

1. Copy the wireframe HTML as the base `console.html`
2. Replace static/hardcoded data with JS fetches to the API
3. Wire up SSE subscription to `GET /api/run/{id}/stream`
4. Serve via FastAPI static files at `localhost:8501`

### Option C — React + Vite (best for long-term)

Use Tailwind CSS tokens matching the design system above. Chart components:
- SVG graphs: d3.js or hand-rolled SVG
- Sparklines: recharts `BarChart` with custom bars
- Score bars: plain CSS `flexbox`

---

## 11. Component Inventory

| Component | Used in | Implementation |
|---|---|---|
| `AgentCard` | Monitor > Left | card with pill, status dot, mini-bar |
| `TraceGroup` | Monitor > Center > Trace | collapsible variant group |
| `TraceEntry` | Monitor > Center > Trace | row with inline expand |
| `StepCard` | Monitor > Center > Detail | collapsible step with typed body |
| `ScoreBars` | Monitor > Center > Detail > Step 4 | horizontal CSS bars |
| `CriticSparkline` | Monitor > Right | 12-bar sparkline |
| `TokenBurnBars` | Monitor > Right | per-agent horizontal bars |
| `MiniCoverageGrid` | Monitor > Right | small heatmap |
| `CoverageMatrix` | Monitor (simple) + Results > Coverage | full heatmap grid |
| `NetworkGraph` | Results > Network Graphs | SVG + positioned nodes |
| `TransactionTable` | Monitor > Detail + Results > Dataset | filterable table |
| `PersonaCard` | Monitor + Results > Personas | card with avatar, risk badge |
| `StatCard` | Results > Coverage | large number + label |
| `SummaryBanner` | Results > Coverage | green banner with key stats |
| `ExportRow` | Results > Export | file entry with download button |

---

## 12. Live Monitor — Interaction Details

### Pause / Resume

Clicking Pause:
1. Sends `POST /api/run/{id}/pause`
2. Adds `animation-paused` class to `<body>` (freezes all pulse animations)
3. Button changes to `▶ Resume`

### Stop

Clicking Stop:
1. Shows inline confirmation: `Stop this run? Partial results will be saved. [Cancel] [Stop Run]`
2. On confirm: `POST /api/run/{id}/stop`
3. Navigate to Results screen with partial data

### Agent filter

1. Click agent card in left panel → adds `active-filter` class to that card, dims others
2. Shows "Agent filter ✕" chip in trace toolbar
3. Trace list shows only entries where `data-agent === selected`
4. Clicking "Agent filter ✕" chip clears filter

### Variant group collapse

Click group header → toggles `collapsed` class on `.vgroup`. When collapsed, `.vgroup-entries` is hidden.

### Trace entry expand

Click row → toggles adjacent `.trace-detail.open` class (show/hide detail block). Expand icon rotates `▶` → `▼`.

### Step card expand (Variant Detail)

Click step header → toggles `step-body.open` on the step's body div.

---

## 13. Coverage Matrix — Cell Encoding

Cells encode 3 dimensions as a compact label: `[hops]h·[topo]·[timing]`

```
hops:   2h, 3h, 4h, 5h, 6h
topo:   ch (chain), fan (fan-out), hyb (hybrid)
timing: sd (same-day), dl (delayed), bst (burst), stg (staggered)
```

Example: `3h·fan·dl` = 3-hop, fan-out, delayed

The grid row/column axes should be labeled in the final implementation. The wireframe shows unlabeled cells for compactness; add axis labels (row = hop_count, column = topology) with timing shown within the cell label.

---

## 14. Animation Specs

| Animation | Element | Keyframe | Duration |
|---|---|---|---|
| `pulse` | Status dots, live indicators, in-progress cells | opacity 1→0.35→1 | 1.8s ease-in-out infinite |
| Cost ticker pulse | `$X.XX` in top bar | Same opacity pulse | 1.8s |
| Green live dot | URL bar, panel header | Same | 1.8s |
| Failed cell border | `.mx-red` in coverage | border-color flicker | CSS animation (optional) |

All animations pause when `body.animation-paused` is set (via Pause button).

---

## 15. Build Order

### Phase 1 — Static shell (1–2h)

1. Set up project (FastAPI + single HTML file or Streamlit)
2. Implement the 3-screen navigation with sidebar
3. Render Screen 1 (Configure Run) fully static
4. Wire slider → cost/time estimate display
5. Wire description textarea → enable/disable Run button

### Phase 2 — Results screen (2–3h)

6. Implement Results screen with all 5 tabs
7. Coverage matrix with static mock data
8. Network graphs with SVG rendering
9. Transaction table with filter chips (filter logic)
10. Personas tab
11. Export tab with download links

### Phase 3 — Live Monitor (3–4h)

12. Implement Monitor screen full 3-column layout
13. Agent Fleet left panel (static then wired)
14. Execution Trace center tab with groups + entries + inline details
15. Variant Detail center tab with step cards
16. Right panel: sparkline, token bars, mini grid
17. Monitor top bar with progress + controls

### Phase 4 — Live wiring (2–3h)

18. FastAPI SSE endpoint
19. Subscribe from JS, update agent cards on `agent_update`
20. Append trace entries on `trace_event`
21. Update coverage cells + variant feed on `variant_complete`
22. Transition to Results on `run_complete`
23. Pause/Resume/Stop controls

---

## 16. Responsive Considerations

The app targets desktop only (1280px+ width). The sidebar is 200px fixed, left panel 240px, right panel 220px, center panel fills remaining space. Minimum supported viewport: 1100px. No mobile breakpoints needed for the hackathon.
