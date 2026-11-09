"""What the API answers, as frozen dataclasses.

Each result keeps the answer it was read from in ``raw`` (without ``"success"``), so a field the
API adds after this release can still be reached.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

import httpx

from ._dates import parse_optional_datetime
from ._errors import WebsiteScreenshotWorldError

__all__ = [
    "Capture",
    "Catalog",
    "Defaults",
    "PageSource",
    "S3Delivery",
    "TriggerResult",
    "Viewport",
]

_T = TypeVar("_T")


@dataclass(frozen=True)
class PageSource:
    """The page source kept next to a capture."""

    format: str
    """``html``, ``json`` or ``text``; see :class:`PageSourceFormat`."""
    content_type: str | None
    size_bytes: int | None
    sha256: str | None
    """Lowercase hex digest of the source."""
    download_url: str | None
    """Short-lived link, reissued on every read. ``None`` in webhooks."""

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> PageSource:
        return cls(
            format=data["format"],
            content_type=data.get("content_type"),
            size_bytes=data.get("size_bytes"),
            sha256=data.get("sha256"),
            download_url=data.get("download_url"),
        )


@dataclass(frozen=True)
class S3Delivery:
    """How the upload to your bucket is going (``capture_to_bucket`` only)."""

    status: str
    """See :class:`S3DeliveryStatus`."""
    bucket: str
    key: str | None
    access_key_id: str | None
    """Masked to its last four characters. ``None`` in webhooks."""
    error: str | None

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> S3Delivery:
        return cls(
            status=data["status"],
            bucket=data["bucket"],
            key=data.get("key"),
            access_key_id=data.get("access_key_id"),
            error=data.get("error"),
        )


@dataclass(frozen=True)
class Capture:
    """An Instant Snap capture."""

    id: str
    status: str
    """See :class:`CaptureStatus`. An async capture is ``queued``, then ``running``, then
    ``succeeded`` or ``failed``."""
    response_type: str
    media_category: str | None
    """``None`` while an async capture is ``queued`` or ``running``."""
    format: str | None
    content_type: str | None
    size_bytes: int | None
    width: int | None
    height: int | None
    duration_ms: int | None
    """How long the capture took."""
    page_http_status: int | None
    """The status the website answered with."""
    captured_at: datetime | None
    final_url: str | None
    """Where the browser ended up, when the page redirected."""
    media_sha256: str | None
    download_url: str | None
    """Valid for 60 minutes and reissued by ``get``. ``None`` for files and bucket uploads."""
    expires_at: datetime | None
    """When the file is deleted."""
    page_source: PageSource | None
    s3_delivery: S3Delivery | None
    callback_url: str | None
    error_code: str | None
    """Why a ``failed`` or ``timed_out`` capture ended."""
    spec_version: str
    """The default set the capture was taken under."""
    raw: dict[str, Any] = field(repr=False, compare=False)

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Capture:
        page_source = data.get("page_source")
        s3_delivery = data.get("s3_delivery")
        return cls(
            id=data["id"],
            status=data["status"],
            response_type=data["response_type"],
            media_category=data.get("media_category"),
            format=data.get("format"),
            content_type=data.get("content_type"),
            size_bytes=data.get("size_bytes"),
            width=data.get("width"),
            height=data.get("height"),
            duration_ms=data.get("duration_ms"),
            page_http_status=data.get("page_http_status"),
            captured_at=parse_optional_datetime(data.get("captured_at")),
            final_url=data.get("final_url"),
            media_sha256=data.get("media_sha256"),
            download_url=data.get("download_url"),
            expires_at=parse_optional_datetime(data.get("expires_at")),
            page_source=PageSource._from_wire(page_source) if page_source else None,
            s3_delivery=S3Delivery._from_wire(s3_delivery) if s3_delivery else None,
            callback_url=data.get("callback_url"),
            error_code=data.get("error_code"),
            spec_version=data["spec_version"],
            raw=dict(data),
        )


@dataclass(frozen=True)
class Viewport:
    """A browser window size."""

    width: int | None
    height: int | None
    device_scale_factor: float | None

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Viewport:
        return cls(
            width=data.get("width"),
            height=data.get("height"),
            device_scale_factor=data.get("device_scale_factor"),
        )


@dataclass(frozen=True)
class Defaults:
    """The values a capture takes for options it leaves out, and the limits it is checked against.

    Every field is ``None`` when the API does not list it.
    """

    spec_version: str | None
    response_type: str | None
    media_category: str | None
    format: Mapping[str, str] | None
    """The default format of each media category."""
    formats: Mapping[str, list[str]] | None
    """The formats each media category accepts."""
    device_category: str | None
    emulated_device: str | None
    viewport: Viewport | None
    zoom: int | None
    scroll_mode: str | None
    auto_height: bool | None
    auto_height_max_height: int | None
    auto_height_max_height_webp: int | None
    block_ads: bool | None
    block_pop_ups: bool | None
    press_escape: bool | None
    page_timeout_ms: int | None
    scrolling_delay_ms: int | None
    geolocation: bool | None
    geolocation_accuracy: float | None
    wait_for_cloud_sync: bool | None
    timestamp_watermark: Mapping[str, Any] | None
    page_source: Mapping[str, Any] | None
    limits: Mapping[str, Any] | None
    left_to_the_browser: list[str] | None
    raw: dict[str, Any] = field(repr=False, compare=False)

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Defaults:
        viewport = data.get("viewport")
        return cls(
            spec_version=data.get("spec_version"),
            response_type=data.get("response_type"),
            media_category=data.get("media_category"),
            format=data.get("format"),
            formats=data.get("formats"),
            device_category=data.get("device_category"),
            emulated_device=data.get("emulated_device"),
            viewport=Viewport._from_wire(viewport) if viewport else None,
            zoom=data.get("zoom"),
            scroll_mode=data.get("scroll_mode"),
            auto_height=data.get("auto_height"),
            auto_height_max_height=data.get("auto_height_max_height"),
            auto_height_max_height_webp=data.get("auto_height_max_height_webp"),
            block_ads=data.get("block_ads"),
            block_pop_ups=data.get("block_pop_ups"),
            press_escape=data.get("press_escape"),
            page_timeout_ms=data.get("page_timeout_ms"),
            scrolling_delay_ms=data.get("scrolling_delay_ms"),
            geolocation=data.get("geolocation"),
            geolocation_accuracy=data.get("geolocation_accuracy"),
            wait_for_cloud_sync=data.get("wait_for_cloud_sync"),
            timestamp_watermark=data.get("timestamp_watermark"),
            page_source=data.get("page_source"),
            limits=data.get("limits"),
            left_to_the_browser=data.get("left_to_the_browser"),
            raw=dict(data),
        )


@dataclass(frozen=True)
class Catalog:
    """What ``emulated_device`` and ``proxy.country`` accept."""

    emulated_devices: list[str]
    proxy_countries: list[str]
    raw: dict[str, Any] = field(repr=False, compare=False)

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Catalog:
        return cls(
            emulated_devices=list(data["emulated_devices"]),
            proxy_countries=list(data["proxy_countries"]),
            raw=dict(data),
        )


@dataclass(frozen=True)
class TriggerResult:
    """The answer to an Auto Schedule trigger-now."""

    status: str
    """``triggered``, or ``already_pending`` when nothing new was started or charged."""
    web_page_id: str
    triggered_by: str
    """See :class:`TriggeredBy`."""
    triggered_at: datetime
    """When the capture was queued; for ``already_pending``, the original trigger."""
    message: str
    raw: dict[str, Any] = field(repr=False, compare=False)

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> TriggerResult:
        triggered_at = parse_optional_datetime(data["triggered_at"])
        if triggered_at is None:
            raise ValueError("triggered_at is null")
        return cls(
            status=data["status"],
            web_page_id=data["web_page_id"],
            triggered_by=data["triggered_by"],
            triggered_at=triggered_at,
            message=data["message"],
            raw=dict(data),
        )


def read_object(data: object, reader: Callable[[Mapping[str, Any]], _T]) -> _T:
    """Build a result from decoded JSON, dropping ``success``.

    A malformed answer raises the base error rather than a ``KeyError`` from deep inside.
    """
    if not isinstance(data, dict):
        raise WebsiteScreenshotWorldError("The API answered with something other than an object.")
    fields = {key: value for key, value in data.items() if key != "success"}
    try:
        return reader(fields)
    except (KeyError, TypeError, ValueError) as exc:
        raise WebsiteScreenshotWorldError(f"The API answer could not be read: {exc!r}") from exc


def read_response(response: httpx.Response, reader: Callable[[Mapping[str, Any]], _T]) -> _T:
    """Build a result from a successful JSON response."""
    try:
        data = response.json()
    except ValueError as exc:
        raise WebsiteScreenshotWorldError(
            "The API answered with a body that is not JSON.",
            http_status=response.status_code,
            body=response.text,
        ) from exc
    return read_object(data, reader)
