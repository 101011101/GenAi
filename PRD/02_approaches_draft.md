# 02 — Approaches [DRAFT]

## Overview

This document covers the technical approach, architecture, and design decisions behind the synthetic fraud data generation system. It explains how the system works, why each component is designed the way it is, and how the output maps to the ML systems institutions already run.

---

## What the System Is

The system is a **synthetic fraud data generation pipeline** driven by adversarial AI agents. It takes a known fraud type as input and produces a diverse, labeled synthetic transaction dataset as output — ready to feed into a financial institution's existing ML training pipeline.

It is a **batch process**, not a real-time system. It runs offline when a fraud team identifies a known fraud pattern they lack sufficient training data for. The output is stored and used to retrain the institution's fraud detection models.

---

## Technical Approach

### Industry Precedent — IBM AMLSim

The synthetic data approach to AML training data is not novel — it is an acknowledged industry need with existing solutions. IBM Research built **AMLSim**, a publicly available synthetic anti-money laundering transaction simulator, specifically because the data scarcity problem is real and well-documented. Banks and researchers use it to generate synthetic transaction graphs when they lack sufficient real labeled examples for model training.

AMLSim works by statistically modeling known transaction patterns and generating synthetic graphs from those distributions. It is effective at producing more examples of fraud patterns that are already well-characterized.

This product is a direct evolution of that concept — using adversarial LLM agents instead of statistical simulation:

| | IBM AMLSim | This System |
|---|---|---|
| Generation method | Statistical simulation from known distributions | Adversarial LLM agents reasoning from first principles |
| Variant diversity | Statistical variation around parameterized distributions | Reasoning-based exploration of novel execution strategies |
| Evasion logic | None — mirrors known patterns | Explicit — agents reason about what controls to evade and why |
| New variant coverage | Limited to what the statistical model was parameterized for | Can explore structurally novel variants within a known fraud class |
| Persona-driven behavior | No | Yes — different criminal profiles produce structurally different outputs |

Statistical simulation generates more examples of what you already know. Adversarial agents reason about what you do not know yet. The IBM precedent validates the market need. This system addresses the limitation of statistical approaches when the goal is covering unknown variants.

### What the Agents Are Actually Producing

The agents produce synthetic transaction records — structured data representing what a bank's database would contain if the fraud had occurred:

```
account_id, timestamp, amount, counterparty, merchant_category, is_fraud, fraud_role
```

The agents are not executing real transactions or connected to any live system. They are generating data that represents what those transactions would look like — a detailed, internally consistent script of a fraud operation, not the operation itself.

All agents run on the same underlying LLM. What makes agents behave differently is not different model weights but different **context**: each agent has a different system prompt, a different information scope, and a different objective. Same underlying model, different situation — producing different emergent behavior. This mirrors how real participants in a fraud operation behave differently not because they are fundamentally different people but because they have different information, different incentives, and different roles.

### Simulation Fidelity — The Spectrum

Agent-based fraud simulation exists on a spectrum from mechanical template generation to full multi-agent role play. The fidelity level determines output quality, build complexity, and what kinds of variants can be produced.

| Level | Approach | How It Works | Output Quality | Feasibility |
|---|---|---|---|---|
| 1 | Template generation | Parameters filled into formulas — no reasoning | Poor — mechanical, immediately identifiable as synthetic | Trivial but pointless |
| 2 | Single-shot LLM | One prompt, full specification, one inference pass | Moderate — plausible but gravitates toward generic "average fraud" | Simple |
| 3 | Multi-step reasoning agent | Agent reasons through persona → strategy → transactions in stages | Good — internally consistent, persona-grounded | Target for this system |
| 4 | Multi-agent role simulation | Each fraud participant gets their own agent with limited information scope | Very good — emergent behavior from information asymmetry | Partial — differentiating architecture |
| 5 | Fine-tuned specialized agents | Different model weights per role, trained on domain-specific data | Excellent | Out of scope |

**Level 3 — Multi-Step Reasoning (Foundation)**

Each sub-agent reasons in stages before generating data:
1. Think through the persona's goals, resources, and constraints
2. Plan the operational strategy as a consequence of those constraints
3. Generate transactions that follow from that plan
4. Review own output for internal consistency

The final transactions are consequences of reasoning, not a single inference guess. This is what chain-of-thought with persona seeding achieves.

