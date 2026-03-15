# FraudGen — Pitch Document

## The hook (say this first, say nothing else)

> "Every fraud ML model in production today is reactive. It learned from attacks that already happened.
> We built the system that sees the attacks before they happen."

---

## The problem (60 seconds)

**Setup the tension:**
Fraud detection at banks runs on ML. ML runs on data. But fraud data has a fundamental problem.

- Fraud is rare by design — less than 0.1% of transactions
- New fraud variants are rarer still — maybe 30–50 confirmed cases at a given institution
- GNNs (the best model for network fraud) need 1,000–5,000 examples minimum
- **The gap: 20–100×**

Banks know this gap exists. They even know *what* the fraud type is. They just don't have enough data to train against it. That's the **known-unknown** — and it's where every new fraud attack starts.

The conventional response: wait. Accumulate more real fraud data. Retrain. Meanwhile, the fraud continues undetected.

---

## The insight (30 seconds)

Ask: *"Who can explore the attack surface faster — the fraudster or the institution?"*

A fraudster is fast because they're motivated and specialized. But they're one person, or a small organization. They can probe a handful of variants before striking.

A financial institution has **compute at scale**. It can simulate thousands of variants in parallel.

The institution has always had this advantage. Nobody was using it on the attacker's side of the problem.

---

## The solution (90 seconds)

**FraudGen deploys an AI red team that thinks like a fraudster — ahead of real attackers.**

It's a fleet of AI agents built on Claude that:

1. **Decomposes** a fraud type into every dimension it can vary across: hop count, timing, network topology, evasion techniques, extraction method
2. **Generates criminal personas** — distinct behavioral profiles that seed structurally different fraud logic
3. **Runs parallel agents** — each exploring a specific point in the fraud variant space, generating a complete, realistic synthetic transaction sequence
4. **Quality-gates output** — a Critic agent scores realism and distinctiveness; weak variants get revised or discarded
5. **Outputs a labeled dataset** — CSV, JSON, and graph adjacency list, ready to feed directly into the bank's existing ML training pipeline

The key differentiator: **agents reason about fraudster behavior**. They don't mirror statistics. They explore structurally novel variants that statistical synthesis tools can't reach.

---

## The demo beat (what to point at — see demo_strategy.md)

> "Let me show you what this looks like running."

1. Show the input — natural language fraud description
2. Show the orchestrator decomposing it into dimensions live
3. Show agents running in parallel — the coverage matrix filling
4. Show a variant completing — persona, parameters, critic score
5. Show the output table — real transactions, labeled, ready for ML
6. Show the network graph — visual proof the topology is structurally diverse

---

## Why not statistical synthesis (30 seconds)

IBM AMLSim and tools like it generate statistical noise around known patterns.
That solves the wrong problem.

| | Statistical tools | FraudGen |
|---|---|---|
| What they generate | More of what you know | What you don't know yet |
| Evasion logic | None | Explicit — agents reason about controls |
| Variant diversity | Statistical variation | Structural exploration |
| Coverage guarantee | None | Coverage matrix |

---

## The business case (30 seconds)

- **Additive, not disruptive** — output plugs into existing ML pipelines. No rip-and-replace.
- **Proactive, not reactive** — runs continuously ahead of real attacks, not in response to them
- **Cost** — ~$5 per 100 labeled variants via Claude API. Compare to cost of a single fraud incident.
- **Target users** — fraud teams and data science teams at any financial institution running ML-based fraud detection

---

## The closer

> "Fraudsters iterate. Static defenses don't. We built the system that lets institutions iterate faster — before the attack, not after it."

> "We are the all-seeing eye."

---

## Anticipated questions

**Q: Isn't this just synthetic data? How do you know it's realistic?**
A: Two validation layers — a deterministic constraint checker (8 rules: valid channels, amount floors, timestamp ordering, regulatory thresholds) and a Critic LLM agent that scores realism 1–10 with a floor of 7. Only variants that pass both make it into the dataset.

**Q: What stops this from being used for actual fraud?**
A: All output is synthetic labeled training data — not instructions or tools. The system generates what transactions *would look like* if fraud occurred. There are no real accounts, no real funds, no PII. It's the same category as a red team pen test report.

**Q: Can it generalize beyond mule networks?**
A: Yes. The orchestrator takes any natural language fraud description. Mule networks are the demo case because they have the largest data gap and the most structural variation. APP fraud, synthetic identity, account takeover — same pipeline.

**Q: Why Claude specifically?**
A: Extended thinking in the orchestrator is key — decomposing fraud types into variation dimensions requires multi-step reasoning that benefits from a longer thinking budget. Sonnet handles persona generation and fraud construction. Haiku is used for rule validation (fast and cheap).
