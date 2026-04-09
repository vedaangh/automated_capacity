"""Read file contents with line numbers."""

from __future__ import annotations

from pathlib import Path

SCHEMA = {
    "name": "read",
    "description": "Read a file's contents. Returns text with line numbers.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string"},
            "offset": {"type": "integer", "default": 0, "description": "Start line (0-indexed)"},
            "limit": {"type": "integer", "default": 200, "description": "Max lines to return"},
        },
        "required": ["path"],
    },
}


async def execute(input: dict, work_dir: str) -> str:
    path = Path(input["path"])
    if not path.exists():
        return f"Error: {path} does not exist"

    text = path.read_text()
    lines = text.splitlines()
    offset = input.get("offset", 0)
    limit = min(input.get("limit", 200), 2000)
    selected = lines[offset : offset + limit]

    numbered = [f"{i + offset + 1:4d} | {line}" for i, line in enumerate(selected)]
    result = "\n".join(numbered)

    remaining = len(lines) - offset - limit
    if remaining > 0:
        result += f"\n\n[{remaining} more lines...]"

    return result
