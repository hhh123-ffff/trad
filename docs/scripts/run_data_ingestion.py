import argparse
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for data ingestion runner."""
    parser = argparse.ArgumentParser(description="Run market data ingestion.")
    parser.add_argument("--provider", default=None, help="Data provider: mock, akshare, or tushare.")
    parser.add_argument("--symbols", default="", help="Comma-separated symbols, e.g. 000001.SZ,600000.SH")
    parser.add_argument("--start-date", default=None, help="Start date in YYYY-MM-DD format.")
    parser.add_argument("--end-date", default=None, help="End date in YYYY-MM-DD format.")
    parser.add_argument("--skip-stock-universe", action="store_true", help="Skip refreshing stock universe.")
    return parser.parse_args()


def to_date(value: str | None, fallback: date) -> date:
    """Convert optional date string to date object with fallback."""
    if value is None or value.strip() == "":
        return fallback
    return date.fromisoformat(value)


def main() -> int:
    """Run data ingestion workflow and print JSON summary."""
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

    get_settings.cache_clear()
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_path)
    init_db()

    today = date.today()
    start = to_date(args.start_date, today - timedelta(days=7))
    end = to_date(args.end_date, today)
    symbols = [symbol.strip().upper() for symbol in args.symbols.split(",") if symbol.strip()]

    db = SessionLocal()
    try:
        service = MarketDataIngestionService()
        result = service.run_full_sync(
            db=db,
            symbols=symbols,
            start_date=start,
            end_date=end,
            include_stock_universe=not args.skip_stock_universe,
        )

        payload = {
            "provider": result.provider,
            "stock_count": result.stock_count,
            "price_inserted": result.price_inserted,
            "price_updated": result.price_updated,
            "symbols_processed": result.symbols_processed,
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
