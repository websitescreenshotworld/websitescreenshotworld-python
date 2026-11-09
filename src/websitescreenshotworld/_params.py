"""Typed shapes of the capture options, spelled exactly as the API's JSON fields."""

from __future__ import annotations

from typing import Literal, TypedDict

__all__ = [
    "CaptureFileOptions",
    "CaptureOptions",
    "GeolocationParam",
    "PageSourceParam",
    "ProxyParam",
    "S3DeliveryParam",
    "SelectorsParam",
    "SubmitOptions",
    "TimestampWatermarkParam",
    "ViewportParam",
]


class ViewportParam(TypedDict, total=False):
    """The browser window."""

    width: int
    """CSS pixels, 250 to 7680. Default 1920."""
    height: int
    """CSS pixels, 250 to 7680. Default 1080."""
    device_scale_factor: float
    """Device pixel ratio, 1 to 3. Default 1."""


class GeolocationParam(TypedDict, total=False):
    """The position the page sees. Send latitude and longitude together."""

    latitude: float
    longitude: float
    accuracy: float
    """Metres, 1 to 10000. Default 100."""


class SelectorsParam(TypedDict, total=False):
    """Elements to act on before capturing."""

    xpath: str
    """Capture only the element this XPath selects. At most 512 characters."""
    hide: str
    """Elements to hide: up to 25 comma-separated CSS selectors (an XPath starting with ``//``
    works too), at most 2000 characters. Each is applied on its own; one the browser rejects is
    skipped."""
    click: str
    """CSS selector of an element to click. At most 512 characters."""
    hover: str
    """CSS selector of an element to hover. At most 512 characters."""


class ProxyParam(TypedDict):
    """Capture through a proxy. Needs the ProxyLocation plan feature."""

    country: str
    """A country from ``catalog().proxy_countries``."""


class TimestampWatermarkParam(TypedDict, total=False):
    """A strip with the capture time and URL. Sending the block turns it on; not for video."""

    enabled: bool
    location: Literal["top", "bottom"]
    font_color: str
    """Hex colour. Default ``#000000``."""
    background_color: str
    """Hex colour. Default ``#FFFFFF``."""


class PageSourceParam(TypedDict, total=False):
    """Also keep the page source, charged as a second capture and capped at 10 MB."""

    format: Literal["html", "json", "text"]


class _S3DeliveryRequired(TypedDict):
    access_key_id: str
    secret_access_key: str
    bucket: str


class S3DeliveryParam(_S3DeliveryRequired, total=False):
    """The bucket ``capture_to_bucket`` and ``submit_to_bucket`` upload to.

    Give ``region`` or ``endpoint_url``.
    """

    region: str
    endpoint_url: str
    """An https endpoint of an S3-compatible service."""
    force_path_style: bool
    key_prefix: str
    wait_for_sync: bool
    """Wait up to 30 seconds for the upload before answering."""


class CaptureFileOptions(TypedDict, total=False):
    """Options of ``capture_file``. Leave an option out to take the API's default."""

    media_category: Literal["image", "video", "pdf"]
    format: Literal[
        "png", "jpeg", "webp", "tiff", "mp4", "webm", "mov", "gif", "image_pdf", "document_pdf"
    ]
    viewport: ViewportParam
    device_category: Literal["desktop", "mobile"]
    emulated_device: str
    scroll_mode: Literal["viewport", "scroll"]
    auto_height: bool
    max_height: int
    zoom: int
    block_ads: bool
    block_pop_ups: bool
    press_escape: bool
    page_timeout_ms: int
    scrolling_delay_ms: int
    user_agent: str
    locale: str
    time_zone: str
    headers: dict[str, str]
    cookies: dict[str, str]
    geolocation: GeolocationParam
    selectors: SelectorsParam
    proxy: ProxyParam
    timestamp_watermark: TimestampWatermarkParam
    callback_url: str


class CaptureOptions(CaptureFileOptions, total=False):
    """Options of ``capture`` and ``capture_to_bucket``."""

    page_source: PageSourceParam


class SubmitOptions(CaptureOptions, total=False):
    """Options of ``submit`` and ``submit_to_bucket``: those of ``capture``, plus ``timeout``."""

    timeout: int
    """Async only (``submit``/``submit_to_bucket``): the browser time the capture may use, in
    seconds, 30 to 300; the server's default is 120. The server refuses it on the other capture
    operations, whose ``timeout`` argument is instead how long the client waits for the answer."""
