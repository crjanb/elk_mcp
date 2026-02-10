import json
import requests

from chat.config import MCP_URL
from chat.tools.normalize import normalize_mcp_tools


class MCPToolsError(Exception):
    """Raised when tools cannot be fetched from the Elastic MCP server."""


class MCPClient:
    def __init__(self, mcp_url: str = MCP_URL):
        self.mcp_url = mcp_url

    def _post_sse_first_data(self, payload: dict, timeout: int = 10) -> dict:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }

        try:
            resp = requests.post(
                self.mcp_url, headers=headers, json=payload, stream=True, timeout=timeout
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise MCPToolsError(f"Failed to reach MCP server at {self.mcp_url}: {e}") from e

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

        return data

    def fetch_tools_raw(self) -> list:
        payload = {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
        data = self._post_sse_first_data(payload, timeout=10)

        tools = data.get("result", {}).get("tools")
        if not tools:
            raise MCPToolsError(
                "MCP server returned no tools (missing or empty 'result.tools')."
            )
        return tools

    def fetch_tools_normalized(self) -> list:
        raw_tools = self.fetch_tools_raw()
        return normalize_mcp_tools(raw_tools)

    # Optional: keep your ES|QL caller (not used by current CLI flow)
    def call_esql(self, query: str) -> str | None:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": "esql",
                "arguments": {"query": query},
            },
        }

        data = self._post_sse_first_data(payload, timeout=60)

        # Your original implementation expected:
        # data["result"]["content"][-1]["text"]
        # We preserve that shape expectation.
        if "result" in data:
            content = data["result"].get("content") or []
            if content and isinstance(content, list):
                last = content[-1]
                if isinstance(last, dict) and "text" in last:
                    return last["text"]

        return None
