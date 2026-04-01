import datetime as dt
import json
import logging
import unittest
from threading import Event

import requests_mock

from vlogs_handler import VictoriaLogsHandler
from vlogs_handler.handler import JSONEncoderPlus


@requests_mock.Mocker()
class TestVictoriaLogsHandler(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(url="http://localhost:30123")
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = Event()

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def text_callback(self, request, context):
        self.ready_event.set()
        return ""

    def test_handler_should_send_normal_log(self, m: requests_mock.Mocker):
        # given
        m.register_uri(
            "POST",
            "http://localhost:30123/insert/jsonline",
            status_code=200,
            text=self.text_callback,
        )

        # when
        self.logger.info("Alpha")

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.last_request.json()  # type: ignore
        self.assertEqual(got["stream"], "test_logger")
        self.assertEqual(got["level"], "INFO")
        self.assertEqual(got["logger"], "test_logger")
        self.assertEqual(got["message"], "Alpha")

    def test_handler_should_send_log_with_extras(self, m: requests_mock.Mocker):
        # given
        m.register_uri(
            "POST",
            "http://localhost:30123/insert/jsonline",
            status_code=200,
            text=self.text_callback,
        )
        my_date = dt.datetime(2026, 1, 11, 12, 15, 42, 99, tzinfo=dt.timezone.utc)

        # when
        self.logger.info("Alpha", extra={"planet": "Jupiter", "deadline": my_date})

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.last_request.json()  # type: ignore
        self.assertEqual(got["message"], "Alpha")
        self.assertEqual(got["planet"], "Jupiter")
        self.assertEqual(got["deadline"], "2026-01-11T12:15:42.000099+00:00")

    def test_handler_should_send_exception_log(self, m: requests_mock.Mocker):
        # given
        m.register_uri(
            "POST",
            "http://localhost:30123/insert/jsonline",
            status_code=200,
            text=self.text_callback,
        )

        # when
        try:
            _ = 1 / 0
        except ZeroDivisionError:
            self.logger.exception("Bravo")

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        got = m.last_request.json()  # type: ignore
        self.assertEqual(got["stream"], "test_logger")
        self.assertEqual(got["level"], "ERROR")
        self.assertEqual(got["logger"], "test_logger")
        self.assertEqual(got["message"], "Bravo")
        self.assertIn("ZeroDivisionError", got["exception"])


@requests_mock.Mocker()
class TestVictoriaLogsHandler_MultipleLogs(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(
            url="http://localhost:30123", suspend_worker_start=True
        )
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)
        self.ready_event = Event()

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def text_callback(self, request, context):
        self.ready_event.set()
        return ""

    def test_handler_sends_log(self, m: requests_mock.Mocker):
        # given
        m.register_uri(
            "POST",
            "http://localhost:30123/insert/jsonline",
            status_code=200,
            text=self.text_callback,
        )

        # when
        self.logger.info("Alpha")
        self.logger.info("Bravo")
        self.handler.start()

        # then
        called_in_time = self.ready_event.wait(timeout=2.0)
        self.assertTrue(called_in_time)

        self.assertEqual(m.call_count, 1)
        data = m.last_request.text  # type: ignore
        lines = data.splitlines()
        self.assertEqual(len(lines), 2)

        e1 = json.loads(lines[0])
        self.assertEqual(e1["message"], "Alpha")

        e2 = json.loads(lines[1])
        self.assertEqual(e2["message"], "Bravo")
        self.assertEqual(e2["message"], "Bravo")


class TestJSONEncoderPlus(unittest.TestCase):
    def test_should_encode(self):
        # given
        def my_func():
            pass

        my_date = dt.datetime(2026, 1, 11, 12, 15, 42, 99, tzinfo=dt.timezone.utc)
        data = {
            "class": JSONEncoderPlus,
            "date": my_date.date(),
            "datetime": my_date,
            "float": 1.23,
            "func": my_func,
            "integer": 1,
            "set": {1, 2, 3},
            "text": "Alpha",
        }

        # when
        got = json.loads(json.dumps(data, cls=JSONEncoderPlus))

        # then
        self.assertEqual(
            got["class"], "<class 'vlogs_handler.handler.JSONEncoderPlus'>"
        )
        self.assertEqual(got["date"], "2026-01-11")
        self.assertEqual(got["datetime"], "2026-01-11T12:15:42.000099+00:00")
        self.assertEqual(got["float"], 1.23)
        self.assertIn("my_func at", got["func"])
        self.assertEqual(got["integer"], 1)
        self.assertEqual(got["set"], [1, 2, 3])
        self.assertEqual(got["text"], "Alpha")