**Level 4 — Multi-Agent Role Simulation (Differentiating Architecture)**

Instead of one agent generating the whole network, each participant in the fraud gets their own agent with its own limited information scope:

- **Criminal mastermind agent** — knows the full plan, gives instructions to mules, does not generate transactions directly
- **Mule agent (per hop)** — knows only what a real mule would know: "you received funds from an unknown party, forward most of it to this account, keep the rest as payment for a processing job"
- **Bank system agent** — applies real transaction processing rules, flags anomalies, rejects impossible transactions

The critical property is **information asymmetry between agents**. The mule agent does not know they are committing fraud. The criminal agent does not reveal the full plan to each mule. The bank agent is actively trying to detect something suspicious. The emergent behavior from these interactions — the mule asking for clarification and receiving a cover story, the criminal routing around a flagged transaction, the mule introducing an unplanned delay — is behavior no single agent would produce alone.

This mirrors the actual information structure of real fraud. Real mules are not fully informed participants. Real criminals compartmentalize. That compartmentalization is why real mule networks produce such varied behavioral signatures — and why simulating it produces more genuine variant coverage than any single-agent approach.

---

## Reference Case — Mule Network Fraud

The primary demonstration case for this system is mule account network fraud. Understanding the mechanics of this fraud type grounds every architectural decision.

### How It Works

A mule network moves stolen money from a traceable origin to an untraceable destination by routing it through a chain of real, legitimate-looking bank accounts. The money moves in three phases:

**Placement** — Stolen funds (from ransomware, romance scams, business email compromise, card fraud) are received into the first mule account. This is the most traceable moment. The criminal's goal is to move the money onward as fast as possible before a flag is raised.

**Layering** — Money moves through a chain of mule accounts across multiple institutions. Each mule receives funds and forwards most of them to the next account, keeping a small cut. From any single bank's perspective, they see one hop: money arrives from an external source and leaves to another external destination. The chain is only visible at the network level — which spans institutions that do not share data in real time.

**Integration** — After enough hops, the origin is sufficiently obscured. The money is extracted via wire to an offshore account, crypto conversion, ATM cash withdrawals, or purchase of high-value goods.

### What Varies Between Criminal Organizations

No two mule networks look the same. The dimensions that vary are exactly the dimensions that defeat pattern-matching defenses:

| Dimension | Low End | High End |
|---|---|---|
| Hop count | 2–3 (fast, riskier) | 8–10 (slow, safer) |
| Timing between hops | Same-day | Weekly |
| Amount structuring | Single transfer | Smurfing — many transactions just below $10K reporting threshold |
| Network topology | Simple chain A→B→C→D | Fan-out tree — one account splits to five, each splits to two more |
| Cover activity | None | High — mule account also has normal purchases, payroll, bills |
| Account type | Newly opened | Compromised legitimate accounts with years of history |
| Geographic spread | Domestic only | Multi-jurisdictional, cross-border |
| Extraction method | Wire | Crypto / cash / goods |

### What Makes It Hard to Detect

**Fragmented visibility** — No single bank sees the full chain. Detection requires network-level visibility across institutions that cannot share data in real time.

**Individually legitimate transactions** — A $4,500 transfer between two accounts is not fraud. Millions happen daily. The signal is the pattern across accounts and time, not any single transaction.

**Payment rail speed** — Real-time payment systems (Zelle, Interac e-Transfer) settle in seconds. By the time a flag is raised and reviewed, the money has already moved through the next hop.

**Mule account legitimacy** — The most valuable mule accounts are old, legitimate accounts belonging to real recruited people. They pass every static account-level check because they are real accounts being misused.

**Structuring below thresholds** — Reporting thresholds are public knowledge. Criminal organizations specifically design transfer amounts to stay beneath them. The specific split logic varies enough that simple threshold-based rules catch only naive operators.

**Jurisdictional gaps** — Routing through 3–4 countries means 3–4 regulatory regimes with no automatic real-time information sharing. International coordination is measured in months.

**No two operations look the same** — A model trained on 30 observed mule networks has learned 30 structural signatures. The 31st operation, run by a different criminal organization with different resources and risk tolerance, looks structurally different and produces no signal in the model.

---

## System Architecture

The system has five layers:

