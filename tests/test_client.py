from __future__ import annotations

import asyncio
import io
import json
import re
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx
import pytest

from websitescreenshotworld import (
    APIConnectionError,
    APITimeoutError,
    AsyncWebsiteScreenshotWorld,
    AuthenticationError,
    Capture,
    CaptureError,
    CaptureStatus,
    RateLimitError,
    S3DeliveryParam,
    WebsiteScreenshotWorld,
    WebsiteScreenshotWorldError,
)
from websitescreenshotworld._config import USER_AGENT
from websitescreenshotworld._errors import error_from_response
from websitescreenshotworld._transport import retry_delay

CAPTURE: dict[str, Any] = {
    "success": True,
    "id": "3f6c2a1e-9b8d-4c7e-a5f4-1d2e3c4b5a69",
    "status": "succeeded",
    "response_type": "json",
    "media_category": "image",
    "format": "png",
    "content_type": "image/png",
    "size_bytes": 5,
    "width": 1920,
    "height": 1080,
    "duration_ms": 4210,
    "page_http_status": 200,
    "captured_at": "2026-09-26T10:30:04.512Z",
    "final_url": None,
    "media_sha256": None,
    "download_url": "https://media.example.com/f.png?e=1&s=secret",
    "expires_at": "2026-09-27T10:30:04.512Z",
    "page_source": None,
    "s3_delivery": None,
    "callback_url": None,
    "error_code": None,
    "spec_version": "v1",
    "added_later": {"ignored": True},
}

Handler = Callable[[httpx.Request], httpx.Response]


class Recorder:
    """An httpx transport that answers from a handler and remembers each request."""

    def __init__(self, handler: Handler) -> None:
        self.requests: list[httpx.Request] = []
        self._handler = handler

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self._handler(request)

    def client(self, **settings: Any) -> WebsiteScreenshotWorld:
        http = httpx.Client(transport=httpx.MockTransport(self))
        return WebsiteScreenshotWorld(http_client=http, **settings)

    def async_client(self, **settings: Any) -> AsyncWebsiteScreenshotWorld:
        http = httpx.AsyncClient(transport=httpx.MockTransport(self))
        return AsyncWebsiteScreenshotWorld(http_client=http, **settings)


def answer(body: Any, status: int = 200, headers: dict[str, str] | None = None) -> Handler:
    return lambda request: httpx.Response(status, json=body, headers=headers)


@pytest.fixture(autouse=True)
def no_keys_in_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WSW_INSTANT_SNAP_API_KEY", raising=False)
    monkeypatch.delenv("WSW_AUTO_SCHEDULE_API_KEY", raising=False)


