# backend

FastAPI backend service for the personal quant trading platform.

## Structure

- `app/main.py`: FastAPI entrypoint.
- `app/api`: API routers.
- `app/core`: settings, logging, exception handlers.
- `app/db`: SQLAlchemy base, engine, session, init logic.
- `app/models`: ORM models.
- `app/schemas`: Pydantic request/response schemas.
- `app/services`: service layer, broker adapter, data ingestion, factor engine, strategy engine, backtest engine, and paper trading engine.
- `app/tasks`: scheduled job functions.
- `app/scheduler`: APScheduler runner and job orchestration.
- `tests`: pytest API and data tests.

## Quick Start

1. Copy `.env.example` to `.env`.
2. Install dependencies:
   - `pip install -e .[dev]`
3. Start API:
   - `uvicorn app.main:app --reload --host 0.0.0.0 --port 8000`
4. Run tests:
   - `pytest`

## Data Provider

- `DATA_PROVIDER=mock`: offline local testing (default).
- `DATA_PROVIDER=akshare`: real market data via akshare.
- `DATA_PROVIDER=tushare`: real market data via tushare (requires `TUSHARE_TOKEN`).

## Strategy Endpoints

- `POST /api/v1/factors/calculate`: calculate and persist factors.
- `POST /api/v1/strategy/run`: generate weekly rebalance signals.
- `GET /api/v1/signals`: query strategy signals.
  - query params: `trade_date`, `strategy_name`, `action`, `limit`, `offset`.

## Backtest Endpoints

- `POST /api/v1/backtest/run`: run historical backtest and persist result.
- `GET /api/v1/backtest`: query latest backtest result or `run_id` specific result.
- `GET /api/v1/backtest/runs`: paginated historical backtest run list.
  - query params: `strategy_name`, `limit`, `offset`.

## Paper Trading Endpoints

- `POST /api/v1/simulation/run`: execute one-day paper trading simulation.
- `GET /api/v1/orders`: query simulated order history.
  - query params: `account_name`, `date_from`, `date_to`, `status`, `side`, `symbol`, `limit`, `offset`.
- `GET /api/v1/orders/{order_id}`: query one order detail by id.
- `GET /api/v1/positions`: query latest holdings snapshot.
  - query params: `account_name`, `snapshot_date`, `symbol`, `limit`, `offset`.
- `GET /api/v1/dashboard`: query portfolio summary and nav series.
  - query params: `account_name`, `days`.
- `GET /api/v1/risk`: query current risk status and alerts.
  - query params: `account_name`.

## Scheduler (APScheduler)

- Run scheduler daemon:
  - `python -m app.scheduler.runner`
- Run one job once:
  - `python -m app.scheduler.runner --once data`
  - `python -m app.scheduler.runner --once strategy`
  - `python -m app.scheduler.runner --once paper`
  - `python -m app.scheduler.runner --once backtest`

Environment variables:

- `SCHEDULER_TIMEZONE` (default: `Asia/Shanghai`)
- `SCHEDULER_DATA_CRON` (default: `30 15 * * 1-5`)
- `SCHEDULER_STRATEGY_CRON` (default: `40 15 * * 1-5`)
- `SCHEDULER_PAPER_TRADING_CRON` (default: `50 15 * * 1-5`)
- `SCHEDULER_BACKTEST_CRON` (default: `0 9 * * 6`)
