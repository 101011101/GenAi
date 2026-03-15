# 10 — Branding & Landing Page

---

## Product Name

**FraudForge**

Tagline: *Out-iterate the attacker.*

Alternate taglines:
- *Explore fraud space before the fraudsters do.*
- *Synthetic fraud data. Real detection advantage.*
- *Red team your models before criminals do.*

---

## Product Philosophy

**Think like the attacker, at scale.**

FraudForge exists because fraud detection is a data problem disguised as a model problem. The models work. The data doesn't exist yet. Every new fraud variant starts with a detection gap — a window where the institution's model has zero signal. FraudForge closes that window by exploring the fraud variant space *before* real attackers get there.

Core beliefs:
1. **Offense informs defense.** The best way to harden a system is to attack it yourself, systematically, at scale. Red teaming is not optional — it is the only way to stay ahead.
2. **Compute is the institutional advantage.** A fraudster can probe a handful of variants. An institution can simulate thousands. Scale, applied to the right problem, is the moat.
3. **Additive, not disruptive.** FraudForge doesn't replace your fraud detection stack. It feeds it the data it's starving for. Plug in, retrain, deploy.
4. **Proactive, not reactive.** Stop patching after attacks. Start exploring before them.

---

## Tone of Voice

**Authoritative. Direct. Zero fluff.**

The landing page speaks like a senior fraud analyst briefing a room of decision-makers. It knows the problem cold. It doesn't oversell. It explains clearly, builds urgency through facts, and lets the architecture speak for itself.

| Do | Don't |
|---|---|
| State the problem directly | Use hype language ("revolutionary", "game-changing") |
| Use concrete numbers and examples | Make vague claims about AI |
| Show the system working | Promise outcomes without evidence |
| Use short, declarative sentences | Write long, flowery paragraphs |
| Speak to fraud teams as peers | Condescend or over-explain basics |
| Use precise technical language where needed | Drown in jargon for jargon's sake |

Voice examples:
- "Your model works. It just hasn't seen the next variant yet."
- "30 confirmed mule cases. Your GNN needs 1,000. That's not a model problem — it's a data problem."
- "Fraudsters iterate. Your training data doesn't. FraudForge changes that."

---

## Colour Scheme

### Primary Palette — "Night Operations"

The palette conveys security, intelligence, and precision. Dark foundation with green as the primary accent — signaling defense, surveillance, and system health.

| Role | Hex | Name | Usage |
|---|---|---|---|
| Background | `#0A0F0D` | Void | Page background, dark sections |
| Surface | `#111916` | Deep Canopy | Cards, panels, elevated surfaces |
| Surface Alt | `#1A2420` | Dark Moss | Secondary containers, code blocks |
| Primary | `#00E676` | Signal Green | CTAs, active states, key metrics, accent |
| Primary Muted | `#2E7D5B` | Forest | Secondary buttons, borders, hover states |
| Primary Glow | `#00E67620` | Ghost Green | Subtle glows, background highlights |
| Text Primary | `#E8F0EC` | Frost | Body text, headings |
| Text Secondary | `#8A9B93` | Lichen | Captions, labels, secondary copy |
| Danger / Red Team | `#FF5252` | Threat Red | Red team elements, fraud indicators, warnings |
| Danger Muted | `#FF525230` | Soft Threat | Red team backgrounds, subtle alerts |
| Caution | `#FFB74D` | Amber | Revision states, medium-priority signals |
| Info / Blue Team | `#448AFF` | Shield Blue | Blue team elements, defense indicators |
| Score High | `#00E676` | (same as Primary) | Critic scores 8+ |
| Score Mid | `#FFB74D` | (same as Caution) | Critic scores 5-7 |
| Score Low | `#FF5252` | (same as Danger) | Critic scores <5 |

### Gradient

Hero section gradient:
```
background: linear-gradient(165deg, #0A0F0D 0%, #111916 40%, #0A1A12 100%);
```

Accent glow (behind hero text or key visuals):
```
radial-gradient(ellipse at 50% 50%, #00E67610 0%, transparent 70%);
```

---

## Art Direction & Visual Language

### Overall Aesthetic — "Tactical Intelligence"

The visual language borrows from military operations centers, cybersecurity dashboards, and financial terminal UIs. It feels like a system built for operators, not a marketing site selling dreams.

### Typography

| Role | Font | Weight | Size (desktop) |
|---|---|---|---|
| Hero headline | `JetBrains Mono` or `IBM Plex Mono` | Bold | 48–64px |
| Section headings | `Inter` or `IBM Plex Sans` | Semibold | 28–36px |
| Body text | `Inter` or `IBM Plex Sans` | Regular | 16–18px |
| Code / data | `JetBrains Mono` | Regular | 14–16px |
| Labels / captions | `Inter` | Medium | 12–14px |

Monospace for the hero creates an immediate "system" feel — this is infrastructure, not a consumer product.

### Iconography

- Line-weight icons, 1.5px stroke, monochrome (frost or signal green)
- Style reference: Lucide or Phosphor icon sets
- Key icons: shield, network graph, target, layers, terminal prompt, radar

