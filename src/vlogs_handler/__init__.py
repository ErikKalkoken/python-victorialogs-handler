"""A log handler for VictoriaLogs."""

from .handler import VictoriaLogsHandler  # noqa: F401

__title__ = "VictoriaLogs Handler"
__version__ = "0.1.0dev7"

__all__ = ["VictoriaLogsHandler"]

# TODO
# - Enable logging and switch to full debug logging in prod for testing
# - Consider using a persistent queue
