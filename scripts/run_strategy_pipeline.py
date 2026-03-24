import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for strategy pipeline runner."""
    parser = argparse.ArgumentParser(description="Run factor calculation and strategy signal generation.")
    parser.add_argument("--trade-date", default=None, help="Strategy trade date in YYYY-MM-DD format.")
    parser.add_argument("--top-n", default=None, type=int, help="Top N stocks for selection.")
    parser.add_argument("--strategy-name", default=None, help="Strategy name override.")
    parser.add_argument("--factor-version", default="v1", help="Factor version label.")
    parser.add_argument("--force-rebalance", action="store_true", help="Force rebalance regardless of weekday.")
    parser.add_argument("--provider", default=None, help="Data provider: mock/akshare/tushare.")
    parser.add_argument("--start-date", default=None, help="Factor/data start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", default=None, help="Factor/data end date in YYYY-MM-DD format.")
    return parser.parse_args()


def parse_date(value: str | None, fallback: date) -> date:
    """Parse optional ISO date string with fallback."""
    if value is None or value.strip() == "":
        return fallback
    return date.fromisoformat(value)


def main() -> int:
    """Run data sync, factor engine, and strategy engine in sequence."""
    args = parse_args()

    backend_path = Path(__file__).resolve().parents[1] / "backend"
    sys.path.insert(0, str(backend_path))

    if args.provider:
        os.environ["DATA_PROVIDER"] = args.provider

    from app.core.config import get_settings
    from app.core.logging import setup_logging
    from app.db.init_db import init_db
    from app.db.session import SessionLocal
    from app.services.data.ingestion import MarketDataIngestionService
    from app.services.strategy.factor_engine import FactorEngine
    from app.services.strategy.strategy_engine import MultiFactorStrategyEngine

    get_settings.cache_clear()
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_path)
    init_db()

    today = date.today()
    start_date = parse_date(args.start_date, today - timedelta(days=180))
    end_date = parse_date(args.end_date, today)
    trade_date = parse_date(args.trade_date, end_date)

    db = SessionLocal()
    try:
        ingestion = MarketDataIngestionService()
        sync_result = ingestion.run_full_sync(
            db=db,
            symbols=None,
            start_date=start_date,
            end_date=end_date,
            include_stock_universe=True,
        )

        factor_engine = FactorEngine()
        factor_result = factor_engine.run(
            db=db,
            start_date=start_date,
            end_date=end_date,
            symbols=None,
            factor_version=args.factor_version,
        )

        strategy_engine = MultiFactorStrategyEngine(factor_engine=factor_engine)
        strategy_result = strategy_engine.run(
            db=db,
            trade_date=trade_date,
            top_n=args.top_n,
            strategy_name=args.strategy_name,
            factor_version=args.factor_version,
            force_rebalance=args.force_rebalance,
        )

        payload = {
            "sync": {
                "provider": sync_result.provider,
                "stock_count": sync_result.stock_count,
                "price_inserted": sync_result.price_inserted,
                "price_updated": sync_result.price_updated,
            },
            "factor": {
                "symbols_processed": factor_result.symbols_processed,
                "trade_dates": factor_result.trade_dates,
                "records_inserted": factor_result.records_inserted,
                "records_updated": factor_result.records_updated,
            },
            "strategy": {
                "trade_date": strategy_result.trade_date.isoformat(),
                "strategy_name": strategy_result.strategy_name,
                "status": strategy_result.status,
                "timing_passed": strategy_result.timing_passed,
                "selected_count": strategy_result.selected_count,
                "buy_count": strategy_result.buy_count,
                "sell_count": strategy_result.sell_count,
                "hold_count": strategy_result.hold_count,
                "reason": strategy_result.reason,
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