### Visual Motifs

1. **Network graphs** — Stylized node-edge diagrams representing mule networks. Used as hero art, section backgrounds, and decorative elements. Abstract enough to be visual, specific enough to be meaningful.

2. **Grid / matrix patterns** — Subtle dot grids or coverage matrix patterns in the background. Reinforces the "systematic exploration" message. Cells filling with color as you scroll.

3. **Terminal / console snippets** — Small embedded code-like blocks showing agent output, JSON fragments, or pipeline logs. Makes the product feel real and technical.

4. **Red vs Green duality** — Red elements represent the attacker / red team. Green elements represent defense / approved output / system health. This red/green tension runs through every visual.

5. **Data flow lines** — Thin animated lines connecting sections, suggesting data flowing through a pipeline. Subtle, not distracting.

### Photography

None. Zero stock photos. Zero team photos on the landing page. The visual story is told entirely through diagrams, data visualizations, and UI screenshots. This is a technical product for technical buyers — the visuals should be the product itself.

---

## Landing Page Structure

---

### Section 1 — Hero

**Purpose:** Hook. State the problem in one breath.

**Content:**
- Headline: "Your model works. It just hasn't seen the next variant yet."
- Subhead: "FraudForge deploys adversarial AI agents to generate the synthetic fraud data your detection models are starving for. Explore the attack surface before the attackers do."
- Primary CTA: "See it run" (scrolls to demo / architecture section)
- Secondary CTA: "Read the problem" (scrolls to Section 2)

**Visual:** Animated network graph in the background — nodes and edges slowly appearing, representing a mule network being constructed. Dark, atmospheric, subtle motion.

---

### Section 2 — The Problem

**Purpose:** Build urgency. Make the data gap tangible.

**Content:**

**"Fraud detection has a data problem."**

Three stat cards side by side:

| Card | Stat | Label |
|---|---|---|
| 1 | < 0.1% | of transactions are fraud. New variants are rarer still. |
| 2 | 30 | confirmed mule cases at a typical bank. GNNs need 1,000+. |
| 3 | $0 | value of a model that hasn't seen the pattern it's supposed to catch. |

**Supporting copy:**
- ML models are effective against fraud they've seen. The assumption breaks at the edges.
- New fraud variants start with a detection gap. The model has no signal. The fraud continues.
- Institutions can't share data across borders. Each bank trains on its own silo.
- The known unknown gap: you know the fraud type exists, you just don't have enough variant data to train against it.

**Visual:** A simple "Known / Known Unknown / Unknown Unknown" tier diagram. The middle tier ("Known Unknown") is highlighted in signal green — this is where FraudForge operates.

---

### Section 3 — The Solution

**Purpose:** Present the core idea. Red team / blue team framing.

**Content:**

**"Stop patching. Start out-iterating."**

Two-column layout:

| Red Team (left, red accent) | Blue Team (right, green accent) |
|---|---|
| AI agents that think like fraudsters | Your existing fraud detection pipeline |
| Explores the full variant space at scale | Retrains on synthetic data to close gaps |
| Runs proactively — before real attacks | Deploys hardened models with new coverage |

**Key message:** "A fraudster can probe a handful of variants. FraudForge simulates thousands. Scale, applied to the right problem, is the moat."

**Visual:** A split-screen animation. Left side: red-tinted agent spawning variant after variant. Right side: green-tinted model absorbing the data and strengthening. Converging in the center.

---

### Section 4 — MVP: The Console

**Purpose:** Show the product is real. Ground it in what the user actually interacts with.

**Subheading:** "Built for fraud analysts, not engineers."

**Content — 3 panels presented as tabs or a horizontal walkthrough:**

**Panel A — Input & Configure**
- The analyst describes a fraud type in natural language
- Sets variant count, fidelity level, quality thresholds
- One click to start
- Screenshot/mockup of the input panel with a mule network description filled in

**Panel B — Live Monitor**
- Watch agents spawn and generate variants in real time
- Persona cards stream in as criminal profiles are created
- Coverage matrix fills as the variant space is explored
- Critic scores arrive live — green/yellow/red quality indicators
- Screenshot/mockup of the monitoring panel with active agents, variant feed, coverage grid

**Panel C — Admin Observability Console**
- Deep pipeline visibility for platform engineers
- 6 operational views: Mission Brief, Coverage, Constructor, Quality Gate, Operations, Variant Journey
- Per-agent reasoning chains, cost tracking, revision history
- Heist Storyboard — watch how each fraud scheme was designed step-by-step
- Quality Battlefield — see every variant's journey through the quality gate
- Pipeline Waterfall — full operational timing at variant-level granularity
- Screenshot/mockup of the admin console showing the Constructor view with money trail graph

**Visual:** Clean UI mockups on dark backgrounds. Floating panels with subtle shadows. Each panel should feel like a screenshot from a working product.

---

### Section 5 — MVP Agent Stack

**Purpose:** Show the intelligence behind the system. Make the agent hierarchy legible.

