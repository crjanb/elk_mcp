def normalize_mcp_tools(raw_tools: list) -> list:
    """
    Convert MCP tool schema (inputSchema) into prompt-friendly format:
    [{name, description, required, optional, params}]
    """
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
