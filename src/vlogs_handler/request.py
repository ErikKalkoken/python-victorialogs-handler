"""Module request provides the functionality to send HTTP requests."""

import io
import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, List, Optional

from . import encoder

logger = logging.getLogger(__name__)


def is_url(url: str) -> bool:
    """Report whether a string represents a valid URL."""
    try:
        result = urllib.parse.urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def post_ndjson(*, url: str, data: List[Any], timeout: Optional[float] = None) -> bool:
    """Send a POST request with the ndjson protocol
    and report whether it was successful.

    Args:
        url: request URL
        data: list of objects to send
        timeout: request timeout in seconds.
            Settings it to None will disable the timeout.
    """

    with io.StringIO() as buffer:
        for obj in data:
            try:
                json.dump(obj, buffer, cls=encoder.JSON)
                buffer.write("\n")
            except Exception:
                logger.exception("convert obj to JSON. Discarded", extra={"entry": obj})
                continue

        data_bytes = buffer.getvalue().encode("utf-8")

    req = urllib.request.Request(url, data=data_bytes, method="POST")
    req.add_header("Content-Type", "application/x-ndjson")

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            logger.debug("Submitted: %d %s", resp.status, resp.reason)
            return True

    except urllib.error.HTTPError as ex:
        body = ex.read(4096).decode("utf-8")
        logger.exception(
            "HTTP Error: %s",
            ex.reason,
            extra={
                "url": ex.url,
                "code": ex.code,
                "reason": ex.reason,
                "body": body,
            },
        )

    except urllib.error.URLError as ex:
        logger.exception(
            "URL Error: %s",
            ex.reason,
            extra={"url": url, "reason": ex.reason},
        )

    except Exception:
        logger.exception("general exception", extra={"url": url})

    return False
