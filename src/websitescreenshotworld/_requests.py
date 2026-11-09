"""Building each operation's request; shared by the sync and async clients."""

from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from typing import Any
from urllib.parse import quote

from ._config import ClientConfig, request_headers
from ._models import Capture
from ._transport import Request

_CAPTURES_PATH = "/instant-snap/v1/captures"


def capture(
    config: ClientConfig,
    *,
    url: str,
    response_type: str,
    options: Mapping[str, Any],
    idempotency_key: str | None,
    timeout: float | None,
    is_async: bool = False,
) -> Request:
    """A capture request. ``timeout`` is the client's wait; with ``is_async`` a ``timeout`` in
    ``options`` is the API's async option and is sent like any other."""
    api_key = config.require_instant_snap_key()
    # An option set to None counts as left out; False, 0 and "" are values and are sent.
    body = {name: value for name, value in options.items() if value is not None}
    body["url"] = url
    body["response_type"] = response_type
    if is_async:
        body["async"] = True
    # An async capture is answered at once (202, status queued), so it waits like any other call.
    default_timeout = config.timeout if is_async else config.capture_timeout
    return Request(
        method="POST",
        url=config.instant_snap_base_url + _CAPTURES_PATH,
        headers=request_headers(
            api_key=api_key,
            accept="*/*" if response_type == "by_format" else "application/json",
            has_body=True,
            idempotency_key=idempotency_key or str(uuid.uuid4()),
        ),
        content=json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        timeout=default_timeout if timeout is None else timeout,
    )


def get_capture(config: ClientConfig, capture_id: str) -> Request:
    return Request(
        method="GET",
        url=f"{config.instant_snap_base_url}{_CAPTURES_PATH}/{quote(capture_id, safe='')}",
        headers=request_headers(api_key=config.require_instant_snap_key()),
        timeout=config.timeout,
    )


def download(config: ClientConfig, capture: Capture, timeout: float | None) -> Request:
    if capture.download_url is None:
        raise ValueError(
            f"Capture {capture.id} has no download_url: files from capture_file and "
            "capture_to_bucket are not kept for download."
        )
    # The link is signed, so the API key is not sent to the file host.
    return Request(
        method="GET",
        url=capture.download_url,
        headers=request_headers(api_key=None, accept="*/*"),
        timeout=config.timeout if timeout is None else timeout,
        follow_redirects=True,
    )


def defaults(config: ClientConfig) -> Request:
    return Request(
        method="GET",
        url=config.instant_snap_base_url + "/instant-snap/v1/defaults",
        headers=request_headers(api_key=None),
        timeout=config.timeout,
    )


def catalog(config: ClientConfig) -> Request:
    return Request(
        method="GET",
        url=config.instant_snap_base_url + "/instant-snap/v1/catalog",
        headers=request_headers(api_key=config.require_instant_snap_key()),
        timeout=config.timeout,
    )


def trigger_now(config: ClientConfig, web_page_id: str) -> Request:
    return Request(
        method="POST",
        url=(
            f"{config.auto_schedule_base_url}/auto-schedule/v1/web-pages/"
            f"{quote(web_page_id, safe='')}/trigger-now"
        ),
        headers=request_headers(api_key=config.require_auto_schedule_key()),
        timeout=config.timeout,
    )
