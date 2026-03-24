import logging
from typing import Any


class StandardLoggerAdapter:
    """Adapter that mimics loguru-style formatting for stdlib logging."""

    def __init__(self, raw_logger: logging.Logger) -> None:
        """Initialize adapter with a standard logger instance."""
        self._raw_logger = raw_logger

    @staticmethod
    def _format(message: str, *args: Any, **kwargs: Any) -> str:
        """Apply brace-style formatting with safe fallback."""
        if not args and not kwargs:
            return message
        try:
            return message.format(*args, **kwargs)
        except Exception:
            return f"{message} | args={args} kwargs={kwargs}"

    def debug(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write debug level log."""
        self._raw_logger.debug(self._format(message, *args, **kwargs))

    def info(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write info level log."""
        self._raw_logger.info(self._format(message, *args, **kwargs))

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write warning level log."""
        self._raw_logger.warning(self._format(message, *args, **kwargs))

    def error(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write error level log."""
        self._raw_logger.error(self._format(message, *args, **kwargs))

    def exception(self, message: str, *args: Any, **kwargs: Any) -> None:
        """Write exception level log with traceback."""
        self._raw_logger.exception(self._format(message, *args, **kwargs))

    def setLevel(self, level: str) -> None:  # noqa: N802
        """Set logger level on underlying logger."""
        self._raw_logger.setLevel(level)

    @property
    def handlers(self) -> list[logging.Handler]:
        """Expose attached handlers for compatibility checks."""
        return self._raw_logger.handlers

    def addHandler(self, handler: logging.Handler) -> None:  # noqa: N802
        """Add handler on underlying logger."""
        self._raw_logger.addHandler(handler)


try:
    from loguru import logger as _logger

    logger = _logger
    LOGURU_AVAILABLE = True
except ModuleNotFoundError:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d - %(message)s",
    )
    logger = StandardLoggerAdapter(logging.getLogger("quant_trading"))
    LOGURU_AVAILABLE = False
