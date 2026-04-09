"""Check remaining time in the agent's work session."""

from __future__ import annotations

import os
from pathlib import Path

SCHEMA = {
    "name": "check_timer",
    "description": (
        "Check how many seconds remain in your work session. "
        "Use occasionally to pace yourself. Don't call this every turn."
    ),
    "input_schema": {"type": "object", "properties": {}},
}


async def execute(input: dict, work_dir: str) -> str:
    path = os.path.join(work_dir, ".remaining_seconds")
    if os.path.exists(path):
        remaining = Path(path).read_text().strip()
        try:
            secs = int(remaining)
            mins = secs // 60
            s = secs % 60
            return f"Remaining: {secs} seconds ({mins}m {s}s)"
        except ValueError:
            return f"Remaining: {remaining}"
    return "Timer not available"