**1. Input Layer**
**2. Orchestrator Agent**
**3. Sub-Agent Fleet (Red Team)**
**4. Critic Agent (Quality Gate)**
**5. Output Layer**

---

## Layer 1 — Input

The user provides a natural language description of a known fraud type. This description should include:
- The general fraud mechanism (e.g. layered fund transfers through third-party accounts)
- The known goal of the fraudster (e.g. obscure the origin of illicit funds before extraction)
- Any known constraints or context (e.g. operates across multiple banks, uses recruited account holders)

**Example input:**
> "Mule account network fraud — criminal organizations recruit individuals to receive stolen funds into their accounts and forward them through a chain of additional accounts before final extraction via wire or cash. Each organization structures the network differently in terms of hop count, timing, and amount patterns."

The input does not need to be exhaustive. The orchestrator's job is to expand it.

---

## Layer 2 — Orchestrator Agent

The orchestrator receives the input and executes four steps:

### Step 1 — Dimension Decomposition

Identifies the key axes along which this fraud type can vary. For mule networks:

| Dimension | Example Range |
|---|---|
| Hop count | 2 → 10+ |
| Timing intervals | Same-day → weekly |
| Amount structuring | Fixed / random / split / tapered |
| Cover activity | None / low / high |
| Extraction method | Wire / crypto / cash |
| Target account type | Personal / business / student |
| Network topology | Chain / fan-out / hybrid |
| Geographic spread | Domestic / multi-jurisdictional |

### Step 2 — Persona Seed Generation

Before building the coverage matrix or spawning any sub-agents, the orchestrator generates a **criminal persona** for each planned variant. This is the key mechanism for producing genuine behavioral diversity rather than surface-level variation.

A persona defines the decision-maker behind the fraud: their risk tolerance, resources, operational constraints, timeline pressure, and specific evasion targets. This persona is passed to the sub-agent as its primary context and seeds every decision the sub-agent makes — hop count, timing, amounts, cover behavior — as consequences of a coherent criminal logic rather than arbitrary parameter choices.

**Example personas:**

> **Viktor** — Organized crime, Eastern European network. Operating across 6 countries with access to 200+ recruited mules and crypto infrastructure. High risk tolerance. Goal: move €2M in 72 hours following a ransomware payment. Specific constraint: avoid triggering flags in Germany and Netherlands where the criminal org has prior exposure.

> **James** — Small-scale domestic operation, previously caught. Low risk tolerance. Access to 8 mules, no crypto. Goal: move £40K over 3 weeks without raising flags. All mules in the same city, same bank. Prioritizes cover activity over speed.

Viktor and James both run mule networks. But Viktor's network is aggressive, distributed, and fast — high hop count, same-day transfers, international routing. James's is short, slow, and conservative — 2-3 hops, weekly intervals, heavy cover activity. A model trained only on Viktor's pattern will not catch James, and vice versa.

Personas are generated to cover diverse combinations of risk profile, resource level, operational scale, and geographic context — not just diverse transaction parameters.

### Step 3 — Coverage Matrix Construction

Builds a grid across variation dimensions and persona profiles to define the full variant space. This matrix is the plan the sub-agent fleet executes against and the baseline for diversity enforcement after collection.

### Step 4 — Sub-Agent Assignment

Spawns sub-agents, each assigned a specific persona and a specific cell or region of the coverage matrix. Assignments are explicit — the sub-agent is told exactly what variant it is responsible for, not given free choice.

**Orchestrator Quality Indicators:**
- Dimension coverage — did it identify all meaningful variation axes?
- Persona diversity — do generated personas span the full range of risk profiles, scales, and operational contexts?
- Assignment distinctiveness — are sub-agent tasks meaningfully different from each other?
- Matrix completeness — does the coverage matrix span the full plausible variant space?

---

## Layer 3 — Sub-Agent Fleet (Red Team)

Each sub-agent is responsible for generating one fraud variant: a complete, realistic synthetic transaction sequence representing its assigned persona and position in the coverage matrix. Sub-agents operate at Level 3 simulation fidelity (multi-step reasoning) as the foundation, with Level 4 (multi-agent role simulation) as the differentiating extension where feasible.

### Sub-Agent Execution — Chain of Thought First

Before generating any transactions, the sub-agent reasons through the scenario from the persona's perspective:
- What is this criminal's specific goal and timeline?
- What resources and mule infrastructure do they have access to?
- What detection controls are they specifically trying to evade, and why?
- What does their transaction behavior look like as a result of those constraints?

