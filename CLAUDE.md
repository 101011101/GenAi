# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**TD Best AI Hack — Detect Financial Fraud**

A hackathon prototype demonstrating an adversarial AI agent system that generates synthetic fraud variant data to close the "known unknown" gap in ML-based fraud detection.

**Core concept:** Deploy a Red Team of AI agents that proactively explores fraud variant space ahead of real attackers, producing labeled synthetic training data for a Blue Team (the institution's existing ML fraud detection pipeline).

## Architecture

### System Components

1. **Orchestrator Agent** — Receives a natural language fraud type description (e.g., "layered mule account network") and decomposes it into variable dimensions:
   - Who is targeted
   - What channels are used
   - How transactions are structured
   - What cover behavior is employed
   - What evasion techniques are applied

2. **Sub-Agent Fleet** — Each sub-agent explores a specific point in the variant space (e.g., "3-hop mule network, same-day settlement" vs "5-hop, randomized timing"). Each generates a complete synthetic transaction sequence for its assigned variant.

3. **Output** — A labeled synthetic dataset ready for ML training, with metadata describing which variant each record represents.

### Key Design Decisions

- **Agents over statistical synthesis:** Statistical tools mirror existing data; agents reason about fraudster behavior and explore structurally different variants — covering unexplored territory, not noise around known data.
- **Additive, not disruptive:** Output plugs into the institution's existing fraud detection infrastructure; the system fills the data gap, not replace the model.
- **Proactive, not reactive:** Red team runs continuously ahead of real attacks, not in response to them.

## PRD

The full problem statement and solution architecture is in `PRD/01_problem_and_solution.md`.

## Development Notes

This project is in early-stage implementation. When building out:

- The orchestrator and sub-agents should use the Claude API (Anthropic SDK) for LLM reasoning
- Transaction sequences must be realistic and structurally diverse across variants
- Output format should be a labeled dataset with per-record variant metadata
