from __future__ import annotations

import logging
import sys
from typing import Any


_CONFIGURED = False


def configure_logging(*, debug: bool = False) -> None:
    global _CONFIGURED
    level = logging.DEBUG if debug else logging.INFO

    if _CONFIGURED:
        logging.getLogger().setLevel(level)
        return

    logging.basicConfig(
        level=level,
        stream=sys.stdout,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
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
        details = " ".join(
            f"{key}={value!r}" for key, value in sorted(fields.items()) if value is not None
        )
        message = event if not details else f"{event} {details}"
        self.logger.log(level, message)
