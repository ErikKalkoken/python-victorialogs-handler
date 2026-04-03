import atexit
import logging
import logging.config

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
            "flush_interval": 0.5,
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

# Make sure to flush logs before exiting
atexit.register(logging.shutdown)

# Create and use the logger
logger = logging.getLogger(__name__)

# Record log events
logger.debug("dict_example: This is a debug message")
logger.info("dict_example: This is an info message")
logger.error("dict_example: This is an error message")
