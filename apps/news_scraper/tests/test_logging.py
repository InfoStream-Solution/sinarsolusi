from __future__ import annotations

import logging

from src.utils.logging import BracketFormatter, LogMixin, configure_logging, get_logger


def test_configure_logging_sets_level_without_duplicating_handlers() -> None:
    root = logging.getLogger()
    original_handlers = list(root.handlers)
    original_level = root.level

    try:
        for handler in list(root.handlers):
            root.removeHandler(handler)

        configure_logging(debug=False)
        first_handlers = list(root.handlers)
        first_level = root.level

        configure_logging(debug=True)
        second_handlers = list(root.handlers)
        second_level = root.level

        assert first_handlers == second_handlers
        assert first_level == logging.INFO
        assert second_level == logging.DEBUG
    finally:
        for handler in list(root.handlers):
            root.removeHandler(handler)
        for handler in original_handlers:
            root.addHandler(handler)
        root.setLevel(original_level)


def test_get_logger_returns_named_logger() -> None:
    logger = get_logger("news_scraper.test")
    assert logger.name == "news_scraper.test"


def test_log_mixin_prefers_logger_name_property() -> None:
    class Demo(LogMixin):
        @property
        def logger_name(self) -> str:
            return "demo.logger"

    assert Demo().logger.name == "demo.logger"


def test_configure_logging_uses_bracketed_format() -> None:
    record = logging.LogRecord(
        name="demo.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello\nfield='value'",
        args=(),
        exc_info=None,
    )

    formatter = BracketFormatter()
    assert formatter.format(record) == (
        f"{formatter.formatTime(record, formatter.datefmt)} [INFO] [demo.logger] hello\n"
        "  field='value'"
    )
