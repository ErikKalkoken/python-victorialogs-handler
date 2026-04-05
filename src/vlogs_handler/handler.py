"""A module that provides the implementation of the vlogs logging handler."""

import io
import logging
import queue
import threading
import traceback
import urllib.parse
from typing import Callable, List, Optional, Tuple

import orjson

from . import request

logger = logging.getLogger(__name__)

_STANDARD_ATTRS: frozenset[str] = frozenset(
    {
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
)


class VictoriaLogsHandler(logging.Handler):
    """A handler class which dispatches logging records to a VictoriaLogs server.

    Args:
        batch_size: New logs are submitted immediately once this threshold is reached.
        flush_interval: New logs are submitted every x seconds.
        buffer_size: Maximum number of logs the buffer can hold.
            If buffer_size <= 0, the size is unlimited (not recommended).
            When the buffer is full any new logs will be discarded.
            100 000 logs consume approx. 80-100 MB of RAM.
        chunk_size: Maximum number of logs send per request to the log server.
        record_to_stream: A function that returns the value for the `stream`field
            for a log record. The default will return the name of the top package.
        request_timeout: Timeout when sending a request to the vlogs server in seconds.
        start_worker: Whether to start the worker at initialization.
            Alternatively, the worker can be started later by calling `start()`.
        shutdown_timeout: Timeout when waiting for the worker to shut down.
        url: URL of the vlogs server, e.g. `"http://localhost:9428"`
    """

    def __init__(
        self,
        batch_size: int = 125,
        buffer_size: int = 100_000,
        chunk_size: int = 1_000,
        flush_interval: float = 5.0,
        record_to_stream: Optional[Callable[[logging.LogRecord], str]] = None,
        request_timeout: float = 3.0,
        shutdown_timeout: float = 2.0,
        start_worker: bool = True,
        url: str = "http://localhost:9428",
    ):
        """Initializes the instance."""

        super().__init__()

        if batch_size < 1:
            raise ValueError(f"batch_size must be >= 1: {batch_size}")

        if chunk_size < 1:
            raise ValueError(f"chunk_size must be >= 1: {chunk_size}")

        if flush_interval < 0:
            raise ValueError(f"flush_interval must be >= 0: {flush_interval}")

        if record_to_stream and not callable(record_to_stream):
            raise ValueError("record_to_stream must be a callable")

        if request_timeout <= 0:
            raise ValueError(f"request_timeout must be > 0: {request_timeout}")

        if shutdown_timeout <= 0:
            raise ValueError(f"shutdown_timeout must be > 0: {shutdown_timeout}")

        if not request.is_url(url):
            raise ValueError(f"url is not valid: {url}")

        name = __package__
        if not name:
            raise RuntimeError("must run as module")

        self.addFilter(_create_filter(name))

        self._batch_size = int(batch_size)
        self._buffer = queue.Queue(int(buffer_size))
        self._chunk_size = int(chunk_size)
        self._flush_interval = float(flush_interval)
        self._record_to_stream = record_to_stream or _top_package_name
        self._request_timeout = float(request_timeout)
        self._shutdown_timeout = float(shutdown_timeout)
        self._vlogs_url = (
            urllib.parse.urljoin(url, "/insert/jsonline")
            + "?"
            + urllib.parse.urlencode(
                {
                    "_stream_fields": "stream",
                    "_time_field": "timestamp",
                    "_msg_field": "message",
                }
            )
        )
        self._worker_thread = threading.Thread(target=self._worker, daemon=True)

        self._lock = threading.Lock()
        self._worker_started = False
        self._worker_run = threading.Event()
        self._worker_shutdown = threading.Event()
        self._added_count = 0

        if start_worker:
            self.start()

    def close(self):
        """Cleanup resources and flush the buffer."""
        with self._lock:
            if self._worker_shutdown.is_set():
                return  # run shutdown once only

            self._worker_shutdown.set()

        if self._worker_started:
            self._worker_run.set()
            self._worker_thread.join(timeout=self._flush_interval)

        self.flush()
        if (n := self._buffer.qsize()) > 0:
            logger.error("Discarded %d logs during shutdown.", n)

        super().close()

    def emit(self, record: logging.LogRecord) -> None:
        """@private"""
        try:
            log = _serialize_log_to_json(record, self._record_to_stream)
            self._buffer.put_nowait(log)

        except Exception:
            self.handleError(record)
            return

        with self._lock:
            self._added_count += 1
            if self._added_count > self._batch_size:
                self._added_count = 0
                self._worker_run.set()

    def start(self):
        """Start the worker. Is a no-op when the worker is already running."""
        with self._lock:
            if self._worker_started:
                return

            self._worker_started = True
            self._worker_thread.start()

        logger.debug("Worker started")

    def _worker(self):
        while not self._worker_shutdown.is_set():
            self._worker_run.wait(timeout=self._flush_interval)
            self._worker_run.clear()
            self.flush()

        logger.debug("Worker stopped")

    def flush(self):
        """Flush the buffer and send all logs to the log server."""
        failed: List[bytes] = []
        done = False

        while not done:
            logs: List[bytes] = []
            while len(logs) < self._chunk_size:
                try:
                    logs.append(self._buffer.get_nowait())
                except queue.Empty:
                    done = True
                    break

            if logs:
                ok = request.post_ndjson(
                    url=self._vlogs_url, objs=logs, timeout=self._request_timeout
                )
                if not ok:
                    failed += logs
                    logger.warning("Failed transmitting %d logs to server", len(logs))
                else:
                    logger.debug("Completed transmitting %s logs to server", len(logs))

        if not failed:
            return

        n = 0
        for log in failed:
            try:
                self._buffer.put_nowait(log)
                n += 1
            except queue.Full:
                logger.error(
                    "Discarded %s logs after failed send because buffer is full",
                    len(failed) - n,
                )
                break

        logger.debug("Saved %d logs to buffer after failed send", n)


def _serialize_log_to_json(
    record: logging.LogRecord, record_to_stream: Callable[[logging.LogRecord], str]
) -> bytes:
    """Serialize a log record into a JSON object and return it."""
    obj = {
        "stream": record_to_stream(record),
        "timestamp": record.created,
        "level": record.levelname,
        "logger": record.name,
        "module": record.module,
        "function": record.funcName,
        "line_number": record.lineno,
        "message": record.getMessage(),
        "process_name": record.processName,
        "process": record.process,
        "thread_name": record.threadName,
        "thread": record.thread,
    }
    if record.exc_info:
        obj["exception_name"], obj["exception"] = _format_exception(record.exc_info)

    for k, v in record.__dict__.items():
        if k not in _STANDARD_ATTRS:
            obj[k] = v

    log = orjson.dumps(obj, default=str)
    return log


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


def _top_package_name(record: logging.LogRecord) -> str:
    """Return the top package name of a log."""
    if record.name == "__main__":
        return "(undefined)"

    s = record.name.split(".")
    if len(s) > 1:
        return s[0]

    return record.name
