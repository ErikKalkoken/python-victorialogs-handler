"""Module log provides a simple logger that works independently from Pythons logger."""

import sys
from typing import Optional


def info(context: str, **extras):
    _log("INFO", context, **extras)


def exception(context: str, ex: Exception, **extras):
    _log("ERROR", context, ex, **extras)


def _log(level: str, context: str, ex: Optional[Exception] = None, **extras):
    text = f"{level}: VictoriaLogsHandler: {context}"

    if ex:
        text += f" {ex} "

    if extras:
        parts = [f"{k}={v}" for k, v in extras.items()]
        text += ", ".join(parts)

    print(text, file=sys.stderr)
