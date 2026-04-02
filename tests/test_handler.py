import datetime as dt
import json
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

    def test_should_should_validate_request_timeout(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(request_timeout=0)

        with self.assertRaises(ValueError):
            VictoriaLogsHandler(request_timeout=-1)

    def test_should_should_validate_url(self):
        with self.assertRaises(ValueError):
            VictoriaLogsHandler(url="123")


@patch(MODULE_PATH + ".request.post_ndjson")
class TestVictoriaLogsHandler_SingleLog(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler()
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = threading.Event()
        self.handler.start()

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def post_mock(self, *args, **kwargs):
        self.ready_event.set()
        return ""

    def test_should_send_a_log(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock

        # when
        self.logger.info("Alpha")

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = json.loads(m.call_args.kwargs["data"])
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
        got = json.loads(m.call_args.kwargs["data"])
        self.assertEqual(got["message"], "Alpha")
        self.assertEqual(got["planet"], "Jupiter")
        self.assertEqual(got["deadline"], "2026-01-11T12:15:42.000099+00:00")

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
        got = json.loads(m.call_args.kwargs["data"])
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
        self.handler = VictoriaLogsHandler(batch_size=3)
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = threading.Event()
        self.counter = 0
        self.counter_target = 0
        self.lock = threading.Lock()

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def post_mock(self, *args, **kwargs):
        with self.lock:
            self.counter += 1
            if self.counter >= self.counter_target:
                self.ready_event.set()
        return ""

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
        got: str = m.call_args.kwargs["data"]
        lines = got.splitlines()
        self.assertEqual(len(lines), 2)

        e1 = json.loads(lines[0])
        self.assertEqual(e1["message"], "Alpha")

        e2 = json.loads(lines[1])
        self.assertEqual(e2["message"], "Bravo")
        self.assertEqual(e2["message"], "Bravo")

    def test_handler_should_abide_by_batch_size_limit(self, m: MagicMock):
        # given
        m.side_effect = self.post_mock
        self.counter_target = 2

        # when
        self.logger.info("l1")
        self.logger.info("l2")
        self.logger.info("l3")
        self.logger.info("l4")
        self.handler.start()

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 2)

        # first request
        got: str = m.call_args_list[0].kwargs["data"]
        lines = got.splitlines()
        self.assertEqual(len(lines), 3)

        # second request
        got: str = m.call_args_list[1].kwargs["data"]
        lines = got.splitlines()
        self.assertEqual(len(lines), 1)
