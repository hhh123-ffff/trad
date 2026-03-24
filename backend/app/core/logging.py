import logging
from pathlib import Path

from app.core.logger import LOGURU_AVAILABLE, logger


def setup_logging(level: str, log_path: str) -> None:
    """Configure application logging with loguru or stdlib fallback."""
    try:
        log_file = Path(log_path)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        if LOGURU_AVAILABLE:
            logger.remove()
            logger.add(
                sink=lambda message: print(message, end=""),
                level=level.upper(),
                enqueue=True,
                backtrace=True,
                diagnose=False,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
            )
            logger.add(
                sink=str(log_file),
                level=level.upper(),
                rotation="10 MB",
                retention="10 days",
                encoding="utf-8",
                enqueue=True,
                backtrace=True,
                diagnose=False,
                format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level:<8} | {name}:{function}:{line} - {message}",
            )
            return

        logger.setLevel(level.upper())
        file_handler = logging.FileHandler(filename=str(log_file), encoding="utf-8")
        formatter = logging.Formatter(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s"
        )
        file_handler.setFormatter(formatter)

        if not any(isinstance(handler, logging.FileHandler) for handler in logger.handlers):
            logger.addHandler(file_handler)
    except OSError as exc:
        raise RuntimeError("Failed to initialize logging sinks.") from exc
