def test_data_sync_endpoint(client) -> None:
    """Validate manual data sync endpoint returns execution summary."""
    response = client.post(
        "/api/v1/data/sync",
        json={
            "symbols": ["000001.SZ"],
            "start_date": "2024-01-01",
            "end_date": "2024-01-05",
            "include_stock_universe": True,
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert "provider" in payload
    assert "price_inserted" in payload
