"""
This script can be used to explore the behavior of the vlogs handler
during execution of a longer running script or application.

It sets up a logger with output to console and vlogs
and configures the vlogs logger to output to the console as well.

Note that this script assumes that there is a vlogs server running
on the same system at the default URL.
"""

import datetime as dt
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

# Configure the vlogs logger to output to console
vlogs_logger = logging.getLogger("vlogs_handler")
vlogs_logger.setLevel(logging.DEBUG)
vlogs_logger.addHandler(console_handler)

# Add a vlogs handler
stream = dt.datetime.now(tz=dt.UTC).strftime("%Y%m%dT%H%M%S")  # Unique ID for grouping
vlogs_handler = VictoriaLogsHandler(batch_size=30, record_to_stream=lambda _: stream)
vlogs_handler.setLevel(logging.DEBUG)
logger.addHandler(vlogs_handler)


i = 0
while True:
    i += 1
    logger.info("%d: This is an info message", i)
    time.sleep(0.1)
