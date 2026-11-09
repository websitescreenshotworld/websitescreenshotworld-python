from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# datetime.fromisoformat only accepts "Z" and fractions other than 3 or 6 digits from 3.11 on.
_ISO_8601 = re.compile(
    r"(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})(?:[.,](\d+))?"
    r"(?:([Zz])|([+-])(\d{2}):?(\d{2}))"
)


def parse_datetime(value: str) -> datetime:
    """Parse an ISO 8601 timestamp with a ``Z`` or offset into an aware ``datetime``."""
    match = _ISO_8601.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"Not an ISO 8601 date-time with a time zone: {value!r}")
    year, month, day, hour, minute, second, fraction, zulu, sign, off_h, off_m = match.groups()
    if zulu:
        tz = timezone.utc
    else:
        offset = timedelta(hours=int(off_h), minutes=int(off_m))
        tz = timezone(-offset if sign == "-" else offset)
    microsecond = int((fraction or "0")[:6].ljust(6, "0"))
    return datetime(
        int(year), int(month), int(day), int(hour), int(minute), int(second), microsecond, tzinfo=tz
    )


def parse_optional_datetime(value: object) -> datetime | None:
    """Parse a timestamp field that may be null or absent."""
    if value is None:
        return None
    return parse_datetime(str(value))
