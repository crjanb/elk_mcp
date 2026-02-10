import sys
import json

from chat.services.mcp_client import MCPClient, MCPToolsError
from chat.services.ollama_client import OllamaClient
from chat.orchestrator.agent import detect_intent


def main():
    if len(sys.argv) < 2:
        print('Usage: python -m chat.cli "your question"')
        sys.exit(1)

    question = sys.argv[1]

    mcp = MCPClient()
    ollama = OllamaClient()

    # Fetch exact tools from Elastic MCP server (raises MCPToolsError on failure)
    try:
        tools = mcp.fetch_tools_normalized()
    except MCPToolsError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    # LLM intent detection: which tool(s) to call and with what arguments
    print("🔍 Detecting intent via LLM...\n")
    raw_intent, intent = detect_intent(question=question, tools=tools, ollama=ollama)

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
