"""Parallel research agents using Bedrock Claude with web_fetch for research."""

from __future__ import annotations

import asyncio
from typing import Any

import anthropic
import httpx

from shared.config import AWS_REGION, RESEARCH_MODEL


# Custom web_fetch tool (since Bedrock doesn't support server-side web_search)
RESEARCH_TOOLS = [
    {
        "name": "web_fetch",
        "description": (
            "Fetch a URL and return its text content. Use this to read documentation, "
            "papers, datasets, or any web resource you find relevant."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
            },
            "required": ["url"],
        },
    },
]


async def _fetch_url(url: str) -> str:
    """Fetch a URL, return text content truncated to 10KB."""
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as http:
            resp = await http.get(url)
        text = resp.text
        if len(text) > 10000:
            text = text[:5000] + "\n\n[...TRUNCATED...]\n\n" + text[-5000:]
        return f"Status {resp.status_code}\n\n{text}"
    except Exception as e:
        return f"Error fetching {url}: {e}"


async def research_single_query(query: str) -> list[dict[str, Any]]:
    """Run one research agent on Bedrock. Returns findings."""
    client = anthropic.AsyncAnthropicBedrock(aws_region=AWS_REGION)

    messages = [
        {"role": "user", "content": (
            f"Research this topic thoroughly: {query}\n\n"
            "You have a web_fetch tool to read URLs. Use your knowledge to identify "
            "relevant URLs (documentation, papers, datasets, GitHub repos) and fetch them. "
            "Synthesize your findings into clear, specific points with sources.\n\n"
            "IMPORTANT: Only find and recommend OPEN-SOURCE tools, libraries, and simulators "
            "(MIT, Apache, GPL, BSD licensed). Only reference publicly accessible data. "
            "Include license information and GitHub URLs where possible."
        )}
    ]

    findings: list[dict[str, Any]] = []

    while True:
        response = await client.messages.create(
            model=RESEARCH_MODEL,
            max_tokens=2048,
            system=(
                "You are a research agent. Use your knowledge and the web_fetch tool "
                "to gather information. Be thorough and cite sources. "
                "Focus on factual, specific, actionable findings."
            ),
            messages=messages,
            tools=RESEARCH_TOOLS,
        )

        messages.append({"role": "assistant", "content": response.content})

        # Extract text findings
        for block in response.content:
            if hasattr(block, "text") and block.text:
                findings.append({"source": "reasoning", "content": block.text})

        if response.stop_reason != "tool_use":
            break

        # Execute tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                if block.name == "web_fetch":
                    result = await _fetch_url(block.input["url"])
                    findings.append({
                        "source": "web_fetch",
                        "content": result[:500],
                        "url": block.input["url"],
                    })
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

        if tool_results:
            messages.append({"role": "user", "content": tool_results})

    return findings


async def run_parallel_research(queries: list[str]) -> list[dict[str, Any]]:
    """Run multiple research queries in parallel. Returns aggregated findings."""
    tasks = [research_single_query(q) for q in queries]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_findings = []
    for query, result in zip(queries, results):
        if isinstance(result, Exception):
            all_findings.append({
                "query": query,
                "error": str(result),
                "results": [],
            })
        else:
            all_findings.append({
                "query": query,
                "results": result,
            })

    return all_findings


def format_findings_for_orchestrator(findings: list[dict]) -> str:
    """Format research findings as readable text for the orchestrator."""
    parts = []
    for entry in findings:
        query = entry.get("query", "unknown")
        parts.append(f"## Research: {query}\n")
        if entry.get("error"):
            parts.append(f"**Error**: {entry['error']}\n")
        for result in entry.get("results", []):
            content = result.get("content", "")
            url = result.get("url", "")
            source = result.get("source", "")
            if url:
                parts.append(f"- [{source}] {content[:300]} ({url})")
            else:
                parts.append(f"- {content[:500]}")
        parts.append("")
    return "\n".join(parts)
