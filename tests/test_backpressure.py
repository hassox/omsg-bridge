import asyncio
import json
import socket

from omsg_bridge.server import REQUESTS


async def test_slow_http_readers_keep_admission_until_response_finishes(client):
    peers = []
    body = json.dumps({"options": {"db": "large-json"}}).encode()
    raw = (
        f"POST /v1/history HTTP/1.1\r\nHost: localhost\r\nContent-Type: application/json\r\n"
        f"Content-Length: {len(body)}\r\n\r\n"
    ).encode() + body
    try:
        async with asyncio.timeout(8):
            for _ in range(8):
                sock = socket.socket()
                sock.setblocking(False)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
                await asyncio.get_running_loop().sock_connect(
                    sock, (client.server.host, client.server.port)
                )
                reader, writer = await asyncio.open_connection(sock=sock, limit=1024)
                peers.append((reader, writer))
                writer.write(raw)
                await writer.drain()
                assert b"200 OK" in await reader.readuntil(b"\r\n\r\n")
            assert len(client.app[REQUESTS]) == 8
            response = await client.post("/v1/chats", json={})
            assert response.status == 503
            assert (await client.get("/health")).status == 200
    finally:
        for _, writer in peers:
            writer.transport.abort()
        await asyncio.gather(*(writer.wait_closed() for _, writer in peers), return_exceptions=True)
    async with asyncio.timeout(12):
        while client.app[REQUESTS]:
            await asyncio.sleep(0.01)
