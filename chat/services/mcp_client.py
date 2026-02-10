import json
import requests
from typing import Any

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

    def call_tool(self, name: str, arguments: dict, timeout: int = 60) -> dict:
        """
        Call ANY MCP tool by name with arguments.
        Returns the full MCP JSON response dict for the first SSE 'data:' event.
        """
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
        }
        return self._post_sse_first_data(payload, timeout=timeout)

    @staticmethod
    def extract_human_text(tool_response: dict) -> str:
        """
        Best-effort extraction of readable text from MCP response.
        Your current MCP returns: result.content[-1].text for esql.
        We try that first, then fallback to JSON.
        """
        try:
            result = tool_response.get("result", {})
            content = result.get("content")
            if isinstance(content, list) and content:
                last = content[-1]
                if isinstance(last, dict):
                    if "text" in last and isinstance(last["text"], str):
                        return last["text"]
                    # some MCP servers use "content": [{"type":"text","text":"..."}]
                    if last.get("type") == "text" and "text" in last:
                        return str(last["text"])
            # fallback to stringify the result
            return json.dumps(result, indent=2, ensure_ascii=False)
        except Exception:
            return json.dumps(tool_response, indent=2, ensure_ascii=False)
