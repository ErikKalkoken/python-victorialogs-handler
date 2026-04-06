# Technical documentation

This section describes how the handler works and how it can be configured.

## Process Flow

The high-level process flow of the vlogs handler is as follows:

- When a log event is received, it is converted into JSON and stored in the buffer.
- When the logs are flushed, they are transferred to the log server by a background worker.
- The flushing of the buffer is triggered when the `flush_interval` expires (e.g. every 5 seconds) or when more then `batch_size` logs (e.g. 125) have been received.
- Logs are combined into chunks defined by `chunk_size` (e.g. 1.000 logs per request) and then submitted to the log server using the JSON Stream API.

## Failure behavior

The failure behavior of the handler in key scenarios is as follows:

- In case the submission to the log server fails (e.g. the server is temporarily down) the logs will be stored in the buffer for later retry.
- If the buffer is full, new log events will be discarded and raise a exceptions (depending on logging configuration).
- The handler will make a final attempt to submit remaining logs during shutdown. If that fails those logs will written to stderr.

## Configuration

This section describes how the handler and it's logger can be configured.

### Handler configuration

> [!TIP]
> The handler comes pre-configured with sensible defaults and often does not need to be configured.

The handler can be configured through keyword argument of the handler's constructor.
All arguments are optional and will be set to sensible defaults when not provided.

For example the size of the log buffer can be configured by setting `buffer_size`:

```python
vlogs_handler = VictoriaLogsHandler(buffer_size=100_000)
```

For a full description of all arguments please see `VictoriaLogsHandler`.

### Handler logging

The vlogs handler has it's own logger and which can be found under the name `vlogs_handler`.
It will log issues related to transferring logs to the vlogs server.

For example this will attach a console handler to the logger with warning level:

```python
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
vlogs_logger = logging.getLogger("vlogs_handler")
vlogs_handler.setLevel(logging.WARNING)
vlogs_logger.addHandler(console_handler)
```

> [!NOTE]
> A vlogs handler instance can not be attached to this logger, as this would create an infinite loop.

## Limitations

The handler was designed for a specific scenario:

- Transfer logs from a Django server to a VictoriaLogs instance running on the same server
- Our focus is on applications logs over server logs (i.e. logs from Django apps over logs from the Django server itself)
- The handler should be easy to install and use

Our design choices result in a few limitations:

- The buffer is kept in memory, which means that there is a risk that some logs are lost when the Django server itself has a failure. Because of that limitation we recommend not to rely on the vlogs handler alone, but to always use a log file as backup.
- The handler does not implement HTTP authentication or backoff and retry logic for HTTP requests. It is therefore currently not suitable to be used with a remote VictoriaLogs instance.

## Data Model

This section describes the structure of the data that is transferred to the vlogs server.

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
`stream` | This can be configured. By default this is name of the top-level Python package that emitted the log the event. | `my_package` | no
`timestamp` | Timestamp of the log event, represented as fractional UNIX epoch | `1775081468.4308655` | no

In addition any custom `extras' fields will be added as they are encountered.

### VictoriaLogs special fields

VictoriaLogs handles three fields in a special way:

- `_msg`: The logged message. This is a mandatory field and is mapped to `message`.
- `_time`: The timestamp of the log event. This field and is mapped to `timestamp`.
- `_stream`: The source of a log event, which is used to group and filter logs. This field is mapped to `stream`.

For more information please also see [VictoriaLogs Data model](https://docs.victoriametrics.com/victorialogs/keyconcepts/#data-model).
