from __future__ import annotations

import os
import platform
from dataclasses import dataclass, field

from ._errors import AuthenticationError
from ._version import __version__

DEFAULT_INSTANT_SNAP_BASE_URL = "https://api.websitescreenshotworld.com"
DEFAULT_AUTO_SCHEDULE_BASE_URL = "https://autoapi.websitescreenshotworld.com"
DEFAULT_TIMEOUT = 30.0
# The API may spend up to 120 seconds on a capture before it answers.
DEFAULT_CAPTURE_TIMEOUT = 180.0
DEFAULT_MAX_RETRIES = 2

INSTANT_SNAP_KEY_ENV = "WSW_INSTANT_SNAP_API_KEY"
AUTO_SCHEDULE_KEY_ENV = "WSW_AUTO_SCHEDULE_API_KEY"

USER_AGENT = (
    f"websitescreenshotworld-python/{__version__} "
    f"({platform.python_implementation()} {platform.python_version()})"
)


@dataclass(frozen=True)
class ClientConfig:
    """Settings shared by both products of one client."""

    instant_snap_api_key: str | None = field(repr=False)
    auto_schedule_api_key: str | None = field(repr=False)
    instant_snap_base_url: str
    auto_schedule_base_url: str
    timeout: float
    capture_timeout: float
    max_retries: int

    @classmethod
    def create(
        cls,
        *,
        instant_snap_api_key: str | None,
        auto_schedule_api_key: str | None,
        instant_snap_base_url: str,
        auto_schedule_base_url: str,
        timeout: float,
        capture_timeout: float,
        max_retries: int,
    ) -> ClientConfig:
        if max_retries < 0:
            raise ValueError("max_retries cannot be negative")
        return cls(
            instant_snap_api_key=instant_snap_api_key or os.environ.get(INSTANT_SNAP_KEY_ENV),
            auto_schedule_api_key=auto_schedule_api_key or os.environ.get(AUTO_SCHEDULE_KEY_ENV),
            instant_snap_base_url=instant_snap_base_url.rstrip("/"),
            auto_schedule_base_url=auto_schedule_base_url.rstrip("/"),
            timeout=timeout,
            capture_timeout=capture_timeout,
            max_retries=max_retries,
        )

    def require_instant_snap_key(self) -> str:
        if not self.instant_snap_api_key:
            raise AuthenticationError(
                f"No Instant Snap API key: pass instant_snap_api_key or set {INSTANT_SNAP_KEY_ENV}."
            )
        return self.instant_snap_api_key

    def require_auto_schedule_key(self) -> str:
        if not self.auto_schedule_api_key:
            raise AuthenticationError(
                "No Auto Schedule API key: pass auto_schedule_api_key or set "
                f"{AUTO_SCHEDULE_KEY_ENV}."
            )
        return self.auto_schedule_api_key


def request_headers(
    *,
    api_key: str | None,
    accept: str = "application/json",
    has_body: bool = False,
    idempotency_key: str | None = None,
) -> dict[str, str]:
    headers = {"Accept": accept, "User-Agent": USER_AGENT}
    if api_key is not None:
        headers["X-Api-Key"] = api_key
    if has_body:
        headers["Content-Type"] = "application/json"
    if idempotency_key is not None:
        headers["Idempotency-Key"] = idempotency_key
    return headers
