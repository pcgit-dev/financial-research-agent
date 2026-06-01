from app.memory.store import SqlConversationStore


def test_store_round_trip(tmp_path):
    db = tmp_path / "test.db"
    store = SqlConversationStore(f"sqlite:///{db}")

    cid = "conv-1"
    assert store.get_history(cid) == []

    store.append(cid, "user", "What is diversification?")
    store.append(cid, "assistant", "Spreading risk across assets.")

    history = store.get_history(cid)
    assert [t.role for t in history] == ["user", "assistant"]
    assert history[0].content == "What is diversification?"


def test_history_limit_returns_most_recent(tmp_path):
    store = SqlConversationStore(f"sqlite:///{tmp_path / 'h.db'}")
    cid = "conv-2"
    for i in range(6):
        store.append(cid, "user", f"q{i}")
    recent = store.get_history(cid, limit=3)
    assert [t.content for t in recent] == ["q3", "q4", "q5"]


def test_conversations_are_isolated(tmp_path):
    store = SqlConversationStore(f"sqlite:///{tmp_path / 'i.db'}")
    store.append("a", "user", "hello a")
    store.append("b", "user", "hello b")
    assert store.get_history("a")[0].content == "hello a"
    assert store.get_history("b")[0].content == "hello b"
