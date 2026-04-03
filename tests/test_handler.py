import datetime as dt
import logging
import threading
import unittest
from unittest.mock import MagicMock, patch

from vlogs_handler import VictoriaLogsHandler

MODULE_PATH = "vlogs_handler.handler"


class TestVictoriaLogsHandler_Validations(unittest.TestCase):
    def test_should_validate_batch_size(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(batch_size=0)

        with self.assertRaises(ValueError):
            VictoriaLogsHandler(batch_size=-1)

    def test_should_should_validate_flush_interval(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(flush_interval=-1)

    def test_should_should_validate_request_timeout(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(request_timeout=0)

        with self.assertRaises(ValueError):
            VictoriaLogsHandler(request_timeout=-1)

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
        self.logger = logging.getLogger("test_logger")
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
        self.assertEqual(got["logger"], "test_logger")
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
        self.assertEqual(got["logger"], "test_logger")
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

        got = m.call_args.kwargs["data"]
        self.assertEqual(len(got), 4)

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
