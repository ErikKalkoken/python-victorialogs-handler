import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.client import HTTPMessage
from io import BytesIO
from typing import NamedTuple
from unittest.mock import MagicMock, patch

from vlogs_handler import request

MODULE_PATH = "vlogs_handler.request"


def make_http_error(status=404, message="Not Found", url="https://example.com"):
    headers = HTTPMessage()
    fp = BytesIO(b"Error body content")
    return urllib.error.HTTPError(
        url=url, code=status, msg=message, hdrs=headers, fp=fp
    )


def make_urlopen_fake(exception=None):
    @contextmanager
    def urlopen_fake(req: urllib.request.Request, timeout):
        if not isinstance(req, urllib.request.Request):
            raise ValueError("req must be a Request")
        if exception:
            raise exception
        yield MagicMock()

    return urlopen_fake


class TestPostNdjson(unittest.TestCase):
    def setUp(self) -> None:
        self.url = "https://api.example.com/logs"
        self.data = [{"event": "test"}, {"event": "more_data"}]

    def test_should_submit_successfully(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect = make_urlopen_fake()
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertTrue(got)

    def test_should_handle_http_exception(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect = make_urlopen_fake(exception=make_http_error())
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertFalse(got)

    def test_should_handle_url_exception(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect = make_urlopen_fake(
                exception=urllib.error.URLError("Network is unreachable")
            )
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertFalse(got)

    def test_should_handle_general_exception(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect = make_urlopen_fake(exception=RuntimeError)
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertFalse(got)


class TestIsURL(unittest.TestCase):
    def test_all(self):
        class Case(NamedTuple):
            url: str
            want: bool

        cases = [
            Case("http://www.example.com", True),
            Case("http://localhost:9428", True),
            Case("http://0.0.0.0:9428", True),
            Case("www.example.com", False),
        ]

        for tc in cases:
            with self.subTest(url=tc.url):
                self.assertIs(request.is_url(tc.url), tc.want)
                self.assertIs(request.is_url(tc.url), tc.want)
