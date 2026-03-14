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

### The Core Rationale: Stop Patching, Start Out-Iterating

The conventional fraud defense posture is reactive: a fraud pattern is detected, controls are updated, the model is retrained. This is a patching loop — and it will always lag behind the attacker.

The insight driving this product is that patching is not the right frame. The right question is: *who can explore the attack surface faster?*

Fraudsters are fast because they are motivated and specialized. But they are fundamentally limited — they are individuals or small organizations with finite time and resources. A financial institution, by contrast, has compute at scale. The institution can run thousands of parallel simulations that a human fraudster could never attempt. The institutional advantage is not superior knowledge of fraud — it is superior capacity to explore the space of possibilities.

This product converts that compute advantage into a detection advantage by deploying it on the attacker's side of the problem, before the attacker gets there.

### The Red Team / Blue Team Model

The system is designed around the adversarial security concept of red teaming:

- **The Red Team** is the aggressor. Its job is to think like a fraudster — to probe, to vary tactics, to find the cases that would slip through existing controls. In this system, the red team is a set of AI agents actively generating fraud variants and stress-testing the edges of what detection models can catch.

- **The Blue Team** is the defender. Its job is to take what the red team surfaces and harden defenses against it — in this case, by training ML models on the synthetic data the red team produced. The blue team does not need to be rebuilt; it is the institution's existing fraud detection infrastructure. The red team feeds it.

The key idea is that the red team runs *continuously and proactively* — not in response to an attack that has already happened, but ahead of it. By the time a new fraud variant reaches real customers, the institution's model has already seen a version of it.

### The Aggressor Agent Architecture

At the core of the red team is an **orchestrator agent** that receives a fraud type description and decomposes it into the dimensions that define how that fraud can vary: who is targeted, what channels are used, how transactions are structured, what cover behavior is employed, and what evasion techniques are applied.

The orchestrator then spawns a fleet of **sub-agents**, each assigned to explore a specific point in that variant space. One agent simulates a mule network with three hops and same-day settlement. Another simulates five hops with randomized timing intervals. Another mixes fraudulent transfers with legitimate-looking noise transactions. Each agent generates a complete, realistic synthetic transaction sequence for its assigned variant and returns it as labeled training data.

This is the aggressor model: not one attack, but a coordinated sweep across the full space of possible attacks within a known fraud type.

### Why Agents — Not Statistical Synthesis

Existing synthetic data tools mirror existing data statistically. They generate more examples that look like what the institution already has. This does not address the known unknown gap — the problem is not that you need more examples of the fraud you have already seen, it is that you need examples of the variants you have not seen yet.

Agents reason about *how a fraudster would behave*. They can explore structurally different variants of the same fraud type: different logic, different sequencing, different evasion strategies. The output is not noise around existing data — it is coverage of unexplored territory. This is the core differentiation from statistical synthesis tools.

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

The adversarial framing resolves the core asymmetry. Fraudsters iterate. Static defenses do not. By deploying an agent system that iterates on the attacker's behalf — systematically, at scale, continuously — the institution flips the dynamic. The attacker's advantage was that they had already explored the attack surface before the defender knew to look. The red team closes that gap by exploring it first.

The institutional advantage is the unlock: a fraudster can probe a handful of variants before attempting an attack. The institution can simulate thousands. Scale, applied to the right problem, is the moat.
