from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from support import SPEC, load_json

from websitescreenshotworld import (
    Capture,
    SignatureVerificationError,
    WebsiteScreenshotWorldError,
    webhooks,
)

VECTORS: dict[str, Any] = load_json(SPEC / "webhook-vectors.json")
EVENT_FILES = sorted((SPEC / "events").glob("*.json"))

EXPECTED_EVENT_CLASSES: dict[str, type[webhooks.BaseEvent[Any]]] = {
    "auto-schedule.capture.changed": webhooks.CaptureChangedEvent,
    "auto-schedule.capture.failed": webhooks.AutoScheduleCaptureEvent,
    "auto-schedule.capture.succeeded": webhooks.AutoScheduleCaptureEvent,
    "auto-schedule.delivery.completed": webhooks.DeliveryCompletedEvent,
    "auto-schedule.ping": webhooks.PingEvent,
    "auto-schedule.schedule.paused": webhooks.SchedulePausedEvent,
    "auto-schedule.sitemap_run.completed": webhooks.SitemapRunCompletedEvent,
    "instant-snap.capture.failed": webhooks.InstantSnapCaptureEvent,
    "instant-snap.capture.succeeded": webhooks.InstantSnapCaptureEvent,
    "unknown": webhooks.UnknownEvent,
}

SECRET = "whsec_test"
NOW = 1_790_418_600


def sign(body: bytes, timestamp: int = NOW, secret: str = SECRET) -> str:
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={digest.hexdigest()}"


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda case: case["name"])
def test_signature_vector(case: dict[str, Any]) -> None:
    kwargs: dict[str, Any] = {"now": case["now"]}
    if "tolerance" in case:
        kwargs["tolerance"] = case["tolerance"]
    if case["valid"]:
        event = webhooks.verify(case["body"], case["header"], VECTORS["secret"], **kwargs)
        assert event.type == "ping"
    else:
        with pytest.raises(SignatureVerificationError):
            webhooks.verify(case["body"], case["header"], VECTORS["secret"], **kwargs)


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda case: case["name"])
def test_signature_vector_as_bytes(case: dict[str, Any]) -> None:
    body = case["body"].encode("utf-8")
    tolerance = case.get("tolerance", webhooks.DEFAULT_TOLERANCE)
    try:
        webhooks.verify(
            body, case["header"], VECTORS["secret"], tolerance=tolerance, now=case["now"]
        )
    except SignatureVerificationError:
        assert not case["valid"]
    else:
        assert case["valid"]


def test_missing_header_is_refused() -> None:
    with pytest.raises(SignatureVerificationError):
        webhooks.verify(b"{}", None, SECRET, now=NOW)


def test_now_defaults_to_the_clock() -> None:
    body = b'{"id":"1","type":"x","created_at":"2026-09-26T10:30:05.000Z","data":{}}'
    with pytest.raises(SignatureVerificationError):
        webhooks.verify(body, sign(body, timestamp=NOW - 3600 * 24 * 365 * 10), SECRET)


def test_signed_body_that_is_not_json() -> None:
    body = b"not json"
    with pytest.raises(WebsiteScreenshotWorldError) as info:
        webhooks.verify(body, sign(body), SECRET, now=NOW)
    assert not isinstance(info.value, SignatureVerificationError)


@pytest.mark.parametrize("path", EVENT_FILES, ids=lambda path: path.stem)
def test_event_example_parses_to_its_type(path: Path) -> None:
    body = path.read_bytes()
    event = webhooks.verify(body, sign(body), SECRET, now=NOW)
    expected: dict[str, Any] = load_json(path)
    assert type(event) is EXPECTED_EVENT_CLASSES[path.stem]
    assert event.id == expected["id"]
    assert event.type == expected["type"]
    assert event.product == expected["product"]
    assert event.created_at == datetime(2026, 9, 26, 10, 30, 5, tzinfo=timezone.utc)
    assert event.raw == expected


def test_instant_snap_capture_event_data() -> None:
    body = (SPEC / "events" / "instant-snap.capture.failed.json").read_bytes()
    event = webhooks.verify(body, sign(body), SECRET, now=NOW)
    assert isinstance(event, webhooks.InstantSnapCaptureEvent)
    assert isinstance(event.data, Capture)
    assert event.data.error_code == "capture_failed"
    assert event.data.download_url is None


def test_delivery_event_data() -> None:
    body = (SPEC / "events" / "auto-schedule.delivery.completed.json").read_bytes()
    event = webhooks.verify(body, sign(body), SECRET, now=NOW)
    assert isinstance(event, webhooks.DeliveryCompletedEvent)
    assert event.data.schedule_id == "7d4e2b1a-6c5f-4a3e-9d8c-2b1a0f9e8d7c"
    assert event.data.page_source is not None
    assert event.data.page_source.sha256 == "ab" * 32
    [destination] = event.data.destinations
    assert destination.provider == "aws_s3"
    assert destination.completed_at == datetime(2026, 9, 26, 10, 30, 9, tzinfo=timezone.utc)


def test_capture_changed_event_data() -> None:
    body = (SPEC / "events" / "auto-schedule.capture.changed.json").read_bytes()
    event = webhooks.verify(body, sign(body), SECRET, now=NOW)
    assert isinstance(event, webhooks.CaptureChangedEvent)
    assert event.data.change_percent == 12.5
    assert event.data.change_image_available is True


def test_sitemap_run_event_data() -> None:
    body = (SPEC / "events" / "auto-schedule.sitemap_run.completed.json").read_bytes()
    event = webhooks.verify(body, sign(body), SECRET, now=NOW)
    assert isinstance(event, webhooks.SitemapRunCompletedEvent)
    assert event.data.pages_over_limit == 30
    assert event.data.message is None


def test_unknown_event_keeps_its_data() -> None:
    body = (SPEC / "events" / "unknown.json").read_bytes()
    event = webhooks.verify(body, sign(body), SECRET, now=NOW)
    assert isinstance(event, webhooks.UnknownEvent)
    assert event.type == "capture.teleported"
    assert event.data == {"anything": 1}
