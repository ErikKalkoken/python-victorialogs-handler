import logging
import logging.config
import time

# Define the configuration dictionary
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {"format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
            "stream": "ext://sys.stdout",
        },
        "vlogs": {
            "class": "vlogs_handler.VictoriaLogsHandler",
            "level": "DEBUG",
            "start_worker": True,
        },
    },
    "loggers": {
        "": {  # Root logger
            "handlers": ["console", "vlogs"],
            "level": "DEBUG",
        },
    },
}

# Apply the configuration
logging.config.dictConfig(LOGGING_CONFIG)

# Create and use the logger
logger = logging.getLogger(__name__)

# Record log events
logger.debug("This is a debug message (visible in console)")
logger.info("This is an info message (visible in console and file)")
logger.error("Something went wrong!")

# Give the worker the chance to send the logs, before exiting.
time.sleep(1)
