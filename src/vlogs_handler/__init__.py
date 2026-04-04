"""A log handler for VictoriaLogs."""

from .handler import VictoriaLogsHandler  # noqa: F401

__title__ = "VictoriaLogs Handler"
__version__ = "0.1.0dev7"

# TODO
# - Consider storing logs as strings or bytes to reduce memory footprint
# - Consider using a persistent queue
# - Enable logging and switch to full debug logging in prod for testing
