"""
This script demonstrates how to setup and use a logger with the vlogs handler.

Note that the script assumes that there is a vlogs server running
on the same system at the default URL.
"""

import logging
import time

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

# 2. Add a handler for VictoriaLogs
vlogs_handler = VictoriaLogsHandler()
vlogs_handler.setLevel(logging.DEBUG)
logger.addHandler(vlogs_handler)

# 4. Start the worker
vlogs_handler.start()

# Log example with structured data
logger.info("This is an info message", extra={"user_id": 42})

# Log example with an exception
try:
    _ = 1 / 0
except Exception:
    logger.exception("This is an error")

# Give the worker the chance to send the logs, before exiting.
time.sleep(1)
