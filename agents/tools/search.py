"""Search files by name (glob) or content (grep)."""

from __future__ import annotations

import asyncio
from pathlib import Path

SCHEMA = {
    "name": "search",
    "description": "Search for files by name pattern (glob) or search file contents (grep).",
    "input_schema": {
        "type": "object",
        "properties": {
            "mode": {"type": "string", "enum": ["glob", "grep"]},
            "pattern": {
                "type": "string",
                "description": "Glob pattern (e.g. '**/*.py') or regex for grep",
            },
            "path": {"type": "string", "default": "/lab", "description": "Directory to search in"},
        },
        "required": ["mode", "pattern"],
    },
}


async def execute(input: dict, work_dir: str) -> str:
    search_path = Path(input.get("path", work_dir))

    if input["mode"] == "glob":
        matches = sorted(search_path.glob(input["pattern"]))[:100]
        if not matches:
            return "No files found"
        return "\n".join(str(m) for m in matches)

    elif input["mode"] == "grep":
        proc = await asyncio.create_subprocess_exec(
            "grep", "-rn", input["pattern"], str(search_path),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            return "[grep timed out]"
        output = stdout.decode(errors="replace")
        lines = output.splitlines()[:50]
        if not lines:
            return "No matches found"
        result = "\n".join(lines)
        if len(output.splitlines()) > 50:
            result += f"\n\n[{len(output.splitlines()) - 50} more matches...]"
        return result

    return f"Error: unknown mode '{input['mode']}'"
