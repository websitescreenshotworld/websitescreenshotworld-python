"""Typed webhook events."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from .._dates import parse_datetime, parse_optional_datetime
from .._models import Capture, PageSource

__all__ = [
    "AutoScheduleCaptureEvent",
    "BaseEvent",
    "CaptureChange",
    "CaptureChangedEvent",
    "Delivery",
    "DeliveryCompletedEvent",
    "Destination",
    "Event",
    "InstantSnapCaptureEvent",
    "Ping",
    "PingEvent",
    "ScheduleCapture",
    "SchedulePaused",
    "SchedulePausedEvent",
    "SitemapRun",
    "SitemapRunCompletedEvent",
    "UnknownEvent",
]

_DataT = TypeVar("_DataT")


@dataclass(frozen=True)
class ScheduleCapture:
    """An Auto Schedule capture, as ``capture.succeeded`` and ``capture.failed`` carry it."""

    id: str
    schedule_id: str
    """The web page's id; ``trigger_now`` calls it ``web_page_id``."""
    schedule_name: str | None
    url: str
    status: str
    media_category: str | None
    format: str | None
    page_http_status: int | None
    captured_at: datetime | None
    final_url: str | None
    media_sha256: str | None
    page_source: PageSource | None
    """Only ``format`` and ``sha256`` are set."""
    sitemap_run_id: str | None
    """Set when the capture belongs to a sitemap run."""

    @staticmethod
    def _fields(data: Mapping[str, Any]) -> dict[str, Any]:
        page_source = data.get("page_source")
        return {
            "id": data["id"],
            "schedule_id": data["schedule_id"],
            "schedule_name": data.get("schedule_name"),
            "url": data["url"],
            "status": data["status"],
            "media_category": data.get("media_category"),
            "format": data.get("format"),
            "page_http_status": data.get("page_http_status"),
            "captured_at": parse_optional_datetime(data.get("captured_at")),
            "final_url": data.get("final_url"),
            "media_sha256": data.get("media_sha256"),
            "page_source": PageSource._from_wire(page_source) if page_source else None,
            "sitemap_run_id": data.get("sitemap_run_id"),
        }

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> ScheduleCapture:
        return cls(**cls._fields(data))


@dataclass(frozen=True)
class Destination:
    """Where ``delivery.completed`` sent a capture."""

    slot: int
    name: str | None
    provider: str
    status: str
    completed_at: datetime | None

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Destination:
        return cls(
            slot=data["slot"],
            name=data.get("name"),
            provider=data["provider"],
            status=data["status"],
            completed_at=parse_optional_datetime(data.get("completed_at")),
        )


@dataclass(frozen=True)
class Delivery(ScheduleCapture):
    """The capture fields, plus where the file went."""

    destinations: list[Destination]

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Delivery:
        destinations = [Destination._from_wire(item) for item in data.get("destinations") or []]
        return cls(**cls._fields(data), destinations=destinations)


@dataclass(frozen=True)
class CaptureChange(ScheduleCapture):
    """The capture fields, plus how much the page changed since the capture before."""

    change_percent: float
    compared_to_capture_id: str | None
    change_image_available: bool

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> CaptureChange:
        return cls(
            **cls._fields(data),
            change_percent=float(data["change_percent"]),
            compared_to_capture_id=data.get("compared_to_capture_id"),
            change_image_available=bool(data.get("change_image_available")),
        )


@dataclass(frozen=True)
class SchedulePaused:
    """A schedule that stopped running, and why."""

    schedule_id: str
    schedule_name: str | None
    url: str | None
    reason: str
    paused_at: datetime | None

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> SchedulePaused:
        return cls(
            schedule_id=data["schedule_id"],
            schedule_name=data.get("schedule_name"),
            url=data.get("url"),
            reason=data["reason"],
            paused_at=parse_optional_datetime(data.get("paused_at")),
        )


@dataclass(frozen=True)
class SitemapRun:
    """One run over a sitemap, with how many pages went each way."""

    sitemap_run_id: str
    schedule_id: str
    schedule_name: str | None
    sitemap_url: str
    status: str
    run_at: datetime | None
    completed_at: datetime | None
    pages_listed: int | None
    pages_matched: int | None
    pages_queued: int | None
    pages_succeeded: int | None
    pages_failed: int | None
    pages_over_limit: int | None
    pages_over_quota: int | None
    message: str | None

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> SitemapRun:
        return cls(
            sitemap_run_id=data["sitemap_run_id"],
            schedule_id=data["schedule_id"],
            schedule_name=data.get("schedule_name"),
            sitemap_url=data["sitemap_url"],
            status=data["status"],
            run_at=parse_optional_datetime(data.get("run_at")),
            completed_at=parse_optional_datetime(data.get("completed_at")),
            pages_listed=data.get("pages_listed"),
            pages_matched=data.get("pages_matched"),
            pages_queued=data.get("pages_queued"),
            pages_succeeded=data.get("pages_succeeded"),
            pages_failed=data.get("pages_failed"),
            pages_over_limit=data.get("pages_over_limit"),
            pages_over_quota=data.get("pages_over_quota"),
            message=data.get("message"),
        )


