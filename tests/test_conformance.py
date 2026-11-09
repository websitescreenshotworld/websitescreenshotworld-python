"""Every case in spec/fixtures, played back by conformance/server.js, with both clients."""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Mapping
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import pytest
from support import SPEC, load_json

from websitescreenshotworld import (
    AsyncWebsiteScreenshotWorld,
    AuthenticationError,
    CaptureError,
    InvalidRequestError,
    NotFoundError,
    PlanLimitError,
    RateLimitError,
    ServiceError,
    WebsiteScreenshotWorld,
    WebsiteScreenshotWorldError,
)
from websitescreenshotworld._dates import parse_datetime

FIXTURES = sorted(path for path in (SPEC / "fixtures").glob("*.json") if path.name != "keys.json")

ERROR_CLASSES: dict[str, type[WebsiteScreenshotWorldError]] = {
    "authentication": AuthenticationError,
    "invalid_request": InvalidRequestError,
    "plan_limit": PlanLimitError,
    "not_found": NotFoundError,
    "rate_limit": RateLimitError,
    "capture": CaptureError,
    "service": ServiceError,
    "base": WebsiteScreenshotWorldError,
}


def client_settings(server_url: str, keys: Mapping[str, str]) -> dict[str, Any]:
    return {
        "instant_snap_api_key": keys["instant_snap"],
        "auto_schedule_api_key": keys["auto_schedule"],
        "instant_snap_base_url": server_url,
        "auto_schedule_base_url": server_url,
    }


def wait_arguments(call: Mapping[str, Any]) -> dict[str, float]:
    names = ("timeout_seconds", "poll_interval_seconds")
    return {name: call[name] for name in names if name in call}


def call_sync(client: WebsiteScreenshotWorld, call: Mapping[str, Any]) -> Any:
    method = call["method"]
    options: dict[str, Any] = dict(call.get("options", {}))
    idempotency_key = call.get("idempotency_key")
    if call["product"] == "auto_schedule":
        return client.auto_schedule.trigger_now(call["web_page_id"])
    snap = client.instant_snap
    if method == "capture":
        return snap.capture(idempotency_key=idempotency_key, **options)
    if method == "capture_to_bucket":
        return snap.capture_to_bucket(idempotency_key=idempotency_key, **options)
    if method == "submit":
        return snap.submit(idempotency_key=idempotency_key, **options)
    if method == "submit_to_bucket":
        return snap.submit_to_bucket(idempotency_key=idempotency_key, **options)
    if method == "wait":
        return snap.wait(call["id"], **wait_arguments(call))
    if method == "capture_file":
        with snap.capture_file(idempotency_key=idempotency_key, **options) as file:
            return file, hashlib.sha256(file.read()).hexdigest()
    if method == "get":
        return snap.get(call["id"])
    if method == "defaults":
        return snap.defaults()
    if method == "catalog":
        return snap.catalog()
    raise AssertionError(f"unknown method {method}")


async def call_async(client: AsyncWebsiteScreenshotWorld, call: Mapping[str, Any]) -> Any:
    method = call["method"]
    options: dict[str, Any] = dict(call.get("options", {}))
    idempotency_key = call.get("idempotency_key")
    if call["product"] == "auto_schedule":
        return await client.auto_schedule.trigger_now(call["web_page_id"])
    snap = client.instant_snap
    if method == "capture":
        return await snap.capture(idempotency_key=idempotency_key, **options)
    if method == "capture_to_bucket":
        return await snap.capture_to_bucket(idempotency_key=idempotency_key, **options)
    if method == "submit":
        return await snap.submit(idempotency_key=idempotency_key, **options)
    if method == "submit_to_bucket":
        return await snap.submit_to_bucket(idempotency_key=idempotency_key, **options)
    if method == "wait":
        return await snap.wait(call["id"], **wait_arguments(call))
    if method == "capture_file":
        async with snap.capture_file(idempotency_key=idempotency_key, **options) as file:
            return file, hashlib.sha256(await file.read()).hexdigest()
    if method == "get":
        return await snap.get(call["id"])
    if method == "defaults":
        return await snap.defaults()
    if method == "catalog":
        return await snap.catalog()
    raise AssertionError(f"unknown method {method}")


