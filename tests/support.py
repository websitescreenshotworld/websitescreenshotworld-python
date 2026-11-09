"""Paths to the shared spec and conformance server."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# spec/ is the websitescreenshotworld-spec submodule: the shared cases and the conformance server.
REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "spec"
SERVER_SCRIPT = SPEC / "conformance" / "server.js"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
