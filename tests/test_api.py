from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_recommendations_endpoint_with_explicit_fields():
    resp = client.post(
        "/api/v1/recommendations",
        json={"category": "laptop", "budget": 100000, "use_cases": ["programming", "gaming"]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["engine"] == "rule_based_v1"
    assert body["candidates_after_filtering"] <= body["candidates_considered"]
    assert len(body["recommendations"]) > 0
    for rec in body["recommendations"]:
        assert "reasons" in rec and rec["reasons"]
        assert 0.0 <= rec["score"] <= 1.0


def test_recommendations_endpoint_with_free_text_query():
    resp = client.post(
        "/api/v1/recommendations",
        json={"category": "laptop", "query": "I need a laptop under 100,000 BDT for programming and gaming."},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["requirement"]["budget_max"] == 100000
    assert "programming" in body["requirement"]["use_cases"]


def test_recommendations_endpoint_returns_404_for_empty_category_catalog():
    resp = client.post("/api/v1/recommendations", json={"category": "monitor"})
    assert resp.status_code == 404  # sample repository only stocks laptops


def test_advisor_message_asks_follow_up_when_incomplete():
    resp = client.post("/api/v1/advisor/message", json={"message": "I need a laptop."})
    assert resp.status_code == 200
    body = resp.json()
    assert body["follow_up_question"] is not None
    assert body["requirement"] is None
    assert body["session_id"]


def test_advisor_message_multi_turn_reaches_recommendations():
    resp1 = client.post("/api/v1/advisor/message", json={"message": "I need a laptop."})
    session_id = resp1.json()["session_id"]

    resp2 = client.post("/api/v1/advisor/message", json={"session_id": session_id, "message": "90k"})
    assert resp2.json()["follow_up_question"] is not None

    resp3 = client.post(
        "/api/v1/advisor/message", json={"session_id": session_id, "message": "Programming"}
    )
    body3 = resp3.json()
    assert body3["follow_up_question"] is None
    assert body3["requirement"] is not None
    assert body3["recommendations"] is not None
    assert len(body3["recommendations"]["recommendations"]) > 0