This produces outputs grounded in adversarial logic. The persona seed ensures that chain-of-thought reasoning leads to structurally different conclusions for different personas — not just different numbers on the same structure.

### Sub-Agent Output — Structured JSON

Agents output structured data, not free text:

```json
{
  "variant_id": "...",
  "fraud_type": "mule_network",
  "persona": {
    "name": "Viktor",
    "risk_tolerance": "high",
    "operational_scale": "large",
    "geographic_scope": "international",
    "timeline_pressure": "72hrs",
    "evasion_targets": ["DE", "NL"]
  },
  "strategy_description": "...",
  "variant_parameters": {
    "hop_count": 6,
    "timing_interval_hrs": 8,
    "amount_logic": "random_noise",
    "cover_activity": "none",
    "topology": "fan_out",
    "extraction_method": "crypto"
  },
  "transactions": [
    {
      "timestamp": "...",
      "amount": 0.00,
      "sender_account_id": "...",
      "receiver_account_id": "...",
      "merchant_category": "...",
      "is_fraud": true,
      "fraud_role": "hop_2_of_6"
    }
  ],
  "evasion_techniques": ["..."],
  "fraud_indicators_present": ["..."]
}
```

### Real-World Grounding

Sub-agents are provided reference context to prevent physically impossible outputs:
- Transaction amount distributions by merchant category and account type
- Bank processing time windows (no instant inter-bank settlement where it does not exist)
- Typical account balance ranges by demographic
- Known regulatory reporting thresholds by jurisdiction

**Sub-Agent Quality Indicators:**
- Internal consistency — does the sequence match the persona's constraints and the assigned parameters?
- Realism — do individual transactions fall within plausible real-world ranges?
- Variant distinctiveness — is this structurally different from what other sub-agents produced?
- Fraud signal integrity — does the sequence actually represent the fraud type it claims to?

---

## Layer 4 — Critic Agent (Quality Gate)

A separate agent reviews every sub-agent output before it enters the dataset. The critic operates independently — it receives the persona and the output, but has no knowledge of what the coverage matrix intended. It evaluates the output on its own merits.

### Critic Scoring

| Dimension | Type | Threshold |
|---|---|---|
| Realism | Score 1–10 | ≥ 7 |
| Persona consistency | Pass / Fail | Pass required |
| Label correctness | Pass / Fail | Pass required |
| Internal consistency | Pass / Fail | Pass required |
| Variant distinctiveness | Score 1–10 | ≥ 6 (vs. batch average) |

Persona consistency is the additional check enabled by seeding: does the generated behavior actually follow from the persona's stated risk tolerance, resources, and constraints? A high-risk, time-pressured persona that generates slow, cautious, conservative transfers has failed this check regardless of how realistic the individual transactions are.

### Revision Loop

Outputs that fail any threshold are returned to the sub-agent with the critic's specific feedback as a revision prompt. The sub-agent revises and resubmits. Maximum 2–3 revision iterations before the variant is discarded and the cell is reassigned to a fresh sub-agent.

### Diversity Enforcement

After the full batch is collected, the orchestrator checks coverage matrix saturation. LLMs gravitate toward typical outputs — the most common, average version of whatever they are asked to generate. If agents have clustered in the same cells, the orchestrator spawns a second pass explicitly targeting underrepresented regions with stronger persona seeds that force more extreme positions.

---

## Layer 5 — Output

The final output is a labeled dataset containing all validated synthetic variants, exportable in standard ML-ready formats (CSV, Parquet, JSON).

**Dataset Schema:**

