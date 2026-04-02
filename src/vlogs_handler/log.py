"""Module log provides a simple logger that works independently from Pythons logger."""

import sys
from typing import Optional


def info(message: str, **extras):
    """Log an info message."""
    _log("INFO", message, **extras)


def error(message: str, **extras):
    """Log an error message."""
    _log("ERROR", message, **extras)


def exception(message: str, ex: Exception, **extras):
    """Log an exception message."""
    _log("ERROR", message, ex, **extras)


def _log(level: str, message: str, ex: Optional[Exception] = None, **extras):
    text = f"{level}: VictoriaLogsHandler: {message}"

    if ex:
        text += f" {ex} "

    if extras:
        parts = [f"{k}={v}" for k, v in extras.items()]
        text += ", ".join(parts)

    print(text, file=sys.stderr)
