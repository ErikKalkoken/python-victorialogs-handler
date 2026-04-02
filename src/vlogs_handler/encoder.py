"""Module encoder provides encoders for the vlogs handler."""

import datetime as dt
import json


class JSON(json.JSONEncoder):
    """JSON is an improved encoder that can convert dates and does not break.

    Instead of breaking it will return a string representation
    for unserializable fields.
    """

    def default(self, o):
        if isinstance(o, (dt.datetime, dt.date)):
            return o.isoformat()

        if isinstance(o, set):
            return list(o)

        try:
            return super().default(o)
        except TypeError:
            # If we can't serialize it, return None or a string representation
            return str(o)
