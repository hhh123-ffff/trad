import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for backtest runner."""
    parser = argparse.ArgumentParser(description="Run historical backtest pipeline.")
    parser.add_argument("--provider", default=None, help="Data provider: mock/akshare/tushare.")
    parser.add_argument("--start-date", default=None, help="Backtest start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", default=None, help="Backtest end date in YYYY-MM-DD format.")
    parser.add_argument("--top-n", default=None, type=int, help="Top N stocks for selection.")
    parser.add_argument("--strategy-name", default=None, help="Strategy name override.")
    parser.add_argument("--factor-version", default="v1", help="Factor version label.")
    parser.add_argument("--initial-nav", default=1.0, type=float, help="Initial NAV for backtest.")
    parser.add_argument("--force-rebalance", action="store_true", help="Force rebalance regardless of weekday.")
    return parser.parse_args()


def parse_date(value: str | None, fallback: date) -> date:
    """Parse optional ISO date string with fallback."""
    if value is None or value.strip() == "":
        return fallback
    return date.fromisoformat(value)


def main() -> int:
    """Run data sync and historical backtest; print JSON summary."""
    args = parse_args()

    backend_path = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_path))

    if args.provider:
        os.environ["DATA_PROVIDER"] = args.provider

    from app.core.config import get_settings
    from app.core.logging import setup_logging
    from app.db.init_db import init_db
    from app.db.session import SessionLocal
    from app.services.backtest.engine import BacktestEngine
    from app.services.data.ingestion import MarketDataIngestionService

    get_settings.cache_clear()
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_path)
    init_db()

    today = date.today()
    end_date = parse_date(args.end_date, today)
    start_date = parse_date(args.start_date, end_date - timedelta(days=365))

    db = SessionLocal()
    try:
        ingestion = MarketDataIngestionService()
        sync_result = ingestion.run_full_sync(
            db=db,
            symbols=None,
            start_date=start_date - timedelta(days=120),
            end_date=end_date,
            include_stock_universe=True,
        )

        engine = BacktestEngine()
        overview = engine.run(
            db=db,
            start_date=start_date,
            end_date=end_date,
            top_n=args.top_n,
            strategy_name=args.strategy_name,
            factor_version=args.factor_version,
            initial_nav=args.initial_nav,
            force_rebalance=args.force_rebalance,
        )

        payload = {
            "sync": {
                "provider": sync_result.provider,
                "stock_count": sync_result.stock_count,
                "price_inserted": sync_result.price_inserted,
                "price_updated": sync_result.price_updated,
            },
            "backtest": {
                "run_id": overview.run_id,
                "strategy_name": overview.strategy_name,
                "annual_return": overview.annual_return,
                "max_drawdown": overview.max_drawdown,
                "sharpe_ratio": overview.sharpe_ratio,
                "win_rate": overview.win_rate,
                "total_return": overview.total_return,
                "status": overview.status,
                "curve_points": len(overview.curve),
            },
        }
        print(json.dumps(payload, ensure_ascii=True))
        return 0
    except Exception as exc:
        print(json.dumps({"error": str(exc)}, ensure_ascii=True))
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
