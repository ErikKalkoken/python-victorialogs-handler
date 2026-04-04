import datetime as dt
import logging
import queue
import threading
import unittest
from unittest.mock import MagicMock, patch

from vlogs_handler import VictoriaLogsHandler, handler

MODULE_PATH = "vlogs_handler.handler"


class TestVictoriaLogsHandler_Init(unittest.TestCase):
    def test_should_init_with_defaults(self):
        handler = VictoriaLogsHandler()
        self.assertEqual(handler._batch_size, 125)
        self.assertEqual(handler._chunk_size, 1000)
        self.assertEqual(handler._flush_interval, 5.0)
        self.assertEqual(handler._request_timeout, 3.0)
        self.assertEqual(handler._shutdown_timeout, 2.0)
        self.assertEqual(
            handler._vlogs_url,
            "http://localhost:9428/insert/jsonline"
            "?_stream_fields=stream&_time_field=timestamp&_msg_field=message",
        )

    def test_should_validate_batch_size(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(batch_size=0)

        with self.assertRaises(ValueError):
            VictoriaLogsHandler(batch_size=-1)

    def test_should_validate_bulk_size(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(chunk_size=0)

        with self.assertRaises(ValueError):
            VictoriaLogsHandler(chunk_size=-1)

    def test_should_should_validate_flush_interval(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(flush_interval=-1)

    def test_should_should_validate_request_timeout(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(request_timeout=0)

        with self.assertRaises(ValueError):
            VictoriaLogsHandler(request_timeout=-1)

    def test_should_should_validate_record_to_stream(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(record_to_stream=1)  # type: ignore

    def test_should_should_validate_shutdown_timeout(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(shutdown_timeout=0)
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(shutdown_timeout=-1)

    def test_should_should_validate_url(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(url="123")


@patch(MODULE_PATH + ".request.post_ndjson")
class TestVictoriaLogsHandler_SingleLog(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(flush_interval=0.01)
        self.logger = logging.getLogger("test_logger.module_1.module_2")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = threading.Event()

    def tearDown(self):
        self.handler.close()
        self.logger.removeHandler(self.handler)

    def post_mock(self, *args, **kwargs):
        self.ready_event.set()
        return True

    def test_should_send_a_log(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock

        # when
        self.logger.info("Alpha")

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.call_args.kwargs["data"][0]
        self.assertEqual(got["stream"], "test_logger")
        self.assertEqual(got["level"], "INFO")
        self.assertEqual(got["logger"], "test_logger.module_1.module_2")
        self.assertEqual(got["message"], "Alpha")
        self.assertNotIn("exception", got)

    def test_should_send_log_with_extras(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock
        my_date = dt.datetime(2026, 1, 11, 12, 15, 42, 99, tzinfo=dt.timezone.utc)

        # when
        self.logger.info("Alpha", extra={"planet": "Jupiter", "deadline": my_date})

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.call_args.kwargs["data"][0]
        self.assertEqual(got["message"], "Alpha")
        self.assertEqual(got["planet"], "Jupiter")
        self.assertEqual(got["deadline"], my_date)

    def test_should_send_exception_log(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock

        # when
        try:
            _ = 1 / 0
        except ZeroDivisionError:
            self.logger.exception("Bravo")

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.call_args.kwargs["data"][0]
        self.assertEqual(got["stream"], "test_logger")
        self.assertEqual(got["level"], "ERROR")
        self.assertEqual(got["logger"], "test_logger.module_1.module_2")
        self.assertEqual(got["message"], "Bravo")
        self.assertEqual("ZeroDivisionError", got["exception_name"])
        self.assertIn("ZeroDivisionError", got["exception"])

    def test_should_do_nothing_when_trying_to_start_again(self, _):
        self.handler.start()


@patch(MODULE_PATH + ".request.post_ndjson")
class TestVictoriaLogsHandler_MultipleLogs(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(
            batch_size=3, flush_interval=0.01, start_worker=False
        )
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = threading.Event()
        self.counter = 0
        self.counter_target = 0
        self.lock = threading.Lock()

    def tearDown(self):
        self.handler.close()
        self.logger.removeHandler(self.handler)

    def post_mock(self, *args, **kwargs):
        with self.lock:
            self.counter += 1
            if self.counter >= self.counter_target:
                self.ready_event.set()
        return True

    def test_handler_should_send_multiple_logs_in_single_request(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock
        self.counter_target = 1

        # when
        self.logger.info("Alpha")
        self.logger.info("Bravo")
        self.handler.start()

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.call_args.kwargs["data"]
        self.assertEqual(len(got), 2)

        self.assertEqual(got[0]["message"], "Alpha")
        self.assertEqual(got[1]["message"], "Bravo")


@patch(MODULE_PATH + ".request.post_ndjson")
class TestVictoriaLogsHandler_MultipleLogs_2(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(
            batch_size=3, flush_interval=5, start_worker=False
        )
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = threading.Event()
        self.counter = 0
        self.counter_target = 0
        self.lock = threading.Lock()

    def tearDown(self):
        self.handler.close()
        self.logger.removeHandler(self.handler)

    def post_mock(self, *args, **kwargs):
        with self.lock:
            self.counter += 1
            if self.counter >= self.counter_target:
                self.ready_event.set()
        return True

    def test_handler_should_send_immediately_when_batch_size_reached(
        self, m: MagicMock
    ):
        # given
        m.side_effect = self.post_mock
        self.counter_target = 1

        # when
        self.logger.info("l1")
        self.logger.info("l2")
        self.logger.info("l3")
        self.logger.info("l4")
        self.handler.start()

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)

        self.assertEqual(len(m.call_args.kwargs["data"]), 4)

    def test_handler_should_shutdown_gracefully(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock
        self.counter_target = 1
        self.logger.info("Alpha")

        # when
        self.handler.start()
        self.handler.close()

        # then
        self.assertEqual(m.call_count, 1)
        got = m.call_args.kwargs["data"]
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["message"], "Alpha")


@patch(MODULE_PATH + ".request.post_ndjson")
class TestVictoriaLogsHandler_Flush(unittest.TestCase):
    def test_should_empty_queue_when_send_successful(self, m: MagicMock):
        # given
        m.return_value = True
        handler = VictoriaLogsHandler(start_worker=False)
        add_to_queue(handler._buffer, make_items(3))
        # when
        handler.flush()
        # then
        self.assertEqual(handler._buffer.qsize(), 0)
        self.assertEqual(m.call_count, 1)

    def test_should_requeue_when_send_failed(self, m: MagicMock):
        # given
        m.return_value = False
        handler = VictoriaLogsHandler(start_worker=False)
        add_to_queue(handler._buffer, make_items(3))
        # when
        handler.flush()
        # then
        self.assertEqual(handler._buffer.qsize(), 3)
        self.assertEqual(m.call_count, 1)

    def test_should_do_nothing_when_queue_empty(self, m: MagicMock):
        # given
        m.return_value = True
        handler = VictoriaLogsHandler(start_worker=False)
        # when
        handler.flush()
        # then
        self.assertEqual(m.call_count, 0)

    def test_should_send_logs_in_chunks(self, m: MagicMock):
        # given
        m.return_value = True
        handler = VictoriaLogsHandler(chunk_size=3, start_worker=False)
        add_to_queue(handler._buffer, make_items(4))
        # when
        handler.flush()
        # then
        self.assertEqual(handler._buffer.qsize(), 0)
        self.assertEqual(m.call_count, 2)
        self.assertEqual(len(m.call_args_list[0].kwargs["data"]), 3)
        self.assertEqual(len(m.call_args_list[1].kwargs["data"]), 1)


def add_to_queue(queue: queue.Queue, items):
    for it in items:
        queue.put_nowait(it)


def make_items(n: int) -> list:
    objs = []
    for i in range(1, n + 1):
        objs.append({"name": f"item#{i}"})
    return objs


class TestTopPackageName(unittest.TestCase):
    def setUp(self):
        self.mock_record: logging.LogRecord = MagicMock(spec=logging.LogRecord)

    def test_main_module_returns_undefined(self):
        self.mock_record.name = "__main__"
        result = handler._top_package_name(self.mock_record)
        self.assertEqual(result, "(undefined)")

    def test_nested_module_returns_root(self):
        self.mock_record.name = "my_app.services.auth"
        result = handler._top_package_name(self.mock_record)
        self.assertEqual(result, "my_app")

    def test_single_module_returns_name(self):
        self.mock_record.name = "database"
        result = handler._top_package_name(self.mock_record)
        self.assertEqual(result, "database")

    def test_empty_string_name(self):
        self.mock_record.name = ""
        result = handler._top_package_name(self.mock_record)
        self.assertEqual(result, "")
        self.assertEqual(result, "")
        self.assertEqual(result, "")
