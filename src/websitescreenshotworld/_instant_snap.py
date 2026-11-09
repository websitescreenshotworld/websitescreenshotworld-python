from __future__ import annotations

import asyncio
import time
from contextlib import closing
from typing import TYPE_CHECKING

from . import _requests
from ._config import ClientConfig
from ._files import (
    AsyncCaptureFile,
    AsyncCaptureFileContext,
    CaptureFile,
    SaveTarget,
    awrite_chunks,
    write_chunks,
)
from ._models import Capture, Catalog, Defaults, read_response
from ._params import CaptureFileOptions, CaptureOptions, S3DeliveryParam, SubmitOptions
from ._transport import AsyncTransport, SyncTransport

if TYPE_CHECKING:
    from typing_extensions import Unpack

__all__ = ["AsyncInstantSnap", "InstantSnap"]

# Statuses of a capture that has not finished yet; ``wait`` keeps reading while it has one.
_UNFINISHED = frozenset({"queued", "running", "pending"})
_DEFAULT_WAIT_TIMEOUT = 360.0
_DEFAULT_POLL_INTERVAL = 3.0


def _capture_id(capture: Capture | str) -> str:
    return capture if isinstance(capture, str) else capture.id


class InstantSnap:
    """The Instant Snap API: capture a page on demand. Reached as ``client.instant_snap``."""

    def __init__(self, config: ClientConfig, transport: SyncTransport) -> None:
        self._config = config
        self._transport = transport

    def capture(
        self,
        *,
        url: str,
        idempotency_key: str | None = None,
        timeout: float | None = None,
        **options: Unpack[CaptureOptions],
    ) -> Capture:
        """Capture ``url`` and return the capture, with a ``download_url`` valid for 60 minutes.

        Args:
            url: The page to capture: absolute http or https, without credentials.
            idempotency_key: Makes the call safe to repeat for 24 hours. A random key is used
                when this is left out, and retries of this call always reuse it.
            timeout: Seconds to wait for the capture, retries included. Defaults to the
                client's ``capture_timeout``.
            **options: Capture options, named as in the API; see :class:`CaptureOptions`.
        """
        request = _requests.capture(
            self._config,
            url=url,
            response_type="json",
            options=options,
            idempotency_key=idempotency_key,
            timeout=timeout,
        )
        return read_response(self._transport.send(request), Capture._from_wire)

    def capture_file(
        self,
        *,
        url: str,
        idempotency_key: str | None = None,
        timeout: float | None = None,
        **options: Unpack[CaptureFileOptions],
    ) -> CaptureFile:
        """Capture ``url`` and stream the file back in the answer; nothing is kept.

        Use the result in a ``with`` block so the connection is released::

            with client.instant_snap.capture_file(url="https://example.com") as file:
                file.save("example.png")

        Arguments are those of :meth:`capture`, without ``page_source``.
        """
        request = _requests.capture(
            self._config,
            url=url,
            response_type="by_format",
            options=options,
            idempotency_key=idempotency_key,
            timeout=timeout,
        )
        return CaptureFile(self._transport.send(request, stream=True))

    def capture_to_bucket(
        self,
        *,
        url: str,
        s3_delivery: S3DeliveryParam,
        idempotency_key: str | None = None,
        timeout: float | None = None,
        **options: Unpack[CaptureOptions],
    ) -> Capture:
        """Capture ``url`` and upload the file to your S3-compatible bucket.

        ``s3_delivery`` names the bucket and the credentials to write with; the returned
        capture's ``s3_delivery.status`` tells how the upload is going. Other arguments are
        those of :meth:`capture`.
        """
        request = _requests.capture(
            self._config,
            url=url,
            response_type="cloud_storage",
            options={**options, "s3_delivery": s3_delivery},
            idempotency_key=idempotency_key,
            timeout=timeout,
        )
        return read_response(self._transport.send(request), Capture._from_wire)

    def submit(
        self,
        *,
        url: str,
        idempotency_key: str | None = None,
        **options: Unpack[SubmitOptions],
    ) -> Capture:
        """Queue an async capture of ``url`` and return it at once, with status ``queued``.

        The capture runs when a browser is free; :meth:`wait` (or :meth:`get`, or the
        ``capture.succeeded``/``capture.failed`` webhook) tells you when it is done. A capture
        still queued 15 minutes after it was accepted ends ``failed`` with ``capture_expired``
        and is not charged.

        The call waits only for the answer, so it uses the client's ``timeout``, not
        ``capture_timeout``. Retries and the ``Idempotency-Key`` work as for :meth:`capture`.

        Args:
            url: The page to capture: absolute http or https, without credentials.
            idempotency_key: As for :meth:`capture`.
            **options: The options of :meth:`capture`, plus ``timeout``: the browser time the
                capture may use, 30 to 300 seconds (120 when left out); see
                :class:`SubmitOptions`.

        Raises:
            RateLimitError: ``queue_full`` when the organization already has as many async
                captures waiting or running as it may. Not retried; wait
                ``retry_after_seconds`` and submit again.
        """
        request = _requests.capture(
            self._config,
            url=url,
            response_type="json",
            options=options,
            idempotency_key=idempotency_key,
            timeout=None,
            is_async=True,
        )
        return read_response(self._transport.send(request), Capture._from_wire)

    def submit_to_bucket(
        self,
        *,
        url: str,
        s3_delivery: S3DeliveryParam,
        idempotency_key: str | None = None,
        **options: Unpack[SubmitOptions],
    ) -> Capture:
        """Queue an async capture of ``url`` into your bucket; returns it at once, ``queued``.

        ``s3_delivery`` is as for :meth:`capture_to_bucket`; other arguments are those of
        :meth:`submit`.
        """
        request = _requests.capture(
            self._config,
            url=url,
            response_type="cloud_storage",
            options={**options, "s3_delivery": s3_delivery},
            idempotency_key=idempotency_key,
            timeout=None,
            is_async=True,
        )
        return read_response(self._transport.send(request), Capture._from_wire)

    def wait(
        self,
        capture: Capture | str,
        *,
        timeout_seconds: float = _DEFAULT_WAIT_TIMEOUT,
        poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL,
    ) -> Capture:
        """Read a capture with :meth:`get` until it has finished, and return it.

        It is finished once its status is no longer ``queued``, ``running`` or ``pending``.
        When ``timeout_seconds`` runs out first, the capture is returned as last read, still
        unfinished, rather than raising, so you can decide whether to wait again. A refusal
        from :meth:`get` is raised unchanged.

        Args:
            capture: The capture, or its id, as :meth:`submit` returned it.
            timeout_seconds: How long to keep reading. Default 360.
            poll_interval_seconds: Seconds between reads. Default 3; ``0`` does not sleep.
        """
        capture_id = _capture_id(capture)
        deadline = time.monotonic() + timeout_seconds
        while True:
            current = self.get(capture_id)
            remaining = deadline - time.monotonic()
            if current.status not in _UNFINISHED or remaining <= 0:
                return current
            if poll_interval_seconds > 0:
                time.sleep(min(poll_interval_seconds, remaining))

    def get(self, capture_id: str) -> Capture:
        """Read a capture back. This also issues a fresh ``download_url``."""
        request = _requests.get_capture(self._config, capture_id)
        return read_response(self._transport.send(request), Capture._from_wire)

    def download(
        self, capture: Capture, target: SaveTarget, *, timeout: float | None = None
    ) -> None:
        """Stream a capture's file from its ``download_url`` to a path or binary stream.

        The link lasts 60 minutes; call :meth:`get` for a fresh one.

        Raises:
            ValueError: The capture has no ``download_url``.
        """
        request = _requests.download(self._config, capture, timeout)
        with closing(self._transport.send(request, stream=True)) as response:
            write_chunks(target, response.iter_bytes())

    def defaults(self) -> Defaults:
        """The values a capture takes for options it leaves out, and its limits. No key needed."""
        request = _requests.defaults(self._config)
        return read_response(self._transport.send(request), Defaults._from_wire)

    def catalog(self) -> Catalog:
        """The devices ``emulated_device`` accepts and the countries ``proxy`` accepts."""
        request = _requests.catalog(self._config)
        return read_response(self._transport.send(request), Catalog._from_wire)


