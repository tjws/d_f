from app.knowledge.retriever import search_knowledge


def test_local_knowledge_retrieval_returns_ranked_documents():
    results = search_knowledge("初一数学试听课收费", limit=3)
    assert results
    assert results[0].score >= results[-1].score


def test_empty_query_is_safe():
    assert search_knowledge("", limit=3) == []
