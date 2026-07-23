# Multi-Agent Task Automation System

An orchestration layer coordinating specialized LLM agents (Planner, Executor, Verifier)
to complete multi-step tasks autonomously — research, summarization, and email drafting/sending —
with a supervisor handling error recovery, state management, observability, and human-in-the-loop
approval for high-stakes actions.

## Project Status
🚧 Phase 1: Project scaffolding, base agent architecture, state management, logging — complete.

## Architecture (evolving across phases)
- `agents/` — Planner, Executor, Verifier agent implementations (share a common `BaseAgent` interface)
- `core/` — task/agent/world state management, structured logging
- `config/` — environment and system settings
- `main.py` — entry point / orchestrator (added in Phase 2)

## Setup
\`\`\`
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
\`\`\`

