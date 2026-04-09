"""WebSocket connection manager: tracks connections per run, broadcasts events."""

from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from shared.protocol import now_iso


class WSManager:
    def __init__(self):
        self._connections: dict[str, list[WebSocket]] = {}

    def connect(self, run_id: str, ws: WebSocket) -> None:
        self._connections.setdefault(run_id, []).append(ws)

    def disconnect(self, run_id: str, ws: WebSocket) -> None:
        conns = self._connections.get(run_id, [])
        if ws in conns:
            conns.remove(ws)

    async def broadcast(self, run_id: str, event: dict[str, Any]) -> None:
        """Send event dict to all connected WebSockets for a run."""
        if "ts" not in event:
            event["ts"] = now_iso()
        message = json.dumps(event)
        dead = []
        for ws in self._connections.get(run_id, []):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(run_id, ws)
