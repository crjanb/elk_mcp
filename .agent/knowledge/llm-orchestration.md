---
title: LLM + MCP Orchestration Details
description: How the chat layer uses Ollama and Elastic MCP to answer questions.
---

## High‑level loop

For each user question (via Streamlit UI or CLI), the system performs:

1. **Fetch tools from MCP** using `MCPClient.fetch_tools_normalized()`.
2. **Ask the LLM to choose tools** (`detect_intent`):
   - Provide a system prompt listing tools and rules (`build_intent_prompt`).
   - Provide the user question.
   - Expect a JSON object: `{"tool_calls": [{ "name": "...", "arguments": {...} }, ...]}`.
3. **Execute chosen tools** (`execute_tool_calls`):
   - For each `tool_calls[i]`, call the MCP server via `tools/call`.
   - Extract human‑readable text from the response.
4. **Build context and answer**:
   - Concatenate tool calls + results into a context string (`build_context_from_executions`).
   - Ask the LLM for a final answer with `answer_from_context`.

## Key Functions and Responsibilities

- **`chat/orchestrator/agent.py`**
  - `detect_intent(question, tools, ollama)`
    - Inputs: natural‑language `question`, list of normalized tools, Ollama client.
    - Output: `(raw_llm_output, parsed_intent_dict_or_none)`.
  - `execute_tool_calls(intent, mcp_client)`
    - Inputs: parsed intent, MCP client.
    - Output: list of execution records.
  - `build_context_from_executions(executions)`
    - Formats arguments and results into a compact, readable context string.
  - `answer_from_context(question, context, ollama)`
    - Builds an answer‑style prompt and invokes Ollama.

- **`chat/services/mcp_client.py`**
  - Implements low‑level HTTP+SSE protocol for MCP (`tools/list`, `tools/call`).
  - Converts MCP response structures into plain text where possible.

- **`chat/services/ollama_client.py`**
  - Single `generate` method that POSTs `{model, prompt, stream}` to Ollama.

- **`chat/prompts/intent_prompt.py` and `chat/tools/format.py`**
  - Encode *how* tools should be used (parameters, examples, allowed index patterns).

- **`chat/parsing/intent_parser.py`**
  - Makes the system robust to LLM formatting issues (e.g., stripping ```json fences).

## Error Handling Patterns

- **Tool discovery errors**
  - `MCPToolsError` signals failures to reach the MCP server or parse its responses.
  - UI / CLI catch this and present a clear error message to the user.

- **Bad LLM intent outputs**
  - If `parse_intent_response` returns `None` or `tool_calls` is empty:
    - UI: writes a diagnostic message (including raw LLM output).
    - CLI: prints the raw response and exits without calling MCP tools.

- **MCP call issues**
  - Exceptions from HTTP / JSON are caught and re‑raised as `MCPToolsError` or surfaced via error text.

## Tuning Guidelines

- **Context length**
  - UI uses `trim_context` to enforce a maximum number of characters sent to the LLM.
  - If responses become slow or truncated, adjust `max_context_chars` via the sidebar slider.

- **Model choice**
  - Controlled by `MODEL` in `chat/config.py`.
  - Heavier models may yield better ES|QL but slower responses.

- **Prompt adjustments**
  - To change *which tools* are preferred:
    - Edit examples and rules in `build_intent_prompt`.
  - To change *how answers are phrased*:
    - Edit instructions in `build_answer_prompt`.

Understanding this orchestration is critical before adding new tools, changing prompts, or debugging incorrect or missing tool calls.

