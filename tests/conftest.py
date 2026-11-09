from __future__ import annotations

import re
import subprocess
from collections.abc import Iterator

import pytest
from support import SERVER_SCRIPT, SPEC, load_json


@pytest.fixture(scope="session")
def keys() -> dict[str, str]:
    data: dict[str, str] = load_json(SPEC / "fixtures" / "keys.json")
    return data


@pytest.fixture(scope="session")
def server_url() -> Iterator[str]:
    """Start the shared conformance server and yield its base URL."""
    process = subprocess.Popen(
        ["node", str(SERVER_SCRIPT)],
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert process.stdout is not None
        first_line = process.stdout.readline()
        match = re.search(r"http://127\.0\.0\.1:(\d+)", first_line)
        assert match, f"unexpected first line from the server: {first_line!r}"
        yield f"http://127.0.0.1:{match.group(1)}"
    finally:
        process.terminate()
        process.wait(timeout=10)
