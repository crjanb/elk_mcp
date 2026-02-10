def format_tools_for_prompt(tools: list) -> str:
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
