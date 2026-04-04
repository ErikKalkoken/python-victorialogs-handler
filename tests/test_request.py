import unittest
import urllib.error
import urllib.request
from contextlib import contextmanager
from http.client import HTTPMessage
from io import BytesIO
from typing import List, NamedTuple
from unittest.mock import MagicMock, patch

from vlogs_handler import request

MODULE_PATH = "vlogs_handler.request"


def make_http_error(status=404, message="Not Found", url="https://example.com"):
    """Create a HTTPError."""
    headers = HTTPMessage()
    fp = BytesIO(b"Error body content")
    return urllib.error.HTTPError(
        url=url, code=status, msg=message, hdrs=headers, fp=fp
    )


def make_urlopen_fake(exception=None):
    """Create and return a fake for urlopen and the list of recorded requests.

    The requests list is updated which every new request.
    """
    requests_history: List[urllib.request.Request] = []

    @contextmanager
    def urlopen_fake(req: urllib.request.Request, timeout):
        if not isinstance(req, urllib.request.Request):
            raise ValueError("req must be a Request")

        requests_history.append(req)

        if exception:
            raise exception
        yield MagicMock()

    return urlopen_fake, requests_history


class TestPostNdjson(unittest.TestCase):
    def setUp(self) -> None:
        self.url = "https://api.example.com/logs"
        self.data = [{"event": "test"}, {"event": "more_data"}]

    def test_should_submit_successfully(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect, requests_history = make_urlopen_fake()
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertTrue(got)
        self.assertEqual(len(requests_history), 1)
        req = requests_history[0]
        self.assertEqual(req.full_url, self.url)
        self.assertEqual(req.get_header("Content-type"), "application/x-ndjson")
        self.assertEqual(req.data, b'{"event":"test"}\n{"event":"more_data"}\n')

    def test_should_handle_http_exception(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect, requests_history = make_urlopen_fake(
                exception=make_http_error()
            )
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertFalse(got)
        self.assertEqual(len(requests_history), 1)

    def test_should_handle_url_exception(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect, requests_history = make_urlopen_fake(
                exception=urllib.error.URLError("Network is unreachable")
            )
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertFalse(got)
        self.assertEqual(len(requests_history), 1)

    def test_should_handle_general_exception(self):
        # when
        with patch(MODULE_PATH + ".urllib.request.urlopen") as m:
            m.side_effect, requests_history = make_urlopen_fake(exception=RuntimeError)
            got = request.post_ndjson(url=self.url, data=self.data)

        # then
        self.assertFalse(got)
        self.assertEqual(len(requests_history), 1)


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
