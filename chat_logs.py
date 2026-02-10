import sys
import json
import re
import requests

MCP_URL = "http://localhost:8080/mcp"
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gpt-oss:120b-cloud"

class MCPToolsError(Exception):
    """Raised when tools cannot be fetched from the Elastic MCP server."""


def fetch_mcp_tools():
    """
    Fetch the exact tool list from the Elastic MCP server.
    Returns tools normalized for the LLM prompt (name, description, required, optional, params).
    Raises MCPToolsError if the request fails or no tools are returned.
    """
    payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    try:
        resp = requests.post(
            MCP_URL, headers=headers, json=payload, stream=True, timeout=10
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise MCPToolsError(f"Failed to reach MCP server at {MCP_URL}: {e}") from e

    # MCP responds with SSE (data: {...}); parse first data line
    data = None
    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8")
        if text.startswith("data:"):
            try:
                data = json.loads(text.replace("data:", "").strip())
            except json.JSONDecodeError as e:
                raise MCPToolsError(f"Invalid JSON in MCP response: {e}") from e
            break

    if not data:
        raise MCPToolsError("MCP server returned no data (empty or non-SSE response).")

    if "error" in data:
        err = data["error"]
        raise MCPToolsError(
            f"MCP error: {err.get('message', err.get('code', 'unknown'))}"
        )

    tools = data.get("result", {}).get("tools")
    if not tools:
        raise MCPToolsError(
            "MCP server returned no tools (missing or empty 'result.tools')."
        )

    return _normalize_mcp_tools(tools)


def _normalize_mcp_tools(raw_tools):
    """Convert MCP tool schema (inputSchema) into our prompt format."""
    normalized = []
    for t in raw_tools:
        schema = t.get("inputSchema") or {}
        props = schema.get("properties") or {}
        required = schema.get("required") or []
        optional = [k for k in props if k not in required]
        params = {k: (v.get("description") or k) for k, v in props.items()}
        normalized.append(
            {
                "name": t.get("name", ""),
                "description": t.get("description", ""),
                "required": required,
                "optional": optional,
                "params": params,
            }
        )
    return normalized


def format_tools_for_prompt(tools):
    """Format tool list for the system prompt."""
    lines = []
    for t in tools:
        name = t.get("name", "")
        desc = t.get("description", "")
        req = t.get("required", [])
        opt = t.get("optional", [])
        params = t.get("params", {})
        parts = [f"- **{name}**: {desc}"]
        if req:
            parts.append(f"  Required: {', '.join(req)}")
        if opt:
            parts.append(f"  Optional: {', '.join(opt)}")
        for p, pdesc in params.items():
            parts.append(f"  - {p}: {pdesc}")
        lines.append("\n".join(parts))
    return "\n\n".join(lines)


def detect_intent_ollama(question: str, tools: list):
    """Use LLM to decide which MCP tool(s) to call and with what arguments."""
    tools_text = format_tools_for_prompt(tools)

    system_prompt = f"""You are an intent classifier for an Elasticsearch/observability assistant.

The user will ask a question about logs, indices, mappings, shards, or search. Your job is to choose which MCP tool(s) to call and with what arguments.

Available tools:

{tools_text}

Rules:
- Pick one or more tools that best answer the user's question. Prefer a single tool when enough.
- For "esql": generate a valid ES|QL query (e.g. FROM index* | LIMIT 10, or WITH stats, WHERE, STATS as needed). Index pattern for backend logs is typically "logs-dummy-backend*".
- For "list_indices": use index_pattern like "logs-*" or "logs-dummy-backend*" if the user wants to see indices.
- For "get_mappings": use the exact index name (user might say "index X"); if unknown, use "logs-dummy-backend-*" or ask for clarification.
- For "get_shards": pass "index" only if the user asks about a specific index.
- For "search": provide "index" and "query_body" (Elasticsearch query DSL). query_body can include "query", "size", "sort", etc.

Respond with a single JSON object only, no markdown or extra text:
{{"tool_calls": [{{"name": "<tool_name>", "arguments": {{ ... }}}}, ...]}}

Example for "how many errors per route?": {{"tool_calls": [{{"name": "esql", "arguments": {{"query": "FROM logs-dummy-backend* | WHERE \\`log.level\\` == \\"ERROR\\" | STATS count() BY route"}}}}]}}
Example for "list my log indices": {{"tool_calls": [{{"name": "list_indices", "arguments": {{"index_pattern": "logs-dummy-backend*"}}}}]}}
"""

    user_prompt = f"User question: {question}"

    payload = {
        "model": MODEL,
        "prompt": f"{system_prompt}\n\n{user_prompt}",
        "stream": False,
    }

    resp = requests.post(OLLAMA_URL, json=payload, timeout=60)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def parse_intent_response(raw: str):
    """Extract JSON tool_calls from LLM response."""
    # Try to find a JSON object in the response
    raw = raw.strip()
    # Remove markdown code blocks if present
    if "```" in raw:
        raw = re.sub(r"```(?:json)?\s*", "", raw)
        raw = raw.replace("```", "").strip()
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        return None
    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def call_mcp_esql(query: str):
    payload = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "esql",
            "arguments": {
                "query": query
            }
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }

    resp = requests.post(MCP_URL, headers=headers, json=payload, stream=True)
    resp.raise_for_status()

    for line in resp.iter_lines():
        if not line:
            continue
        text = line.decode("utf-8")
        if text.startswith("data:"):
            data = json.loads(text.replace("data:", "").strip())
            if "result" in data:
                return data["result"]["content"][-1]["text"]

    return None


def ask_ollama(question: str, context: str):
    prompt = f"""
You are an observability assistant.

User question:
{question}

Elasticsearch log data (from ES|QL):
{context}

Answer clearly in plain English.
Highlight insights, trends, or anomalies.
"""

    payload = {
        "model": MODEL,
        "prompt": prompt,
        "stream": False
    }

    resp = requests.post(OLLAMA_URL, json=payload)
    resp.raise_for_status()
    return resp.json()["response"]


def main():
    if len(sys.argv) < 2:
        print("Usage: python chat_logs.py \"your question\"")
        sys.exit(1)

    question = sys.argv[1]

    # Fetch exact tools from Elastic MCP server (raises MCPToolsError on failure)
    try:
        tools = fetch_mcp_tools()
    except MCPToolsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # LLM intent detection: which tool(s) to call and with what arguments
    print("🔍 Detecting intent via LLM...\n")
    raw_intent = detect_intent_ollama(question, tools)
    intent = parse_intent_response(raw_intent)

    # Print user question and chosen tool(s)
    print("User question:")
    print(f"  {question}\n")
    print("Tool(s) to call:")

    if intent and "tool_calls" in intent and intent["tool_calls"]:
        for i, tc in enumerate(intent["tool_calls"], 1):
            name = tc.get("name", "?")
            args = tc.get("arguments", {})
            print(f"  {i}. {name}")
            for k, v in args.items():
                if isinstance(v, (dict, list)):
                    v = json.dumps(v, indent=4) if isinstance(v, dict) else json.dumps(v)
                print(f"     {k}: {v}")
    else:
        print("  (could not parse LLM response as tool_calls)")
        print("\nRaw LLM response:")
        print(raw_intent)


if __name__ == "__main__":
    main()
