import json
import logging
import time
import unittest

import requests_mock
from vlogs_handler import VictoriaLogsHandler


@requests_mock.Mocker()
class TestVictoriaLogsHandler(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(url="http://localhost:30123")
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_handler_sends_log(self, m: requests_mock.Mocker):
        # given
        m.register_uri(
            "POST",
            "http://localhost:30123/insert/jsonline",
            status_code=200,
        )

        # when
        self.logger.info("Alpha")
        time.sleep(0.5)

        # then
        self.assertEqual(m.call_count, 1)
        data = m.last_request.json()  # type: ignore
        self.assertEqual(data["stream"], "test_logger")
        self.assertEqual(data["level"], "INFO")
        self.assertEqual(data["logger"], "test_logger")
        self.assertEqual(data["message"], "Alpha")


@requests_mock.Mocker()
class TestVictoriaLogsHandler_MultipleLogs(unittest.TestCase):
    def setUp(self):
        self.handler = VictoriaLogsHandler(
            url="http://localhost:30123", suspend_worker_start=True
        )
        self.logger = logging.getLogger("test_logger")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self):
        self.logger.removeHandler(self.handler)

    def test_handler_sends_log(self, m: requests_mock.Mocker):
        # given
        m.register_uri(
            "POST",
            "http://localhost:30123/insert/jsonline",
            status_code=200,
        )

        # when
        self.logger.info("Alpha")
        self.logger.info("Bravo")
        self.handler.start()
        time.sleep(0.5)

        # then
        self.assertEqual(m.call_count, 1)
        data = m.last_request.text  # type: ignore
        lines = data.splitlines()
        self.assertEqual(len(lines), 2)

        e1 = json.loads(lines[0])
        self.assertEqual(e1["message"], "Alpha")

        e2 = json.loads(lines[1])
        self.assertEqual(e2["message"], "Bravo")
