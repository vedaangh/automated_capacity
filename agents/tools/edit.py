"""Write or modify files."""

from __future__ import annotations

from pathlib import Path

SCHEMA = {
    "name": "edit",
    "description": (
        "Write or modify a file. mode='write' to create/overwrite, "
        "mode='replace' to do a string replacement in an existing file."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute file path"},
            "mode": {"type": "string", "enum": ["write", "replace"]},
            "content": {
                "type": "string",
                "description": "For write: full file content. For replace: the new string.",
            },
            "old_string": {
                "type": "string",
                "description": "For replace mode: the exact string to find and replace.",
            },
        },
        "required": ["path", "mode", "content"],
    },
}


async def execute(input: dict, work_dir: str) -> str:
    path = Path(input["path"])

    # Security: ensure path is under work_dir
    try:
        path.resolve().relative_to(Path(work_dir).resolve())
    except ValueError:
        return f"Error: path must be under {work_dir}"

    if input["mode"] == "write":
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(input["content"])
        return f"Wrote {len(input['content'])} chars to {path}"

    elif input["mode"] == "replace":
        if not path.exists():
            return f"Error: {path} does not exist"
        old = input.get("old_string", "")
        if not old:
            return "Error: old_string is required for replace mode"
        text = path.read_text()
        if old not in text:
            return f"Error: old_string not found in {path}"
        count = text.count(old)
        new_text = text.replace(old, input["content"], 1)
        path.write_text(new_text)
        return f"Replaced 1 of {count} occurrence(s) in {path}"

    return f"Error: unknown mode '{input['mode']}'"
