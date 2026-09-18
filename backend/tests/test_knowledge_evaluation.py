from app.knowledge.evaluation import evaluate_knowledge


def test_knowledge_evaluation_reports_keyword_and_vector_metrics():
    result = evaluate_knowledge(limit=2)

    assert result["case_count"] == 9
    assert set(result["summary"]) == {"keyword", "vector"}
    assert 0.0 <= result["summary"]["keyword"]["hit_at_k"] <= 1.0
    assert len(result["cases"]["keyword"]) == 9
    assert len(result["cases"]["vector"]) == 9


def test_knowledge_evaluation_clamps_limit():
    assert evaluate_knowledge(limit=99)["k"] == 5
    assert evaluate_knowledge(limit=0)["k"] == 1
