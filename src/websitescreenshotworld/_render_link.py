"""Render links: signed URLs of an Instant Snap key that are themselves a screenshot."""

from __future__ import annotations

import hashlib
import hmac
import re
from decimal import Decimal
from typing import Literal
from urllib.parse import quote

from ._config import DEFAULT_INSTANT_SNAP_BASE_URL

RenderLinkFormat = Literal["png", "jpeg", "webp"]

_PATH_PREFIX = "/instant-snap/v1/render/"
_FORMATS = ("png", "jpeg", "webp")
_KEY_PREFIX = re.compile(r"^[0-9a-f]{12}$")


def _wire_value(value: str | int | float | bool) -> str:
    """Booleans as ``true``/``false``, numbers in their shortest decimal form (``2``, ``1.5``)."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return format(Decimal(repr(value)).normalize(), "f")
    return value


def _encode(value: str) -> str:
    """RFC 3986: every UTF-8 byte but ``A-Z a-z 0-9 - . _ ~``."""
    return quote(value, safe="-._~")


class RenderLink:
    """Builds render links locally. Nothing is sent, and no client or API key is needed."""

    @staticmethod
    def build(
        *,
        render_secret: str,
        key_prefix: str,
        url: str,
        format: RenderLinkFormat = "png",
        base_url: str | None = None,
        ttl: int | None = None,
        width: int | None = None,
        height: int | None = None,
        device_scale_factor: float | None = None,
        device_category: str | None = None,
        emulated_device: str | None = None,
        scroll_mode: str | None = None,
        auto_height: bool | None = None,
        max_height: int | None = None,
        zoom: int | None = None,
        block_ads: bool | None = None,
        block_pop_ups: bool | None = None,
        press_escape: bool | None = None,
        page_timeout_ms: int | None = None,
        scrolling_delay_ms: int | None = None,
        locale: str | None = None,
        time_zone: str | None = None,
        hide: str | None = None,
        xpath: str | None = None,
        click: str | None = None,
        hover: str | None = None,
        country: str | None = None,
        thumb_width: int | None = None,
    ) -> str:
        """A signed render link: a URL that is itself a screenshot, for an ``<img>`` tag,
        an email or a social preview. Every view of it that is not already cached makes one
        Instant Snap capture.

        ``render_secret`` is the key's render secret (``wsw_rsk_...``), shown on the API Keys
        page once render links are on for the key; ``key_prefix`` is the key's 12-character
        prefix. ``ttl`` is how long, in seconds, a capture of the link is served from cache
        (3600 to 2592000; the server uses a day when it is left out). ``hide``, ``xpath``,
        ``click`` and ``hover`` are the capture's selectors, ``country`` its proxy country, and
        ``thumb_width`` shrinks the image to that width. An option that is not set is not in
        the link.

        Raises ``ValueError`` when ``render_secret``, ``key_prefix`` or ``url`` is missing,
        ``key_prefix`` is not 12 lower-case hex characters, or ``format`` is not ``png``,
        ``jpeg`` or ``webp``.
        """
        if not render_secret:
            raise ValueError("render_secret is required.")
        if not key_prefix or not _KEY_PREFIX.match(key_prefix):
            raise ValueError("key_prefix must be the key's 12-character prefix (lower-case hex).")
        if not url:
            raise ValueError("url is required.")
        if format not in _FORMATS:
            raise ValueError("format must be png, jpeg or webp.")

        parameters: dict[str, str | int | float | bool | None] = {
            "url": url,
            "ttl": ttl,
            "width": width,
            "height": height,
            "device_scale_factor": device_scale_factor,
            "device_category": device_category,
            "emulated_device": emulated_device,
            "scroll_mode": scroll_mode,
            "auto_height": auto_height,
            "max_height": max_height,
            "zoom": zoom,
            "block_ads": block_ads,
            "block_pop_ups": block_pop_ups,
            "press_escape": press_escape,
            "page_timeout_ms": page_timeout_ms,
            "scrolling_delay_ms": scrolling_delay_ms,
            "locale": locale,
            "time_zone": time_zone,
            "hide": hide,
            "xpath": xpath,
            "click": click,
            "hover": hover,
            "country": country,
            "thumb_width": thumb_width,
        }
        pairs = sorted(
            (_encode(name), _encode(_wire_value(value)))
            for name, value in parameters.items()
            if value is not None
        )
        query = "&".join(f"{name}={value}" for name, value in pairs)
        canonical = f"{_PATH_PREFIX}{key_prefix}/{format}?{query}"
        signature = hmac.new(
            render_secret.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        base = (base_url or DEFAULT_INSTANT_SNAP_BASE_URL).rstrip("/")
        return f"{base}{canonical}&sig={signature}"
