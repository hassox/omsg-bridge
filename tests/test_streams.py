import asyncio
import base64
import os

import pytest
from aiohttp import WSMsgType, WSServerHandshakeError

from omsg_bridge.config import Settings
from omsg_bridge.server import create_app


async def assert_reaped(pid):
    async with asyncio.timeout(3):
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            await asyncio.sleep(0.02)


async def test_watch_events_concurrent_rest_and_disconnect(client):
    async with client.ws_connect("/v1/watch?reactions=true&bb-events=true") as ws:
        message = await ws.receive_json()
        pid = message["pid"]
        assert message["text"] == "synthetic"
        assert (await ws.receive_json())["is_reaction"]
        assert (await ws.receive_json())["type"] == "edited"
        assert (await ws.receive_json())["type"] == "unsent"
        assert (await ws.receive_json())["kind"] == "bridge-event"
        async with asyncio.timeout(2):
            response = await client.post("/v1/send", json={"options": {"text": "synthetic only"}})
            assert response.status == 200
    await assert_reaped(pid)


async def test_watch_errors_and_validation(client):
    with pytest.raises(WSServerHandshakeError) as caught:
        await client.ws_connect("/v1/watch?bad=option")
    assert caught.value.status == 400
    async with client.ws_connect("/v1/watch?db=fail") as ws:
        assert (await ws.receive_json())["success"] is False
        error = await ws.receive_json()
        assert error["type"] == "bridge.error"
        assert "Full Disk Access" in error["error"]["stderr"]
        assert (await ws.receive()).type == WSMsgType.CLOSE


async def test_rpc_subscriptions_and_disconnect(client):
    async with client.ws_connect("/v1/rpc/ws") as ws:
        await ws.send_json({"jsonrpc": "2.0", "id": 1, "method": "watch.subscribe", "params": {}})
        response = await ws.receive_json()
        pid = response["result"]["pid"]
        assert response["id"] == 1
        assert (await ws.receive_json())["method"] == "message"
        await ws.send_json(
            {"jsonrpc": "2.0", "id": 2, "method": "send", "params": {"text": "fake"}}
        )
        assert (await ws.receive_json())["id"] == 2
    await assert_reaped(pid)


async def test_ws_auth_and_origin(aiohttp_client, fake_imsg):
    client = await aiohttp_client(
        create_app(Settings(imsg=fake_imsg, username="test", password="synthetic"))
    )
    headers = {"Authorization": "Basic " + base64.b64encode(b"test:synthetic").decode()}
    for path in ("/v1/watch", "/v1/rpc/ws"):
        with pytest.raises(WSServerHandshakeError) as caught:
            await client.ws_connect(path)
        assert caught.value.status == 401
        with pytest.raises(WSServerHandshakeError) as caught:
            await client.ws_connect(path, headers=headers, origin="https://bad.invalid")
        assert caught.value.status == 403
    async with client.ws_connect("/v1/watch", headers=headers) as ws:
        assert (await ws.receive_json())["id"] == 1


async def test_rpc_malformed_request_closes_with_useful_error(client):
    async with client.ws_connect("/v1/rpc/ws") as ws:
        await ws.send_str("not json")
        error = await ws.receive_json()
        assert error["method"] == "omsg.error"
        assert error["params"]["code"] == "invalid_request"
