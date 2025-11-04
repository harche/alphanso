"""Logging configuration for Alphanso framework.

This module provides comprehensive logging setup with support for:
- Rich console output with colors and formatting
- Text file logging with detailed formatting
- Structured JSON logging for machine parsing
- Configurable log levels for both CLI and API users
- Custom TRACE level (5) for ultra-verbose diagnostics
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.logging import RichHandler

# Define custom TRACE log level (below DEBUG)
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def trace(self, message, *args, **kwargs):
    """Log a message with severity 'TRACE' on this logger."""
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


# Add trace method to Logger class
logging.Logger.trace = trace  # type: ignore


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging.

    Outputs one JSON object per line with timestamp, level, logger name,
    message, and optional extra fields.

    Example output:
        {"timestamp": "2025-11-03T14:30:45.123Z", "level": "INFO",
         "logger": "alphanso.graph.nodes", "message": "Entering validate node",
         "extra": {"node": "validate", "attempt": 1}}
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record as a JSON string.

        Args:
            record: Log record to format

        Returns:
            JSON string representing the log record
        """
        log_data: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add any extra fields from the record
        # Skip standard fields to avoid duplication
        standard_fields = {
            "name",
            "msg",
            "args",
            "created",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "module",
            "msecs",
            "message",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "thread",
            "threadName",
            "exc_info",
            "exc_text",
            "stack_info",
        }

        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in standard_fields and not key.startswith("_")
        }

        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data)


def setup_logging(
    level: int = logging.INFO,
    log_file: Path | None = None,
    log_format: str = "text",
    enable_colors: bool = True,
) -> None:
    """Configure logging for the entire Alphanso application.

    This should be called once at application startup (either in CLI or API).
    Sets up handlers for console output and optional file output.

    Args:
        level: Logging level (logging.DEBUG, logging.INFO, etc.)
        log_file: Optional path to write log file. If provided, logs are
                 written to this file in addition to console output.
        log_format: Format for file output ("text" or "json")
        enable_colors: Whether to use Rich colored console output.
                      Set to False for environments without color support.

    Example:
        >>> from alphanso.utils.logging import setup_logging
        >>> import logging
        >>>
        >>> # CLI usage
        >>> setup_logging(level=logging.DEBUG, log_file=Path("debug.log"))
        >>>
        >>> # API usage with JSON output
        >>> setup_logging(
        ...     level=logging.INFO,
        ...     log_file=Path("alphanso.json"),
        ...     log_format="json"
        ... )
    """
    # Get root logger for alphanso package
    logger = logging.getLogger("alphanso")
    logger.setLevel(level)

    # Remove any existing handlers to avoid duplicates
    logger.handlers.clear()

    # Prevent propagation to root logger (avoid duplicate output)
    logger.propagate = False

    # Console handler with Rich formatting
    if enable_colors and sys.stdout.isatty():
        console = Console(file=sys.stdout, force_terminal=True)
        console_handler = RichHandler(
            console=console,
            show_time=False,  # We'll handle timestamps in file logging
            show_path=False,  # Don't show file path in console
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            markup=True,  # Allow rich markup in messages
        )
    else:
        # Fallback to standard stream handler
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            fmt="%(levelname)s - %(name)s - %(message)s"
        )
        console_handler.setFormatter(formatter)

    console_handler.setLevel(level)
    logger.addHandler(console_handler)

    # File handler (optional)
    if log_file:
        log_file = Path(log_file)
        log_file.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, mode="a")
        file_handler.setLevel(logging.DEBUG)  # Always log DEBUG to file

        if log_format == "json":
            file_handler.setFormatter(JSONFormatter())
        else:
            # Detailed text format for file
            file_formatter = logging.Formatter(
                fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
            file_handler.setFormatter(file_formatter)

        logger.addHandler(file_handler)


def get_logger(name: str) -> logging.Logger:
    """Get a logger for a specific module.

    Creates a hierarchical logger under the alphanso namespace.
    For example, alphanso.graph.nodes or alphanso.agent.client.

    Args:
        name: Module name, typically __name__

    Returns:
        Logger instance for the module

    Example:
        >>> from alphanso.utils.logging import get_logger
        >>>
        >>> logger = get_logger(__name__)
        >>> logger.info("Processing validation results")
        >>> logger.debug("State: %s", state)
    """
    return logging.getLogger(name)


# Convenience function for checking if logging is configured
def is_logging_configured() -> bool:
    """Check if Alphanso logging has been configured.

    Returns:
        True if setup_logging() has been called, False otherwise
    """
    logger = logging.getLogger("alphanso")
    return len(logger.handlers) > 0
