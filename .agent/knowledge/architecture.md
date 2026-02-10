---
title: System Architecture – ELK + Elastic MCP Log Assistant
description: High‑level architecture and data flow for this project.
---

## Overview

This repository implements an observability assistant that lets a user ask natural‑language questions about application logs. It consists of:

- a **dummy backend** that emits structured JSON logs,
- an **Elastic stack** (Elasticsearch, Kibana, Filebeat),
- an **Elastic MCP server** exposing tools over HTTP,
- a **Python chat layer** (CLI + Streamlit UI) that orchestrates an LLM (Ollama) and the MCP tools.

The typical question flow is: **User → UI/CLI → Ollama (intent) → MCP tools → Ollama (answer) → User**.

## Services and Components

### Docker services (`docker-compose.yml`)

- **backend**
  - Image built from `backend/Dockerfile`.
  - Runs `backend/app.py`, which continuously writes ECS‑friendly JSON log lines to `/var/log/app/app_ecs.log` (mounted from the local `logs/` directory).

- **elasticsearch**
  - Official `elasticsearch:8.12.2` single‑node.
  - Security is enabled with username `elastic` and password `changeme`.

- **kibana**
  - `kibana:8.12.2`, pointing at the `elasticsearch` service.

- **filebeat**
  - `filebeat:8.12.2`, configured by `filebeat/filebeat.yml`.
  - Reads `/var/log/app/app_ecs.log` from the shared `logs/` volume.
  - Sends documents to Elasticsearch into index pattern `logs-dummy-backend-*`.

- **elastic_mcp**
  - `docker.elastic.co/mcp/elasticsearch:0.4.0`.
  - Exposes an HTTP‑based MCP endpoint on `http://localhost:8080/mcp`.
  - Authenticates to Elasticsearch using an API key (`ES_API_KEY`).

### Backend log generator (`backend/app.py`)

- Produces one JSON log line roughly every 0.5 seconds.
- Fields include:
  - `@timestamp` (UTC ISO‑8601),
  - `service.name`, `log.level`,
  - `route`, `status`, `latency_ms`, `user_id`, `message`, `trace.id`.
- Log output path is configured via `LOG_PATH` env var (defaults to `/var/log/app/app.log` outside Docker; overridden to `logs/app_ecs.log` via docker‑compose).

### Ingestion pipeline (`filebeat/filebeat.yml`)

- Reads from `/var/log/app/app_ecs.log`.
- Uses Filebeat JSON settings (`json.keys_under_root: true`) so log fields become top‑level document fields in Elasticsearch.
- Writes to `logs-dummy-backend-%{+yyyy.MM.dd}` with an index template named `logs-dummy-backend`.

### Chat / LLM orchestration (`chat/` package)

- **Config (`chat/config.py`)**
  - `MCP_URL`: `http://localhost:8080/mcp`.
  - `OLLAMA_URL`: local Ollama HTTP endpoint.
  - `MODEL`: default LLM model name (e.g. `gpt-oss:120b-cloud`).
  - `DEFAULT_LOG_INDEX_PATTERN`: default index pattern for ES|QL queries (`logs-dummy-backend*`).

- **MCP client (`chat/services/mcp_client.py`)**
  - Sends JSON‑RPC requests (`tools/list`, `tools/call`) to the MCP HTTP endpoint.
  - Streams SSE responses and extracts the first `data:` event.
  - `extract_human_text` converts the MCP result payload into human‑readable text (prefers the last `content[].text` field).

- **Ollama client (`chat/services/ollama_client.py`)**
  - Simple wrapper around `OLLAMA_URL` with a `generate(prompt, stream, timeout)` method.
  - Always returns the `.response` field from Ollama’s JSON.

- **Orchestration (`chat/orchestrator/agent.py`)**
  - `detect_intent(question, tools, ollama)`
    - Builds a system prompt from `chat/prompts/intent_prompt.py` describing available MCP tools and how to use them.
    - Calls Ollama and parses a JSON object with `tool_calls` using `chat/parsing/intent_parser.py`.
  - `execute_tool_calls(intent, mcp_client)`
    - Iterates `tool_calls`, calling each MCP tool via `MCPClient.call_tool`.
    - Returns a list of `{name, arguments, raw_response, extracted_text}` records.
  - `build_context_from_executions(executions)`
    - Formats tool calls + results into a concise context string.
  - `answer_from_context(question, context, ollama)`
    - Builds an answer‑prompt (`chat/prompts/answer_prompt.py`) and calls Ollama again to generate the final natural‑language answer.

- **Prompts (`chat/prompts/*.py`)**
  - `intent_prompt.build_intent_prompt(tools)`:
    - Explains available MCP tools (names, params, examples).
    - Instructs the LLM to return a strict JSON object with `tool_calls` only (no extra text/markdown).
  - `answer_prompt.build_answer_prompt(question, context)`:
    - Poses the user question and MCP context, instructing the LLM to answer clearly, highlight trends/anomalies, and stay in plain English.

- **User interfaces**
  - `chat/ui.py`:
    - Streamlit app titled “Elastic MCP Log Assistant”.
    - Lets users ask a question, shows chosen tool calls and MCP results (optional), and streams the final answer.
  - `chat/cli.py`:
    - CLI entrypoint: `python -m chat.cli "your question"`.
    - Prints the chosen tools, raw MCP results, and the final answer to stdout.

## Data Flow Summary

1. **Log generation**: `backend/app.py` writes JSON logs into the `logs/` directory.
2. **Ingestion**: Filebeat tails the log file and sends events into Elasticsearch (`logs-dummy-backend-*` indices).
3. **Tool exposure**: The Elastic MCP server exposes Elasticsearch queries and utilities as MCP tools over HTTP.
4. **Question handling**:
   - UI/CLI collects a user question.
   - Ollama chooses MCP tool calls (`esql`, `list_indices`, etc.) via `detect_intent`.
   - MCP tools are executed via `MCPClient`.
   - The results are summarized into a text context for the LLM.
   - Ollama uses that context to generate a final answer.

Understanding this flow is essential when modifying prompts, adding tools, changing index patterns, or debugging incorrect answers.

