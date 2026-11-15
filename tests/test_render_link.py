from __future__ import annotations

from typing import Any

import pytest
from support import SPEC, load_json

from websitescreenshotworld import RenderLink

VECTORS: dict[str, Any] = load_json(SPEC / "render-link-vectors.json")


@pytest.mark.parametrize("case", VECTORS["cases"], ids=lambda case: case["name"])
def test_render_link_vector(case: dict[str, Any]) -> None:
    extra: dict[str, Any] = {}
    if "format" in case:
        extra["format"] = case["format"]
    if "base_url" in case:
        extra["base_url"] = case["base_url"]

    link = RenderLink.build(
        render_secret=case["render_secret"],
        key_prefix=case["key_prefix"],
        **extra,
        **case["options"],
    )

    assert link == case["url"]


VALID: dict[str, Any] = {
    "render_secret": "wsw_rsk_x",
    "key_prefix": "0123456789ab",
    "url": "https://example.com",
}


@pytest.mark.parametrize(
    "change",
    [
        {"render_secret": ""},
        {"key_prefix": "0123456789AB"},
        {"key_prefix": "wsw_api_0123"},
        {"url": ""},
        {"format": "pdf"},
    ],
)
def test_refuses_what_cannot_be_a_link(change: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match=r"\w"):
        RenderLink.build(**{**VALID, **change})


def test_leaves_out_an_option_that_is_not_set() -> None:
    link = RenderLink.build(**VALID, width=None, block_ads=False)

    assert "block_ads=false" in link
    assert "width=" not in link
    assert link.rsplit("&sig=", 1)[1].isalnum()
