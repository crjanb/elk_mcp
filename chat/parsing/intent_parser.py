import json
import re


def parse_intent_response(raw: str) -> dict | None:
    """
    Extract JSON tool_calls from LLM response.
    Tries to find a JSON object in the response and parse it.
    """
    raw = (raw or "").strip()

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