@dataclass(frozen=True)
class Ping:
    """A test delivery sent from the dashboard."""

    endpoint_id: str
    endpoint_name: str | None
    message: str | None
    sent_at: datetime | None

    @classmethod
    def _from_wire(cls, data: Mapping[str, Any]) -> Ping:
        return cls(
            endpoint_id=data["endpoint_id"],
            endpoint_name=data.get("endpoint_name"),
            message=data.get("message"),
            sent_at=parse_optional_datetime(data.get("sent_at")),
        )


@dataclass(frozen=True)
class BaseEvent(Generic[_DataT]):
    """The envelope every delivery shares."""

    id: str
    """The delivery id; the same on redeliveries, so use it to drop duplicates."""
    type: str
    """See :class:`EventType`."""
    created_at: datetime
    product: str
    """``instant_snap`` or ``auto_schedule``; see :class:`Product`."""
    data: _DataT
    raw: dict[str, Any] = field(repr=False, compare=False)
    """The whole envelope as received."""


@dataclass(frozen=True)
class InstantSnapCaptureEvent(BaseEvent[Capture]):
    """``capture.succeeded`` or ``capture.failed`` for an Instant Snap capture.

    ``data`` is the capture as ``get`` returns it, without download links or the access key.
    """


@dataclass(frozen=True)
class AutoScheduleCaptureEvent(BaseEvent[ScheduleCapture]):
    """``capture.succeeded`` or ``capture.failed`` for an Auto Schedule capture."""


@dataclass(frozen=True)
class DeliveryCompletedEvent(BaseEvent[Delivery]):
    """``delivery.completed``: an Auto Schedule capture reached its destinations."""


@dataclass(frozen=True)
class CaptureChangedEvent(BaseEvent[CaptureChange]):
    """``capture.changed``: an Auto Schedule capture differs from the one before."""


@dataclass(frozen=True)
class SchedulePausedEvent(BaseEvent[SchedulePaused]):
    """``schedule.paused``: a schedule stopped running."""


@dataclass(frozen=True)
class SitemapRunCompletedEvent(BaseEvent[SitemapRun]):
    """``sitemap_run.completed``: every page of a sitemap run has been handled."""


@dataclass(frozen=True)
class PingEvent(BaseEvent[Ping]):
    """``ping``: a test delivery."""


@dataclass(frozen=True)
class UnknownEvent(BaseEvent[dict[str, Any]]):
    """An event type this version of the library does not know yet; ``data`` is left as is."""


Event = (
    InstantSnapCaptureEvent
    | AutoScheduleCaptureEvent
    | DeliveryCompletedEvent
    | CaptureChangedEvent
    | SchedulePausedEvent
    | SitemapRunCompletedEvent
    | PingEvent
    | UnknownEvent
)
"""Any event :func:`verify` can return."""

_CAPTURE_TYPES = frozenset({"capture.succeeded", "capture.failed"})


def parse_event(envelope: Mapping[str, Any]) -> Event:
    """Type an event envelope by its ``type`` and ``product``."""
    event_type = envelope["type"]
    product = envelope.get("product")
    data = envelope.get("data") or {}
    common: dict[str, Any] = {
        "id": envelope["id"],
        "type": event_type,
        "created_at": parse_datetime(envelope["created_at"]),
        "product": product,
        "raw": dict(envelope),
    }
    if event_type in _CAPTURE_TYPES and product == "instant_snap":
        return InstantSnapCaptureEvent(**common, data=Capture._from_wire(data))
    if event_type in _CAPTURE_TYPES and product == "auto_schedule":
        return AutoScheduleCaptureEvent(**common, data=ScheduleCapture._from_wire(data))
    if event_type == "delivery.completed":
        return DeliveryCompletedEvent(**common, data=Delivery._from_wire(data))
    if event_type == "capture.changed":
        return CaptureChangedEvent(**common, data=CaptureChange._from_wire(data))
    if event_type == "schedule.paused":
        return SchedulePausedEvent(**common, data=SchedulePaused._from_wire(data))
    if event_type == "sitemap_run.completed":
        return SitemapRunCompletedEvent(**common, data=SitemapRun._from_wire(data))
    if event_type == "ping":
        return PingEvent(**common, data=Ping._from_wire(data))
    return UnknownEvent(**common, data=dict(data))
