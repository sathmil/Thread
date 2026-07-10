"""API-level test for POST /query. No OpenAI key is available here, so
this only verifies the guaranteed fallback path (the real tool-calling
loop is covered at the unit level in test_agent_service.py).
"""
def test_query_route_returns_unavailable_without_openai_key(client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post("/query", json={"question": "What themes show up most often?"})

    assert response.status_code == 200
    body = response.json()
    assert body["available"] is False
    assert body["tool_calls"] == []
    assert body["answer"]
