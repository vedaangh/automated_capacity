"""Agent tools: each module exports SCHEMA (dict) and execute(input, work_dir) -> str."""

from agents.tools import bash, edit, read, search, web_fetch, timer, create_stream, signal


ALL_TOOLS = [bash, edit, read, search, web_fetch, timer, create_stream, signal]


def collect_tool_schemas() -> list[dict]:
    """Return all tool JSON schemas for the Claude API tools parameter."""
    return [{"name": t.SCHEMA["name"], "description": t.SCHEMA["description"],
             "input_schema": t.SCHEMA["input_schema"]} for t in ALL_TOOLS]
