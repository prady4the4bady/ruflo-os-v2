from app.memory import LumynMemory


def test_memory_retrieval_prefers_semantically_similar_session(tmp_path) -> None:
    mem = LumynMemory(tmp_path / "chroma")

    mem.add_conversation(
        session_id="s1",
        content="how to reset wifi adapter on linux",
        outcome="completed",
    )
    mem.add_conversation(
        session_id="s2",
        content="best pasta recipe with tomato sauce",
        outcome="completed",
    )
    mem.add_conversation(
        session_id="s3",
        content="configure network interface and wifi troubleshooting",
        outcome="completed",
    )

    hits = mem.search("linux wifi troubleshooting", top_k=3)
    assert len(hits) >= 1
    # One of the network-related sessions should rank first.
    assert hits[0].session_id in {"s1", "s3"}
