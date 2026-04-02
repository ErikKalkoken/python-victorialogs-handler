"""Module handler provides the implementation of the vlogs handler.

- The handler collects log events and sends them to the Victoria Logs server
on a background thread.
- The handler uses the vlogs's JSON Stream API for data ingestion.
- Multiple logs are batched together into a single request using the ndjson protocol
    to minimize the number of requests.
- Log records are converted into JSON objects. The handler uses an extension
of Python's default json encoder to serialize additional types and improve robustness.
"""

import io
import json
import logging
import queue
import threading
import time
import traceback
from typing import Any, Dict, List, Tuple

from . import encoder, request

logger = logging.getLogger(__name__)

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
    """VictoriaLogsHandler dispatches log events to a Victoria Logs server.

    Args:
        batch_size: Upper limit for how many logs are combined into one request
            to the vlogs server.
        request_timeout: Timeout for sending a request to the vlogs server in seconds.
        start_worker: Whether to start the worker at initialization.
            Alternatively, the worker can be started later by calling `start()`.
        url: URL of the vlogs server, e.g. `"http://localhost:9428"`
        worker_timeout: time a worker will wait to potentially collect
            additional logs for each request
    """

    # TODO: add validation checks

    def __init__(
        self,
        batch_size: int = 50,
        request_timeout: float = 5.0,
        start_worker: bool = False,
        url: str = "http://localhost:9428",
        worker_timeout: float = 0.5,
    ):
        super().__init__()

        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1 {batch_size}")

        if request_timeout <= 0:
            raise ValueError(f"request_timeout must be > 0: {request_timeout}")

        if worker_timeout < 0:
            raise ValueError(f"worker_timeout must be >= 0: {worker_timeout}")

        if not request.is_url(url):
            raise ValueError(f"url is not valid: {url}")

        name = __package__
        if not name:
            raise RuntimeError("Must run as module")

        self.addFilter(_create_filter(name))

        self._batch_size = int(batch_size)
        self._queue = queue.Queue(-1)
        self._request_timeout = float(request_timeout)
        self._url = str(url)
        self._worker_timeout = float(worker_timeout)

        # Start background worker
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_started = False
        self._worker_lock = threading.Lock()
        if start_worker:
            self.start()

    def close(self):
        """Cleanup resources and flush the queue."""
        self._queue.put(None)  # "Poison pill" to tell worker to stop
        self._worker_thread.join(timeout=self._request_timeout + 1)
        self._worker_started = False
        super().close()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self._format_log_record(record)
            self._queue.put(log_entry)
        except Exception:
            logger.exception("emitting record")
            self.handleError(record)

    def start(self):
        """Start the worker. Do nothing when the worker is already running."""
        with self._worker_lock:
            if self._worker_started:
                return

            self._worker_started = True
            self._worker_thread.start()

    def _format_log_record(self, record: logging.LogRecord) -> Dict[str, Any]:
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
        entries: List[Dict[str, Any]] = []
        is_shutdown = False
        while not is_shutdown:
            entry = self._queue.get()
            if entry is None:
                break  # Shutdown signal

            entries = [entry]
            time.sleep(self._worker_timeout)  # wait to collect more logs for batch
            while len(entries) < self._batch_size:
                try:
                    entry = self._queue.get_nowait()
                except queue.Empty:
                    break

                if entry is None:
                    is_shutdown = True
                    break  # Shutdown signal

                entries.append(entry)

            self._send(entries)

    def _send(self, entries: List[Dict[str, Any]]):
        lines = []
        for entry in entries:
            try:
                data = json.dumps(entry, cls=encoder.JSON)
                lines.append(data)
            except Exception:
                logger.exception("convert entry to JSON", extra={"entry": entry})
                continue

        data = "\n".join(lines)
        url = f"{self._url}/{_VLOGS_INSERT_PATH}?{_VLOGS_PARAMS}"
        request.post_ndjson(url=url, data=data, timeout=self._request_timeout)


def _create_filter(name: str):
    def filter_logic(record: logging.LogRecord) -> bool:
        return not record.name.startswith(name)

    f = logging.Filter()
    f.filter = filter_logic
    return f


def _format_exception(ei) -> Tuple[str, str]:
    """Format and return the name of the exception
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
