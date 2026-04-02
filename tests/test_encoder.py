import datetime as dt
import json
import unittest

from vlogs_handler import encoder


class TestJSONEncoderPlus(unittest.TestCase):
    def test_should_encode(self):
        # given
        def my_func():
            pass

        my_date = dt.datetime(2026, 1, 11, 12, 15, 42, 99, tzinfo=dt.timezone.utc)
        data = {
            "class": encoder.JSON,
            "date": my_date.date(),
            "datetime": my_date,
            "float": 1.23,
            "func": my_func,
            "integer": 1,
            "set": {1, 2, 3},
            "text": "Alpha",
        }

        # when
        got = json.loads(json.dumps(data, cls=encoder.JSON))

        # then
        self.assertEqual(got["class"], "<class 'vlogs_handler.encoder.JSON'>")
        self.assertEqual(got["date"], "2026-01-11")
        self.assertEqual(got["datetime"], "2026-01-11T12:15:42.000099+00:00")
        self.assertEqual(got["float"], 1.23)
        self.assertIn("my_func at", got["func"])
        self.assertEqual(got["integer"], 1)
        self.assertEqual(got["set"], [1, 2, 3])
        self.assertEqual(got["text"], "Alpha")
        self.assertEqual(got["text"], "Alpha")
