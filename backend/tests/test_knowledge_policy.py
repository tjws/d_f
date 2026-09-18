from app.ai.providers.bailian import BailianReplyProvider
from app.ai.providers.mock import MockReplyProvider
from app.knowledge.policy import retrieve_knowledge
from app.knowledge.retriever import KnowledgeDocument


def test_low_score_knowledge_hit_returns_consultant_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.knowledge.policy.search_knowledge",
        lambda *args, **kwargs: [KnowledgeDocument("faq", "FAQ", "片段", 1.0, 1)],
    )

    result = retrieve_knowledge("课程价格", consultant_name="李老师")

    assert result.matched is False
    assert result.hits == ()
    assert result.fallback_message is not None
    assert "李老师" in result.fallback_message


def test_approved_hit_is_exposed_with_retrieval_metadata(monkeypatch):
    monkeypatch.setattr(
        "app.knowledge.policy.search_knowledge",
        lambda *args, **kwargs: [KnowledgeDocument("faq", "FAQ", "课程价格说明", 2.0, 1)],
    )

    result = retrieve_knowledge("课程价格", consultant_name="李老师")

    assert result.matched is True
    assert result.retrieval_mode == "keyword"
    assert result.threshold == 2.0
    assert len(result.hits) == 1
    assert result.fallback_message is None


def test_no_hit_reply_does_not_call_bailian_model(monkeypatch):
    context = {
        "customer": {"interested_subject": "数学"},
        "confirmed_profile": {"id": 1, "dimensions": {}},
        "knowledge_policy": {
            "query": "没有答案的问题",
            "matched": False,
            "fallback_message": "我是李老师，先为您核实。",
        },
    }

    class ExplodingClient:
        def __getattr__(self, name):
            raise AssertionError("model client must not be called for a knowledge fallback")

    mock_payload = MockReplyProvider().generate(context)
    bailian_payload = BailianReplyProvider(client=ExplodingClient()).generate(context)

    assert mock_payload["evidence_level"] == "insufficient"
    assert bailian_payload["evidence_level"] == "insufficient"
    assert "李老师" in str(bailian_payload["content"])
