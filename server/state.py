"""State persistence: SQLite for structured data, JSONL for transcripts."""

from __future__ import annotations

import json
import os
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

from server.models import AgentState, Run, SimSpec, StreamSpec
from shared.config import DATA_DIR
from shared.protocol import TranscriptMessage, now_iso

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL DEFAULT 'research',
    question TEXT NOT NULL,
    sim_spec TEXT,
    research_findings TEXT,
    findings TEXT,
    error TEXT,
    engineer_timeout INTEGER NOT NULL DEFAULT 1200,
    scientist_timeout INTEGER NOT NULL DEFAULT 1200,
    model TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agents (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    role TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    ec2_instance_id TEXT,
    timeout_seconds INTEGER NOT NULL DEFAULT 1200,
    started_at TEXT,
    tool_calls INTEGER NOT NULL DEFAULT 0,
    tokens_used INTEGER NOT NULL DEFAULT 0,
    last_activity TEXT NOT NULL DEFAULT '',
    last_heartbeat TEXT,
    result TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS streams (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL REFERENCES runs(id),
    component_type TEXT NOT NULL,
    title TEXT NOT NULL,
    config TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class StateManager:
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self.db_path = os.path.join(data_dir, "runs.db")
        self.transcripts_dir = os.path.join(data_dir, "transcripts")

    async def init_db(self) -> None:
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.transcripts_dir, exist_ok=True)
        async with aiosqlite.connect(self.db_path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    # -- helpers --

    async def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(sql, params)
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

    async def _execute(self, sql: str, params: tuple = ()) -> None:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(sql, params)
            await db.commit()

    # -----------------------------------------------------------------------
    # Runs
    # -----------------------------------------------------------------------

    async def create_run(self, question: str,
                         engineer_timeout: int = 1200,
                         scientist_timeout: int = 1200,
                         model: str = "") -> Run:
        run_id = uuid.uuid4().hex[:12]
        ts = now_iso()
        await self._execute(
            "INSERT INTO runs (id, status, question, engineer_timeout, scientist_timeout, model, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (run_id, "research", question, engineer_timeout, scientist_timeout, model, ts, ts),
        )
        return Run(id=run_id, status="research", question=question,
                   engineer_timeout=engineer_timeout, scientist_timeout=scientist_timeout,
                   model=model, created_at=ts, updated_at=ts)

    async def get_run(self, run_id: str) -> Run | None:
        row = await self._fetchone("SELECT * FROM runs WHERE id = ?", (run_id,))
        if not row:
            return None
        return self._row_to_run(row)

    async def list_runs(self, limit: int = 50) -> list[Run]:
        rows = await self._fetchall(
            "SELECT * FROM runs ORDER BY created_at DESC LIMIT ?", (limit,))
        return [self._row_to_run(r) for r in rows]

    async def update_run(self, run_id: str, **kwargs: Any) -> None:
        if "sim_spec" in kwargs:
            val = kwargs["sim_spec"]
            if isinstance(val, SimSpec):
                kwargs["sim_spec"] = val.model_dump_json()
            elif isinstance(val, dict):
                kwargs["sim_spec"] = json.dumps(val)
        if "research_findings" in kwargs and not isinstance(kwargs["research_findings"], str):
            kwargs["research_findings"] = json.dumps(kwargs["research_findings"])
        kwargs["updated_at"] = now_iso()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [run_id]
        await self._execute(f"UPDATE runs SET {sets} WHERE id = ?", tuple(vals))

    def _row_to_run(self, row: dict) -> Run:
        sim_spec = None
        if row.get("sim_spec"):
            sim_spec = SimSpec(**json.loads(row["sim_spec"]))
        findings_data = None
        if row.get("research_findings"):
            findings_data = json.loads(row["research_findings"])
        return Run(
            id=row["id"], status=row["status"], question=row["question"],
            sim_spec=sim_spec, research_findings=findings_data,
            findings=row.get("findings"), error=row.get("error"),
            engineer_timeout=row.get("engineer_timeout", 1200),
            scientist_timeout=row.get("scientist_timeout", 1200),
            model=row.get("model", ""),
            created_at=row["created_at"], updated_at=row["updated_at"],
        )

    # -----------------------------------------------------------------------
    # Agents
    # -----------------------------------------------------------------------

    async def create_agent(self, run_id: str, role: str, timeout: int) -> AgentState:
        role_suffix = {"engineer": "eng", "scientist": "sci", "orchestrator": "orch"}
        agent_id = f"{run_id}-{role_suffix.get(role, role[:4])}"
        ts = now_iso()
        await self._execute(
            "INSERT INTO agents (id, run_id, role, status, timeout_seconds, created_at, updated_at) "
            "VALUES (?, ?, ?, 'pending', ?, ?, ?)",
            (agent_id, run_id, role, timeout, ts, ts),
        )
        return AgentState(id=agent_id, run_id=run_id, role=role,
                          timeout_seconds=timeout, created_at=ts, updated_at=ts)

    async def get_agent(self, agent_id: str) -> AgentState | None:
        row = await self._fetchone("SELECT * FROM agents WHERE id = ?", (agent_id,))
        if not row:
            return None
        return AgentState(**row)

    async def get_agents_for_run(self, run_id: str) -> list[AgentState]:
        rows = await self._fetchall(
            "SELECT * FROM agents WHERE run_id = ? ORDER BY created_at", (run_id,))
        return [AgentState(**r) for r in rows]

    async def get_running_agents(self) -> list[AgentState]:
        rows = await self._fetchall("SELECT * FROM agents WHERE status = 'running'")
        return [AgentState(**r) for r in rows]

    async def update_agent(self, agent_id: str, **kwargs: Any) -> None:
        kwargs["updated_at"] = now_iso()
        sets = ", ".join(f"{k} = ?" for k in kwargs)
        vals = list(kwargs.values()) + [agent_id]
        await self._execute(f"UPDATE agents SET {sets} WHERE id = ?", tuple(vals))

    # -----------------------------------------------------------------------
    # Streams
    # -----------------------------------------------------------------------

    async def create_stream(self, run_id: str, component_type: str,
                            title: str, config: dict, created_by: str = "") -> str:
        # Count existing streams for this run to generate sequential ID
        rows = await self._fetchall(
            "SELECT COUNT(*) as cnt FROM streams WHERE run_id = ?", (run_id,))
        n = rows[0]["cnt"] if rows else 0
        stream_id = f"{run_id}-s{n}"
        ts = now_iso()
        await self._execute(
            "INSERT INTO streams (id, run_id, component_type, title, config, created_by, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (stream_id, run_id, component_type, title, json.dumps(config), created_by, ts),
        )
        return stream_id

    async def get_streams_for_run(self, run_id: str) -> list[StreamSpec]:
        rows = await self._fetchall(
            "SELECT * FROM streams WHERE run_id = ? ORDER BY created_at", (run_id,))
        return [StreamSpec(**{**r, "config": json.loads(r["config"])}) for r in rows]

    # -----------------------------------------------------------------------
    # Transcripts (JSONL files, not SQLite)
    # -----------------------------------------------------------------------

    async def append_transcript(self, agent_id: str, messages: list[TranscriptMessage]) -> None:
        path = os.path.join(self.transcripts_dir, f"{agent_id}.jsonl")
        with open(path, "a") as f:
            for msg in messages:
                f.write(msg.model_dump_json() + "\n")

    async def read_transcript(self, agent_id: str) -> list[dict]:
        path = os.path.join(self.transcripts_dir, f"{agent_id}.jsonl")
        if not os.path.exists(path):
            return []
        messages = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    messages.append(json.loads(line))
        return messages
