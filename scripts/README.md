# scripts

Command-line helper scripts for initialization, data bootstrap, and operational maintenance tasks.

## Available Scripts

- `run_data_ingestion.py`: Run market data ingestion and persistence workflow.
- `run_strategy_pipeline.py`: Run data sync, factor calculation, and strategy signal generation.
- `run_backtest.py`: Run data sync and historical backtest with persisted NAV curve.
- `run_paper_trading.py`: Run data sync, factor, strategy, and paper trading simulation.
- `run_scheduler.py`: Run APScheduler daemon or one-off jobs (`--once data|strategy|paper|backtest|all`).
