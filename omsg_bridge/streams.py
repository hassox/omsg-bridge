import asyncio
import contextlib
import json

from aiohttp import WSMsgType, web

from .catalog import build_argv, query_payload
from .errors import APIError
from .process import MAX_RECORD, validate_rpc

SOCKETS = web.AppKey("sockets", dict)


async def close_socket(ws, transport):
    try:
        async with asyncio.timeout(1):
            await ws.close(drain=False)
    except (ConnectionError, TimeoutError):
        if transport is not None:
            transport.close()


async def stream(request, bridge, *, rpc=False):
    name = "rpc" if rpc else "watch"
    argv = build_argv(name, query_payload(name, request.query))
    ws = web.WebSocketResponse(heartbeat=30, max_msg_size=MAX_RECORD)
    # Validate the HTTP upgrade before starting a child.
    if not ws.can_prepare(request).ok:
        raise web.HTTPBadRequest(reason="This endpoint requires a WebSocket upgrade")
    async with bridge.spawn(argv) as child:
        await ws.prepare(request)
        request.app[SOCKETS][ws] = request.transport

        async def output():
            while True:
                value = await child.line()
                async with asyncio.timeout(10):
                    await ws.send_json(value)

        async def input_():
            async for message in ws:
                if message.type == WSMsgType.TEXT:
                    if not rpc:
                        raise ValueError("Watch is read-only; supply filters in the URL")
                    value = json.loads(message.data)
                    validate_rpc(value)
                    child.process.stdin.write(json.dumps(value).encode() + b"\n")
                    async with asyncio.timeout(10):
                        await child.process.stdin.drain()
                elif message.type == WSMsgType.BINARY:
                    raise ValueError("Send JSON text frames, not binary")

        tasks = [asyncio.create_task(output()), asyncio.create_task(input_())]
        try:
            done, _ = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in done:
                task.result()
        except (APIError, ValueError, TimeoutError, ConnectionError) as exc:
            error = (
                exc.payload["error"]
                if isinstance(exc, APIError)
                else {
                    "code": "stream_timeout"
                    if isinstance(exc, TimeoutError)
                    else "invalid_request",
                    "message": str(exc)
                    or "Stream peer stopped responding; reconnect and refresh history",
                    "retry_safe": False,
                }
            )
            frame = (
                {"jsonrpc": "2.0", "method": "omsg.error", "params": error}
                if rpc
                else {"type": "bridge.error", "error": error}
            )
            with contextlib.suppress(ConnectionError, TimeoutError):
                async with asyncio.timeout(1):
                    await ws.send_json(frame)
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            try:
                await close_socket(ws, request.transport)
            finally:
                request.app[SOCKETS].pop(ws, None)
    return ws
