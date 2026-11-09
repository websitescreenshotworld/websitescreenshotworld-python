"""Captured files streamed straight from the response."""

from __future__ import annotations

import os
from collections.abc import AsyncIterable, AsyncIterator, Coroutine, Generator, Iterable, Iterator
from datetime import datetime
from email.message import Message
from types import TracebackType
from typing import Any, Protocol

import httpx

from ._dates import parse_optional_datetime

__all__ = ["AsyncCaptureFile", "AsyncCaptureFileContext", "CaptureFile", "SaveTarget"]


class _Writable(Protocol):
    def write(self, data: bytes, /) -> object: ...


SaveTarget = str | os.PathLike[str] | _Writable
"""A file path, or a binary stream opened for writing."""


def write_chunks(target: SaveTarget, chunks: Iterable[bytes]) -> None:
    if isinstance(target, (str, os.PathLike)):
        with open(target, "wb") as file:
            for chunk in chunks:
                file.write(chunk)
    else:
        for chunk in chunks:
            target.write(chunk)


async def awrite_chunks(target: SaveTarget, chunks: AsyncIterable[bytes]) -> None:
    if isinstance(target, (str, os.PathLike)):
        with open(target, "wb") as file:
            async for chunk in chunks:
                file.write(chunk)
    else:
        async for chunk in chunks:
            target.write(chunk)


def _int_header(headers: httpx.Headers, name: str) -> int | None:
    value = headers.get(name)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _filename(headers: httpx.Headers) -> str | None:
    disposition = headers.get("Content-Disposition")
    if disposition is None:
        return None
    # email.message understands both filename="..." and the RFC 2231 filename*=UTF-8''... form.
    message = Message()
    message["Content-Disposition"] = disposition
    return message.get_filename()


class _CaptureFileMetadata:
    id: str | None
    """The capture id."""
    status: str | None
    """``delivered``: the file came back in the answer and is not kept."""
    content_type: str | None
    filename: str | None
    """The file name the API suggests, from ``Content-Disposition``."""
    width: int | None
    height: int | None
    size_bytes: int | None
    duration_ms: int | None
    """How long the capture took."""
    page_http_status: int | None
    """The status the website answered with."""
    spec_version: str | None
    captured_at: datetime | None
    final_url: str | None
    """Where the browser ended up; ``None`` when that URL is not plain ASCII."""
    sha256: str | None
    """Lowercase hex digest of the file."""
    part_count: int | None
    """Set only when the answer has more than one part."""
    headers: httpx.Headers
    """Every response header, including the ``X-InstantSnap-*`` ones."""

    def __init__(self, response: httpx.Response) -> None:
        headers = response.headers
        self.id = headers.get("X-InstantSnap-Id")
        self.status = headers.get("X-InstantSnap-Status")
        self.content_type = headers.get("Content-Type")
        self.filename = _filename(headers)
        self.width = _int_header(headers, "X-InstantSnap-Width")
        self.height = _int_header(headers, "X-InstantSnap-Height")
        self.size_bytes = _int_header(headers, "X-InstantSnap-Size-Bytes")
        self.duration_ms = _int_header(headers, "X-InstantSnap-Duration-Ms")
        self.page_http_status = _int_header(headers, "X-InstantSnap-Page-Http-Status")
        self.spec_version = headers.get("X-InstantSnap-Spec-Version")
        self.captured_at = parse_optional_datetime(headers.get("X-InstantSnap-Captured-At"))
        self.final_url = headers.get("X-InstantSnap-Final-Url")
        self.sha256 = headers.get("X-InstantSnap-Sha256")
        self.part_count = _int_header(headers, "X-InstantSnap-Part-Count")
        self.headers = headers

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(id={self.id!r}, filename={self.filename!r}, "
            f"content_type={self.content_type!r}, size_bytes={self.size_bytes!r})"
        )


class CaptureFile(_CaptureFileMetadata):
    """A file returned by ``capture_file``, with its metadata as attributes.

    The body is streamed from the open connection and can be read once: call :meth:`save`,
    :meth:`read` or :meth:`iter_bytes`. Use it in a ``with`` block, or call :meth:`close`, to
    release the connection.
    """

    def __init__(self, response: httpx.Response) -> None:
        super().__init__(response)
        self._response = response

    def iter_bytes(self, chunk_size: int | None = None) -> Iterator[bytes]:
        """Yield the file in chunks as it arrives."""
        return self._response.iter_bytes(chunk_size)

    def read(self) -> bytes:
        """Read the whole file into memory."""
        return self._response.read()

    def save(self, target: SaveTarget) -> None:
        """Stream the file to a path, or to a binary stream opened for writing."""
        write_chunks(target, self.iter_bytes())

    def close(self) -> None:
        """Release the connection. Safe to call more than once."""
        self._response.close()

    def __enter__(self) -> CaptureFile:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.close()


class AsyncCaptureFile(_CaptureFileMetadata):
    """The async counterpart of :class:`CaptureFile`."""

    def __init__(self, response: httpx.Response) -> None:
        super().__init__(response)
        self._response = response

    def iter_bytes(self, chunk_size: int | None = None) -> AsyncIterator[bytes]:
        """Yield the file in chunks as it arrives."""
        return self._response.aiter_bytes(chunk_size)

    async def read(self) -> bytes:
        """Read the whole file into memory."""
        return await self._response.aread()

    async def save(self, target: SaveTarget) -> None:
        """Stream the file to a path, or to a binary stream opened for writing."""
        await awrite_chunks(target, self.iter_bytes())

    async def close(self) -> None:
        """Release the connection. Safe to call more than once."""
        await self._response.aclose()

    async def __aenter__(self) -> AsyncCaptureFile:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()


class AsyncCaptureFileContext:
    """What async ``capture_file`` returns: use it with ``async with``, or ``await`` it.

    ``async with`` closes the file on the way out; after ``await``, close it yourself.
    """

    def __init__(self, opening: Coroutine[Any, Any, AsyncCaptureFile]) -> None:
        self._opening = opening
        self._file: AsyncCaptureFile | None = None

    def __await__(self) -> Generator[Any, None, AsyncCaptureFile]:
        return self._opening.__await__()

    async def __aenter__(self) -> AsyncCaptureFile:
        self._file = await self._opening
        return self._file

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._file is not None:
            await self._file.close()
