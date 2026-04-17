from __future__ import annotations

import logging
import sys
from typing import Any


_CONFIGURED = False


class BracketFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        asctime = self.formatTime(record, self.datefmt)
        message = record.getMessage()
        if "\n" not in message:
            return f"{asctime} [{record.levelname}] [{record.name}] {message}"

        lines = message.splitlines()
        formatted_lines = [f"{asctime} [{record.levelname}] [{record.name}] {lines[0]}"]
        formatted_lines.extend(f"  {line}" for line in lines[1:])
        return "\n".join(formatted_lines)


def configure_logging(*, debug: bool = False) -> None:
    global _CONFIGURED
    level = logging.DEBUG if debug else logging.INFO

    if _CONFIGURED:
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(message)s",
    )
    for handler in logging.getLogger().handlers:
        handler.setFormatter(BracketFormatter())
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


class LogMixin:
    @property
    def logger(self) -> logging.Logger:
        logger_name = getattr(self, "logger_name", None)
        if callable(logger_name):
            logger_name = logger_name()
        if not logger_name:
            logger_name = self.__class__.__name__
        return get_logger(str(logger_name))

    def log_event(self, level: int, event: str, **fields: Any) -> None:
        field_lines = [
            f"{key}={value!r}"
            for key, value in sorted(fields.items())
            if value is not None
        ]
        message = event if not field_lines else "\n".join([event, *field_lines])
        self.logger.log(level, message)
