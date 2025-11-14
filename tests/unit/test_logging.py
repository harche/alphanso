"""Unit tests for logging configuration."""

import json
import logging
import sys
from io import StringIO

from alphanso.utils.logging import (
    JSONFormatter,
    get_logger,
    is_logging_configured,
    setup_logging,
)


class TestJSONFormatter:
    """Test JSONFormatter for structured logging."""

    def test_format_basic_message(self):
        """Test formatting a basic log message as JSON."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert "timestamp" in data

    def test_format_with_extra_fields(self):
        """Test formatting with extra fields."""
        formatter = JSONFormatter()
        record = logging.LogRecord(
            name="test.logger",
            level=logging.DEBUG,
            pathname="test.py",
            lineno=20,
            msg="Debug message",
            args=(),
            exc_info=None,
        )
        record.node_name = "validate"
        record.attempt = 3

        result = formatter.format(record)
        data = json.loads(result)

        assert data["extra"]["node_name"] == "validate"
        assert data["extra"]["attempt"] == 3

    def test_format_with_exception(self):
        """Test formatting with exception info."""
        formatter = JSONFormatter()
        try:
            raise ValueError("Test error")
        except ValueError:
            exc_info = sys.exc_info()

        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=30,
            msg="Error occurred",
            args=(),
            exc_info=exc_info,
        )

        result = formatter.format(record)
        data = json.loads(result)

        assert data["level"] == "ERROR"
        assert "exception" in data
        assert "ValueError: Test error" in data["exception"]


class TestSetupLogging:
    """Test setup_logging function."""

    def teardown_method(self):
        """Clean up logging handlers after each test."""
        logger = logging.getLogger("alphanso")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

    def test_setup_logging_default(self):
        """Test setup_logging with defaults."""
        setup_logging()

        logger = logging.getLogger("alphanso")
        assert logger.level == logging.INFO
        assert len(logger.handlers) == 1
        assert logger.propagate is False

    def test_setup_logging_custom_level(self):
        """Test setup_logging with custom log level."""
        setup_logging(level=logging.DEBUG)

        logger = logging.getLogger("alphanso")
        assert logger.level == logging.DEBUG

    def test_setup_logging_file_handler_text(self, tmp_path):
        """Test setup_logging with text file handler."""
        log_file = tmp_path / "test.log"
        setup_logging(log_file=log_file, log_format="text")

        logger = logging.getLogger("alphanso")
        assert len(logger.handlers) == 2  # Console + file

        # Write a test message using alphanso logger (not test logger)
        # This ensures the message goes to the configured handlers
        test_logger = get_logger("alphanso.test")
        test_logger.info("Test message")

        # Flush all handlers to ensure logs are written to file
        for handler in logger.handlers:
            handler.flush()

        # Check file contents
        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content
        assert "INFO" in content

    def test_setup_logging_file_handler_json(self, tmp_path):
        """Test setup_logging with JSON file handler."""
        log_file = tmp_path / "test.json"
        setup_logging(log_file=log_file, log_format="json")

        logger = logging.getLogger("alphanso")
        assert len(logger.handlers) == 2  # Console + file

        # Write a test message using alphanso logger (not test logger)
        # This ensures the message goes to the configured handlers
        test_logger = get_logger("alphanso.test")
        test_logger.info("JSON test message")

        # Flush all handlers to ensure logs are written to file
        for handler in logger.handlers:
            handler.flush()

        # Check file contents
        assert log_file.exists()
        content = log_file.read_text()
        data = json.loads(content.strip())
        assert data["level"] == "INFO"
        assert data["message"] == "JSON test message"

    def test_setup_logging_no_colors(self):
        """Test setup_logging without colors."""
        setup_logging(enable_colors=False)

        logger = logging.getLogger("alphanso")
        assert len(logger.handlers) == 1

        # Handler should be regular StreamHandler, not RichHandler
        from rich.logging import RichHandler

        assert not isinstance(logger.handlers[0], RichHandler)

    def test_setup_logging_removes_existing_handlers(self):
        """Test that setup_logging removes existing handlers."""
        logger = logging.getLogger("alphanso")
        # Add a dummy handler
        logger.addHandler(logging.StreamHandler())
        assert len(logger.handlers) == 1

        setup_logging()
        # Should only have the new handler
        assert len(logger.handlers) == 1


class TestGetLogger:
    """Test get_logger function."""

    def test_get_logger_returns_hierarchical_logger(self):
        """Test that get_logger returns hierarchical logger."""
        logger = get_logger("alphanso.test.module")

        assert logger.name == "alphanso.test.module"
        assert isinstance(logger, logging.Logger)

    def test_get_logger_inherits_from_alphanso(self):
        """Test that child logger inherits from alphanso namespace."""
        setup_logging(level=logging.DEBUG)

        parent_logger = logging.getLogger("alphanso")
        child_logger = get_logger("alphanso.test")

        # Child should inherit level from parent
        assert child_logger.level == logging.NOTSET  # Inherits from parent
        assert child_logger.parent == parent_logger


class TestIsLoggingConfigured:
    """Test is_logging_configured function."""

    def setup_method(self):
        """Clean up logging handlers before each test to ensure clean state."""
        logger = logging.getLogger("alphanso")
        logger.handlers.clear()

    def teardown_method(self):
        """Clean up logging handlers after each test."""
        logger = logging.getLogger("alphanso")
        logger.handlers.clear()

    def test_is_logging_configured_false_initially(self):
        """Test that is_logging_configured returns False initially."""
        assert is_logging_configured() is False

    def test_is_logging_configured_true_after_setup(self):
        """Test that is_logging_configured returns True after setup."""
        assert is_logging_configured() is False
        setup_logging()
        assert is_logging_configured() is True


class TestLoggingIntegration:
    """Integration tests for logging system."""

    def teardown_method(self):
        """Clean up logging handlers after each test."""
        logger = logging.getLogger("alphanso")
        logger.handlers.clear()
        logger.setLevel(logging.NOTSET)

    def test_logging_output_levels(self):
        """Test that different log levels work correctly."""
        # Setup logging to capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

        logger = logging.getLogger("alphanso")
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logger.propagate = False

        # Test different levels using alphanso logger (not test logger)
        # This ensures the messages go to the configured handlers
        test_logger = get_logger("alphanso.test")
        test_logger.debug("Debug message")
        test_logger.info("Info message")
        test_logger.warning("Warning message")
        test_logger.error("Error message")

        # Flush handler to ensure output is written
        handler.flush()

        output = stream.getvalue()
        assert "DEBUG - Debug message" in output
        assert "INFO - Info message" in output
        assert "WARNING - Warning message" in output
        assert "ERROR - Error message" in output

    def test_logging_respects_level_filter(self):
        """Test that log level filtering works."""
        # Setup logging to capture output
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))

        logger = logging.getLogger("alphanso")
        logger.setLevel(logging.WARNING)  # Only WARNING and above
        logger.addHandler(handler)
        logger.propagate = False

        # Test different levels using alphanso logger (not test logger)
        # This ensures the messages go to the configured handlers
        test_logger = get_logger("alphanso.test")
        test_logger.debug("Debug message")  # Should not appear
        test_logger.info("Info message")  # Should not appear
        test_logger.warning("Warning message")  # Should appear
        test_logger.error("Error message")  # Should appear

        # Flush handler to ensure output is written
        handler.flush()

        output = stream.getvalue()
        assert "DEBUG" not in output
        assert "INFO" not in output
        assert "WARNING - Warning message" in output
        assert "ERROR - Error message" in output
