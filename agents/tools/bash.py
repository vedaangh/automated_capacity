"""Execute shell commands."""

from __future__ import annotations

import asyncio
import os

SCHEMA = {
    "name": "bash",
    "description": (
        "Execute a shell command and return its output. "
        "For long-running commands, redirect output to a file: cmd > out.log 2>&1"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {"type": "string", "description": "The shell command to run"},
            "timeout": {
                "type": "integer",
                "default": 120,
                "description": "Max seconds before killing the command",
            },
        },
        "required": ["command"],
    },
}


async def execute(input: dict, work_dir: str) -> str:
    cmd = input["command"]
    timeout = min(input.get("timeout", 120), 300)

    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=work_dir,
        env={**os.environ, "HOME": work_dir},
    )

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return f"[Command timed out after {timeout}s]"

    output = ""
    if stdout:
        output += stdout.decode(errors="replace")
    if stderr:
        output += stderr.decode(errors="replace")

    if len(output) > 30000:
        output = output[:12000] + "\n\n[...TRUNCATED...]\n\n" + output[-12000:]

    if not output.strip():
        return f"[exit code {proc.returncode}]"

    return output
