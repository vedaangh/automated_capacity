"""Signal that the agent is finished with its current phase."""

from __future__ import annotations

SCHEMA = {
    "name": "signal_done",
    "description": (
        "Signal that you are finished with your work. Include comprehensive "
        "notes about what you built, how it works, what's mutable, and any known issues. "
        "For engineer: these notes are handed to the scientist. "
        "For scientist: these are the final research findings."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "result": {"type": "string", "description": "Your handoff notes or findings"},
        },
        "required": ["result"],
    },
}


async def execute(input: dict, work_dir: str) -> str:
    # This is handled as a special case in the harness loop.
    # When the agent calls signal_done, run_agent() returns input["result"].
    # This function should never actually be called.
    return input["result"]
