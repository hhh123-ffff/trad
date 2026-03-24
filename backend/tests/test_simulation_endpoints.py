def test_paper_trading_simulation_flow(client) -> None:
    """Validate paper trading simulation updates orders, positions, and dashboard."""
    sync_resp = client.post(
        "/api/v1/data/sync",
        json={
            "symbols": ["000001.SZ", "600000.SH", "600519.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-04-30",
            "include_stock_universe": True,
        },
    )
    assert sync_resp.status_code == 200

    factor_resp = client.post(
        "/api/v1/factors/calculate",
        json={
            "symbols": ["000001.SZ", "600000.SH", "600519.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-04-30",
            "factor_version": "v1",
        },
    )
    assert factor_resp.status_code == 200

    strategy_resp = client.post(
        "/api/v1/strategy/run",
        json={
            "trade_date": "2024-04-30",
            "top_n": 2,
            "strategy_name": "multi_factor_v1",
            "factor_version": "v1",
            "force_rebalance": True,
        },
    )
    assert strategy_resp.status_code == 200

    simulation_resp = client.post(
        "/api/v1/simulation/run",
        json={
            "trade_date": "2024-04-30",
            "account_name": "paper_account",
        },
    )
    assert simulation_resp.status_code == 200

    simulation_payload = simulation_resp.json()
    assert simulation_payload["orders_created"] >= 1
    assert simulation_payload["total_asset"] > 0

    orders_resp = client.get("/api/v1/orders")
    assert orders_resp.status_code == 200
    orders_payload = orders_resp.json()
    assert isinstance(orders_payload, list)
    assert len(orders_payload) >= 1

    positions_resp = client.get("/api/v1/positions")
    assert positions_resp.status_code == 200
    positions_payload = positions_resp.json()
    assert isinstance(positions_payload, list)

    dashboard_resp = client.get("/api/v1/dashboard")
    assert dashboard_resp.status_code == 200
    dashboard_payload = dashboard_resp.json()
    assert dashboard_payload["total_asset"] > 0
