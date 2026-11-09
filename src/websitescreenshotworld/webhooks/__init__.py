"""Verify webhook deliveries and read them as typed events.

::

    from websitescreenshotworld import webhooks

    event = webhooks.verify(raw_body, request.headers["X-WSW-Signature"], secret)
    if isinstance(event, webhooks.InstantSnapCaptureEvent):
        print(event.data.status)
"""

from .._errors import SignatureVerificationError
from ._events import (
    AutoScheduleCaptureEvent,
    BaseEvent,
    CaptureChange,
    CaptureChangedEvent,
    Delivery,
    DeliveryCompletedEvent,
    Destination,
    Event,
    InstantSnapCaptureEvent,
    Ping,
    PingEvent,
    ScheduleCapture,
    SchedulePaused,
    SchedulePausedEvent,
    SitemapRun,
    SitemapRunCompletedEvent,
    UnknownEvent,
)
from ._verify import DEFAULT_TOLERANCE, SIGNATURE_HEADER, verify

__all__ = [
    "DEFAULT_TOLERANCE",
    "SIGNATURE_HEADER",
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
    "SignatureVerificationError",
    "SitemapRun",
    "SitemapRunCompletedEvent",
    "UnknownEvent",
    "verify",
]
