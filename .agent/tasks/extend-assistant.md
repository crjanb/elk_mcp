---
title: Extend the Elastic MCP Log Assistant
description: How to add new capabilities or adjust behavior safely.
---

## 1. Add or modify MCP tools

Elastic MCP exposes tools such as `esql`, `list_indices`, `get_mappings`, etc. To change what the assistant can do:

- **Add tools on the MCP side**
  - Modify the Elastic MCP configuration (outside this repo) so new tools are available via `tools/list`.
  - Confirm with:
    - `MCPClient.fetch_tools_raw()` (or just run the UI/CLI and inspect the “Tool calls” section).

- **Normalize new tools for prompts**
  - `chat/tools/normalize.py` converts MCP tool schemas into a uniform format (`name`, `description`, `required`, `optional`, `params`).
  - Ensure your new tool’s `inputSchema` has good `description` strings for each parameter so the prompt can describe them clearly.

## 2. Teach the LLM how to use new tools

The LLM chooses tools via `detect_intent`:

- Update `chat/prompts/intent_prompt.py`:
  - Ensure `format_tools_for_prompt` in `chat/tools/format.py` correctly renders new tools.
  - Add or adjust **rules and examples** in the prompt to show when to use new tools.
  - Keep examples in strict JSON form:

```json
{"tool_calls": [{"name": "your_tool", "arguments": {"param": "value"}}]}
```

The `intent_parser` (`chat/parsing/intent_parser.py`) expects a single JSON object and strips markdown fences if present.

## 3. Adjust default index pattern or search behavior

- The default log index pattern is defined in `chat/config.py` as `DEFAULT_LOG_INDEX_PATTERN`.
- If you rename indices or add more sources:
  - Update `DEFAULT_LOG_INDEX_PATTERN`.
  - Update examples in `intent_prompt.build_intent_prompt` to match the new pattern(s).
  - Optionally add logic to your MCP tools so they handle multiple indices or index aliases.

## 4. Change answer style or summarization

- Edit `chat/prompts/answer_prompt.py` to adjust:
  - Tone (e.g., shorter/longer answers),
  - Required structure (bullets vs paragraphs),
  - Emphasis (e.g., always call out anomalies).

- If adding richer context:
  - Update `build_context_from_executions` in `chat/orchestrator/agent.py` to include new metadata or multi‑tool summaries.
  - For large contexts, keep `trim_context` in `chat/ui.py` conservative to avoid hitting model context limits.

## 5. Add guardrails or validation

- **Before calling MCP tools**:
  - Add validation on `intent["tool_calls"]` in `detect_intent` or just before `execute_tool_calls`.
  - Example: enforce that ES|QL queries reference only allowed indices.

- **After MCP responses**:
  - Wrap `MCPClient.call_tool` with additional checks (e.g., detect errors in `result.content` and surface them clearly to the user).

## 6. Testing changes

Basic manual test loop:

1. Run the stack (`.agent/tasks/run-stack.md`).
2. Use the CLI with a set of canonical questions:
   - “List available log indices.”
   - “How many errors per route?”
   - “Show the 5 slowest requests.”
3. Confirm:
   - The chosen tools and arguments make sense.
   - MCP outputs match expectations in Kibana.
   - Final answers are correct, clear, and follow your updated style.

When in doubt, keep changes minimal and well‑documented so other agents (and humans) can follow your reasoning.

