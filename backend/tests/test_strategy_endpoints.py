def test_factor_calculation_and_strategy_run(client) -> None:
    """Validate factor calculation and strategy run endpoints end-to-end."""
    sync_resp = client.post(
        "/api/v1/data/sync",
        json={
            "symbols": ["000001.SZ", "600000.SH", "600519.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-03-29",
            "include_stock_universe": True,
        },
    )
    assert sync_resp.status_code == 200

    factor_resp = client.post(
        "/api/v1/factors/calculate",
        json={
            "symbols": ["000001.SZ", "600000.SH", "600519.SH"],
            "start_date": "2024-01-01",
            "end_date": "2024-03-29",
            "factor_version": "v1",
        },
    )
    assert factor_resp.status_code == 200
    factor_payload = factor_resp.json()
    assert factor_payload["records_inserted"] > 0

    strategy_resp = client.post(
        "/api/v1/strategy/run",
        json={
            "trade_date": "2024-03-29",
            "top_n": 2,
            "strategy_name": "multi_factor_v1",
            "factor_version": "v1",
            "force_rebalance": True,
        },
    )
    assert strategy_resp.status_code == 200
    strategy_payload = strategy_resp.json()
    assert strategy_payload["status"] in ["SUCCESS", "SKIPPED"]

    signals_resp = client.get("/api/v1/signals")
    assert signals_resp.status_code == 200
    signals_payload = signals_resp.json()
    assert isinstance(signals_payload, list)
    if signals_payload:
        assert signals_payload[0]["strategy_name"] == "multi_factor_v1"
        assert signals_payload[0]["action"] in ["BUY", "SELL", "HOLD"]
