from app.agent.citations import (
    build_citations,
    format_reference_list,
    format_sources_for_prompt,
)
from app.tools.base import SearchResult


def _results():
    return [
        SearchResult(title="Fed holds rates", url="https://fed.gov/a", content="held at 4.5%"),
        SearchResult(title="Reuters", url="https://reuters.com/b", content="inflation elevated"),
    ]


def test_build_citations_is_one_based_and_ordered():
    citations = build_citations(_results())
    assert [c["index"] for c in citations] == [1, 2]
    assert citations[0]["title"] == "Fed holds rates"
    assert citations[1]["url"] == "https://reuters.com/b"


def test_format_sources_for_prompt_numbers_each_source():
    text = format_sources_for_prompt(_results())
    assert "[1] Fed holds rates" in text
    assert "[2] Reuters" in text
    assert "https://fed.gov/a" in text


def test_format_reference_list_renders_sources_block():
    out = format_reference_list(build_citations(_results()))
    assert "**Sources:**" in out
    assert "[1] Fed holds rates" in out


def test_empty_citations_render_nothing():
    assert format_reference_list([]) == ""
