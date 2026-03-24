import argparse
import os
import signal
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.logger import logger
from app.core.logging import setup_logging
from app.db.init_db import init_db
from app.db.session import SessionLocal
from app.models.job_run import JobRun
from app.tasks.backtest_jobs import run_periodic_backtest
from app.tasks.data_jobs import run_daily_data_update
from app.tasks.paper_trading_jobs import run_daily_paper_trading
from app.tasks.strategy_jobs import run_weekly_strategy


@dataclass
class SchedulerSettings:
    """Runtime settings for APScheduler runner."""

    timezone_name: str
    data_cron: str
    strategy_cron: str
    paper_trading_cron: str
    backtest_cron: str


def _utc_now() -> datetime:
    """Return current UTC datetime."""
    return datetime.now(tz=timezone.utc)


def _record_job_run(job_name: str, status: str, message: str, duration_ms: int) -> None:
    """Persist scheduler job execution audit record to database."""
    db = SessionLocal()
    try:
        db.add(
            JobRun(
                job_name=job_name,
                status=status,
                message=message,
                duration_ms=duration_ms,
            )
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to record job run {}: {}", job_name, exc)
    finally:
        db.close()


def _execute_with_audit(job_name: str, fn) -> None:
    """Execute one job and write success/failure audit logs."""
    start = time.perf_counter()
    try:
        payload = fn()
        duration_ms = int((time.perf_counter() - start) * 1000)
        _record_job_run(
            job_name=job_name,
            status="SUCCESS",
            message=str(payload),
            duration_ms=duration_ms,
        )
        logger.info("Scheduled job {} completed in {} ms.", job_name, duration_ms)
    except Exception as exc:
        duration_ms = int((time.perf_counter() - start) * 1000)
        _record_job_run(
            job_name=job_name,
            status="FAILED",
            message=str(exc),
            duration_ms=duration_ms,
        )
        logger.exception("Scheduled job {} failed after {} ms: {}", job_name, duration_ms, exc)


def _load_scheduler_settings() -> SchedulerSettings:
    """Load scheduler cron and timezone settings from environment."""
    return SchedulerSettings(
        timezone_name=os.getenv("SCHEDULER_TIMEZONE", "Asia/Shanghai"),
        data_cron=os.getenv("SCHEDULER_DATA_CRON", "30 15 * * 1-5"),
        strategy_cron=os.getenv("SCHEDULER_STRATEGY_CRON", "40 15 * * 1-5"),
        paper_trading_cron=os.getenv("SCHEDULER_PAPER_TRADING_CRON", "50 15 * * 1-5"),
        backtest_cron=os.getenv("SCHEDULER_BACKTEST_CRON", "0 9 * * 6"),
    )


def _parse_timezone(timezone_name: str) -> ZoneInfo:
    """Parse timezone name and fallback to UTC when invalid."""
    try:
        return ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError:
        logger.warning("Unknown timezone {}. Fallback to UTC.", timezone_name)
        return ZoneInfo("UTC")


def _build_scheduler(settings: SchedulerSettings):
    """Create APScheduler with configured cron jobs."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "APScheduler is required to run daemon mode. Install dependency with 'pip install apscheduler'."
        ) from exc

    timezone_value = _parse_timezone(settings.timezone_name)
    scheduler = BlockingScheduler(timezone=timezone_value)

    scheduler.add_job(
        func=lambda: _execute_with_audit("daily_data_update", lambda: run_daily_data_update(symbols=None)),
        trigger=CronTrigger.from_crontab(settings.data_cron, timezone=timezone_value),
        id="daily_data_update",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        func=lambda: _execute_with_audit("daily_strategy", run_weekly_strategy),
        trigger=CronTrigger.from_crontab(settings.strategy_cron, timezone=timezone_value),
        id="daily_strategy",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        func=lambda: _execute_with_audit("daily_paper_trading", lambda: run_daily_paper_trading(run_date=None)),
        trigger=CronTrigger.from_crontab(settings.paper_trading_cron, timezone=timezone_value),
        id="daily_paper_trading",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=300,
    )

    scheduler.add_job(
        func=lambda: _execute_with_audit("weekly_backtest", lambda: run_periodic_backtest(days=365)),
        trigger=CronTrigger.from_crontab(settings.backtest_cron, timezone=timezone_value),
        id="weekly_backtest",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=600,
    )

    return scheduler


def _run_once(job_name: str) -> None:
    """Run one named job immediately and exit."""
    if job_name == "data":
        _execute_with_audit("daily_data_update", lambda: run_daily_data_update(symbols=None))
        return
    if job_name == "strategy":
        _execute_with_audit("daily_strategy", run_weekly_strategy)
        return
    if job_name == "paper":
        _execute_with_audit("daily_paper_trading", lambda: run_daily_paper_trading(run_date=None))
        return
    if job_name == "backtest":
        _execute_with_audit("weekly_backtest", lambda: run_periodic_backtest(days=365))
        return
    if job_name == "all":
        _execute_with_audit("daily_data_update", lambda: run_daily_data_update(symbols=None))
        _execute_with_audit("daily_strategy", run_weekly_strategy)
        _execute_with_audit("daily_paper_trading", lambda: run_daily_paper_trading(run_date=None))
        _execute_with_audit("weekly_backtest", lambda: run_periodic_backtest(days=365))
        return

    raise ValueError("Unsupported --once job. Use one of: data, strategy, paper, backtest, all.")


def _parse_args() -> argparse.Namespace:
    """Parse CLI arguments for scheduler runner."""
    parser = argparse.ArgumentParser(description="Quant trading APScheduler runner.")
    parser.add_argument(
        "--once",
        choices=["data", "strategy", "paper", "backtest", "all"],
        default=None,
        help="Run one job immediately and exit.",
    )
    return parser.parse_args()


def main() -> None:
    """Entrypoint for scheduler process."""
    setup_logging(level=os.getenv("LOG_LEVEL", "INFO"), log_path=os.getenv("LOG_PATH", "logs/app.log"))
    init_db()

    args = _parse_args()
    if args.once:
        logger.info("Scheduler run-once mode started at {} (UTC).", _utc_now().isoformat())
        _run_once(args.once)
        logger.info("Scheduler run-once mode finished.")
        return

    settings = _load_scheduler_settings()
    scheduler = _build_scheduler(settings)

    def _shutdown_handler(signum, _frame) -> None:
        """Gracefully shutdown scheduler process on OS signals."""
        logger.warning("Received signal {}. Shutting down scheduler.", signum)
        if scheduler.running:
            scheduler.shutdown(wait=False)

    signal.signal(signal.SIGINT, _shutdown_handler)
    signal.signal(signal.SIGTERM, _shutdown_handler)

    logger.info(
        "Scheduler started with timezone={} | data={} | strategy={} | paper={} | backtest={}",
        settings.timezone_name,
        settings.data_cron,
        settings.strategy_cron,
        settings.paper_trading_cron,
        settings.backtest_cron,
    )
    scheduler.start()


if __name__ == "__main__":
    main()
