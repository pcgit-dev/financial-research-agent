"""Router fast-path tests — exercise the regex pre-check without calling an LLM."""
from app.agent.router import _REALTIME_PATTERNS


def test_time_sensitive_queries_match_fast_path():
    for q in [
        "Current EUR/USD",
        "Latest Fed decision",
        "Tesla stock price today",
        "What is the current US inflation rate?",
        "recent market news",
    ]:
        assert _REALTIME_PATTERNS.search(q), q


def test_conceptual_queries_do_not_match_fast_path():
    for q in [
        "What is diversification?",
        "Hello",
        "Explain the P/E ratio",
        "How does compound interest work?",
    ]:
        assert not _REALTIME_PATTERNS.search(q), q
