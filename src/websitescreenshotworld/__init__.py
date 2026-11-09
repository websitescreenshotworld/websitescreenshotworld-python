"""Python client for the Website Screenshot World Instant Snap and Auto Schedule APIs.

::

    from websitescreenshotworld import WebsiteScreenshotWorld

    with WebsiteScreenshotWorld() as client:
        capture = client.instant_snap.capture(url="https://example.com")
        print(capture.download_url)
"""

from . import webhooks
from ._client import AsyncWebsiteScreenshotWorld, WebsiteScreenshotWorld
from ._constants import (
    CaptureStatus,
    EventType,
    Format,
    MediaCategory,
    PageSourceFormat,
    Product,
    ResponseType,
    S3DeliveryStatus,
    TriggeredBy,
    TriggerStatus,
)
from ._errors import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    CaptureError,
    InvalidRequestError,
    NotFoundError,
    PlanLimitError,
    RateLimitError,
    ServiceError,
    SignatureVerificationError,
    WebsiteScreenshotWorldError,
)
from ._files import AsyncCaptureFile, AsyncCaptureFileContext, CaptureFile, SaveTarget
from ._models import Capture, Catalog, Defaults, PageSource, S3Delivery, TriggerResult, Viewport
from ._params import (
    CaptureFileOptions,
    CaptureOptions,
    GeolocationParam,
    PageSourceParam,
    ProxyParam,
    S3DeliveryParam,
    SelectorsParam,
    SubmitOptions,
    TimestampWatermarkParam,
    ViewportParam,
)
from ._version import __version__

__all__ = [
    "APIConnectionError",
    "APITimeoutError",
    "AsyncCaptureFile",
    "AsyncCaptureFileContext",
    "AsyncWebsiteScreenshotWorld",
    "AuthenticationError",
    "Capture",
    "CaptureError",
    "CaptureFile",
    "CaptureFileOptions",
    "CaptureOptions",
    "CaptureStatus",
    "Catalog",
    "Defaults",
    "EventType",
    "Format",
    "GeolocationParam",
    "InvalidRequestError",
    "MediaCategory",
    "NotFoundError",
    "PageSource",
    "PageSourceFormat",
    "PageSourceParam",
    "PlanLimitError",
    "Product",
    "ProxyParam",
    "RateLimitError",
    "ResponseType",
    "S3Delivery",
    "S3DeliveryParam",
    "S3DeliveryStatus",
    "SaveTarget",
    "SelectorsParam",
    "ServiceError",
    "SignatureVerificationError",
    "SubmitOptions",
    "TimestampWatermarkParam",
    "TriggerResult",
    "TriggerStatus",
    "TriggeredBy",
    "Viewport",
    "ViewportParam",
    "WebsiteScreenshotWorld",
    "WebsiteScreenshotWorldError",
    "__version__",
    "webhooks",
]
