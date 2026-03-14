## FraudGen — Synthetic Fraud Variant Generator

FraudGen is a hackathon prototype for **TD Best AI Hack — Detect Financial Fraud**.

It simulates a **Red Team of AI agents** that generates realistic, labeled **synthetic fraud variants** to help banks close the “known unknown” gap in ML-based fraud detection. The output is a structured dataset that can be fed into an institution’s existing fraud models.

### High‑Level Workflow

- **Describe a fraud pattern** in natural language (e.g., “layered 3‑hop mule account network with burst withdrawals”).
- **Orchestrator agent** decomposes the description into variation dimensions (hop count, timing, topology, cover behaviour, etc.) and proposes coverage cells.
- **Sub‑agent fleet** explores those cells and generates full synthetic transaction sequences per variant.
- **Console UI** lets you monitor progress, inspect variants, visualize networks/coverage, and export a training dataset.

### Requirements

- **Python**: 3.10+ recommended
- **Dependencies**: managed via `requirements.txt` (typical stack includes `streamlit`, `anthropic`, `pydantic`, `pandas`, `networkx`, `plotly`, etc.)
- **Anthropic API key**:
  - Set `ANTHROPIC_API_KEY` in your environment for live calls.
  - Or set `FRAUDGEN_MOCK=1` to use the built‑in mock mode (no external API calls, useful for demos and development).

### Setup

```bash
git clone <this-repo-url>
cd GenAi
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

Configure your environment:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."   # for real runs
# or
export FRAUDGEN_MOCK=1                 # for fully local mock mode
```

### Running the App

FraudGen ships with a Streamlit console defined in `app.py`.

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (usually `http://localhost:8501`) in your browser.

### Using the Console

- **Input phase**:
  - Enter a natural‑language description of the fraud type.
  - Choose number of variants, fidelity level, and parallelism.
  - (Optional) Adjust advanced orchestrator controls in the side panel.
- **Running phase**:
  - Watch variants being generated and controlled (pause/resume/stop).
  - See progress and current phase in the sidebar.
- **Results phase**:
  - Review aggregate stats for generated variants.
  - Inspect network graphs and coverage matrix.
  - Browse the synthetic dataset and **export** CSV/JSON files for ML training.

You can also trigger a preconfigured **demo run** from the main screen or by appending `?demo=true` to the Streamlit URL.

### Project Docs

For a deeper architecture and product overview, see:

- `CLAUDE.md` — guidance for AI agents working on this repo
- `PRD/01_problem_and_solution.md` — problem statement and solution outline
- `PRD/05_architecture_draft.md`
- `PRD/06_api_and_console_draft.md`
- `PRD/07_user_flow_and_console.md`

### Notes & Limitations

- This is a **hackathon‑stage prototype**; interfaces and internals may change rapidly.
- Generated data is **synthetic** and should be validated and calibrated before use in production risk models.
- The system is designed to be **additive** to existing fraud detection pipelines, not a replacement.

