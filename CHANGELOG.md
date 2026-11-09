# Changelog

All notable changes to this package are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the package uses
[semantic versioning](https://semver.org/).

## [0.1.0] - 2026-11-09

The first release.

### Added

- `WebsiteScreenshotWorld` and `AsyncWebsiteScreenshotWorld`, one client for both products, with keys
  read from `WSW_INSTANT_SNAP_API_KEY` and `WSW_AUTO_SCHEDULE_API_KEY` when not passed, and an
  optional `httpx.Client` or `httpx.AsyncClient` of your own.
- Instant Snap: `capture`, `capture_file` (the file streamed from the answer, with its metadata),
  `capture_to_bucket`, `get`, `download`, `defaults` and `catalog`, taking every capture option as a
  typed keyword argument.
- Instant Snap async captures: `submit` and `submit_to_bucket` (answered at once with the capture
  `queued`) and `wait`, which reads the capture until it has finished or `timeout_seconds` runs out;
  the `timeout` option (`SubmitOptions`, 30 to 300 seconds); the `CaptureStatus.QUEUED` and
  `CaptureStatus.RUNNING` statuses; and the `queue_full` (`RateLimitError`, not retried) and
  `capture_expired` (`CaptureError`) error codes.
- Auto Schedule: `trigger_now`.
- The `press_escape` capture option, and the `sitemap_schedule_not_triggerable` error code (an
  `InvalidRequestError`: a sitemap schedule runs only on its schedule), from API version 1.1.0.
- Frozen dataclass results with timezone-aware `datetime` fields, string tokens with named constants,
  and the answer as received in `raw`.
- An `Idempotency-Key` on every capture, generated when not given and reused on retries.
- Retries of `rate_limited`, `capture_busy`, `service_unavailable`, `idempotency_key_in_use` and
  connection failures, honouring `retry_after_seconds` and `Retry-After`, within the call's timeout.
- One error class per kind of refusal under `WebsiteScreenshotWorldError`, plus `APIConnectionError`
  and `APITimeoutError`.
- `webhooks.verify`, which checks the `X-WSW-Signature` header and returns a typed event for every
  documented event type, or `UnknownEvent` for a type added later.

[0.1.0]: https://github.com/websitescreenshotworld/websitescreenshotworld-python/tree/v0.1.0
