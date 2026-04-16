from __future__ import annotations


# health は最小 liveness endpoint として独立に確認しておく。
def test_health_returns_ok(api_client) -> None:
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}