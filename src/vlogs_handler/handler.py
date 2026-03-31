import io
import json
import logging
import queue
import sys
import threading
import traceback
from typing import Any, Dict

import requests


class VictoriaLogsHandler(logging.Handler):
    def __init__(self, url: str):
        super().__init__()
        self.url = url
        self._queue = queue.Queue(-1)

        # Start background worker
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self.format_log_entry(record)
            self._queue.put(log_entry)
        except Exception as ex:
            _print_exception("emitting record", ex)
            self.handleError(record)

    def format_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        if record.name == "__main__":
            stream = "(undefined)"
        else:
            s = record.name.split(".")
            if len(s) > 1:
                stream = s[0]
            else:
                stream = record.name
        entry = {
            "stream": stream,
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
            entry["exception"] = _format_exception(record.exc_info)
        return entry

    def _worker(self):
        while True:
            record = self._queue.get()
            self._send(record)

    def _send(self, entry: Dict[str, Any]):
        try:
            data = json.dumps(entry)
        except Exception as ex:
            _print_exception("convert entry to JSON", ex, entry=entry)
            return

        try:
            response = requests.post(
                f"{self.url}/insert/jsonline?_stream_fields=stream&_time_field=timestamp&_msg_field=message",
                data=data,
                headers={"Content-Type": "application/stream+json"},
                timeout=5,
            )
            response.raise_for_status()
        except Exception as ex:
            _print_exception("send entry", ex)


def _print_exception(context: str, ex: Exception, **extras):
    print(
        f"ERROR: VictoriaLogsHandler: {context}: {ex} {extras}",
        file=sys.stderr,
    )


def _format_exception(ei):
    """
    Format and return the specified exception information as a string.

    This default implementation just uses
    traceback.print_exception()

    Source: logging.Formatter.formatException()
    """
    sio = io.StringIO()
    tb = ei[2]
    traceback.print_exception(ei[0], ei[1], tb, None, sio)
    s = sio.getvalue()
    sio.close()
    if s[-1:] == "\n":
        s = s[:-1]
    return s


# class HTTPJsonHandler(logging.Handler):
#     def __init__(self, url):
#         super().__init__()
#         self.url = url

#     def emit(self, record):
#         log_entry = self.format(record)

#         try:
#             response = requests.post(
#                 f"{self.url}/insert/jsonline?_stream_fields=stream&_time_field=timestamp&_msg_field=message",
#                 data=log_entry,
#                 headers={"Content-Type": "application/stream+json"},
#                 timeout=5,
#             )
#             response.raise_for_status()
#         except Exception:
#             print(
#                 f"ERROR: HTTPJsonHandler failed to send record to {self.url}: "
#                 f"{response.status_code} {response.text}",
#                 file=sys.stderr,
#             )
#             # Avoid crashing the app if the logging endpoint is down
#             self.handleError(record)


# class JsonFormatter(logging.Formatter):
#     def format(self, record):
#         stream = ""
#         s = record.name.split(".")
#         if len(s) > 1:
#             stream = s[0]
#         else:
#             stream = record.name
#         log_data = {
#             "timestamp": record.created,
#             "level": record.levelname,
#             "logger": record.name,
#             "stream": stream,
#             "message": record.getMessage(),
#         }
#         if record.exc_info:
#             log_data["exception"] = self.formatException(record.exc_info)

#         return json.dumps(log_data)
