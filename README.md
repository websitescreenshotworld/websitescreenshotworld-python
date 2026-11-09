# Website Screenshot World for Python

The Python client for [Website Screenshot World](https://websitescreenshotworld.com): capture web pages
on demand with **Instant Snap**, start a scheduled capture now with **Auto Schedule**, and verify the
webhooks both send.

It has a sync and an asyncio client, typed options and results, streamed file downloads, async
captures (`submit`, `submit_to_bucket` and `wait`), and the retry and idempotency rules the API
expects.

## Install

```sh
pip install websitescreenshotworld
```

Python 3.10 or later. The only dependency is [httpx](https://www.python-httpx.org/).

## Quick start

Create API keys in the dashboard and put them in the environment:

```sh
export WSW_INSTANT_SNAP_API_KEY="wsw_api_..."
export WSW_AUTO_SCHEDULE_API_KEY="wsw_autoapi_..."
```

### Instant Snap

```python
from websitescreenshotworld import WebsiteScreenshotWorld

with WebsiteScreenshotWorld() as client:
    capture = client.instant_snap.capture(
        url="https://example.com",
        format="webp",
        viewport={"width": 1440, "height": 900},
        block_ads=True,
    )
    print(capture.id, capture.width, capture.height)
    print(capture.download_url)  # valid for 60 minutes
```

Options are keyword arguments named exactly as in the
[API reference](https://api.websitescreenshotworld.com/instant-snap/v1/openapi.json). Nested blocks
(`viewport`, `geolocation`, `selectors`, `proxy`, `timestamp_watermark`, `page_source`) are plain
dictionaries, typed with `TypedDict`s so your editor and type checker know their fields. An option you
leave out (or pass as `None`) is not sent and takes the API's default; `False`, `0` and `""` are sent.
The names in `headers` and `cookies` are sent exactly as you write them.

### Auto Schedule

```python
from websitescreenshotworld import TriggerStatus, WebsiteScreenshotWorld

with WebsiteScreenshotWorld() as client:
    result = client.auto_schedule.trigger_now("7d4e2b1a-6c5f-4a3e-9d8c-2b1a0f9e8d7c")
    if result.status == TriggerStatus.ALREADY_PENDING:
        print("A capture of this page is already queued; nothing new was charged.")
```

The web page's id is in the dashboard. The capture's result arrives by [webhook](#webhooks).

### asyncio

`AsyncWebsiteScreenshotWorld` has the same settings and methods; await them.

```python
import asyncio

from websitescreenshotworld import AsyncWebsiteScreenshotWorld


async def main() -> None:
    async with AsyncWebsiteScreenshotWorld() as client:
        capture = await client.instant_snap.capture(url="https://example.com")
        print(capture.download_url)


asyncio.run(main())
```

## Getting the file

### In the answer: `capture_file`

`capture_file` returns the file itself, streamed from the connection rather than held in memory.
Use it in a `with` block so the connection is released:

```python
from websitescreenshotworld import WebsiteScreenshotWorld

client = WebsiteScreenshotWorld()

with client.instant_snap.capture_file(url="https://example.com", format="png") as file:
    print(file.filename, file.content_type, file.width, file.height, file.sha256)
    file.save("example.png")
```

The body can be read once: `save(path_or_stream)`, `read()` for the bytes, or `iter_bytes()` for
chunks. The metadata from the `X-InstantSnap-*` headers is on the object (`id`, `status`, `width`,
`height`, `size_bytes`, `duration_ms`, `page_http_status`, `captured_at`, `final_url`, `sha256`,
`part_count`, `spec_version`), with `filename` taken from `Content-Disposition`.

With asyncio, `async with client.instant_snap.capture_file(...) as file:` and `await file.save(...)`.

A file returned this way is not kept by the API, and `page_source` is not available with it.

### Later: `get` and `download`

A capture made with `capture` is kept for 24 hours. `get` reads it back with a fresh
`download_url`, and `download` streams the file to a path or a binary stream:

```python
from websitescreenshotworld import WebsiteScreenshotWorld

client = WebsiteScreenshotWorld()

capture = client.instant_snap.get("3f6c2a1e-9b8d-4c7e-a5f4-1d2e3c4b5a69")
client.instant_snap.download(capture, "example.png")

with open("example-copy.png", "wb") as stream:
    client.instant_snap.download(capture, stream)
```

The download link is signed, so the API key is not sent with it.

### Into your bucket: `capture_to_bucket`

```python
import os

from websitescreenshotworld import WebsiteScreenshotWorld

client = WebsiteScreenshotWorld()

capture = client.instant_snap.capture_to_bucket(
    url="https://example.com",
    s3_delivery={
        "access_key_id": os.environ["S3_ACCESS_KEY_ID"],
        "secret_access_key": os.environ["S3_SECRET_ACCESS_KEY"],
        "bucket": "captures",
        "region": "eu-west-2",
        "key_prefix": "example/",
    },
)
assert capture.s3_delivery is not None
print(capture.s3_delivery.status)  # "in_progress", or "completed" with wait_for_sync
```

Any S3-compatible service works: give `endpoint_url` (https) instead of, or as well as, `region`.

### Defaults and catalog

`client.instant_snap.defaults()` returns the value each option takes when you leave it out, and the
limits (no key needed). `client.instant_snap.catalog()` lists the devices `emulated_device` accepts
and the countries `proxy` accepts.

## Async captures

`submit` queues a capture and answers at once with the capture in status `queued`; it then runs when a
browser is free (`queued`, then `running`, then `succeeded` or `failed`). `wait` reads it with `get`
until it has finished:

```python
from websitescreenshotworld import CaptureStatus, WebsiteScreenshotWorld

with WebsiteScreenshotWorld() as client:
    queued = client.instant_snap.submit(url="https://example.com", format="png", timeout=240)
    print(queued.id, queued.status)  # "queued"

    capture = client.instant_snap.wait(queued, timeout_seconds=360, poll_interval_seconds=3)
    if capture.status == CaptureStatus.SUCCEEDED:
        client.instant_snap.download(capture, "example.png")
    elif capture.status == CaptureStatus.FAILED:
        print("Failed:", capture.error_code)
    else:
        print("Still", capture.status, "- wait again later")
```

`submit_to_bucket` does the same into your bucket, taking `s3_delivery` as `capture_to_bucket` does:

```python
import os

from websitescreenshotworld import WebsiteScreenshotWorld

client = WebsiteScreenshotWorld()

queued = client.instant_snap.submit_to_bucket(
    url="https://example.com",
    s3_delivery={
        "access_key_id": os.environ["S3_ACCESS_KEY_ID"],
        "secret_access_key": os.environ["S3_SECRET_ACCESS_KEY"],
        "bucket": "captures",
        "region": "eu-west-2",
    },
)
capture = client.instant_snap.wait(queued.id)
```

- `timeout` here is the API's option (`SubmitOptions`): the browser time the capture may use, 30 to
  300 seconds, 120 when left out. Only `submit` and `submit_to_bucket` take it. The call itself waits
  only for the answer, so it uses the client's `timeout` (30 seconds), not `capture_timeout`.
- A capture still waiting 15 minutes after it was accepted ends `failed` with `capture_expired`, and
  is not charged.
- When the organization already has as many async captures waiting or running as it may, `submit`
  raises `RateLimitError` with `error_code` `queue_full` and `retry_after_seconds`. It is not retried
  by the library: wait that long, or for some captures to finish, and submit again.
- `wait` takes the capture or its id. It returns as soon as the status is no longer `queued`,
  `running` or `pending`. If `timeout_seconds` (default 360) runs out first, it returns the capture as
  last read, still unfinished, rather than raising. `poll_interval_seconds` defaults to 3. An error
  from `get` is raised as it is. With asyncio, cancelling the task or `asyncio.timeout()` stops it.

## Results

Results are frozen dataclasses: `Capture`, `TriggerResult`, `Defaults`, `Catalog`. Timestamps are
timezone-aware `datetime`s. Tokens such as `status` and `format` stay plain strings, so a value the
API adds later still comes through; compare them with the constants in `CaptureStatus`, `Format`,
`MediaCategory`, `ResponseType`, `S3DeliveryStatus`, `TriggerStatus` and `TriggeredBy`. Each result
also has `raw`, the answer as received, for fields added after this release.

## Errors and retries

Every error is a `WebsiteScreenshotWorldError` with `error_code`, `message`, `http_status`,
`retry_after_seconds` and `body`. Branch on the class or on `error_code`, never on the status or the
message:

| Class | Raised for |
|---|---|
| `AuthenticationError` | `api_key_invalid`, or no key for the product (raised before sending) |
| `InvalidRequestError` | `validation_failed`, `s3_destination_invalid`, `web_page_id_invalid`, `idempotency_key_reused`, `sitemap_schedule_not_triggerable` |
| `PlanLimitError` | `quota_exhausted`, `feature_not_available`, `no_trigger_allowance`, `forbidden` |
| `NotFoundError` | `capture_not_found`, `web_page_not_found`, `not_found` |
| `RateLimitError` | `rate_limited`, `queue_full` |
| `CaptureError` | `capture_failed`, `capture_timeout`, `payload_too_large`, `capture_expired` |
| `ServiceError` | `capture_busy`, `service_unavailable`, `internal_error`, `request_cancelled`, `idempotency_key_in_use` |
| `APIConnectionError` | the request could not be sent, or no answer came back |
| `APITimeoutError` | a subclass of `APIConnectionError`: the timeout passed |
| `SignatureVerificationError` | a webhook signature that does not match |

A code this version does not know yet raises `WebsiteScreenshotWorldError` itself.

```python
from websitescreenshotworld import (
    CaptureError,
    PlanLimitError,
    WebsiteScreenshotWorld,
    WebsiteScreenshotWorldError,
)

client = WebsiteScreenshotWorld()

try:
    capture = client.instant_snap.capture(url="https://example.com")
except CaptureError as error:
    print("The page could not be captured:", error.message)
except PlanLimitError as error:
    print("Plan limit:", error.error_code)
except WebsiteScreenshotWorldError as error:
    print("Failed:", error)
```

`rate_limited`, `capture_busy`, `service_unavailable`, `idempotency_key_in_use` and connection
failures are retried twice (three attempts in all). The wait is the API's `retry_after_seconds` (or
`Retry-After`), at most 60 seconds, and otherwise 0.5 s and then 1 s with a little jitter. Nothing
else is retried: `capture_failed` and `capture_timeout` are answers about the website, and a retry
would fail the same way; `queue_full` would only meet the same full queue, so it is raised at once
with `retry_after_seconds`. Set `max_retries` on the client to change the count, or `0` to turn retries
off.

## Idempotency keys

Every capture carries an `Idempotency-Key`, so a retry never captures or charges twice. The client
makes a random one per call and reuses it on that call's retries. Pass your own to make a call safe
to repeat across processes for 24 hours, for example when a job queue may run a task twice:

```python
from websitescreenshotworld import WebsiteScreenshotWorld

client = WebsiteScreenshotWorld()

capture = client.instant_snap.capture(
    url="https://example.com/pricing",
    idempotency_key="order-1234-hero",
)
```

A repeat with the same key gets the first capture back. The key must not be reused with different
options (`InvalidRequestError`, `idempotency_key_reused`), and `capture_file` results are not kept,
so they cannot be replayed. `trigger_now` needs no key: it is idempotent by itself.

## Timeouts

A capture may take the API up to 120 seconds on a slow page, so captures are allowed 180 seconds
and every other call 30 seconds. The time covers the whole call, retries included: once it has
passed, retrying stops and `APITimeoutError` is raised. Change the defaults on the client, or pass
`timeout` to a single capture or download:

```python
from websitescreenshotworld import WebsiteScreenshotWorld

client = WebsiteScreenshotWorld(timeout=10, capture_timeout=240)
capture = client.instant_snap.capture(url="https://example.com", timeout=60)
```

`submit` and `submit_to_bucket` use `timeout`, not `capture_timeout`, since they are answered at
once; their `timeout` keyword is the API's async option (see [Async captures](#async-captures)).

For asyncio, `asyncio.timeout()` and task cancellation stop a call, retries included, at once.

## Webhooks

Deliveries are signed with the endpoint's secret in the `X-WSW-Signature` header.
`webhooks.verify` checks the signature and the timestamp (within 5 minutes by default) and returns a
typed event:

```python
from websitescreenshotworld import webhooks


def handle(body: bytes, signature: str | None, secret: str) -> None:
    event = webhooks.verify(body, signature, secret)
    match event:
        case webhooks.InstantSnapCaptureEvent(type="capture.succeeded", data=capture):
            print("Instant Snap capture ready:", capture.id)
        case webhooks.AutoScheduleCaptureEvent(data=capture):
            print(event.type, capture.schedule_id, capture.status)
        case webhooks.CaptureChangedEvent(data=change):
            print(f"{change.url} changed by {change.change_percent}%")
        case webhooks.UnknownEvent():
            print("An event type this library does not know yet:", event.type, event.data)
```

| Class | `type` | `data` |
|---|---|---|
| `InstantSnapCaptureEvent` | `capture.succeeded`, `capture.failed` (Instant Snap) | `Capture` |
| `AutoScheduleCaptureEvent` | `capture.succeeded`, `capture.failed` (Auto Schedule) | `ScheduleCapture` |
| `DeliveryCompletedEvent` | `delivery.completed` | `Delivery` |
| `CaptureChangedEvent` | `capture.changed` | `CaptureChange` |
| `SchedulePausedEvent` | `schedule.paused` | `SchedulePaused` |
| `SitemapRunCompletedEvent` | `sitemap_run.completed` | `SitemapRun` |
| `PingEvent` | `ping` | `Ping` |
| `UnknownEvent` | anything else | the `data` dictionary |

Every event has `id` (the same on redeliveries, so you can drop duplicates), `type`, `created_at`,
`product` and `raw`. A bad signature raises `SignatureVerificationError`; answer it with a 400.

**Pass the raw body.** The signature covers the exact bytes sent. A framework that parses the JSON
and serialises it again changes them, and the signature no longer matches.

Flask:

```python
from flask import Flask, request

from websitescreenshotworld import webhooks

app = Flask(__name__)


@app.post("/webhooks/wsw")
def wsw_webhook() -> tuple[str, int]:
    try:
        event = webhooks.verify(
            request.get_data(), request.headers.get("X-WSW-Signature"), app.config["WSW_SECRET"]
        )
    except webhooks.SignatureVerificationError:
        return "bad signature", 400
    print(event.type)
    return "", 204
```

Django:

```python
from django.conf import settings
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from websitescreenshotworld import webhooks


@csrf_exempt
@require_POST
def wsw_webhook(request: HttpRequest) -> HttpResponse:
    try:
        event = webhooks.verify(
            request.body, request.headers.get("X-WSW-Signature"), settings.WSW_SECRET
        )
    except webhooks.SignatureVerificationError:
        return HttpResponseBadRequest("bad signature")
    print(event.type)
    return HttpResponse(status=204)
```

FastAPI (and Starlette):

```python
import os

from fastapi import FastAPI, HTTPException, Request, Response

from websitescreenshotworld import webhooks

app = FastAPI()


@app.post("/webhooks/wsw", status_code=204)
async def wsw_webhook(request: Request) -> Response:
    try:
        event = webhooks.verify(
            await request.body(),
            request.headers.get("X-WSW-Signature"),
            os.environ["WSW_WEBHOOK_SECRET"],
        )
    except webhooks.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="bad signature") from None
    print(event.type)
    return Response(status_code=204)
```

`webhooks.SignatureVerificationError` is the same class as `websitescreenshotworld.SignatureVerificationError`.

## Configuration

| Argument | Default |
|---|---|
| `instant_snap_api_key` | `WSW_INSTANT_SNAP_API_KEY` from the environment |
| `auto_schedule_api_key` | `WSW_AUTO_SCHEDULE_API_KEY` from the environment |
| `instant_snap_base_url` | `https://api.websitescreenshotworld.com` |
| `auto_schedule_base_url` | `https://autoapi.websitescreenshotworld.com` |
| `capture_timeout` | 180 seconds |
| `timeout` | 30 seconds, for everything but captures |
| `max_retries` | 2 |
| `http_client` | a new `httpx.Client` (`httpx.AsyncClient` for the async client) |

Either key may be left out if you use only one product; calling the other raises
`AuthenticationError` before anything is sent.

Pass your own `httpx.Client` for proxies, custom certificates or connection limits. The library does
not close a client you pass in:

```python
import httpx

from websitescreenshotworld import WebsiteScreenshotWorld

http = httpx.Client(proxy="http://proxy.example.com:3128")
client = WebsiteScreenshotWorld(http_client=http)
```

Create the client once and reuse it, so connections are pooled.

## Supported versions

CPython 3.10 to 3.13, tested on 3.10 and 3.13. The library follows semantic versioning; until 1.0, a
minor version may change the API, as noted in the [changelog](CHANGELOG.md).

## Development

```sh
pip install -e ".[dev]"
ruff format --check . && ruff check . && mypy
pytest
```

The tests start `spec/conformance/server.js`, so they need Node.js 22 or later. `spec/` is the
[websitescreenshotworld-spec](https://github.com/websitescreenshotworld/websitescreenshotworld-spec) submodule:
clone with `git clone --recurse-submodules`, or run `git submodule update --init` in an existing clone.

## License

MIT. See [LICENSE](LICENSE).
