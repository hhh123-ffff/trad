from collections.abc import Generator

from app.core.logger import logger
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.exceptions import ApiException

settings = get_settings()


def _build_engine():
    """Create SQLAlchemy engine using current settings."""
    connect_args: dict[str, object] = {}
    if settings.database_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    try:
        return create_engine(
            settings.database_url,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
    except SQLAlchemyError as exc:
        raise RuntimeError("Failed to create SQLAlchemy engine.") from exc


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Provide a request-scoped SQLAlchemy session."""
    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Database operation failed: {}", exc)
        raise ApiException(status_code=500, detail="Database operation failed.") from exc
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
