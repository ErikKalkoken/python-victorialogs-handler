"""Module request provides the functionality to send HTTP requests."""

import urllib.error
import urllib.request
from typing import Optional

from vlogs_handler import log


def post_ndjson(*, url: str, data: str, timeout: Optional[float] = None) -> bool:
    """Send a POST request with the ndjson protocol
    and report whether it was successful.
    """

    data_bytes = data.encode("utf-8")
    req = urllib.request.Request(url, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/x-ndjson")

    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return True

    except urllib.error.HTTPError as ex:
        body = ex.read(4096).decode("utf-8")
        log.error(
            "post_ndjson HTTP Error",
            url=ex.url,
            code=ex.code,
            reason=ex.reason,
            body=body,
        )

    except urllib.error.URLError as ex:
        log.error("post_ndjson URL Error", url=url, reason=ex.reason)

    except Exception as ex:
        log.exception("post_ndjson general exception", ex, url=url)

    return False
