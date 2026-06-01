"""Convert search results into numbered, citable sources.

Keeps citation formatting in one place so both the LLM prompt and the final
human-readable reference list stay consistent (1-based, stable ordering).
"""
from __future__ import annotations

from app.agent.state import Citation
from app.tools.base import SearchResult


def build_citations(results: list[SearchResult]) -> list[Citation]:
    """Assign stable 1-based indices to search results."""
    return [
        Citation(
            index=i,
            title=result.title,
            url=result.url,
        )
        for i, result in enumerate(results, start=1)
    ]


def format_sources_for_prompt(results: list[SearchResult]) -> str:
    """Render numbered sources for injection into the synthesis prompt."""
    blocks = []
    for i, r in enumerate(results, start=1):
        snippet = r.content.strip().replace("\n", " ")
        blocks.append(f"[{i}] {r.title}\nURL: {r.url}\nExcerpt: {snippet}")
    return "\n\n".join(blocks)


def format_reference_list(citations: list[Citation]) -> str:
    """Render the human-readable reference list appended to the final answer."""
    if not citations:
        return ""
    lines = ["", "---", "**Sources:**"]
    for c in citations:
        lines.append(f"[{c['index']}] {c['title']}\n    {c['url']}")
    return "\n".join(lines)
