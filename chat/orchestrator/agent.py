from chat.prompts.intent_prompt import build_intent_prompt
from chat.parsing.intent_parser import parse_intent_response


def detect_intent(question: str, tools: list, ollama) -> tuple[str, dict | None]:
    """
    Uses LLM (Ollama) to decide which MCP tool(s) to call and with what arguments.
    Returns (raw_llm_output, parsed_json_or_none)
    """
    system_prompt = build_intent_prompt(tools)
    user_prompt = f"User question: {question}"

    raw = ollama.generate(prompt=f"{system_prompt}\n\n{user_prompt}", stream=False, timeout=60)
    intent = parse_intent_response(raw)
    return raw, intent
