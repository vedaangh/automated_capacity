"""Thin HTTP client for agent → server communication."""

from __future__ import annotations

from typing import Any

import httpx


class ServerClient:
    """All outbound HTTP calls from agent to server."""

    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")
        self.http = httpx.AsyncClient(timeout=10.0)

    async def heartbeat(self, agent_id: str, tool_calls: int,
                        tokens: int, last_activity: str) -> None:
        try:
            await self.http.post(
                f"{self.base_url}/agents/{agent_id}/heartbeat",
                json={"tool_calls": tool_calls, "tokens": tokens,
                      "last_activity": last_activity},
            )
        except Exception:
            pass  # non-fatal

    async def append_transcript(self, agent_id: str, messages: list[dict]) -> None:
        try:
            await self.http.post(
                f"{self.base_url}/agents/{agent_id}/transcript",
                json={"messages": messages},
            )
        except Exception:
            pass  # non-fatal

    async def signal_done(self, agent_id: str, result: str,
                          status: str = "done") -> None:
        await self.http.post(
            f"{self.base_url}/agents/{agent_id}/done",
            json={"result": result, "status": status},
        )

    async def create_stream(self, run_id: str, component_type: str,
                            title: str, config: dict[str, Any]) -> str:
        resp = await self.http.post(
            f"{self.base_url}/runs/{run_id}/streams",
            json={"component_type": component_type, "title": title, "config": config},
        )
        resp.raise_for_status()
        return resp.json()["stream_id"]

    async def push_stream_data(self, run_id: str, stream_id: str,
                               points: list[dict[str, Any]]) -> None:
        try:
            await self.http.post(
                f"{self.base_url}/runs/{run_id}/streams/{stream_id}/data",
                json={"points": points},
            )
        except Exception:
            pass  # non-fatal

    async def close(self) -> None:
        await self.http.aclose()
