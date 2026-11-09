"""Named values for the string tokens the API returns.

Results keep tokens as plain strings, so a value added to the API later still comes through;
compare them with these constants, for example ``capture.status == CaptureStatus.SUCCEEDED``.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "CaptureStatus",
    "EventType",
    "Format",
    "MediaCategory",
    "PageSourceFormat",
    "Product",
    "ResponseType",
    "S3DeliveryStatus",
    "TriggerStatus",
    "TriggeredBy",
]


class CaptureStatus:
    """Values of ``Capture.status``.

    An async capture (``submit``, ``submit_to_bucket``) starts ``queued``, is ``running`` once a
    browser has it, and ends ``succeeded`` or ``failed``.
    """

    QUEUED: Final = "queued"
    """Accepted by ``submit``/``submit_to_bucket``, waiting for a browser."""
    RUNNING: Final = "running"
    """An async capture a browser is taking now."""
    PENDING: Final = "pending"
    SUCCEEDED: Final = "succeeded"
    DELIVERED: Final = "delivered"
    FAILED: Final = "failed"
    TIMED_OUT: Final = "timed_out"
    EXPIRED: Final = "expired"


class ResponseType:
    """Values of ``Capture.response_type``."""

    JSON: Final = "json"
    BY_FORMAT: Final = "by_format"
    CLOUD_STORAGE: Final = "cloud_storage"


class MediaCategory:
    """Values of ``media_category``."""

    IMAGE: Final = "image"
    VIDEO: Final = "video"
    PDF: Final = "pdf"


class Format:
    """Values of ``format``."""

    PNG: Final = "png"
    JPEG: Final = "jpeg"
    WEBP: Final = "webp"
    TIFF: Final = "tiff"
    MP4: Final = "mp4"
    WEBM: Final = "webm"
    MOV: Final = "mov"
    GIF: Final = "gif"
    IMAGE_PDF: Final = "image_pdf"
    DOCUMENT_PDF: Final = "document_pdf"


class PageSourceFormat:
    """Values of ``page_source.format``."""

    HTML: Final = "html"
    JSON: Final = "json"
    TEXT: Final = "text"


class S3DeliveryStatus:
    """Values of ``Capture.s3_delivery.status``."""

    NOT_STARTED: Final = "not_started"
    IN_PROGRESS: Final = "in_progress"
    COMPLETED: Final = "completed"
    FAILED: Final = "failed"


class TriggerStatus:
    """Values of ``TriggerResult.status``."""

    TRIGGERED: Final = "triggered"
    ALREADY_PENDING: Final = "already_pending"


class TriggeredBy:
    """Values of ``TriggerResult.triggered_by``."""

    API: Final = "api"
    UI: Final = "ui"


class Product:
    """Values of a webhook event's ``product``."""

    INSTANT_SNAP: Final = "instant_snap"
    AUTO_SCHEDULE: Final = "auto_schedule"


class EventType:
    """Values of a webhook event's ``type``."""

    CAPTURE_SUCCEEDED: Final = "capture.succeeded"
    CAPTURE_FAILED: Final = "capture.failed"
    CAPTURE_CHANGED: Final = "capture.changed"
    DELIVERY_COMPLETED: Final = "delivery.completed"
    SCHEDULE_PAUSED: Final = "schedule.paused"
    SITEMAP_RUN_COMPLETED: Final = "sitemap_run.completed"
    PING: Final = "ping"
