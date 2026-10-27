import asyncio

import pytest

from omsg_bridge.catalog import COMMANDS
from omsg_bridge.config import Settings
from omsg_bridge.server import create_app


@pytest.mark.parametrize("name", [name for name in COMMANDS if name not in {"watch", "rpc"}])
async def test_every_finite_command_roundtrip(client, name):
    response = await client.post(f"/v1/{name}", json={})
    assert response.status == 200, await response.text()
    body = await response.json()
    assert body["stderr"] == ""
    if name == "completions":
        assert body["data"] == ["# synthetic completions\n"]
    elif name == "chats":
        assert len(body["data"]) == 2
    else:
        assert body["data"][0]["command"] == name
        assert "--json" in body["data"][0]["argv"]


async def test_get_options_and_send_literal_text(client):
    response = await client.get(
        "/v1/history?chat-id=42&attachments=true&participants=one&participants=two"
    )
    argv = (await response.json())["data"][0]["argv"]
    assert "--chat-id=42" in argv and "--attachments" in argv
    assert "--participants=one" in argv and "--participants=two" in argv
    payload = {"options": {"text": "--help; $(touch /never-run)", "to": "+15555550100"}}
    response = await client.post("/v1/send", json=payload)
    assert "--text=--help; $(touch /never-run)" in (await response.json())["data"][0]["argv"]
    assert (await client.get("/v1/send")).status == 405


@pytest.mark.parametrize(
    "scenario,status,code",
    [
        ("fail", 502, "imsg_failed"),
        ("malformed", 502, "invalid_output"),
        ("large", 502, "output_limit"),
    ],
)
async def test_errors(client, scenario, status, code):
    response = await client.post("/v1/history", json={"options": {"db": scenario}})
    assert response.status == status
    error = (await response.json())["error"]
    assert error["code"] == code
    if scenario == "fail":
        assert error["data"] == [{"success": False, "error": "synthetic refusal"}]
        assert "Full Disk Access" in error["stderr"]
        assert error["exit_code"] == 1


async def test_timeout_and_missing_executable(aiohttp_client, fake_imsg):
    client = await aiohttp_client(
        create_app(Settings(imsg=fake_imsg, auth_enabled=False, command_timeout=0.1))
    )
    response = await client.post("/v1/send", json={"options": {"db": "slow"}})
    assert response.status == 504
    assert (await response.json())["error"]["retry_safe"] is False
    client = await aiohttp_client(
        create_app(Settings(imsg="/nonexistent/imsg", auth_enabled=False))
    )
    response = await client.post("/v1/chats", json={})
    assert response.status == 503
    assert "brew install" in (await response.json())["error"]["message"]


async def test_no_blocking_and_stderr_drained(client):
    slow = asyncio.create_task(client.post("/v1/history", json={"options": {"db": "slow"}}))
    try:
        async with asyncio.timeout(2):
            response = await client.get("/health")
            assert response.status == 200
            response = await client.post("/v1/history", json={"options": {"db": "stderr"}})
            assert response.status == 200
            assert len((await response.json())["stderr"]) <= 65536
        assert not slow.done()
    finally:
        slow.cancel()
        await asyncio.gather(slow, return_exceptions=True)


async def test_request_validation(client):
    for body in ([], {"options": {"evil": True}}, {"args": ["--version"]}):
        assert (await client.post("/v1/chats", json=body)).status == 400
    assert (
        await client.post(
            "/v1/chats", data="not json", headers={"Content-Type": "application/json"}
        )
    ).status == 400
    assert (await client.post("/v1/chats", data="{}")).status == 415
    assert (await client.get("/v1/history?attachments=no")).status == 400


async def test_rest_rpc(client):
    request = {"jsonrpc": "2.0", "id": "request1", "method": "chats.list", "params": {}}
    response = await client.post("/v1/rpc", json=request)
    body = await response.json()
    assert body["id"] == request["id"]
    assert body["result"]["method"] == "chats.list"
    for method in ("watch.subscribe", "bridge.events.subscribe", "watch.unsubscribe"):
        request["method"] = method
        assert (await client.post("/v1/rpc", json=request)).status == 400
