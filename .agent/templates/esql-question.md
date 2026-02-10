---
title: Template – Answering questions with ES|QL via MCP
description: Prompting pattern for ES|QL‑backed log analysis.
---

Use this template when adding examples or designing new flows that rely on the MCP `esql` tool.

## Canonical question

> How many errors per route in the last 2 hours?

## Expected tool call (conceptual)

```json
{
  "tool_calls": [
    {
      "name": "esql",
      "arguments": {
        "query": "FROM logs-dummy-backend* | WHERE `@timestamp` >= NOW() - INTERVAL 2 HOURS AND `log.level` == \"ERROR\" | STATS count() BY route"
      }
    }
  ]
}
```

## Answering pattern

1. Run ES|QL via MCP.
2. Summarize key aggregates:
   - total error count,
   - per‑route counts,
   - any routes with unusually high error ratios.
3. Provide a short, human‑readable interpretation, e.g.:

- Which routes are most problematic.
- Whether the error rate is concerning.
- Suggested follow‑up questions or queries.

Keep the final answer in clear English, referencing routes and counts explicitly where useful.

