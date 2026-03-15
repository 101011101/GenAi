# 03 — Product Requirements [DRAFT]

---

## Users & Stakeholders

**Fraud Analyst** — Primary operator of the system. Identifies a known unknown fraud pattern through investigation or intelligence and provides the natural language description that seeds the pipeline. Does not need technical knowledge to operate the console.

**Data Scientist / ML Engineer** — Consumes the output dataset. Processes the exported data into the format their model pipeline requires — graph format for GNN training, time-ordered sequences for LSTM/Transformer, flat rows for XGBoost. Does not interact with the console directly.

**Hackathon Judges** — Evaluate the demo. Need to understand the problem, see the system run, and see the output make sense.

---

## User Stories

- As a fraud analyst, I provide a natural language description of a known fraud type and receive a labeled synthetic dataset without needing to know how the agents work.
- As a fraud analyst, I can control how deep and detailed the simulation runs based on how much time and cost I want to spend.
- As a data scientist, I receive a dataset that I can directly convert into the input format my ML model requires (graph, sequence, or flat tabular).
- As a fraud analyst, I can monitor the pipeline in real time and see how many variants have been generated, their quality scores, and coverage across the variant space.

---

## Agent Hierarchy

```
Console
    ↓
Orchestrator
    ├── Persona Generator Agent
    ├── Coverage Matrix Manager
    └── Fraud Network Constructor Agent
            ├── Criminal Mastermind Agent (per variant)
            │       └── Cover Story Agent
            ├── Mule Agents (per hop, per variant)
            └── Bank System Agent
    ├── Schema Validator (synchronous, automated)
    ├── Critic Agent
    └── Data Handler Agent
            ├── Graph formatter → GNN
            ├── Sequence formatter → LSTM / Transformer
            └── Flat formatter → XGBoost / Random Forest
```

### Agent Responsibilities

**Orchestrator** — Receives input from the console. Coordinates all downstream agents. Manages the coverage matrix and triggers second passes if diversity is insufficient.

**Persona Generator Agent** — Generates criminal personas that seed the Fraud Network Constructor. Personas define risk tolerance, resources, operational scale, geographic scope, timeline pressure, and evasion targets.

**Coverage Matrix Manager** — Builds and tracks the variation dimension grid. Monitors saturation after each batch and flags underrepresented cells for a second pass.

**Fraud Network Constructor Agent** — Responsible for simulating the full fraud operation for a given persona and variant assignment. At higher fidelity levels, spawns dedicated sub-agents for each participant role.

**Criminal Mastermind Agent** — Knows the full operational plan. Gives instructions to mule agents without revealing the full picture. Generates evasion decisions when the bank system agent flags a transaction.

**Cover Story Agent** — Generates plausible explanations the criminal gives to mules when questioned. Feeds into mule agent context to determine compliance and suspicion level.

**Mule Agents** — Each represents one participant in the network. Has limited information — only what a real mule would know (recruitment story, instructions, payment). Context includes personal financial situation, suspicion level, and motivation for taking the job. Behavior varies based on how suspicious or compliant they are.

**Bank System Agent** — Applies realistic transaction processing rules. Flags anomalies, rejects impossible transfers. When it flags something, the criminal mastermind agent must route around it — producing evasion behavior organically.

**Schema Validator** — Synchronous, automated. Runs before the critic. Rejects outputs that fail the JSON schema before spending LLM cost on evaluation.

**Critic Agent** — LLM-based quality gate. Scores each variant on realism, persona consistency, label correctness, and variant distinctiveness. Returns feedback to sub-agents for revision if below threshold.

**Data Handler Agent** — Transforms validated output into ML-ready formats. Produces graph, sequence, and flat tabular representations from the same source JSON.

---

## Console & Controls

The console is the primary interface for the fraud analyst. It manages input, orchestration control, real-time monitoring, and output export.

### Input Panel
- Natural language fraud description entry
- Run configuration (see controls below)
- Submit to orchestrator

### Orchestration Controls

**Fidelity Level** — Controls which agents are active and how deeply each participant is simulated. Cascades through the entire agent hierarchy.

| Level | What's Active | Cost | Speed |
|---|---|---|---|
| 2 | Constructor generates all output in single pass | Low | Fast |
| 3 | Multi-step chain-of-thought, persona-seeded constructor | Medium | Moderate |
| 4 | Full role simulation — criminal, mule, bank system agents all active | High | Slow |

**Volume Controls**
- Target variant count
- Max parallel agents (cost/speed tradeoff)
- Coverage matrix density (granularity of the variation grid)

**Quality Controls**
- Critic score floor (minimum to enter the dataset)
- Max revision iterations before variant is discarded
- Auto second-pass on diversity (on/off)

**Persona Controls**
- Number of distinct personas to generate
- Risk profile distribution (e.g. 30% high / 40% mid / 30% low)
- Geographic scope (domestic / international / specific regions)

**Mule Context Depth** — Independent of fidelity level. Controls how detailed each mule agent's backstory is.
- Shallow: job description only
- Medium: financial situation and motivation
- Deep: full backstory, suspicion level, relationship to criminal org

### Live Monitoring Panel
- Variants completed vs target
- Critic scores as they come in (mean, distribution)
- Coverage matrix visualization — which cells are filled vs empty
- Active agents and their current status
- Revision loop activity (how many retries are happening)

### Output Panel
- Browse generated variants, filter by persona / score / fraud role
- Export format selector (CSV / Parquet / JSON / graph)
- Dataset summary stats (variant count, mean critic score, persona diversity, coverage saturation)

---

## Functional Requirements

*To be expanded — high level for now.*

- System must accept a natural language fraud description as input
- Orchestrator must decompose input into variation dimensions
- System must generate at least one persona per sub-agent assignment
- Critic must evaluate every output before dataset inclusion
- Schema validation must run before critic evaluation
- System must support revision loop with configurable max iterations
- System must export labeled dataset in at least CSV and JSON
- Each output record must include: `is_fraud`, `fraud_role`, `variant_id`, `persona_id`, `variant_parameters`, `critic_scores`
- Console must reflect real-time pipeline state
- Fidelity level must be settable before run and must cascade to agent configuration

---

## Non-Functional Requirements

*To be expanded.*

- Minimum useful variant count: 50 for demo, 1,000+ for production use
- Critic score floor default: ≥ 7 / 10 for dataset inclusion
- Batch run should complete within a reasonable time at the configured fidelity and variant count
- API cost per run should be configurable via parallel agent cap and fidelity level
- All agent decisions must be logged for traceability and audit

---

## Demo Scope

*To be expanded.*

- Input: mule network fraud description via console
- Show live orchestration: agents spawning, variants completing, critic scores arriving
- Show coverage matrix filling in real time
- Export dataset and show sample records
- Stretch: show Level 2 vs Level 4 output side by side to demonstrate quality delta

---

## Acceptance Criteria

*To be expanded.*

- Given a mule network description, system produces target variant count
- Mean critic realism score across dataset meets configured floor
- Coverage matrix saturation is above a minimum threshold
- Output exports cleanly in all supported formats
- Each record contains all required fields with correct labels

---

## Constraints

- No real bank data — all data is synthetic
- No live bank system connection
- All generation happens via LLM API calls
- Hackathon time and cost limits apply
- Output must be usable by a data scientist without modification
