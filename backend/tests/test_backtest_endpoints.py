def test_backtest_run_and_query(client) -> None:
    """Validate backtest run endpoint, query endpoint, and run list endpoint integration."""
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

    run_resp = client.post(
        "/api/v1/backtest/run",
        json={
            "start_date": "2024-03-01",
            "end_date": "2024-04-30",
            "top_n": 2,
            "strategy_name": "multi_factor_v1",
            "factor_version": "v1",
            "initial_nav": 1.0,
            "force_rebalance": True,
        },
    )
    assert run_resp.status_code == 200

    run_payload = run_resp.json()
    assert run_payload["run_id"] is not None
    assert run_payload["status"] == "SUCCESS"
    assert len(run_payload["curve"]) > 0

    latest_resp = client.get("/api/v1/backtest")
    assert latest_resp.status_code == 200
    latest_payload = latest_resp.json()
    assert latest_payload["run_id"] == run_payload["run_id"]

    query_resp = client.get(f"/api/v1/backtest?run_id={run_payload['run_id']}")
    assert query_resp.status_code == 200
    query_payload = query_resp.json()
    assert query_payload["run_id"] == run_payload["run_id"]

    runs_resp = client.get("/api/v1/backtest/runs?strategy_name=multi_factor_v1&limit=5&offset=0")
    assert runs_resp.status_code == 200
    runs_payload = runs_resp.json()
    assert runs_payload["total"] >= 1
    assert runs_payload["limit"] == 5
    assert runs_payload["offset"] == 0
    assert isinstance(runs_payload["items"], list)
    assert any(item["run_id"] == run_payload["run_id"] for item in runs_payload["items"])
