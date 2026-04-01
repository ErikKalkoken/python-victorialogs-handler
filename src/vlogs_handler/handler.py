"""Module handler provides the implementation of the vlogs handler."""

import datetime as dt
import io
import json
import logging
import queue
import threading
import traceback
from typing import Any, Dict, List, Tuple

import requests

from . import log

_VLOGS_INSERT_PATH = "insert/jsonline"
_VLOGS_PARAMS = "_stream_fields=stream&_time_field=timestamp&_msg_field=message"


_STANDARD_ATTRS = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "message",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "taskName",
    "thread",
    "threadName",
}


class VictoriaLogsHandler(logging.Handler):
    """VictoriaLogsHandler dispatches log events to a Victoria Logs server."""

    def __init__(
        self,
        url: str,
        request_timeout: float = 5.0,
        suspend_worker_start: bool = False,
    ):
        super().__init__()
        self._url = url
        self._queue = queue.Queue(-1)
        self._request_timeout = request_timeout

        # Start background worker
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        if not suspend_worker_start:
            self.start()

    def start(self):
        """Starts the worker. This should only be called when the worker
        has not already been started at instantiation.

        Trying to start an already running worker will raise a RuntimeError exception.
        """
        self._worker_thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self.format_log_entry(record)
            self._queue.put(log_entry)
        except Exception as ex:
            log.exception("emitting record", ex)
            self.handleError(record)

    def format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        entry = {
            "stream": _calc_stream_from_record(record),
            "timestamp": record.created,
            "logger": record.name,
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line_number": record.lineno,
            "thread": record.thread,
            "thread_name": record.threadName,
            "process": record.process,
            "process_name": record.processName,
        }
        if record.exc_info:
            entry["exception_name"], entry["exception"] = _format_exception(
                record.exc_info
            )

        for k, v in record.__dict__.items():
            if k not in _STANDARD_ATTRS:
                entry[k] = v

        return entry

    def _worker(self):
        while True:
            entries: List[Dict[str, Any]] = []

            entries.append(self._queue.get())
            while True:
                try:
                    entries.append(self._queue.get_nowait())
                except queue.Empty:
                    break

            self._send(entries)

    def _send(self, entries: List[Dict[str, Any]]):
        lines = []
        for entry in entries:
            try:
                data = json.dumps(entry, cls=_JSONEncoderPlus)
                lines.append(data)
            except Exception as ex:
                log.exception("convert entry to JSON", ex, entry=entry)
                continue

        data = "\n".join(lines)
        try:
            response = requests.post(
                f"{self._url}/{_VLOGS_INSERT_PATH}?{_VLOGS_PARAMS}",
                data=data,
                headers={"Content-Type": "application/stream+json"},
                timeout=self._request_timeout,
            )
            response.raise_for_status()
        except Exception as ex:
            log.exception("send entry", ex)


def _format_exception(ei) -> Tuple[str, str]:
    """
    Format and return the name of the exception
    and specified exception information as strings.

    This default implementation just uses
    traceback.print_exception()

    Based on: logging.Formatter.formatException()
    """
    sio = io.StringIO()
    tb = ei[2]
    traceback.print_exception(ei[0], ei[1], tb, None, sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]

    name = ei[0].__name__ if ei[0] is not None else ""
    return name, s


def _calc_stream_from_record(record: logging.LogRecord):
    if record.name == "__main__":
        stream = "(undefined)"
    else:
        s = record.name.split(".")
        if len(s) > 1:
            stream = s[0]
        else:
            stream = record.name
    return stream


class _JSONEncoderPlus(json.JSONEncoder):
    """JSONEncoderPlus is an improved encoder that can convert dates and does not break.

    Instead of breaking it will return a string representation
    for unserializable fields.
    """

    def default(self, obj):
        if isinstance(obj, (dt.datetime, dt.date)):
            return obj.isoformat()

        if isinstance(obj, set):
            return list(obj)

        try:
            return super().default(obj)
        except TypeError:
            # If we can't serialize it, return None or a string representation
            return str(obj)
