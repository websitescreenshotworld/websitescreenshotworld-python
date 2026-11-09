from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from websitescreenshotworld._dates import parse_datetime, parse_optional_datetime

UTC = timezone.utc


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("2026-09-26T10:30:04.512Z", datetime(2026, 9, 26, 10, 30, 4, 512000, tzinfo=UTC)),
        ("2026-09-26T10:30:04Z", datetime(2026, 9, 26, 10, 30, 4, tzinfo=UTC)),
        ("2026-09-26T10:30:04.5Z", datetime(2026, 9, 26, 10, 30, 4, 500000, tzinfo=UTC)),
        ("2026-09-26T10:30:04.123456789Z", datetime(2026, 9, 26, 10, 30, 4, 123456, tzinfo=UTC)),
        ("2026-09-26t10:30:04.512z", datetime(2026, 9, 26, 10, 30, 4, 512000, tzinfo=UTC)),
        ("2026-09-26T10:30:04.512+00:00", datetime(2026, 9, 26, 10, 30, 4, 512000, tzinfo=UTC)),
        (
            "2026-09-26T16:00:04+05:30",
            datetime(2026, 9, 26, 16, 0, 4, tzinfo=timezone(timedelta(hours=5, minutes=30))),
        ),
        (
            "2026-09-26T05:30:04.000-0500",
            datetime(2026, 9, 26, 5, 30, 4, tzinfo=timezone(timedelta(hours=-5))),
        ),
    ],
)
def test_parses_leniently(text: str, expected: datetime) -> None:
    parsed = parse_datetime(text)
    assert parsed == expected
    assert parsed.utcoffset() == expected.utcoffset()


def test_offsets_are_the_same_instant() -> None:
    assert parse_datetime("2026-09-26T16:00:04+05:30") == parse_datetime("2026-09-26T10:30:04Z")


@pytest.mark.parametrize("text", ["2026-09-26T10:30:04", "yesterday", "2026-09-26"])
def test_refuses_timestamps_without_a_zone(text: str) -> None:
    with pytest.raises(ValueError, match="ISO 8601"):
        parse_datetime(text)


def test_null_stays_none() -> None:
    assert parse_optional_datetime(None) is None
