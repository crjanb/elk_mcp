---
title: ELK + Elastic MCP + Chat UI – Agent Rules
description: High-level guidance for LLM agents working in this repository.
---

## Purpose

This repo is a demo observability assistant that uses:
- a dummy Python backend that emits structured logs,
- an Elastic stack (Elasticsearch + Kibana + Filebeat),
- an Elastic MCP server exposing tools over HTTP,
- a Python/Streamlit UI and CLI that orchestrate an LLM (Ollama) + MCP.

These rules tell LLM agents how to reason about and modify this project.

## Core Behaviors

- **Explain changes**: When editing code or config, describe *why* as well as *what*.
- **Preserve architecture**: Keep the current flow – backend → logs → Filebeat → Elasticsearch → Elastic MCP → `chat` clients.
- **Prefer small, testable changes**: Avoid broad refactors unless explicitly requested.
- **Avoid secrets**: Never hard-code real secrets or API keys; use placeholders and document where to set them.

## Project Entry Points

- **Docker / Infra**
  - `docker-compose.yml`: spins up `backend`, `elasticsearch`, `kibana`, `filebeat`, and `elastic_mcp`.
  - `filebeat/filebeat.yml`: ships log files from `./logs` into Elasticsearch.
- **Log Producer**
  - `backend/app.py`: generates ECS-style JSON logs to `$LOG_PATH` (default `logs/app.log` or `logs/app_ecs.log` in Docker).
- **Chat / LLM Orchestration**
  - `chat/ui.py`: Streamlit UI for the Elastic MCP Log Assistant.
  - `chat/cli.py`: CLI interface for asking questions about logs.
  - `chat/orchestrator/agent.py`: intent detection, MCP tool execution, context building, final answer generation.
  - `chat/services/mcp_client.py`: low-level client for Elastic MCP HTTP endpoint.
  - `chat/services/ollama_client.py`: Ollama HTTP client (not shown above but required for LLM calls).
  - `chat/prompts/*`: system prompts for intent classification and answer generation.
  - `chat/parsing/intent_parser.py`: parses LLM JSON describing tool calls.
  - `chat/tools/*`: helpers for formatting and normalizing MCP tool metadata.

## When Modifying Behavior

- **Changing log schema**
  - Update `backend/app.py` but keep outputs JSON and ECS-friendly (e.g., `@timestamp`, `service.name`, `log.level`).
  - If you add fields, ensure Filebeat and ES mappings still ingest them without errors.

- **Changing ES|QL / search behavior**
  - Default log index pattern lives in `chat/config.py` as `DEFAULT_LOG_INDEX_PATTERN`.
  - Keep prompts in `chat/prompts/intent_prompt.py` and `chat/prompts/answer_prompt.py` aligned with the index pattern and tools exposed by MCP.

- **Changing MCP tools usage**
  - `chat/services/mcp_client.py` should remain a thin HTTP JSON-RPC client.
  - Any new logic selecting tools or arguments belongs in the orchestrator (`chat/orchestrator/agent.py`) and prompts (`chat/prompts/`).

## Safety & Local Development

- **Docker usage**
  - Prefer updating `docker-compose.yml` rather than introducing new ad‑hoc scripts.
  - Do not change default Elasticsearch credentials or API key behavior without updating `README.md` and related `.agent/knowledge` docs.

- **Ollama**
  - The model name and base URL (`MODEL`, `OLLAMA_URL`) live in `chat/config.py`.
  - If you change models, ensure prompts and timeouts are still reasonable.

## How To Use These Agent Docs

- **Start with** `.agent/knowledge/architecture.md` for an overview.
- **Use** `.agent/tasks/*.md` as step‑by‑step guides for common operations (running the stack, debugging MCP, extending the assistant).
- **Reuse** `.agent/templates/*.md` when adding new MCP tools, ES|QL flows, or answering patterns to keep behavior consistent.

