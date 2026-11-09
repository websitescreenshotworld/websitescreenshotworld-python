from __future__ import annotations

import json
from typing import Any

import httpx

__all__ = [
    "APIConnectionError",
    "APITimeoutError",
    "AuthenticationError",
    "CaptureError",
    "InvalidRequestError",
    "NotFoundError",
    "PlanLimitError",
    "RateLimitError",
    "ServiceError",
    "SignatureVerificationError",
    "WebsiteScreenshotWorldError",
]


class WebsiteScreenshotWorldError(Exception):
    """Base class of every error this library raises.

    Branch on ``error_code`` (or the subclass), never on ``http_status`` or ``message``.

    Attributes:
        message: A sentence for a person. The API may change its wording between releases.
        error_code: The API's error token, such as ``"rate_limited"``. ``None`` when the error
            did not come from the API.
        http_status: The HTTP status of the refusal, when there was one.
        retry_after_seconds: How long the API asked to wait before retrying, when it said.
        body: The response body as received, when there was one.
    """

    def __init__(
        self,
        message: str,
        *,
        error_code: str | None = None,
        http_status: int | None = None,
        retry_after_seconds: int | None = None,
        body: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.http_status = http_status
        self.retry_after_seconds = retry_after_seconds
        self.body = body

    def __str__(self) -> str:
        if self.error_code is None:
            return self.message
        return f"[{self.error_code}] {self.message}"


class AuthenticationError(WebsiteScreenshotWorldError):
    """The API key is missing, malformed, revoked or for the other product."""


class InvalidRequestError(WebsiteScreenshotWorldError):
    """The request was refused as invalid; sending it again unchanged will not help."""


class PlanLimitError(WebsiteScreenshotWorldError):
    """The plan has no allowance left, or does not include the feature."""


class NotFoundError(WebsiteScreenshotWorldError):
    """The capture or web page does not exist for this account."""


class RateLimitError(WebsiteScreenshotWorldError):
    """Too many requests.

    ``rate_limited`` is retried automatically before this is raised. ``queue_full`` (too many async
    captures waiting or running) is not retried; wait ``retry_after_seconds`` and submit again.
    """


class CaptureError(WebsiteScreenshotWorldError):
    """The website could not be captured, the result was too large, or an async capture waited
    too long in the queue (``capture_expired``). Not retried."""


class ServiceError(WebsiteScreenshotWorldError):
    """The service could not answer; the retryable codes are retried before this is raised."""


class APIConnectionError(WebsiteScreenshotWorldError):
    """The request could not be sent, or no answer came back."""


class APITimeoutError(APIConnectionError):
    """No answer came back before the timeout. Not retried, because the time is used up."""


class SignatureVerificationError(WebsiteScreenshotWorldError):
    """A webhook's ``X-WSW-Signature`` header does not match its body, or is too old."""


_KIND_BY_CODE: dict[str, type[WebsiteScreenshotWorldError]] = {
    "api_key_invalid": AuthenticationError,
    "validation_failed": InvalidRequestError,
    "s3_destination_invalid": InvalidRequestError,
    "web_page_id_invalid": InvalidRequestError,
    "idempotency_key_reused": InvalidRequestError,
    "sitemap_schedule_not_triggerable": InvalidRequestError,
    "quota_exhausted": PlanLimitError,
    "feature_not_available": PlanLimitError,
    "no_trigger_allowance": PlanLimitError,
    "forbidden": PlanLimitError,
    "capture_not_found": NotFoundError,
    "web_page_not_found": NotFoundError,
    "not_found": NotFoundError,
    "rate_limited": RateLimitError,
    "queue_full": RateLimitError,
    "capture_failed": CaptureError,
    "capture_timeout": CaptureError,
    "payload_too_large": CaptureError,
    "capture_expired": CaptureError,
    "capture_busy": ServiceError,
    "service_unavailable": ServiceError,
    "internal_error": ServiceError,
    "request_cancelled": ServiceError,
    "idempotency_key_in_use": ServiceError,
}

RETRYABLE_CODES = frozenset(
    {"rate_limited", "capture_busy", "service_unavailable", "idempotency_key_in_use"}
)

# Used when a proxy or load balancer answered instead of the API, so there is no JSON refusal.
_CODE_BY_STATUS = {
    400: "validation_failed",
    401: "api_key_invalid",
    403: "forbidden",
    404: "not_found",
    409: "idempotency_key_in_use",
    413: "payload_too_large",
    429: "rate_limited",
    500: "internal_error",
    502: "service_unavailable",
    503: "service_unavailable",
    504: "service_unavailable",
}


def error_from_response(response: httpx.Response) -> WebsiteScreenshotWorldError:
    """Build the error for a refusal whose body has already been read."""
    text = response.content.decode("utf-8", errors="replace")
    refusal = _json_refusal(text)
    status = response.status_code
    if refusal is not None:
        code = str(refusal["error_code"])
        message = str(refusal.get("error_message") or f"The API refused the request ({status}).")
        retry_after = _as_seconds(refusal.get("retry_after_seconds"))
    else:
        code = _CODE_BY_STATUS.get(status, "unknown_error")
        reason = httpx.codes.get_reason_phrase(status) or "Error"
        message = f"The server answered {status} {reason} without an error description."
        retry_after = None
    if retry_after is None:
        retry_after = _as_seconds(response.headers.get("Retry-After"))
    error_class = _KIND_BY_CODE.get(code, WebsiteScreenshotWorldError)
    return error_class(
        message,
        error_code=code,
        http_status=status,
        retry_after_seconds=retry_after,
        body=text or None,
    )


def _json_refusal(text: str) -> dict[str, Any] | None:
    try:
        value = json.loads(text)
    except ValueError:
        return None
    if isinstance(value, dict) and isinstance(value.get("error_code"), str):
        return value
    return None


def _as_seconds(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value >= 0 else None
    if isinstance(value, str):
        try:
            seconds = int(value.strip())
        except ValueError:
            return None
        return seconds if seconds >= 0 else None
    return None
