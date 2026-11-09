"""Sending requests, with the retry rules every client library shares."""

from __future__ import annotations

import asyncio
import random
import time
from dataclasses import dataclass

import httpx

from ._errors import (
    RETRYABLE_CODES,
    APIConnectionError,
    APITimeoutError,
    WebsiteScreenshotWorldError,
    error_from_response,
)

_MAX_RETRY_AFTER = 60.0
_BACKOFF = (0.5, 1.0)
_JITTER = 0.25


@dataclass(frozen=True)
class Request:
    """One API call. Its retries reuse it unchanged, including the Idempotency-Key."""

    method: str
    url: str
    headers: dict[str, str]
    timeout: float
    """Seconds for the whole call; retries stop once it has passed."""
    content: bytes | None = None
    follow_redirects: bool = False


def retry_delay(error: WebsiteScreenshotWorldError, attempt: int) -> float | None:
    """Seconds to wait before retrying after ``error``, or ``None`` when it is final."""
    if isinstance(error, APITimeoutError):
        return None
    if isinstance(error, APIConnectionError):
        hint = None
    elif error.error_code in RETRYABLE_CODES:
        hint = error.retry_after_seconds
    else:
        return None
    if hint is not None:
        return min(float(hint), _MAX_RETRY_AFTER)
    base = _BACKOFF[min(attempt, len(_BACKOFF) - 1)]
    return base + random.uniform(0, base * _JITTER)


def _next_delay(
    error: WebsiteScreenshotWorldError, attempt: int, max_retries: int, deadline: float
) -> float | None:
    if attempt >= max_retries:
        return None
    delay = retry_delay(error, attempt)
    if delay is None or time.monotonic() + delay >= deadline:
        return None
    return delay


def _remaining(request: Request, deadline: float) -> float:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise _timeout_error(request)
    return remaining


def _describe(request: Request) -> str:
    # Leave the query out: a download URL carries its signature there.
    return f"{request.method} {httpx.URL(request.url).copy_with(query=None, fragment=None)}"


def _timeout_error(request: Request) -> APITimeoutError:
    return APITimeoutError(f"No answer to {_describe(request)} within {request.timeout:g} s.")


def _transport_error(request: Request, exc: httpx.TransportError) -> APIConnectionError:
    if isinstance(exc, httpx.TimeoutException):
        return _timeout_error(request)
    return APIConnectionError(f"{_describe(request)} failed: {exc}")


class SyncTransport:
    def __init__(self, http_client: httpx.Client | None, max_retries: int) -> None:
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.Client()
        self._max_retries = max_retries

    def close(self) -> None:
        if self._owns_client:
            self._http.close()

    def send(self, request: Request, *, stream: bool = False) -> httpx.Response:
        """Send with retries. With ``stream``, a successful body is left unread for the caller."""
        deadline = time.monotonic() + request.timeout
        attempt = 0
        while True:
            try:
                return self._send_once(request, deadline, stream)
            except WebsiteScreenshotWorldError as error:
                delay = _next_delay(error, attempt, self._max_retries, deadline)
                if delay is None:
                    raise
            time.sleep(delay)
            attempt += 1

    def _send_once(self, request: Request, deadline: float, stream: bool) -> httpx.Response:
        http_request = self._http.build_request(
            request.method,
            request.url,
            headers=request.headers,
            content=request.content,
            timeout=_remaining(request, deadline),
        )
        try:
            response = self._http.send(
                http_request, stream=True, follow_redirects=request.follow_redirects
            )
        except httpx.TransportError as exc:
            raise _transport_error(request, exc) from exc
        if response.is_success and stream:
            return response
        try:
            response.read()
        except httpx.TransportError as exc:
            raise _transport_error(request, exc) from exc
        finally:
            response.close()
        if response.is_success:
            return response
        raise error_from_response(response)


class AsyncTransport:
    def __init__(self, http_client: httpx.AsyncClient | None, max_retries: int) -> None:
        self._owns_client = http_client is None
        self._http = http_client if http_client is not None else httpx.AsyncClient()
        self._max_retries = max_retries

    async def close(self) -> None:
        if self._owns_client:
            await self._http.aclose()

    async def send(self, request: Request, *, stream: bool = False) -> httpx.Response:
        """Send with retries. With ``stream``, a successful body is left unread for the caller."""
        deadline = time.monotonic() + request.timeout
        attempt = 0
        while True:
            try:
                return await self._send_once(request, deadline, stream)
            except WebsiteScreenshotWorldError as error:
                delay = _next_delay(error, attempt, self._max_retries, deadline)
                if delay is None:
                    raise
            await asyncio.sleep(delay)
            attempt += 1

    async def _send_once(self, request: Request, deadline: float, stream: bool) -> httpx.Response:
        http_request = self._http.build_request(
            request.method,
            request.url,
            headers=request.headers,
            content=request.content,
            timeout=_remaining(request, deadline),
        )
        try:
            response = await self._http.send(
                http_request, stream=True, follow_redirects=request.follow_redirects
            )
        except httpx.TransportError as exc:
            raise _transport_error(request, exc) from exc
        if response.is_success and stream:
            return response
        try:
            await response.aread()
        except httpx.TransportError as exc:
            raise _transport_error(request, exc) from exc
        finally:
            await response.aclose()
        if response.is_success:
            return response
        raise error_from_response(response)
