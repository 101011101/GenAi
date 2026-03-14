# 01 — Problem & Solution

## Context

TD Best AI Hack — Detect Financial Fraud
Scope: Hackathon prototype demonstrating a production-viable concept

---

## The Problem

### Fraud Detection Relies on ML — ML Relies on Data

Banks and financial institutions defend against fraud using machine learning models trained on historical transaction data. These models are effective against fraud patterns they have seen before. The fundamental assumption is: *if it happened before, we can detect it again*.

This assumption breaks down at the edges.

### The Data Scarcity Problem

Fraud is rare by design — typically less than 0.1% of transactions. New or emerging fraud variants are rarer still. A fraud type that surfaced six months ago might have generated only dozens of confirmed labeled examples at a given institution. No ML model can generalize from dozens of examples.

The standard response is to wait — accumulate more data, retrain, redeploy. In the meantime, the fraud continues undetected.

### The Information Asymmetry Problem

Fraudsters have a structural advantage: they know exactly what they are targeting. They have studied the institution's controls, tested the edges, and adapted their methods before the institution even knows an attack is happening. This is the attacker's advantage.

Institutions, by contrast, are defending against patterns they have already seen. Every new fraud variant starts with a detection gap — a window where the model has no signal.

### Why Institutions Cannot Simply Share Data

The obvious fix — pool fraud data across institutions so everyone benefits from the full picture — is blocked by regulatory constraints, competitive concerns, and customer privacy obligations. Each institution trains on its own siloed dataset. A fraud pattern that Bank A has seen extensively may be entirely novel to Bank B.

### The Known Unknown Gap

Fraud problems exist on a spectrum:

| Tier | What It Means | ML Status |
|---|---|---|
| Known known | We know the fraud type and have abundant examples | Well-solved |
| **Known unknown** | We know the fraud type exists but lack enough variant data | **Active gap** |
| Unknown unknown | Entirely novel fraud methods not yet conceived | Research problem |

The known unknown tier is where institutions are most exposed right now. They know mule networks exist — but each criminal organization structures them differently. They know synthetic identity fraud happens — but the specific execution patterns vary infinitely. The model learned the three cases it has seen. The fourth one gets through.

---

## The Solution

### Synthetic Fraud Data Generation via Adversarial Agents

We are building an agentic system that takes a known fraud type as input and produces diverse, labeled synthetic transaction data as output — specifically targeting the known unknown gap.

The system operates as a **red team**: a set of AI agents that reason like fraudsters, exploring the full space of how a known fraud type could be executed. Each agent explores a different variant — different timing, different structuring, different evasion behavior — and generates realistic synthetic transactions for that variant.

The output is training data. It feeds directly into a bank's existing ML pipeline, expanding the model's coverage from "the cases we have seen" to "the space of cases that are possible."

### Why Agents — Not Statistical Synthesis

Existing synthetic data tools mirror existing data statistically. They generate more examples that look like what you already have. This does not help with known unknowns — you need examples of things you have not seen yet.

Agents reason about *how a fraudster would behave*. They can explore structurally different variants of the same fraud type, not just noisy copies of the same pattern. This is the core differentiation.

### The Scope for This Hackathon

Full red-team capability — discovering entirely new fraud methods — is a larger research problem. This prototype focuses on the known unknown tier:

- **Input:** A natural language description of a known fraud type (e.g., "layered mule account network used to launder funds across multiple banks")
- **Process:** An orchestrator agent decomposes the fraud type into its variable dimensions. Sub-agents each explore a distinct variant within those dimensions, generating synthetic transaction sequences that are realistic, diverse, and labeled.
- **Output:** A labeled synthetic dataset ready for ML training, with metadata describing which variant each record represents.

### Who This Is For

Any financial institution running ML-based fraud detection that encounters a new or emerging fraud pattern and does not have enough labeled data to retrain their model. The immediate use case is fraud teams and data science teams at banks — but the same model applies to payment processors, insurers, and any institution with a fraud surface.

---

## Why This Works

The system does not try to replace the institution's fraud model. It fills the data gap that prevents the model from being effective against new patterns. It is additive, not disruptive — the output plugs into existing infrastructure.

The adversarial framing is key. A fraudster does not generate one attack — they probe, iterate, and adapt. The agent system mirrors that behavior, producing coverage across the variant space rather than a single synthetic pattern. The institution stops defending against what it has seen and starts training against what is possible.
