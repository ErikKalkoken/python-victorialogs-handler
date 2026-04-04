"""A log handler for VictoriaLogs."""

from .handler import VictoriaLogsHandler  # noqa: F401

__title__ = "VictoriaLogs Handler"
__version__ = "0.1.0dev6"

# TODO
# [ ] - Split very large requests
# [ ] - Consider using a persistent queue
# [ ] - Enable logging and switch to full debug logging in prod for testing
