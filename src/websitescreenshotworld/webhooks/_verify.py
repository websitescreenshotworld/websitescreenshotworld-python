from __future__ import annotations

import hashlib
import hmac
import json
import re
import time

from .._errors import SignatureVerificationError, WebsiteScreenshotWorldError
from .._models import read_object
from ._events import Event, parse_event

__all__ = ["DEFAULT_TOLERANCE", "SIGNATURE_HEADER", "verify"]

SIGNATURE_HEADER = "X-WSW-Signature"
"""The header that carries a delivery's signature."""

DEFAULT_TOLERANCE = 300
"""Seconds a signature's timestamp may be away from now."""

_TIMESTAMP = re.compile(r"[0-9]+")


def verify(
    body: bytes | str,
    signature_header: str | None,
    secret: str,
    *,
    tolerance: int = DEFAULT_TOLERANCE,
    now: float | None = None,
) -> Event:
    """Check a webhook delivery's signature and return its typed event.

    Args:
        body: The request body exactly as received. A body that was parsed and serialised
            again no longer matches its signature.
        signature_header: The value of the ``X-WSW-Signature`` header.
        secret: The endpoint's signing secret from the dashboard.
        tolerance: Seconds the signature's timestamp may be before or after ``now``.
        now: Unix time to check against; the current time when left out.

    Raises:
        SignatureVerificationError: The header is missing or malformed, too old or too new,
            or no signature in it matches.
    """
    payload = body.encode("utf-8") if isinstance(body, str) else bytes(body)
    timestamp, signatures = _parse_header(signature_header or "")

    current = time.time() if now is None else now
    if abs(current - int(timestamp)) > tolerance:
        raise SignatureVerificationError(
            f"The signature timestamp is more than {tolerance} seconds from now."
        )

    signed = timestamp.encode("ascii") + b"." + payload
    expected = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest().encode()
    matches = [
        hmac.compare_digest(expected, candidate.lower().encode("utf-8")) for candidate in signatures
    ]
    if not any(matches):
        raise SignatureVerificationError("No signature in the header matches the body.")

    try:
        envelope = json.loads(payload)
    except ValueError as exc:
        raise WebsiteScreenshotWorldError("The webhook body is not JSON.") from exc
    return read_object(envelope, parse_event)


def _parse_header(header: str) -> tuple[str, list[str]]:
    timestamp: str | None = None
    signatures: list[str] = []
    for part in header.split(","):
        name, separator, value = part.partition("=")
        if not separator:
            continue
        name, value = name.strip(), value.strip()
        if name == "t" and timestamp is None:
            timestamp = value
        elif name == "v1":
            signatures.append(value)
    if timestamp is None or not _TIMESTAMP.fullmatch(timestamp):
        raise SignatureVerificationError(f"The {SIGNATURE_HEADER} header has no valid timestamp.")
    if not signatures:
        raise SignatureVerificationError(f"The {SIGNATURE_HEADER} header has no v1 signature.")
    return timestamp, signatures
