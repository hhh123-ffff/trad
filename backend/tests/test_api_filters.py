def _prepare_simulation_data(client) -> None:
    """Prepare mock market data, factors, signals, and simulated orders for API filter tests."""
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


def test_api_filters_and_order_detail(client) -> None:
    """Validate API filter, pagination, and order detail endpoints with real simulated data."""
    _prepare_simulation_data(client)

    orders_resp = client.get("/api/v1/orders")
    assert orders_resp.status_code == 200
    orders_payload = orders_resp.json()
    assert len(orders_payload) >= 1

    first_order = orders_payload[0]
    order_id = first_order["order_id"]
    order_date = first_order["order_date"]
    symbol = first_order["symbol"]
    side = first_order["side"]
    status = first_order["status"]

    order_detail_resp = client.get(f"/api/v1/orders/{order_id}")
    assert order_detail_resp.status_code == 200
    assert order_detail_resp.json()["order_id"] == order_id

    missing_order_resp = client.get("/api/v1/orders/999999")
    assert missing_order_resp.status_code == 404
    missing_payload = missing_order_resp.json()
    assert missing_payload["success"] is False

    filtered_orders_resp = client.get(
        f"/api/v1/orders?symbol={symbol}&side={side}&status={status}&date_from={order_date}&date_to={order_date}&limit=10&offset=0"
    )
    assert filtered_orders_resp.status_code == 200
    filtered_orders_payload = filtered_orders_resp.json()
    assert len(filtered_orders_payload) >= 1
    assert all(item["symbol"] == symbol for item in filtered_orders_payload)
    assert all(item["side"] == side for item in filtered_orders_payload)
    assert all(item["status"] == status for item in filtered_orders_payload)

    positions_resp = client.get("/api/v1/positions?account_name=paper_account&limit=1&offset=0")
    assert positions_resp.status_code == 200
    positions_payload = positions_resp.json()
    assert isinstance(positions_payload, list)

    if positions_payload:
        first_position = positions_payload[0]
        snapshot_date = first_position["snapshot_date"]
        pos_symbol = first_position["symbol"]
        position_filter_resp = client.get(
            f"/api/v1/positions?snapshot_date={snapshot_date}&symbol={pos_symbol}&account_name=paper_account"
        )
        assert position_filter_resp.status_code == 200
        position_filter_payload = position_filter_resp.json()
        assert all(item["snapshot_date"] == snapshot_date for item in position_filter_payload)
        assert all(item["symbol"] == pos_symbol for item in position_filter_payload)

    signals_resp = client.get("/api/v1/signals?trade_date=2024-04-30&strategy_name=multi_factor_v1&limit=100")
    assert signals_resp.status_code == 200
    signals_payload = signals_resp.json()
    assert len(signals_payload) >= 1
    assert all(item["trade_date"] == "2024-04-30" for item in signals_payload)
    assert all(item["strategy_name"] == "multi_factor_v1" for item in signals_payload)

    action = signals_payload[0]["action"]
    action_filter_resp = client.get(
        f"/api/v1/signals?trade_date=2024-04-30&strategy_name=multi_factor_v1&action={action}"
    )
    assert action_filter_resp.status_code == 200
    action_filter_payload = action_filter_resp.json()
    assert all(item["action"] == action for item in action_filter_payload)

    dashboard_resp = client.get("/api/v1/dashboard?account_name=paper_account&days=30")
    assert dashboard_resp.status_code == 200
    dashboard_payload = dashboard_resp.json()
    assert dashboard_payload["total_asset"] > 0

    risk_resp = client.get("/api/v1/risk?account_name=paper_account")
    assert risk_resp.status_code == 200
    risk_payload = risk_resp.json()
    assert risk_payload["overall_level"] in ["INFO", "WARNING", "CRITICAL"]


def test_api_validation_for_query_params(client) -> None:
    """Validate query parameter constraints for API endpoints."""
    dashboard_resp = client.get("/api/v1/dashboard?days=0")
    assert dashboard_resp.status_code == 422

    positions_resp = client.get("/api/v1/positions?offset=-1")
    assert positions_resp.status_code == 422

    orders_resp = client.get("/api/v1/orders?limit=0")
    assert orders_resp.status_code == 422
