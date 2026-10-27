import asyncio
import os
import signal
from unittest.mock import AsyncMock

import pytest
from aiohttp import web

from omsg_bridge.config import Settings
from omsg_bridge.errors import APIError
from omsg_bridge.process import Bridge
from omsg_bridge.streams import close_socket


async def reaped(pid):
    async with asyncio.timeout(4):
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            await asyncio.sleep(0.02)


async def test_close_marks_bridge_terminal(fake_imsg):
    bridge = Bridge(Settings(imsg=fake_imsg, auth_enabled=False))
    await bridge.close()
    with pytest.raises(APIError) as caught:
        await bridge.execute("chats", {})
    assert caught.value.payload["error"]["code"] == "shutting_down"


async def test_cancellation_during_term_ignoring_child_cleanup(fake_imsg):
    bridge = Bridge(Settings(imsg=fake_imsg, auth_enabled=False))
    task = asyncio.create_task(
        bridge.rpc({"jsonrpc": "2.0", "id": 1, "method": "status"}, {"db": "ignore-term"})
    )
    async with asyncio.timeout(2):
        while not bridge.children:
            await asyncio.sleep(0.005)
    child = next(iter(bridge.children))
    try:
        async with asyncio.timeout(2):
            while child.cleanup_task is None:
                await asyncio.sleep(0.005)
        task.cancel()
        await asyncio.sleep(0.05)
        assert bridge.tasks  # No early admission release while child still exists.
        await bridge.close()  # A second cancellation must not orphan cleanup.
        await reaped(child.process.pid)
        assert not bridge.tasks and not bridge.children
        assert child.stderr_task.done() and child.cleanup_task.done()
    finally:
        if child.process.returncode is None:
            os.killpg(child.process.pid, signal.SIGKILL)
        await asyncio.gather(task, return_exceptions=True)


async def test_term_ignoring_descendant_reaped(fake_imsg):
    bridge = Bridge(Settings(imsg=fake_imsg, auth_enabled=False))
    result = await bridge.execute("history", {"options": {"db": "descendant"}})
    pid = result["data"][0]["descendant"]
    try:
        await reaped(pid)
    finally:
        try:
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass


async def test_socket_close_has_deadline():
    ws = web.WebSocketResponse()
    started = asyncio.Event()

    async def stuck_close(**kwargs):
        started.set()
        await asyncio.Event().wait()

    ws.close = stuck_close
    transport = AsyncMock()
    transport.close = lambda: started.clear()
    async with asyncio.timeout(2):
        await close_socket(ws, transport)
    assert not started.is_set()