class AsyncInstantSnap:
    """The Instant Snap API for asyncio. Reached as ``client.instant_snap``."""

    def __init__(self, config: ClientConfig, transport: AsyncTransport) -> None:
        self._config = config
        self._transport = transport

    async def capture(
        self,
        *,
        url: str,
        idempotency_key: str | None = None,
        timeout: float | None = None,
        **options: Unpack[CaptureOptions],
    ) -> Capture:
        """Capture ``url`` and return the capture. See :meth:`InstantSnap.capture`."""
        request = _requests.capture(
            self._config,
            url=url,
            response_type="json",
            options=options,
            idempotency_key=idempotency_key,
            timeout=timeout,
        )
        return read_response(await self._transport.send(request), Capture._from_wire)

    def capture_file(
        self,
        *,
        url: str,
        idempotency_key: str | None = None,
        timeout: float | None = None,
        **options: Unpack[CaptureFileOptions],
    ) -> AsyncCaptureFileContext:
        """Capture ``url`` and stream the file back. See :meth:`InstantSnap.capture_file`.

        Use it with ``async with`` so the connection is released::

            async with client.instant_snap.capture_file(url="https://example.com") as file:
                await file.save("example.png")
        """
        request = _requests.capture(
            self._config,
            url=url,
            response_type="by_format",
            options=options,
            idempotency_key=idempotency_key,
            timeout=timeout,
        )

        async def open_file() -> AsyncCaptureFile:
            return AsyncCaptureFile(await self._transport.send(request, stream=True))

        return AsyncCaptureFileContext(open_file())

    async def capture_to_bucket(
        self,
        *,
        url: str,
        s3_delivery: S3DeliveryParam,
        idempotency_key: str | None = None,
        timeout: float | None = None,
        **options: Unpack[CaptureOptions],
    ) -> Capture:
        """Capture ``url`` into your bucket. See :meth:`InstantSnap.capture_to_bucket`."""
        request = _requests.capture(
            self._config,
            url=url,
            response_type="cloud_storage",
            options={**options, "s3_delivery": s3_delivery},
            idempotency_key=idempotency_key,
            timeout=timeout,
        )
        return read_response(await self._transport.send(request), Capture._from_wire)

    async def submit(
        self,
        *,
        url: str,
        idempotency_key: str | None = None,
        **options: Unpack[SubmitOptions],
    ) -> Capture:
        """Queue an async capture and return it at once. See :meth:`InstantSnap.submit`."""
        request = _requests.capture(
            self._config,
            url=url,
            response_type="json",
            options=options,
            idempotency_key=idempotency_key,
            timeout=None,
            is_async=True,
        )
        return read_response(await self._transport.send(request), Capture._from_wire)

    async def submit_to_bucket(
        self,
        *,
        url: str,
        s3_delivery: S3DeliveryParam,
        idempotency_key: str | None = None,
        **options: Unpack[SubmitOptions],
    ) -> Capture:
        """Queue an async capture into your bucket. See :meth:`InstantSnap.submit_to_bucket`."""
        request = _requests.capture(
            self._config,
            url=url,
            response_type="cloud_storage",
            options={**options, "s3_delivery": s3_delivery},
            idempotency_key=idempotency_key,
            timeout=None,
            is_async=True,
        )
        return read_response(await self._transport.send(request), Capture._from_wire)

    async def wait(
        self,
        capture: Capture | str,
        *,
        timeout_seconds: float = _DEFAULT_WAIT_TIMEOUT,
        poll_interval_seconds: float = _DEFAULT_POLL_INTERVAL,
    ) -> Capture:
        """Read a capture until it has finished, and return it. See :meth:`InstantSnap.wait`.

        Cancelling the task (or ``asyncio.timeout()``) stops it at once.
        """
        capture_id = _capture_id(capture)
        deadline = time.monotonic() + timeout_seconds
        while True:
            current = await self.get(capture_id)
            remaining = deadline - time.monotonic()
            if current.status not in _UNFINISHED or remaining <= 0:
                return current
            if poll_interval_seconds > 0:
                await asyncio.sleep(min(poll_interval_seconds, remaining))

    async def get(self, capture_id: str) -> Capture:
        """Read a capture back. This also issues a fresh ``download_url``."""
        request = _requests.get_capture(self._config, capture_id)
        return read_response(await self._transport.send(request), Capture._from_wire)

    async def download(
        self, capture: Capture, target: SaveTarget, *, timeout: float | None = None
    ) -> None:
        """Stream a capture's file to a path or binary stream. See :meth:`InstantSnap.download`."""
        request = _requests.download(self._config, capture, timeout)
        response = await self._transport.send(request, stream=True)
        try:
            await awrite_chunks(target, response.aiter_bytes())
        finally:
            await response.aclose()

    async def defaults(self) -> Defaults:
        """The values a capture takes for options it leaves out, and its limits. No key needed."""
        request = _requests.defaults(self._config)
        return read_response(await self._transport.send(request), Defaults._from_wire)

    async def catalog(self) -> Catalog:
        """The devices ``emulated_device`` accepts and the countries ``proxy`` accepts."""
        request = _requests.catalog(self._config)
        return read_response(await self._transport.send(request), Catalog._from_wire)
