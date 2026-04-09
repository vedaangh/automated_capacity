"""Create a live UI component in the browser."""

from __future__ import annotations

import json
import os
from pathlib import Path

SCHEMA = {
    "name": "create_stream",
    "description": (
        "Create a live UI component in the browser (chart, video, table, etc). "
        "Returns a file path. Write JSONL data to that file and it streams to the UI "
        "automatically via the background watcher."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "component_type": {
                "type": "string",
                "enum": [
                    "line_chart", "scatter_plot", "bar_chart", "heatmap",
                    "text_log", "video_stream", "table", "metric_card",
                ],
            },
            "title": {"type": "string"},
            "config": {
                "type": "object",
                "description": (
                    "Component-specific config. Examples:\n"
                    '  line_chart: {"x": "step", "y": ["loss", "val_loss"]}\n'
                    '  video_stream: {"width": 640, "height": 480, "fps": 10}\n'
                    '  table: {"columns": ["experiment", "p", "d", "result"]}\n'
                    '  metric_card: {"name": "Best Loss", "format": ".4f"}'
                ),
            },
        },
        "required": ["component_type", "title", "config"],
    },
}


async def execute(input: dict, work_dir: str, *,
                  run_id: str = "", state=None, ws=None) -> str:
    streams_dir = os.path.join(work_dir, "streams")
    os.makedirs(streams_dir, exist_ok=True)

    # Register with state manager if available
    if state and run_id:
        stream_id = await state.create_stream(
            run_id, input["component_type"], input["title"], input["config"])
    else:
        import hashlib
        stream_id = "local-" + hashlib.md5(input["title"].encode()).hexdigest()[:6]

    # Broadcast to browser
    if ws and run_id:
        await ws.broadcast(run_id, {
            "type": "stream_created",
            "data": {
                "stream_id": stream_id,
                "component_type": input["component_type"],
                "title": input["title"],
                "config": input["config"],
            },
        })

    if input["component_type"] == "video_stream":
        stream_path = os.path.join(streams_dir, stream_id)
        os.makedirs(stream_path, exist_ok=True)
        return (
            f"Stream '{stream_id}' created. Write PNG frames to:\n"
            f"  {stream_path}/frame_0001.png\n"
            f"  {stream_path}/frame_0002.png\n"
            f"Frames stream to the browser automatically."
        )
    else:
        stream_path = os.path.join(streams_dir, f"{stream_id}.jsonl")
        Path(stream_path).touch()
        data_fields = list(input["config"].get("y", [])) or ["value"]
        x_field = input["config"].get("x", "x")
        example = json.dumps({x_field: 1, **{f: 0.0 for f in data_fields}})
        return (
            f"Stream '{stream_id}' created. Append JSONL to:\n"
            f"  {stream_path}\n"
            f"Each line should be a JSON object, e.g.:\n"
            f"  {example}\n"
            f"Data streams to the browser automatically."
        )
