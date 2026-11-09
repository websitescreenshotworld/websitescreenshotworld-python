from __future__ import annotations

from types import TracebackType

import httpx

from ._auto_schedule import AsyncAutoSchedule, AutoSchedule
from ._config import (
    DEFAULT_AUTO_SCHEDULE_BASE_URL,
    DEFAULT_CAPTURE_TIMEOUT,
    DEFAULT_INSTANT_SNAP_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    ClientConfig,
)
from ._instant_snap import AsyncInstantSnap, InstantSnap
from ._transport import AsyncTransport, SyncTransport

__all__ = ["AsyncWebsiteScreenshotWorld", "WebsiteScreenshotWorld"]


class WebsiteScreenshotWorld:
    """A client for the Instant Snap and Auto Schedule APIs.

    Either key may be left out; calling a product without its key raises
    :class:`AuthenticationError` before anything is sent.

    Args:
        instant_snap_api_key: Defaults to the ``WSW_INSTANT_SNAP_API_KEY`` environment variable.
        auto_schedule_api_key: Defaults to the ``WSW_AUTO_SCHEDULE_API_KEY`` environment variable.
        instant_snap_base_url: Where the Instant Snap API is served.
        auto_schedule_base_url: Where the Auto Schedule API is served.
        timeout: Seconds allowed for a call other than a capture, retries included.
        capture_timeout: Seconds allowed for a capture, retries included. The API can take
            up to 120 seconds on a slow page, so keep this above that.
        max_retries: How many times a retryable failure is retried.
        http_client: An ``httpx.Client`` to send requests with, for proxies, custom TLS or
            connection limits. It is not closed by :meth:`close`.
    """

    instant_snap: InstantSnap
    auto_schedule: AutoSchedule

    def __init__(
        self,
        *,
        instant_snap_api_key: str | None = None,
        auto_schedule_api_key: str | None = None,
        instant_snap_base_url: str = DEFAULT_INSTANT_SNAP_BASE_URL,
        auto_schedule_base_url: str = DEFAULT_AUTO_SCHEDULE_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        capture_timeout: float = DEFAULT_CAPTURE_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.Client | None = None,
    ) -> None:
        config = ClientConfig.create(
            instant_snap_api_key=instant_snap_api_key,
            auto_schedule_api_key=auto_schedule_api_key,
            instant_snap_base_url=instant_snap_base_url,
            auto_schedule_base_url=auto_schedule_base_url,
            timeout=timeout,
            capture_timeout=capture_timeout,
            max_retries=max_retries,
        )
        self._transport = SyncTransport(http_client, config.max_retries)
        self.instant_snap = InstantSnap(config, self._transport)
        self.auto_schedule = AutoSchedule(config, self._transport)

    def close(self) -> None:
        """Close the connections this client opened."""
        self._transport.close()

    def __enter__(self) -> WebsiteScreenshotWorld:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncWebsiteScreenshotWorld:
    """The asyncio client, with the same settings and methods as :class:`WebsiteScreenshotWorld`.

    ``http_client`` takes an ``httpx.AsyncClient``.
    """

    instant_snap: AsyncInstantSnap
    auto_schedule: AsyncAutoSchedule

    def __init__(
        self,
        *,
        instant_snap_api_key: str | None = None,
        auto_schedule_api_key: str | None = None,
        instant_snap_base_url: str = DEFAULT_INSTANT_SNAP_BASE_URL,
        auto_schedule_base_url: str = DEFAULT_AUTO_SCHEDULE_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        capture_timeout: float = DEFAULT_CAPTURE_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        config = ClientConfig.create(
            instant_snap_api_key=instant_snap_api_key,
            auto_schedule_api_key=auto_schedule_api_key,
            instant_snap_base_url=instant_snap_base_url,
            auto_schedule_base_url=auto_schedule_base_url,
            timeout=timeout,
            capture_timeout=capture_timeout,
            max_retries=max_retries,
        )
        self._transport = AsyncTransport(http_client, config.max_retries)
        self.instant_snap = AsyncInstantSnap(config, self._transport)
        self.auto_schedule = AsyncAutoSchedule(config, self._transport)

    async def close(self) -> None:
        """Close the connections this client opened."""
        await self._transport.close()

    async def __aenter__(self) -> AsyncWebsiteScreenshotWorld:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()
