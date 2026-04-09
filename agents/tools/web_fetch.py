"""Fetch a URL and return its content."""

from __future__ import annotations

from pathlib import Path

import httpx

SCHEMA = {
    "name": "web_fetch",
    "description": (
        "Fetch a URL and return its text content. Useful for downloading "
        "data files, reading documentation, or checking APIs."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "url": {"type": "string"},
            "save_to": {
                "type": "string",
                "description": (
                    "Optional: save response body to this file path "
                    "instead of returning it (for binary/large files)"
                ),
            },
        },
        "required": ["url"],
    },
}


async def execute(input: dict, work_dir: str = "") -> str:
    url = input["url"]
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as http:
            resp = await http.get(url)
    except httpx.HTTPError as e:
        return f"Error fetching {url}: {e}"

    if input.get("save_to"):
        path = Path(input["save_to"])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(resp.content)
        return f"Saved {len(resp.content)} bytes to {path} (status {resp.status_code})"

    text = resp.text
    if len(text) > 15000:
        text = text[:7000] + "\n\n[...TRUNCATED...]\n\n" + text[-7000:]
    return f"Status {resp.status_code}\n\n{text}"
