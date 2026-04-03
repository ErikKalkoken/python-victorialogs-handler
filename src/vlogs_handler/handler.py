"""Module handler provides the implementation of the vlogs handler.

- The handler collects log events and sends them to the VictoriaLogs server
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
    """VictoriaLogsHandler dispatches log events to a VictoriaLogs server.

    Args:
        batch_size: New logs are submitted immediately once a threshold is reached.
        flush_interval: New logs are submitted every x seconds.
        queue_size: Maximum number of queued logs.
            If queue_size <= 0, the queue size is infinite.
            When the queue is full additional logs will be discarded.
            100 000 log entries consume roughly 100 MB of RAM.
        request_timeout: Timeout when sending a request to the vlogs server in seconds.
        start_worker: Whether to start the worker at initialization.
            Alternatively, the worker can be started later by calling `start()`.
        shutdown_timeout: Timeout when waiting for the worker to shut down.
        url: URL of the vlogs server, e.g. `"http://localhost:9428"`
    """

    def __init__(
        self,
        batch_size: int = 1_000,
        flush_interval: float = 5.0,
        queue_size: int = 100_000,
        request_timeout: float = 3.0,
        start_worker: bool = False,
        shutdown_timeout: float = 2.0,
        url: str = "http://localhost:9428",
    ):
        super().__init__()

        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1 {batch_size}")

        if flush_interval < 0:
            raise ValueError(f"flush_interval must be >= 0: {flush_interval}")

        if request_timeout <= 0:
            raise ValueError(f"request_timeout must be > 0: {request_timeout}")

        if shutdown_timeout <= 0:
            raise ValueError(f"shutdown_timeout must be > 0: {shutdown_timeout}")

        if not request.is_url(url):
            raise ValueError(f"url is not valid: {url}")

        name = __package__
        if not name:
            raise RuntimeError("Must run as module")

        self.addFilter(_create_filter(name))

        self._batch_size = int(batch_size)
        self._flush_interval = float(flush_interval)
        self._queue = queue.Queue(int(queue_size))
        self._request_timeout = float(request_timeout)
        self._shutdown_timeout = float(shutdown_timeout)
        self._url = str(url)

        # Start background worker
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)
        self._worker_started = False
        self._worker_lock = threading.Lock()
        self._worker_run = threading.Event()
        self._worker_shutdown = threading.Event()
        if start_worker:
            self.start()

    def close(self):
        """Cleanup resources and flush the queue."""
        with self._worker_lock:
            if self._worker_shutdown.is_set():
                return  # run shutdown once only

            self._worker_shutdown.set()

        self._worker_run.set()
        self._worker_thread.join(timeout=self._flush_interval)
        self.flush()
        super().close()

    def emit(self, record: logging.LogRecord) -> None:
        try:
            log_entry = self._format_log_record(record)
            self._queue.put_nowait(log_entry)
        except queue.Full:
            logger.error("queue full. Discarding new log.")
            return
        except Exception:
            logger.exception("emitting record")
            self.handleError(record)
            return

        if self._queue.qsize() > self._batch_size:
            self._worker_run.set()

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

    def start(self):
        """Start the worker. Do nothing when the worker is already running."""
        with self._worker_lock:
            if self._worker_started:
                return

            self._worker_started = True
            self._worker_thread.start()

        logger.debug("worker started")

    def _worker(self):
        while not self._worker_shutdown.is_set():
            self._worker_run.wait(timeout=self._flush_interval)
            self.flush()
            self._worker_run.clear()

        logger.debug("worker stopped")

    def flush(self):
        """Flush the queue and send all entries to the log server."""
        entries: List[Dict[str, Any]] = []
        while True:
            try:
                entries.append(self._queue.get_nowait())
            except queue.Empty:
                break

        if entries:
            self._send(entries)

    def _send(self, entries: List[Dict[str, Any]]):
        if not entries:
            return

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
        ok = request.post_ndjson(url=url, data=data, timeout=self._request_timeout)
        if ok:
            logger.debug("entries to log server sent: %d", len(entries))


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