**Subheading:** "A coordinated red team, not a single prompt."

**Content — Agent hierarchy table:**

| Agent | Role | In MVP |
|---|---|---|
| Orchestrator | Decomposes fraud type into variant dimensions | Yes |
| Persona Generator | Creates diverse criminal profiles that seed behavior | Yes |
| Coverage Matrix Manager | Tracks variant space exploration, prevents clustering | Yes |
| Fraud Network Constructor | Multi-step reasoning chain — generates complete fraud variants | Yes |
| Schema Validator | Automated structural validation before quality scoring | Yes |
| Critic Agent | Independent quality gate — scores realism and diversity | Yes |
| Data Handler | Transforms output into ML-ready formats (CSV, JSON, graph) | Yes |
| Criminal Mastermind | Full operation planning with compartmentalized mule instructions | Level 4 |
| Mule Agents | Limited-information participants with behavioral variation | Level 4 |
| Bank System Agent | Realistic transaction processing, flags and rejections | Level 4 |

**Key callout box:**
> "Level 4 agents don't just generate data — they simulate information asymmetry. The mule doesn't know it's committing fraud. The criminal compartmentalizes. The bank flags suspicious activity. The emergent behavior from these interactions produces variants no single-agent system can."

**Visual:** A vertical agent hierarchy diagram with connecting lines. MVP agents are solid green nodes. Level 4 agents are outlined/dashed nodes (coming next). Lines show data flow between agents.

---

### Section 6 — Architecture Flow

**Purpose:** Make the system architecture visually intuitive. The "how it works" diagram.

**Subheading:** "From description to dataset in minutes."

**Content — 8 pipeline stages, each rendered as a card:**

**1. Describe**
The analyst provides a natural language description of a known fraud type — the only input the system needs.

**2. Decompose**
The orchestrator breaks the fraud description into the dimensions that define how it can vary — hop count, timing, topology, extraction method.

**3. Seed**
Persona Generator creates diverse criminal profiles; Coverage Matrix maps the full variant space to ensure systematic exploration, not clustering.

**4. Generate**
A fleet of sub-agents runs in parallel, each assigned a unique persona and variant cell, reasoning through a 5-step chain: Motive, Blueprint, Crew, Execution, Cleanup.

**5. Validate**
Schema Validator runs automated structural checks on every agent output — malformed data is rejected instantly before spending compute on quality scoring.

**6. Score**
The Critic Agent independently evaluates each variant on realism, persona consistency, and structural distinctiveness against the rest of the batch.

**7. Revise**
Variants that fail the quality gate receive specific feedback and are sent back to the constructor for revision — up to 3 attempts before the cell is reassigned.

**8. Export**
Approved variants are compiled into a labeled synthetic dataset and exported in ML-ready formats — CSV, JSON, or graph adjacency lists for GNN training.

**Key stats alongside the flow:**
- 20-50 variants per run
- Mean critic score >= 7/10
- 50%+ coverage matrix saturation
- ~5-7 minutes for a demo run
- ~$4-6 per 20-variant run

**Visual:** This should be rendered as an actual flow diagram with the FraudForge colour scheme — dark background, green connection lines, green node borders, red accents on the critic/revision loop. Animated data flow lines pulsing through the pipeline.

---

### Section 7 — Footer / Closing CTA

**Purpose:** Close. Point to next steps.

**Content:**
- Headline: "The attacker is iterating. Are you?"
- CTA button: "Try the demo" or "View on GitHub"
- Secondary links: PRD, Architecture docs, Contact
- Built for TD Best AI Hack

**Visual:** Minimal. Dark. The network graph from the hero fades back in, subtly, behind the CTA.

---

## Responsive Behavior

| Breakpoint | Layout Notes |
|---|---|
| Desktop (1200px+) | Full layout as described. Two-column sections. Inline stat cards. |
| Tablet (768–1199px) | Single column. Stat cards stack. Agent table scrolls horizontally. |
| Mobile (< 768px) | Single column. Simplified flow diagram (vertical only). Tab panels become accordion. |

---

## Motion & Animation Guidelines

| Element | Animation | Duration | Trigger |
|---|---|---|---|
| Hero network graph | Nodes and edges fade in sequentially | 3-4s | On page load |
| Stat cards | Counter animation (0 → final number) | 1.5s | On scroll into view |
| Coverage matrix cells | Fill with color sequentially | 2s | On scroll into view |
| Pipeline flow lines | Pulsing dash animation along paths | Continuous | On scroll into view |
| Agent hierarchy nodes | Scale in from center | 0.3s stagger | On scroll into view |
| Section transitions | Fade up + slight translate Y | 0.5s | On scroll into view |

All animations should be reducible (respect `prefers-reduced-motion`). Subtle > dramatic. The product is serious — the motion should feel precise, not playful.

---

## Do Not Include

- Pricing (hackathon prototype — no pricing model yet)
- Team bios or photos
- Testimonials or social proof
- Login / signup flows
- Detailed API documentation on the landing page
- Folder structure diagrams
