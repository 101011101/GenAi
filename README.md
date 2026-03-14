FraudGen — Synthetic Fraud Variant Generator
Bridging the Gap in Machine Learning Fraud Detection via Agentic Simulation

FraudGen is a high-fidelity simulation framework designed for the TD Best AI Hack — Detect Financial Fraud. It addresses the "cold start" problem in financial security: the difficulty of training machine learning models to detect novel fraud patterns that have not yet occurred in historical datasets.

By utilizing a coordinated Red Team of autonomous AI agents, FraudGen generates structured, labeled synthetic datasets that mirror the complexity of modern financial crimes, allowing institutions to strengthen their defenses against "known unknown" threats.

High-Level Workflow and Agent Logic
FraudGen employs an agentic architecture to ensure that synthetic data is not just random noise, but a collection of logical, adversarial transaction sequences.

Natural Language Specification: Users define a fraud hypothesis in plain English (e.g., "A sophisticated account takeover followed by rapid layering through multiple internal accounts and a final external wire transfer to a high-risk jurisdiction").

The Orchestrator Agent: This lead agent acts as the system architect. it parses the natural language input into a structured simulation plan, identifying key dimensions such as network topology, transaction velocity, obfuscation techniques, and "noise" injection.

The Generation Fleet: A specialized swarm of sub-agents executes the plan. Each agent is responsible for simulating a specific "entity" or "actor" within the fraud network, ensuring that transaction timestamps, amounts, and metadata (IP addresses, device IDs) remain consistent and realistic.

The Command Center: A unified Console UI built in Streamlit provides real-time visibility into the generation process, allowing users to inspect the logic behind specific variants before they are finalized.

Technical Requirements
Python: Version 3.10 or higher.

Core Libraries:

Generation: anthropic (Claude 3/3.5 models), pydantic (Data validation).

Processing: pandas (Data manipulation), numpy (Statistical modeling).

Visualization: networkx (Graph theory/Topology), plotly (Interactive charting).

Interface: streamlit (Web-based console).

API Configuration:

Live Mode: Requires an ANTHROPIC_API_KEY for high-reasoning synthetic generation.

Mock Mode: Enable FRAUDGEN_MOCK=1 to run the system locally for testing, UI development, or demonstrations without external API costs.

Setup and Configuration
Bash
# Clone the repository and enter the directory
git clone <this-repo-url>
cd GenAi

# Initialize a virtual environment for dependency isolation
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install the required software stack
pip install -r requirements.txt
Environment Variables:

Bash
# Option A: Real-world generation (Requires Anthropic credits)
export ANTHROPIC_API_KEY="sk-ant-..."

# Option B: Development/Demo mode (No cost, local data generation)
export FRAUDGEN_MOCK=1
The Interactive Console
Launch the FraudGen Command Center to manage the simulation lifecycle:

Bash
streamlit run app.py
1. Configuration Phase
Users can tune the "Fidelity vs. Variety" slider. Higher fidelity results in more computationally expensive reasoning to ensure transactions bypass basic heuristic filters, while higher variety explores a wider range of edge cases and topologies.

2. Live Monitoring Phase
The console displays a real-time log of agent activity. You can witness the "thought process" of the Orchestrator as it adjusts parameters to meet the user's fraud description. Users can pause the fleet at any time to inspect a specific transaction sequence.

3. Intelligence and Export Phase
Network Graphs: Visualize the flow of funds through mule accounts and shell companies using interactive 2D/3D plots.

Coverage Matrix: See how well the generated data covers different "risk dimensions" (e.g., geography, time-of-day, amount ranges).

Data Synthesis: Export the final results into standardized CSV or JSON formats, ready for ingestion by Scikit-Learn, PyTorch, or existing enterprise fraud engines.

Internal Architecture and Documentation
For developers looking to extend the agentic logic or integrate new LLM providers, refer to the following internal documentation:

CLAUDE.md: Contains specific system prompts and formatting instructions for the AI agents to ensure consistent data output.

PRD/05_architecture_draft.md: Breaks down the state management and communication protocols between the Orchestrator and the Generation Fleet.

PRD/06_api_and_console_draft.md: Technical specifications for the Streamlit components and API endpoints.

Notes and Safety
Prototype Status: This tool is a hackathon-stage prototype. While the generation logic is robust, the internal interfaces are subject to breaking changes as the project evolves.

Synthetic Nature: All data produced by FraudGen is mathematically generated. It contains no PII (Personally Identifiable Information) and is intended for model training and stress-testing only.

Integration: This system is designed to complement existing fraud detection pipelines by providing "Adversarial Data Augmentation." It is not a replacement for real-time monitoring systems.
