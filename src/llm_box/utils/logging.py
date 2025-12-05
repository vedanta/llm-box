"""Structured logging setup for llm-box."""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

# Module-level logger
logger = logging.getLogger("llm_box")


class JSONFormatter(logging.Formatter):
    """JSON formatter for machine-readable logs."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add extra fields if present
        if hasattr(record, "extra") and isinstance(record.extra, dict):
            log_data.update(record.extra)

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add standard fields
        log_data["module"] = record.module
        log_data["function"] = record.funcName
        log_data["line"] = record.lineno

        return json.dumps(log_data)


class RichFormatter(logging.Formatter):
    """Human-readable formatter with colors."""

    COLORS = {
        "DEBUG": "\033[36m",  # Cyan
        "INFO": "\033[32m",  # Green
        "WARNING": "\033[33m",  # Yellow
        "ERROR": "\033[31m",  # Red
        "CRITICAL": "\033[35m",  # Magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool = True) -> None:
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        """Format log record with optional colors."""
        level = record.levelname
        message = record.getMessage()

        if self.use_color:
            color = self.COLORS.get(level, "")
            return f"{color}{level:8}{self.RESET} {record.name}: {message}"
        else:
            return f"{level:8} {record.name}: {message}"


def setup_logging(
    level: str = "INFO",
    log_file: Path | None = None,
    json_format: bool = False,
    use_color: bool = True,
) -> logging.Logger:
    """Configure logging for llm-box.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Optional file path for logging.
        json_format: Use JSON format for logs.
        use_color: Use colors in console output.

    Returns:
        Configured logger instance.
    """
    # Get numeric level
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    # Configure root llm_box logger
    logger.setLevel(numeric_level)

    # Remove existing handlers
    logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setLevel(numeric_level)

    if json_format:
        console_handler.setFormatter(JSONFormatter())
    else:
        console_handler.setFormatter(RichFormatter(use_color=use_color))

    logger.addHandler(console_handler)

    # File handler (always JSON for parsing)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)

    # Don't propagate to root logger
    logger.propagate = False

    return logger


def get_logger(name: str) -> logging.Logger:
    """Get a child logger for a module.

    Args:
        name: Module name (e.g., 'llm_box.providers').

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)


def log_with_context(
    logger: logging.Logger,
    level: int,
    message: str,
    **context: Any,
) -> None:
    """Log a message with additional context.

    Args:
        logger: Logger instance.
        level: Log level (e.g., logging.INFO).
        message: Log message.
        **context: Additional key-value pairs to include.
    """
    record = logger.makeRecord(
        logger.name,
        level,
        "(unknown)",
        0,
        message,
        (),
        None,
    )
    record.extra = context  # noqa: attr assignment for extra context
    logger.handle(record)


# Convenience functions
def debug(message: str, **context: Any) -> None:
    """Log debug message with context."""
    log_with_context(logger, logging.DEBUG, message, **context)


def info(message: str, **context: Any) -> None:
    """Log info message with context."""
    log_with_context(logger, logging.INFO, message, **context)


def warning(message: str, **context: Any) -> None:
    """Log warning message with context."""
    log_with_context(logger, logging.WARNING, message, **context)


def error(message: str, **context: Any) -> None:
    """Log error message with context."""
    log_with_context(logger, logging.ERROR, message, **context)


def critical(message: str, **context: Any) -> None:
    """Log critical message with context."""
    log_with_context(logger, logging.CRITICAL, message, **context)
