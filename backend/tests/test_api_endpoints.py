def test_dashboard_endpoint(client) -> None:
    """Validate dashboard endpoint returns baseline payload."""
    response = client.get("/api/v1/dashboard")
    assert response.status_code == 200

    payload = response.json()
    assert "total_asset" in payload
    assert "nav_series" in payload


def test_positions_endpoint(client) -> None:
    """Validate positions endpoint returns list payload."""
    response = client.get("/api/v1/positions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_orders_endpoint(client) -> None:
    """Validate orders endpoint returns list payload."""
    response = client.get("/api/v1/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_signals_endpoint(client) -> None:
    """Validate signals endpoint returns list payload."""
    response = client.get("/api/v1/signals")
    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload, list)


def test_backtest_endpoint(client) -> None:
    """Validate backtest endpoint returns metric payload."""
    response = client.get("/api/v1/backtest")
    assert response.status_code == 200

    payload = response.json()
    assert "annual_return" in payload
    assert "curve" in payload


def test_risk_endpoint(client) -> None:
    """Validate risk endpoint returns baseline status."""
    response = client.get("/api/v1/risk")
    assert response.status_code == 200

    payload = response.json()
    assert payload["overall_level"] == "INFO"
    assert isinstance(payload["alerts"], list)
