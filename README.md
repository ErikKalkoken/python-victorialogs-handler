# python-victorialogs-handler

A Python log handler for Victoria Logs.

[![release](https://img.shields.io/pypi/v/python-victorialogs-handler?label=release)](https://pypi.org/project/python-victorialogs-handler/)
[![python](https://img.shields.io/pypi/pyversions/python-victorialogs-handler)](https://pypi.org/project/python-victorialogs-handler/)
[![CI/CD](https://github.com/ErikKalkoken/python-victorialogs-handler/actions/workflows/cicd.yaml/badge.svg)](https://github.com/ErikKalkoken/python-victorialogs-handler/actions/workflows/cicd.yaml)
[![codecov](https://codecov.io/gh/ErikKalkoken/python-victorialogs-handler/graph/badge.svg?token=2pPb3lid2k)](https://codecov.io/gh/ErikKalkoken/python-victorialogs-handler)
[![license](https://img.shields.io/badge/license-MIT-green)](https://gitlab.com/ErikKalkoken/python-victorialogs-handler/-/blob/master/LICENSE)

STATUS: In development

## Description

This package provides a Python log handler for Victoria Logs. The log handler is designed to work with Python's default logging module and will send all log events to a configured Victoria Logs server for log ingestion.

## Key Features

- Asynchronous design: Log events are queued and then processed in a separate thread so that the performance impact on the main program remains minimal.
- Request batching: Log events are processed without delay. Multiple log events will be sent in a single request as batch to minimize the number of requests to the VictoriaLogs server.
- Supports extras: Extra fields are supported. This includes non-standard types like sets and datetime objects. Fields that can not be serialized to JSON (e.g. functions) will be converted into their string representation
- Supports dict config: The handler supports dict configuration, e.g. for a Django server
