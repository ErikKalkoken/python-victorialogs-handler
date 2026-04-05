# Technical overview

This section gives a technical overview of how the vlogs handler works.

## Process Flow

The high-level process flow of the vlogs handler is as follows:

1. When a a log event is received, it is converted into JSON and stored
    in the buffer
1. At the tick of an interval (e.g. 5 seconds) or when a threshold is reached
    (e.g. 125 logs) a background worker starts the process of submitting logs
    from the buffer to the log server
1. Logs are combined into chunks (e.g. 1.000 logs per request)
    and then submitted to the log server using vlog's the JSON Stream API

## Failure behavior

The failure behavior of the handler in key scenarios is as follows:

- In case the submission to the log server fails
    (e.g. the server is temporarily down) the logs will be stored
    in the buffer for later retry
- If the buffer is full, new log events will be discarded
    and raise a exceptions (depending on logging configuration)
- The handler will make a final attempt to submit remaining logs during shutdown.
If that fails those logs will written to stderr.

## LogRecord fields

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

## VictoriaLogs special fields

VictoriaLogs handles three fields in a special way:

- `_msg`: The logged message. This is a mandatory field and is mapped to `message`.
- `_time`: The timestamp of the log event. This field and is mapped to `timestamp`.
- `_stream`: The source of a log event, which is used to group and filter logs. This field is mapped to `stream`.

For more information please also see [VictoriaLogs Data model](https://docs.victoriametrics.com/victorialogs/keyconcepts/#data-model).
