import sys
import json

from chat.services.mcp_client import MCPClient, MCPToolsError
from chat.services.ollama_client import OllamaClient
from chat.orchestrator.agent import (
    detect_intent,
    execute_tool_calls,
    build_context_from_executions,
    answer_from_context,
)


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

    # 1) LLM intent detection
    print("🔍 Detecting intent via LLM...\n")
    raw_intent, intent = detect_intent(question=question, tools=tools, ollama=ollama)

    print("User question:")
    print(f"  {question}\n")

    if not (intent and "tool_calls" in intent and intent["tool_calls"]):
        print("Tool(s) to call:")
        print("  (could not parse LLM response as tool_calls)")
        print("\nRaw LLM response:")
        print(raw_intent)
        return

    # Print chosen tool(s)
    print("Tool(s) to call:")
    for i, tc in enumerate(intent["tool_calls"], 1):
        name = tc.get("name", "?")
        args = tc.get("arguments", {})
        print(f"  {i}. {name}")
        for k, v in args.items():
            if isinstance(v, (dict, list)):
                v = json.dumps(v, indent=4, ensure_ascii=False) if isinstance(v, dict) else json.dumps(v, ensure_ascii=False)
            print(f"     {k}: {v}")

    # 2) Execute tool calls against MCP
    print("\n⚙️ Executing tool calls against MCP...\n")
    executions = execute_tool_calls(intent=intent, mcp_client=mcp)

    if not executions:
        print("No tool calls executed.")
        return

    # Print raw tool outputs (CLI)
    print("📦 MCP results:\n")
    for i, ex in enumerate(executions, 1):
        print(f"--- Result #{i}: {ex['name']} ---")
        print(ex.get("extracted_text") or "")
        print()

    # 3) Ask LLM to produce final natural-language answer
    context = build_context_from_executions(executions)
    final_answer = answer_from_context(question=question, context=context, ollama=ollama)

    print("✅ Final answer:\n")
    print(final_answer)


if __name__ == "__main__":
    main()



# run from cli: python -m chat.cli "how many errors per route?"