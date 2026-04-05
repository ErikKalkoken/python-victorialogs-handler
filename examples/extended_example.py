"""
This script demonstrates how to setup and use a logger with the vlogs handler.
It also sets up a console handler and a logger for the vlogs handler itself.

Note that this script assumes that there is a vlogs server running
on the same system at the default URL.
"""

import logging

from vlogs_handler import VictoriaLogsHandler

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set the lowest level to capture

# Add a handler for console logging
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
log_format = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(log_format)
logger.addHandler(console_handler)

# Configure the vlogs logger to output to console
vlogs_logger = logging.getLogger("vlogs_handler")
vlogs_logger.setLevel(logging.DEBUG)
vlogs_logger.addHandler(console_handler)

# Add a vlogs handler
vlogs_handler = VictoriaLogsHandler()
vlogs_handler.setLevel(logging.DEBUG)
logger.addHandler(vlogs_handler)


# Log example with structured data
logger.info("basic_example: This is an info message", extra={"user_id": 42})

# Log example with an exception
try:
    _ = 1 / 0
except Exception:
    logger.exception("basic_example: This is an exception")
