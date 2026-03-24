from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.logger import logger

from app.api.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db.init_db import init_db


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """Initialize and release app resources during startup and shutdown."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_path)
    logger.info("Application startup sequence started.")
    init_db()
    yield
    logger.info("Application shutdown sequence completed.")


def create_app() -> FastAPI:
    """Create and configure FastAPI application instance."""
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        debug=settings.app_debug,
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)

    @app.get("/")
    def root() -> dict[str, str]:
        """Return basic service metadata for quick checks."""
        return {
            "service": settings.app_name,
            "env": settings.app_env,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }

    return app


app = create_app()
