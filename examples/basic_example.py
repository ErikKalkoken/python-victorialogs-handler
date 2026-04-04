"""
This script demonstrates how to setup and use a logger with the vlogs handler.

Note that the script assumes that there is a vlogs server running
on the same system at the default URL.
"""

import atexit
import logging

from vlogs_handler import VictoriaLogsHandler

# Create a custom logger with INFO level
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add a handler for VictoriaLogs
vlogs_handler = VictoriaLogsHandler()
vlogs_handler.setLevel(logging.DEBUG)
logger.addHandler(vlogs_handler)

# Make sure to flush logs before exiting
atexit.register(logging.shutdown)

# Log example
logger.info("This is an info message")