def assert_fields(actual: Any, expected: Any, where: str) -> None:
    if isinstance(expected, dict):
        assert actual is not None, f"{where} is None"
        for name, value in expected.items():
            field = actual[name] if isinstance(actual, Mapping) else getattr(actual, name)
            assert_fields(field, value, f"{where}.{name}")
    elif isinstance(actual, datetime):
        assert actual == parse_datetime(expected), where
    elif isinstance(expected, list):
        assert list(actual) == expected, where
    else:
        assert actual == expected, where


def assert_result(fixture: Mapping[str, Any], outcome: Any) -> None:
    expected = dict(fixture["expect"]["result"])
    if fixture["call"]["method"] == "capture_file":
        file, body_sha256 = outcome
        assert body_sha256 == expected.pop("body_sha256")
        outcome = file
    assert_fields(outcome, expected, "result")


def assert_error(fixture: Mapping[str, Any], error: WebsiteScreenshotWorldError) -> None:
    expected = fixture["expect"]["error"]
    assert type(error) is ERROR_CLASSES[expected["kind"]]
    assert error.error_code == expected["error_code"]
    assert error.http_status == expected["http_status"]
    if "message" in expected:
        assert error.message == expected["message"]
    if "retry_after_seconds" in expected:
        assert error.retry_after_seconds == expected["retry_after_seconds"]


def assert_requests(fixture: Mapping[str, Any], received: list[dict[str, Any]]) -> None:
    expected_requests = fixture["expect_requests"]
    assert len(received) == len(expected_requests)
    shared_keys: set[str] = set()
    for got, want in zip(received, expected_requests, strict=True):
        headers = {name.lower(): value for name, value in got["headers"].items()}
        assert got["method"] == want["method"]
        assert got["path"] == want["path"]
        for name, value in want.get("headers", {}).items():
            assert headers.get(name.lower()) == value, name
        assert headers["user-agent"].startswith("websitescreenshotworld-python/")
        if fixture["call"]["method"] == "defaults":
            assert "x-api-key" not in headers
        if "body" in want:
            body = None if got["body"] is None else json.loads(got["body"])
            assert body == want["body"]
        if want.get("idempotency_key") == "present":
            assert headers.get("idempotency-key")
        if want.get("idempotency_key") == "same":
            shared_keys.add(headers["idempotency-key"])
    assert len(shared_keys) <= 1


def load_fixture(server_url: str, path: Path) -> dict[str, Any]:
    fixture: dict[str, Any] = load_json(path)
    httpx.post(f"{server_url}/__load", json=fixture).raise_for_status()
    return fixture


def received_requests(server_url: str) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = httpx.get(f"{server_url}/__requests").json()
    return requests


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_fixture_sync(path: Path, server_url: str, keys: dict[str, str]) -> None:
    fixture = load_fixture(server_url, path)
    with WebsiteScreenshotWorld(**client_settings(server_url, keys)) as client:
        if "error" in fixture["expect"]:
            with pytest.raises(WebsiteScreenshotWorldError) as info:
                call_sync(client, fixture["call"])
            assert_error(fixture, info.value)
        else:
            assert_result(fixture, call_sync(client, fixture["call"]))
    assert_requests(fixture, received_requests(server_url))


@pytest.mark.parametrize("path", FIXTURES, ids=lambda path: path.stem)
def test_fixture_async(path: Path, server_url: str, keys: dict[str, str]) -> None:
    fixture = load_fixture(server_url, path)

    async def run() -> None:
        async with AsyncWebsiteScreenshotWorld(**client_settings(server_url, keys)) as client:
            if "error" in fixture["expect"]:
                with pytest.raises(WebsiteScreenshotWorldError) as info:
                    await call_async(client, fixture["call"])
                assert_error(fixture, info.value)
            else:
                assert_result(fixture, await call_async(client, fixture["call"]))

    asyncio.run(run())
    assert_requests(fixture, received_requests(server_url))