Each record includes:
- All transaction fields (timestamp, amount, accounts, merchant category, etc.)
- `is_fraud` label (boolean)
- `fraud_role` label (role this transaction plays in the sequence)
- `variant_id` (which sub-agent generated it)
- `persona_id` (which persona seed was used)
- `fraud_type` (the input fraud category)
- `variant_parameters` (the specific axes of variation for this record's variant)
- `critic_scores` (realism and distinctiveness scores for traceability)

**Output Quality Indicators:**
- Total variant count
- Coverage matrix saturation percentage
- Persona diversity distribution across the dataset
- Mean critic realism score across dataset
- Pairwise similarity distribution across variants (diversity measure)

---

## ML Systems This Feeds — How They Work and What They Need

### XGBoost / Random Forest — Tabular Classification

The most widely deployed fraud detection model type. Each row is one transaction with engineered features:

```
amount                  float
hour_of_day             int (0–23)
day_of_week             int (0–6)
merchant_category       categorical → one-hot encoded
account_age_days        int
txn_velocity_1hr        int
txn_velocity_24hr       int
amount_vs_user_avg      float
location_delta_km       float
is_new_merchant         bool
label: is_fraud         bool
```

The model learns which feature combinations correlate with fraud. At inference it outputs a 0–1 fraud probability per transaction.

**The data gap:** fraud rows represent <0.1% of transactions. A new fraud variant with 200 confirmed cases produces 200 training rows against millions of legitimate rows. The model cannot learn a meaningful signal from 200 examples.

**What synthetic data adds:** diverse labeled fraud rows that balance the class imbalance and expose the model to structural variants it has not seen — different timing signatures, amount patterns, velocity profiles.

### Graph Neural Networks — Network Fraud

The appropriate model type for mule networks and organized fraud rings. The input is not a flat table — it is a graph:

- **Nodes** = accounts
- **Edges** = transactions between accounts (with features: amount, timestamp, direction)

The GNN learns to classify nodes or subgraphs as fraudulent by learning what network topology looks like for fraud versus legitimate activity. The signal is structural: not "this transaction is suspicious" but "this account sits in a graph pattern consistent with a layered transfer network."

**The data gap:** a bank with 30 confirmed mule network cases has 30 labeled fraud graphs. Minimum viable GNN training requires 1,000–5,000. The gap is an order of magnitude.

**What synthetic data adds:** diverse labeled fraud graph topologies — different hop counts, fan-out structures, cover activity patterns, timing distributions across the graph. The model learns the class of network structure rather than 30 specific instances of it.

### Sequence Models — Behavioral Fraud

LSTMs and Transformers that operate on time-ordered transaction sequences per account. The input is:

```
[txn_1_features, txn_2_features, txn_3_features, ...]
```

The model learns temporal dependencies — the fraud signal is not in any single transaction but in the cadence and order of behavior over time. A mule account that receives funds, waits 48 hours, forwards 92% of the amount, then receives again — that rhythm is the signal.

**The data gap:** sequence models need diverse fraud sequences to learn the behavioral class rather than a single behavioral instance. 30 real mule sequences produce 30 temporal signatures. The model learns those 30 rhythms and misses the 31st.

**What synthetic data adds:** diverse behavioral sequences across the full range of timing intervals, amount progressions, and cover activity patterns. Persona seeding is particularly valuable here — Viktor's sequences are fast and aggressive, James's are slow and cautious. A sequence model trained on both learns the structural class of mule behavior, not a specific tempo.

### Data Requirements Summary

| Model Type | Minimum Viable (new fraud variant) | Typical Bank Has | Gap |
|---|---|---|---|
| XGBoost / RF | ~1,000 fraud rows | 200–500 | 2–5x |
| GNN | ~1,000–5,000 fraud graphs | 30–50 | 20–100x |
| Sequence Model | ~500–2,000 fraud sequences | 30–50 | 10–40x |

GNNs face the largest gap for network fraud types, which is why mule networks are the primary demonstration case.

---

## The Quality Loop — End to End

```
Input: fraud type description
         ↓
Orchestrator: dimension decomposition → persona seed generation
         ↓
Coverage matrix construction → sub-agent assignments
         ↓
Sub-agents: persona-grounded chain-of-thought reasoning
         ↓
Structured JSON output (real-world grounded)
         ↓
Schema validation (automated, synchronous)
         ↓
Critic agent: realism / persona consistency / label / distinctiveness
         ↓
Below threshold → revision loop (max 2–3 iterations, critic feedback passed back)
         ↓
Batch diversity check → second pass for underrepresented cells
         ↓
Output: labeled synthetic dataset
```

---

## What Is Out of Scope

- **Real-time fraud detection** — this system generates training data, it does not score live transactions
- **Unknown unknown discovery** — finding entirely novel fraud methods not yet categorized is a future capability
- **Model training** — the system produces data, it does not train or manage the institution's ML models
- **Data validation against live transaction data** — downstream model performance benchmarking requires the institution's real data and is outside the system boundary
