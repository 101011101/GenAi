# FraudGen — Synthetic Fraud Variant Generator

## Project Inspiration

Fraud detection at financial institutions relies on machine learning models trained on historical transaction data. These models work well against patterns they've seen before — but break down against new variants. This is the **"known unknown" gap**: institutions know fraud types like mule networks exist, but each criminal organization structures them differently, and a model trained on three observed variants will miss the fourth.

The data scarcity problem makes this worse. Fraud is rare by design (< 0.1% of transactions), and emerging variants produce only dozens of labeled examples — far too few for any ML model to generalize from. The standard response is to wait, accumulate more data, retrain, and redeploy. Meanwhile, the fraud continues undetected.

Institutions can't simply share fraud data across organizations due to regulatory constraints, competitive concerns, and privacy obligations. Each institution trains on its own siloed dataset.

**FraudGen flips the dynamic.** Instead of waiting for fraud to happen and then reacting, FraudGen deploys a Red Team of AI agents that proactively explores the fraud variant space *ahead of real attackers*. The insight is that fraudsters are fast but fundamentally limited — they're individuals with finite time. An institution has compute at scale. FraudGen converts that compute advantage into a detection advantage by generating structurally diverse synthetic fraud data before the attacker gets there.

This is inspired by the adversarial security concept of red teaming and builds on industry precedent like IBM's AMLSim — but uses adversarial LLM agents instead of statistical simulation, enabling reasoning-based exploration of novel execution strategies rather than just statistical variation around known patterns.

## Technology Stack

### Languages
- **Python 3.10+** — Primary language for the entire stack

### Frameworks and Libraries
- **Anthropic SDK** (`anthropic`) — Claude API for all LLM-powered agent reasoning
- **Streamlit** — Interactive web console for the analyst-facing UI
- **Pydantic** — Data validation and schema enforcement across the pipeline
- **Pandas** — Dataset compilation and CSV/JSON export
- **NetworkX** — Graph theory for fraud network topology visualization
- **Matplotlib** — Network graph rendering
- **PyArrow** — High-performance data serialization

### Platforms
- **Anthropic Claude API** — Powers all four AI agents (Orchestrator, Persona Generator, Fraud Constructor, Critic) using Claude Haiku for fast inference

### Tools
- **asyncio** — Concurrent variant generation with semaphore-based flow control
- **Git/GitHub** — Version control and collaboration
- **Claude Code** — AI-assisted development

## Product Summary

FraudGen is a synthetic fraud data generation pipeline that takes a natural language description of a known fraud type and produces a diverse, labeled synthetic transaction dataset ready for ML training.

### How It Works

1. **Natural Language Input** — A fraud analyst describes a fraud hypothesis in plain English (e.g., "layered mule account network used to launder funds across multiple banks")

2. **Orchestrator Agent** — Decomposes the fraud type into structural variation dimensions (network topology, transaction velocity, evasion techniques, extraction methods) and generates a coverage matrix of cells to explore

3. **Persona Generator** — Creates distinct criminal personas with different risk tolerances, resources, and operational constraints — because a cautious solo operator structures fraud fundamentally differently than an aggressive organized crime network

4. **Fraud Constructor Fleet** — A parallel fleet of sub-agents each executes a 5-step reasoning chain (persona analysis → network planning → participant profiles → transaction generation → self-review) to produce complete synthetic transaction sequences. Each agent explores a different point in the variant space

5. **Critic Agent** — An independent quality gate scores each variant on realism, distinctiveness, persona consistency, and label correctness. Variants below threshold are sent back for revision with specific feedback

6. **Export** — Approved variants are compiled into labeled CSV and JSON datasets with per-record variant metadata, ready for ingestion by existing fraud detection ML pipelines

### Key Features

- **Live Monitoring Console** — Real-time visibility into agent activity, variant completion, critic scores, and coverage matrix saturation via Streamlit
- **Coverage Matrix** — Ensures the generated data covers the full variant space (different hop counts, topologies, extraction methods, timing patterns) rather than clustering around common patterns
- **Pause/Stop Controls** — Analysts can pause or stop generation mid-run
- **Cost Tracking** — Real-time cost accumulation with configurable cost caps
- **Demo Mode** — Pre-configured quick-start that completes in ~60 seconds for demonstrations
- **Mock Mode** — Full offline pipeline testing without API costs (`FRAUDGEN_MOCK=1`)

### What Makes It Different

Unlike statistical synthesis tools (like IBM AMLSim) that generate more examples of what you already know, FraudGen's agents *reason about how a fraudster would behave*. They explore structurally different variants — different network topologies, different evasion logic, different timing strategies — producing coverage of unexplored territory rather than noise around existing data.

## Setup

```bash
# Clone and enter the repository
git clone <this-repo-url>
cd GenAi

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set API key for live generation
export ANTHROPIC_API_KEY="sk-ant-..."

# Or use mock mode for offline testing
export FRAUDGEN_MOCK=1

# Launch the console
streamlit run app.py
```

## AI Use

Yes — more than 70% of the code was generated by AI (Claude Code).
