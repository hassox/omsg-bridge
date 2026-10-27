"""Real server process + TCP + CLI subprocess churn, no real Messages access."""

import asyncio
import base64
import json
import os
import socket
import sys

import pytest
from aiohttp import ClientError, ClientSession
from mcp import ClientSession as MCPSession
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.fixture
async def running_server(tmp_path, fake_imsg):
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    config = tmp_path / "settings.toml"
    config.write_text(
        f'imsg = {json.dumps(fake_imsg)}\n[auth]\nusername = "test"\npassword = "synthetic"\n'
    )
    env = {**os.environ, "PORT": str(port)}
    env.pop("OMSG_USERNAME", None)
    env.pop("OMSG_PASSWORD", None)
    proc = await asyncio.create_subprocess_exec(
        sys.executable,
        "-m",
        "omsg_bridge.server",
        "--config",
        str(config),
        env=env,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    url = f"http://127.0.0.1:{port}"
    headers = {"Authorization": "Basic " + base64.b64encode(b"test:synthetic").decode()}
    try:
        async with ClientSession(headers=headers) as session:
            async with asyncio.timeout(15):
                while True:
                    if proc.returncode is not None:
                        raise AssertionError((await proc.stderr.read()).decode())
                    try:
                        async with session.get(url + "/health") as response:
                            if response.status == 200:
                                break
                    except ClientError:
                        pass
                    await asyncio.sleep(0.02)
            yield proc, session, url, config
    finally:
        if proc.returncode is None:
            proc.terminate()
        try:
            async with asyncio.timeout(10):
                _, stderr = await proc.communicate()
        except TimeoutError:
            proc.kill()
            await proc.communicate()
            raise
        assert not stderr, stderr.decode()


async def sample(pid):
    proc = await asyncio.create_subprocess_exec(
        "ps", "-o", "rss=", "-o", "time=", "-p", str(pid), stdout=asyncio.subprocess.PIPE
    )
    output, _ = await proc.communicate()
    rss, cpu = output.decode().split()
    parts = cpu.split(":")
    seconds = sum(float(value) * (60**index) for index, value in enumerate(reversed(parts)))
    return int(rss), seconds


async def test_full_process_mcp_http_websocket(running_server):
    proc, session, url, config = running_server
    async with session.get(url + "/docs/ui") as response:
        assert response.status == 200 and "swagger-ui" in await response.text()
    async with session.ws_connect(url + "/v1/watch") as ws:
        assert (await ws.receive_json())["text"] == "synthetic"
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "omsg_bridge.mcp", "--url", url, "--config", str(config)],
        )
        async with stdio_client(params) as (read, write):
            async with MCPSession(read, write) as mcp:
                await mcp.initialize()
                assert len((await mcp.list_tools()).tools) == 3
                for _ in range(20):
                    result = await mcp.call_tool("execute_action", {"name": "chats", "payload": {}})
                    assert not result.isError
        assert (await ws.receive_json())["is_reaction"]
    assert proc.returncode is None


async def test_memory_and_idle_cpu_plateau(running_server):
    proc, session, url, _ = running_server
    samples = []
    for _batch in range(6):
        for _ in range(40):
            async with session.post(url + "/v1/chats", json={}) as response:
                assert response.status == 200
                await response.read()
            for path in ("/v1/watch", "/v1/rpc/ws"):
                async with session.ws_connect(url + path) as ws:
                    if path.endswith("ws"):
                        await ws.send_json({"jsonrpc": "2.0", "id": 1, "method": "status"})
                    value = await ws.receive_json()
                    pid = value.get("pid") or value["result"]["pid"]
                async with asyncio.timeout(3):
                    while True:
                        try:
                            os.kill(pid, 0)
                        except ProcessLookupError:
                            break
                        await asyncio.sleep(0.005)
        samples.append((await sample(proc.pid))[0])
    _, cpu_before = await sample(proc.pid)
    await asyncio.sleep(2)
    _, cpu_after = await sample(proc.pid)
    print(
        f"\nBridge RSS KiB after each 120-operation batch: {samples}; "
        f"idle CPU seconds: {cpu_after - cpu_before:.3f}"
    )
    # Warm-up/allocator retention is normal; continued growth after warm-up is not.
    assert max(samples[2:]) - min(samples[2:]) < 8 * 1024
    assert samples[-1] - samples[1] < 8 * 1024
    assert cpu_after - cpu_before < 0.2
    assert samples[-1] < 128 * 1024


async def test_idle_keep_alive_connections_do_not_retain_request_bodies(running_server):
    proc, session, url, _ = running_server
    for _ in range(5):
        async with session.post(url + "/v1/chats", json={}) as response:
            await response.read()
    baseline = (await sample(proc.pid))[0]
    peers = []
    body = b"{}" + b" " * (900 * 1024)
    try:
        for _ in range(32):
            peer = ClientSession(headers=session.headers)
            peers.append(peer)
            async with peer.post(
                url + "/v1/chats", data=body, headers={"Content-Type": "application/json"}
            ) as response:
                assert response.status == 200
                await response.read()
        retained = (await sample(proc.pid))[0] - baseline
        print(f"\nRSS growth with 32 idle large-body connections: {retained} KiB")
        assert retained < 12 * 1024
    finally:
        await asyncio.gather(*(peer.close() for peer in peers))
