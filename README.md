# victorialogs-handler

A Python log handler for VictoriaLogs.

[![release](https://img.shields.io/pypi/v/python-victorialogs-handler?label=release)](https://pypi.org/project/python-victorialogs-handler/)
[![python](https://img.shields.io/pypi/pyversions/python-victorialogs-handler)](https://pypi.org/project/python-victorialogs-handler/)
[![CI/CD](https://github.com/ErikKalkoken/python-victorialogs-handler/actions/workflows/cicd.yaml/badge.svg)](https://github.com/ErikKalkoken/python-victorialogs-handler/actions/workflows/cicd.yaml)
[![codecov](https://codecov.io/gh/ErikKalkoken/python-victorialogs-handler/graph/badge.svg?token=2pPb3lid2k)](https://codecov.io/gh/ErikKalkoken/python-victorialogs-handler)
[![license](https://img.shields.io/badge/license-MIT-green)](https://gitlab.com/ErikKalkoken/python-victorialogs-handler/-/blob/master/LICENSE)

> [!IMPORTANT]
> STATUS: In development. The API is not yet stable.

## Description

**victorialogs-handler** is a high-performance Python log handler tailored for [VictoriaLogs](https://victoriametrics.com/products/victorialogs/). It integrates seamlessly with Python’s native logging module, allowing you to stream log events to a VictoriaLogs instance with minimal configuration and zero friction.

## Key Features

- **Asynchronous Processing**: Log events are queued and dispatched in a dedicated background thread, ensuring your application's main execution flow remains non-blocking and highly responsive.

- **Efficient Request Batching**: To optimize network throughput and reduce overhead on your VictoriaLogs server, multiple log events are combined into chunks per request.

- **Rich Exception Handling**: Automatically captures and flattens stack traces. Log messages include both the exception name and the full traceback as searchable fields.

- **Smart Serialization**: Supports extra fields out of the box. It intelligently handles non-standard types like set and datetime. Any non-serializable objects (such as functions or custom classes) are gracefully converted to their string representation.

- **Standard Configuration Support**: Fully compatible with `logging.config.dictConfig`, making it easy to drop into frameworks like Django, Flask, or FastAPI.

## Installation

The handler can be installed with PIP from PyPI:

```sh
pip install victorialogs-handler
```

Then it can be used like any other logging handler to configure a logger.

## Quick start

> [!NOTE]
> The script assumes that there is a VictoriaLogs server running
> on the same system at the default URL: `http://localhost:9428`

Here is a quick example on how to use the handler in your Python script:

```python
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
```

Please see the directory `/examples` for additional examples on how to use the handler.

## Technical details

This section documents technical details of the solution.

### Technical process

The vlogs handler works as follows:

1. When a a log event is received, it is converted into JSON and stored in the buffer
2. At an interval (e.g. 5 second) or when a threshold is reached (e.g. 125 logs) a background worker starts the process of submitting logs from the buffer to the log server
3. Logs are combined into chunks (e.g. 1.000 logs per request) and then submitted to the log server using vlog's the JSON Stream API
4. In case submission fails (e.g. the log server is down) the logs will be stored back to the buffer for later retry
5. In case the buffer is full new logs will be discarded.
6. When the service shuts down, logs remaining in the buffer are transferred to the log server.

### LogRecord fields

The following fields will be transferred for each log event. They are derived from Python's [LogRecord](https://docs.python.org/3/library/logging.html#logrecord-objects):

Name | Description | Example | Optional
-- | -- | -- | --
`exception_name` | Name of the exception | `ZeroDivisionError` | yes
`exception` | Full traceback of the exception | `Traceback ...` | yes
`function` | Name of the function that emitted the log event | `my_function` | no
`level` | Name of the level of the emitted log event | `INFO` | no
`line_number` | Line number where the log event was emitted | `89` | no
`logger` | Name of the related Python logger | `my_package.my_module` | no
`message` | The logged message | 'This is a log entry' | no
`stream` | Name of the top-level Python package that emitted the log the event. | `my_package` | no
`timestamp` | Timestamp of the log event, represented as fractional UNIX epoch | `1775081468.4308655` | no

In addition any custom `extras' fields will be added as they are encountered.

### VictoriaLogs special fields

VictoriaLogs handles three fields in a special:

- `_msg`: The logged message. This is a mandatory field and is mapped to `message`.
- `_time`: The timestamp of the log event. This field and is mapped to `timestamp`.
- `_stream`: The source of a log event, which is used to group and filter logs. This field is mapped to `stream`.

For more information please also see [VictoriaLogs Data model](https://docs.victoriametrics.com/victorialogs/keyconcepts/#data-model).
