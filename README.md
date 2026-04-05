# victorialogs-handler

A high-performance Python log handler for VictoriaLogs.

[![release](https://img.shields.io/pypi/v/python-victorialogs-handler?label=release)](https://pypi.org/project/python-victorialogs-handler/)
[![python](https://img.shields.io/pypi/pyversions/python-victorialogs-handler)](https://pypi.org/project/python-victorialogs-handler/)
[![CI/CD](https://github.com/ErikKalkoken/python-victorialogs-handler/actions/workflows/cicd.yaml/badge.svg)](https://github.com/ErikKalkoken/python-victorialogs-handler/actions/workflows/cicd.yaml)
[![codecov](https://codecov.io/gh/ErikKalkoken/python-victorialogs-handler/graph/badge.svg?token=2pPb3lid2k)](https://codecov.io/gh/ErikKalkoken/python-victorialogs-handler)
[![license](https://img.shields.io/badge/license-MIT-green)](https://gitlab.com/ErikKalkoken/python-victorialogs-handler/-/blob/master/LICENSE)

> [!IMPORTANT]
> STATUS: In development. The API may still change.

## Description

**victorialogs-handler** is a high-performance Python log handler tailored for [VictoriaLogs](https://victoriametrics.com/products/victorialogs/). It integrates seamlessly with Python’s native logging module, allowing you to stream log events to a VictoriaLogs instance with minimal configuration.

- Non-blocking: Logs are stored in a buffer and later processed in a background thread.
- Hybrid trigger: Log processing is triggered by a ticker and/or when a size threshold is reached.
- Batching: Multiple logs are combined into one request to the log server to minimize the amount of requests.
- Complete logs: All fields of a log record are transmitted including exceptions and `extra` fields.
- Highly customizable: The handler's behavior is highly customizable (see also [Documentation](#documentation))

## Installation

The handler can be installed with PIP from PyPI:

```sh
pip install victorialogs-handler
```

## Quick start

> [!NOTE]
> The script assumes that there is a VictoriaLogs server running
> on the same system at the default URL: `http://localhost:9428`

Here is a quick example on how to use the handler in your Python script:

```python
import logging

from vlogs_handler import VictoriaLogsHandler

# Create a custom logger with INFO level
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Add a handler for VictoriaLogs
vlogs_handler = VictoriaLogsHandler()
vlogs_handler.setLevel(logging.DEBUG)
logger.addHandler(vlogs_handler)

# Log example
logger.info("This is an info message")
```

Please see the directory `/examples` for additional examples on how to use the handler.

## Documentation

The full documentation can be found here: [Documentation](https://erikkalkoken.github.io/python-victorialogs-handler/).
