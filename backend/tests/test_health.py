def test_health_endpoint(client) -> None:
    """Validate liveness endpoint returns healthy payload."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["env"] == "test"
    assert "timestamp" in payload


def test_ready_endpoint(client) -> None:
    """Validate readiness endpoint returns ready payload."""
    response = client.get("/api/v1/ready")
    assert response.status_code == 200

    payload = response.json()
    assert payload["status"] == "ready"
