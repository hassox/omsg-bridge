import runpy
from pathlib import Path

import pytest

from omsg_bridge.catalog import COMMANDS, build_argv, openapi


def test_catalog_covers_source_inventory():
    assert len(COMMANDS) == 38
    assert set(COMMANDS) >= {"send", "react", "tapback", "poll", "watch", "rpc", "completions"}
    spec = openapi()
    for name in COMMANDS:
        assert f"/v1/{name}" in spec["paths"]


def test_catalog_matches_released_cli_reference():
    parse = runpy.run_path("scripts/import_catalog.py")["parse"]
    reference = Path(__file__).with_name("fixtures") / "imsg-v0.19.1-help.md"
    assert parse(reference.read_text()) == COMMANDS


def test_cli_mapping():
    assert build_argv("send", {"options": {"to": "+15555550100", "text": "--help"}}) == [
        "send",
        "--json",
        "--to=+15555550100",
        "--text=--help",
    ]
    assert build_argv("poll", {"args": ["send"], "options": {"option": ["Tea", "Coffee"]}}) == [
        "poll",
        "--json",
        "--option=Tea",
        "--option=Coffee",
        "--",
        "send",
    ]
    assert build_argv("completions", {"args": ["llm"]}) == ["completions", "--", "llm"]
    assert build_argv(
        "history", {"options": {"participants": ["one", "two"], "attachments": True}}
    ) == ["history", "--json", "--participants=one", "--participants=two", "--attachments"]
    assert build_argv("scheduled", {"args": ["list"]}) == ["scheduled", "--json", "--", "list"]
    assert "--stop=true" in build_argv("typing", {"options": {"stop": "true"}})
    assert "--reactions" in build_argv("watch", {"options": {"reactions": True}})
    assert "--reactions" not in build_argv("watch", {"options": {"reactions": False}})


@pytest.mark.parametrize(
    "command,payload",
    [
        ("unknown", {}),
        ("send", {"options": {"json": False}}),
        ("send", {"options": {"oops": "x"}}),
        ("send", {"args": ["--help"]}),
        ("send", {"options": {"text": {"bad": "object"}}}),
        ("watch", {"options": {"reactions": "false"}}),
        ("send", {"options": {"text": "nul\0"}}),
        ("send", {"extra": 1}),
    ],
)
def test_invalid_requests(command, payload):
    with pytest.raises(ValueError):
        build_argv(command, payload)
