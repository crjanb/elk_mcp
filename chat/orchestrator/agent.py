import json
from typing import Any, Tuple

from chat.prompts.intent_prompt import build_intent_prompt
from chat.prompts.answer_prompt import build_answer_prompt
from chat.parsing.intent_parser import parse_intent_response


def detect_intent(question: str, tools: list, ollama) -> Tuple[str, dict | None]:
    """
    Uses LLM (Ollama) to decide which MCP tool(s) to call and with what arguments.
    Returns (raw_llm_output, parsed_json_or_none)
    """
    system_prompt = build_intent_prompt(tools)
    user_prompt = f"User question: {question}"

    raw = ollama.generate(prompt=f"{system_prompt}\n\n{user_prompt}", stream=False, timeout=60)
    intent = parse_intent_response(raw)
    return raw, intent


def execute_tool_calls(intent: dict, mcp_client) -> list[dict]:
    """
    Executes intent['tool_calls'] using MCP.
    Returns a list of execution records:
      [{name, arguments, raw_response, extracted_text}]
    """
    executions: list[dict] = []
    tool_calls = (intent or {}).get("tool_calls") or []

    for tc in tool_calls:
        name = tc.get("name")
        arguments = tc.get("arguments") or {}
        if not name:
            continue

        raw_resp = mcp_client.call_tool(name=name, arguments=arguments, timeout=60)
        extracted = mcp_client.extract_human_text(raw_resp)

        executions.append(
            {
                "name": name,
                "arguments": arguments,
                "raw_response": raw_resp,
                "extracted_text": extracted,
            }
        )

    return executions


def build_context_from_executions(executions: list[dict]) -> str:
    """
    Builds a compact context string to feed into answer LLM.
    """
    parts = []
    for i, ex in enumerate(executions, 1):
        name = ex.get("name")
        args = ex.get("arguments") or {}
        txt = ex.get("extracted_text") or ""
        parts.append(
            f"=== Tool call #{i}: {name} ===\n"
            f"Arguments:\n{json.dumps(args, indent=2, ensure_ascii=False)}\n\n"
            f"Result:\n{txt}\n"
        )
    return "\n\n".join(parts).strip()


def answer_from_context(question: str, context: str, ollama) -> str:
    """
    Calls Ollama to produce a final natural-language answer.
    """
    prompt = build_answer_prompt(question=question, context=context)
    return ollama.generate(prompt=prompt, stream=False, timeout=60)
