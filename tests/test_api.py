"""API contract tests with the agent dependency stubbed (offline)."""
import json


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["app"]


def test_query_direct_path(client):
    resp = client.post("/query", json={"query": "What is diversification?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["route"] == "direct"
    assert body["search_provider"] is None
    assert body["citations"] == []
    assert "diversification" in body["answer"].lower()
    assert body["conversation_id"]


def test_query_search_path_has_citations(client):
    resp = client.post("/query", json={"query": "Current EUR/USD rate?"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["route"] == "search"
    assert body["citations"][0]["index"] == 1
    assert "[1]" in body["answer"]


def test_query_validation_rejects_empty(client):
    resp = client.post("/query", json={"query": ""})
    assert resp.status_code == 422


def test_stream_emits_sse_events(client):
    with client.stream("POST", "/query/stream", json={"query": "What is diversification?"}) as resp:
        assert resp.status_code == 200
        assert "text/event-stream" in resp.headers["content-type"]
        types = []
        for line in resp.iter_lines():
            if line.startswith("data: "):
                types.append(json.loads(line[6:])["type"])
    assert types[0] == "metadata"
    assert "token" in types
    assert types[-1] == "done"