@pytest.fixture
def no_sleep(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    waits: list[float] = []
    monkeypatch.setattr(time, "sleep", waits.append)
    return waits


def test_missing_instant_snap_key_fails_before_sending() -> None:
    recorder = Recorder(answer(CAPTURE))
    client = recorder.client(auto_schedule_api_key="as-key")
    with pytest.raises(AuthenticationError, match="WSW_INSTANT_SNAP_API_KEY"):
        client.instant_snap.capture(url="https://example.com")
    with pytest.raises(AuthenticationError, match="instant_snap_api_key"):
        client.instant_snap.get("id")
    with pytest.raises(AuthenticationError):
        client.instant_snap.capture_file(url="https://example.com")
    assert recorder.requests == []


def test_missing_auto_schedule_key_fails_before_sending() -> None:
    recorder = Recorder(answer({}))
    client = recorder.client(instant_snap_api_key="is-key")
    with pytest.raises(AuthenticationError, match="WSW_AUTO_SCHEDULE_API_KEY"):
        client.auto_schedule.trigger_now("7d4e2b1a-6c5f-4a3e-9d8c-2b1a0f9e8d7c")
    assert recorder.requests == []


def test_missing_key_fails_before_sending_async() -> None:
    recorder = Recorder(answer(CAPTURE))

    async def run() -> None:
        async with recorder.async_client() as client:
            with pytest.raises(AuthenticationError):
                await client.instant_snap.capture(url="https://example.com")
            with pytest.raises(AuthenticationError):
                client.instant_snap.capture_file(url="https://example.com")
            with pytest.raises(AuthenticationError):
                await client.auto_schedule.trigger_now("id")

    asyncio.run(run())
    assert recorder.requests == []


def test_defaults_need_no_key() -> None:
    recorder = Recorder(answer({"success": True, "spec_version": "v1"}))
    defaults = recorder.client().instant_snap.defaults()
    assert defaults.spec_version == "v1"
    assert "X-Api-Key" not in recorder.requests[0].headers


def test_keys_default_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WSW_INSTANT_SNAP_API_KEY", "from-env")
    recorder = Recorder(answer(CAPTURE))
    recorder.client().instant_snap.get(CAPTURE["id"])
    assert recorder.requests[0].headers["X-Api-Key"] == "from-env"


def test_keys_are_not_in_the_repr() -> None:
    client = WebsiteScreenshotWorld(instant_snap_api_key="secret-key")
    assert "secret-key" not in repr(vars(client.instant_snap))


def test_user_agent_names_the_library_and_runtime() -> None:
    assert re.fullmatch(
        r"websitescreenshotworld-python/0\.1\.0 \(\w+ \d+\.\d+\.\d+\S*\)", USER_AGENT
    )
    recorder = Recorder(answer(CAPTURE))
    recorder.client(instant_snap_api_key="k").instant_snap.get(CAPTURE["id"])
    request = recorder.requests[0]
    assert request.headers["User-Agent"] == USER_AGENT
    assert request.headers["Accept"] == "application/json"


def test_options_left_out_or_none_are_not_sent_but_false_zero_and_empty_are() -> None:
    recorder = Recorder(answer(CAPTURE))
    recorder.client(instant_snap_api_key="k").instant_snap.capture(
        url="https://example.com",
        block_ads=False,
        scrolling_delay_ms=0,
        user_agent="",
        locale=None,  # type: ignore[arg-type]
        headers={"sessionId": "abc"},
    )
    body = json.loads(recorder.requests[0].content)
    assert body == {
        "url": "https://example.com",
        "block_ads": False,
        "scrolling_delay_ms": 0,
        "user_agent": "",
        "headers": {"sessionId": "abc"},
        "response_type": "json",
    }


def test_each_capture_gets_its_own_idempotency_key() -> None:
    recorder = Recorder(answer(CAPTURE))
    client = recorder.client(instant_snap_api_key="k")
    client.instant_snap.capture(url="https://example.com")
    client.instant_snap.capture(url="https://example.com")
    first, second = (request.headers["Idempotency-Key"] for request in recorder.requests)
    assert first != second


def test_capture_result_is_typed_and_ignores_unknown_fields() -> None:
    recorder = Recorder(answer(CAPTURE))
    capture = recorder.client(instant_snap_api_key="k").instant_snap.get(CAPTURE["id"])
    assert capture.status == CaptureStatus.SUCCEEDED
    assert capture.captured_at is not None
    assert capture.captured_at.isoformat() == "2026-09-26T10:30:04.512000+00:00"
    assert "success" not in capture.raw
    assert capture.raw["added_later"] == {"ignored": True}


def test_download_writes_to_a_path_without_the_api_key(tmp_path: Path) -> None:
    recorder = Recorder(lambda request: httpx.Response(200, content=b"image"))
    client = recorder.client(instant_snap_api_key="k")
    capture = Capture._from_wire(CAPTURE)
    target = tmp_path / "page.png"
    client.instant_snap.download(capture, target)
    assert target.read_bytes() == b"image"
    request = recorder.requests[0]
    assert str(request.url) == CAPTURE["download_url"]
    assert "X-Api-Key" not in request.headers
    assert request.headers["Accept"] == "*/*"


def test_download_writes_to_a_stream() -> None:
    recorder = Recorder(lambda request: httpx.Response(200, content=b"image"))
    stream = io.BytesIO()
    recorder.client().instant_snap.download(Capture._from_wire(CAPTURE), stream)
    assert stream.getvalue() == b"image"


def test_download_async(tmp_path: Path) -> None:
    recorder = Recorder(lambda request: httpx.Response(200, content=b"image"))
    target = tmp_path / "page.png"

    async def run() -> None:
        async with recorder.async_client() as client:
            await client.instant_snap.download(Capture._from_wire(CAPTURE), str(target))

    asyncio.run(run())
    assert target.read_bytes() == b"image"


def test_download_needs_a_download_url() -> None:
    capture = Capture._from_wire({**CAPTURE, "download_url": None})
    with pytest.raises(ValueError, match="download_url"):
        WebsiteScreenshotWorld().instant_snap.download(capture, io.BytesIO())


def test_download_errors_do_not_show_the_signed_query(no_sleep: list[float]) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    recorder = Recorder(refuse)
    with pytest.raises(APIConnectionError) as info:
        recorder.client().instant_snap.download(Capture._from_wire(CAPTURE), io.BytesIO())
    assert "secret" not in str(info.value)


def test_capture_file_streams_to_a_path(tmp_path: Path) -> None:
    headers = {
        "Content-Type": "image/png",
        "Content-Disposition": "attachment; filename*=UTF-8''caf%C3%A9.png",
        "X-InstantSnap-Id": "abc",
        "X-InstantSnap-Width": "1440",
        "X-InstantSnap-Captured-At": "2026-09-26T10:30:04.512Z",
    }
    recorder = Recorder(lambda request: httpx.Response(200, content=b"png-bytes", headers=headers))
    client = recorder.client(instant_snap_api_key="k")
    with client.instant_snap.capture_file(url="https://example.com") as file:
        assert file.filename == "café.png"
        assert file.width == 1440
        assert file.height is None
        assert file.captured_at is not None
        file.save(tmp_path / "out.png")
    assert (tmp_path / "out.png").read_bytes() == b"png-bytes"
    assert recorder.requests[0].headers["Accept"] == "*/*"


def test_capture_file_async_can_be_awaited() -> None:
    recorder = Recorder(lambda request: httpx.Response(200, content=b"abc"))

    async def run() -> bytes:
        async with recorder.async_client(instant_snap_api_key="k") as client:
            file = await client.instant_snap.capture_file(url="https://example.com")
            try:
                return b"".join([chunk async for chunk in file.iter_bytes()])
            finally:
                await file.close()

    assert asyncio.run(run()) == b"abc"


def test_connection_failures_are_retried(no_sleep: list[float]) -> None:
    def refuse(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    recorder = Recorder(refuse)
    with pytest.raises(APIConnectionError):
        recorder.client(instant_snap_api_key="k").instant_snap.capture(url="https://example.com")
    assert len(recorder.requests) == 3
    assert len({request.headers["Idempotency-Key"] for request in recorder.requests}) == 1
    assert 0.5 <= no_sleep[0] <= 0.625
    assert 1.0 <= no_sleep[1] <= 1.25


def test_timeouts_are_not_retried(no_sleep: list[float]) -> None:
    def too_slow(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    recorder = Recorder(too_slow)
    with pytest.raises(APITimeoutError):
        recorder.client(instant_snap_api_key="k").instant_snap.capture(
            url="https://example.com", timeout=5
        )
    assert len(recorder.requests) == 1


def test_retries_stop_when_the_wait_would_pass_the_deadline(no_sleep: list[float]) -> None:
    refusal = {"success": False, "error_code": "rate_limited", "error_message": "Slow down."}
    recorder = Recorder(answer({**refusal, "retry_after_seconds": 30}, status=429))
    with pytest.raises(RateLimitError):
        recorder.client(instant_snap_api_key="k").instant_snap.capture(
            url="https://example.com", timeout=10
        )
    assert len(recorder.requests) == 1
    assert no_sleep == []


def test_max_retries_zero_disables_retries(no_sleep: list[float]) -> None:
    recorder = Recorder(lambda request: httpx.Response(503, text="busy"))
    with pytest.raises(WebsiteScreenshotWorldError):
        recorder.client(instant_snap_api_key="k", max_retries=0).instant_snap.catalog()
    assert len(recorder.requests) == 1


def test_user_http_client_is_left_open() -> None:
    http = httpx.Client(transport=httpx.MockTransport(answer(CAPTURE)))
    with WebsiteScreenshotWorld(http_client=http):
        pass
    assert not http.is_closed
    http.close()


def test_retry_after_header_is_used_when_the_body_has_no_hint() -> None:
    response = httpx.Response(429, text="Too many", headers={"Retry-After": "7"})
    error = error_from_response(response)
    assert isinstance(error, RateLimitError)
    assert error.retry_after_seconds == 7
    assert error.body == "Too many"


def test_retry_waits() -> None:
    def refusal(code: str, hint: int | None) -> WebsiteScreenshotWorldError:
        return WebsiteScreenshotWorldError("x", error_code=code, retry_after_seconds=hint)

    assert retry_delay(refusal("rate_limited", 5), 0) == 5
    assert retry_delay(refusal("capture_busy", 600), 0) == 60
    assert retry_delay(refusal("capture_failed", None), 0) is None
    assert retry_delay(refusal("something_new", 1), 0) is None
    first = retry_delay(refusal("service_unavailable", None), 0)
    second = retry_delay(refusal("service_unavailable", None), 1)
    assert first is not None
    assert 0.5 <= first <= 0.625
    assert second is not None
    assert 1.0 <= second <= 1.25
    assert retry_delay(APITimeoutError("x"), 0) is None


def test_error_string_carries_the_code() -> None:
    error = error_from_response(
        httpx.Response(
            402,
            json={
                "success": False,
                "error_code": "quota_exhausted",
                "error_message": "No captures are left this month.",
                "retry_after_seconds": None,
            },
        )
    )
    assert str(error) == "[quota_exhausted] No captures are left this month."


QUEUED: dict[str, Any] = {
    **CAPTURE,
    "status": "queued",
    "media_category": None,
    "format": None,
    "download_url": None,
}


@pytest.fixture
def fake_clock(monkeypatch: pytest.MonkeyPatch) -> list[float]:
    """A clock that moves only when the code sleeps; returns the sleeps."""
    now = [1000.0]
    waits: list[float] = []

    def sleep(seconds: float) -> None:
        waits.append(seconds)
        now[0] += seconds

    async def async_sleep(seconds: float) -> None:
        sleep(seconds)

    monkeypatch.setattr(time, "monotonic", lambda: now[0])
    monkeypatch.setattr(time, "sleep", sleep)
    monkeypatch.setattr(asyncio, "sleep", async_sleep)
    return waits


def test_submit_sends_async_and_waits_only_the_ordinary_timeout() -> None:
    recorder = Recorder(answer(QUEUED, status=202, headers={"Location": "/x"}))
    client = recorder.client(instant_snap_api_key="k", timeout=30, capture_timeout=180)
    capture = client.instant_snap.submit(url="https://example.com", timeout=240)
    assert capture.status == CaptureStatus.QUEUED
    assert capture.media_category is None
    request = recorder.requests[0]
    assert json.loads(request.content) == {
        "url": "https://example.com",
        "timeout": 240,
        "response_type": "json",
        "async": True,
    }
    assert request.headers["Idempotency-Key"]
    assert 0 < request.extensions["timeout"]["read"] <= 30


def test_submit_to_bucket_sends_async_and_cloud_storage() -> None:
    recorder = Recorder(answer({**QUEUED, "response_type": "cloud_storage"}, status=202))
    bucket: S3DeliveryParam = {
        "access_key_id": "a",
        "secret_access_key": "s",
        "bucket": "b",
        "region": "r",
    }

    async def run() -> Capture:
        async with recorder.async_client(instant_snap_api_key="k") as client:
            return await client.instant_snap.submit_to_bucket(
                url="https://example.com", s3_delivery=bucket
            )

    assert asyncio.run(run()).status == CaptureStatus.QUEUED
    body = json.loads(recorder.requests[0].content)
    assert body == {
        "url": "https://example.com",
        "s3_delivery": bucket,
        "response_type": "cloud_storage",
        "async": True,
    }


def test_queue_full_is_a_rate_limit_error_and_not_retried(no_sleep: list[float]) -> None:
    refusal = {
        "success": False,
        "error_code": "queue_full",
        "error_message": "Too many async captures are waiting.",
        "retry_after_seconds": 30,
    }
    recorder = Recorder(answer(refusal, status=429))
    with pytest.raises(RateLimitError) as info:
        recorder.client(instant_snap_api_key="k").instant_snap.submit(url="https://example.com")
    assert info.value.error_code == "queue_full"
    assert info.value.retry_after_seconds == 30
    assert len(recorder.requests) == 1
    assert no_sleep == []


def test_capture_expired_is_a_capture_error() -> None:
    error = error_from_response(
        httpx.Response(410, json={"success": False, "error_code": "capture_expired"})
    )
    assert isinstance(error, CaptureError)


def test_wait_returns_the_capture_once_it_has_finished(fake_clock: list[float]) -> None:
    answers = iter([QUEUED, {**QUEUED, "status": "running"}, CAPTURE])
    recorder = Recorder(lambda request: httpx.Response(200, json=next(answers)))
    snap = recorder.client(instant_snap_api_key="k").instant_snap
    capture = snap.wait(Capture._from_wire(QUEUED))
    assert capture.status == CaptureStatus.SUCCEEDED
    assert len(recorder.requests) == 3
    assert recorder.requests[0].url.path.endswith("/captures/" + CAPTURE["id"])
    assert fake_clock == [3, 3]


def test_wait_returns_the_last_capture_when_time_runs_out(fake_clock: list[float]) -> None:
    recorder = Recorder(answer(QUEUED))
    snap = recorder.client(instant_snap_api_key="k").instant_snap
    capture = snap.wait(CAPTURE["id"], timeout_seconds=7, poll_interval_seconds=3)
    assert capture.status == CaptureStatus.QUEUED
    assert len(recorder.requests) == 4
    assert fake_clock == [3, 3, 1]


def test_wait_async_returns_the_last_capture_when_time_runs_out(fake_clock: list[float]) -> None:
    recorder = Recorder(answer({**QUEUED, "status": "running"}))

    async def run() -> Capture:
        async with recorder.async_client(instant_snap_api_key="k") as client:
            return await client.instant_snap.wait(CAPTURE["id"], timeout_seconds=0)

    assert asyncio.run(run()).status == CaptureStatus.RUNNING
    assert len(recorder.requests) == 1
    assert fake_clock == []


def test_wait_raises_what_get_raises(fake_clock: list[float]) -> None:
    refusal = {"success": False, "error_code": "capture_not_found", "error_message": "No."}
    recorder = Recorder(answer(refusal, status=404))
    with pytest.raises(WebsiteScreenshotWorldError) as info:
        recorder.client(instant_snap_api_key="k").instant_snap.wait("missing")
    assert info.value.error_code == "capture_not_found"
    assert len(recorder.requests) == 1
