from app.core.logger import logger
from sqlalchemy.exc import SQLAlchemyError

from app.db.base import Base
from app.db.session import engine
from app.models import backtest_nav, backtest_run, factor, job_run, order, portfolio, position, price, risk_log, signal, stock  # noqa: F401


def init_db() -> None:
    """Create tables for all imported ORM models."""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("Database schema initialization completed.")
    except SQLAlchemyError as exc:
        logger.exception("Database initialization failed: {}", exc)
        raise RuntimeError("Database initialization failed.") from exc
