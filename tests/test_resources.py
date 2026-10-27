import asyncio
import os

import pytest

from omsg_bridge.config import Settings
from omsg_bridge.process import Bridge
from omsg_bridge.server import BRIDGE, create_app
from omsg_bridge.streams import SOCKETS


async def test_child_admission_is_bounded(client):
    sockets = []
    try:
        for _ in range(8):
            ws = await client.ws_connect("/v1/watch")
            await ws.receive_json()
            sockets.append(ws)
        response = await client.post("/v1/chats", json={})
        assert response.status == 503
        assert (await response.json())["error"]["code"] == "busy"
        assert (await client.get("/health")).status == 200
        assert len(client.app[BRIDGE].children) == 8
    finally:
        await asyncio.gather(*(ws.close() for ws in sockets))


async def test_repeated_disconnects_release_every_reference(client):
    before = set(asyncio.all_tasks())
    for _ in range(30):
        async with client.ws_connect("/v1/watch") as ws:
            await ws.receive_json()
        async with client.ws_connect("/v1/rpc/ws") as ws:
            await ws.send_json({"jsonrpc": "2.0", "id": 1, "method": "status"})
            await ws.receive_json()
    async with asyncio.timeout(3):
        while client.app[BRIDGE].children:
            await asyncio.sleep(0.01)
    assert not client.app[BRIDGE].tasks
    assert not client.app[SOCKETS]
    # Allow the TCP handlers to finish after websocket close acknowledgement.
    await asyncio.sleep(0.05)
    leaked = [
        task
        for task in asyncio.all_tasks() - before
        if any(name in repr(task.get_coro()) for name in ("stream.", "Child.", "Process.wait"))
    ]
    assert not leaked


async def test_cancelled_finite_request_reaps_child(fake_imsg):
    bridge = Bridge(Settings(imsg=fake_imsg, auth_enabled=False))
    task = asyncio.create_task(bridge.execute("history", {"options": {"db": "slow"}}))
    async with asyncio.timeout(2):
        while not bridge.children:
            await asyncio.sleep(0.01)
    pid = next(iter(bridge.children)).process.pid
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    assert not bridge.children and not bridge.tasks
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


async def test_shutdown_reaps_live_children(aiohttp_client, fake_imsg):
    client = await aiohttp_client(create_app(Settings(imsg=fake_imsg, auth_enabled=False)))
    ws = await client.ws_connect("/v1/watch")
    pid = (await ws.receive_json())["pid"]
    await client.close()
    assert not client.app[BRIDGE].children
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)
