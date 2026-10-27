import asyncio
import json
import os
import signal
from contextlib import asynccontextmanager

from .catalog import COMMANDS, build_argv
from .errors import APIError

MAX_RECORD = 1024 * 1024
MAX_OUTPUT = 16 * 1024 * 1024
MAX_STDERR = 64 * 1024


def records(raw):
    if not raw.strip():
        return []
    try:
        return [json.loads(raw)]
    except ValueError:
        try:
            return [json.loads(line) for line in raw.splitlines() if line.strip()]
        except ValueError as exc:
            raise APIError(
                502, "invalid_output", "imsg stdout was not JSON", retry_safe=False
            ) from exc


class Child:
    def __init__(self, process):
        self.process = process
        self.stderr = bytearray()
        self.stderr_task = asyncio.create_task(self.drain_stderr())

    async def drain_stderr(self):
        while chunk := await self.process.stderr.read(8192):
            self.stderr.extend(chunk[: max(0, MAX_STDERR - len(self.stderr))])

    def diagnostics(self):
        return self.stderr.decode("utf-8", errors="replace")

    async def stop(self):
        # Terminate this child's process group, not Messages.app or unrelated processes.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass

        async def discard_stdout():
            while await self.process.stdout.read(65536):
                pass

        drain = asyncio.create_task(discard_stdout())
        try:
            async with asyncio.timeout(1):
                await asyncio.shield(self.process.wait())
        except TimeoutError:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            await self.process.wait()
        finally:
            drain.cancel()
            await asyncio.gather(drain, return_exceptions=True)
        self.stderr_task.cancel()
        await asyncio.gather(self.stderr_task, return_exceptions=True)

    async def line(self):
        try:
            line = await self.process.stdout.readline()
        except ValueError as exc:
            raise APIError(
                502, "output_limit", "imsg record exceeds 1 MiB", retry_safe=False
            ) from exc
        if not line:
            await self.process.wait()
            await self.stderr_task
            raise APIError(
                502,
                "stream_ended",
                "imsg stream exited; reconnect and refresh history",
                exit_code=self.process.returncode,
                stderr=self.diagnostics(),
                retry_safe=False,
            )
        try:
            return json.loads(line)
        except ValueError as exc:
            raise APIError(
                502, "invalid_output", "imsg stream record was not JSON", retry_safe=False
            ) from exc


class Bridge:
    def __init__(self, settings):
        self.settings = settings
        self.children = set()
        self.tasks = set()

    @asynccontextmanager
    async def spawn(self, argv):
        try:
            process = await asyncio.create_subprocess_exec(
                self.settings.imsg,
                *argv,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=MAX_RECORD,
                start_new_session=True,
            )
        except OSError as exc:
            raise APIError(
                503,
                "imsg_unavailable",
                "Cannot execute imsg. Install with: brew install steipete/tap/imsg; "
                "check the imsg setting and executable permissions.",
                retry_safe=True,
            ) from exc
        child = Child(process)
        self.children.add(child)
        task = asyncio.current_task()
        self.tasks.add(task)
        try:
            yield child
        finally:
            await child.stop()
            self.children.discard(child)
            self.tasks.discard(task)

    async def close(self):
        tasks = tuple(self.tasks)
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def execute(self, command, payload):
        argv = build_argv(command, payload)
        try:
            async with self.spawn(argv) as child:
                child.process.stdin.close()
                async with asyncio.timeout(self.settings.command_timeout):
                    output = bytearray()
                    while chunk := await child.process.stdout.read(65536):
                        output.extend(chunk)
                        if len(output) > MAX_OUTPUT:
                            raise APIError(
                                502,
                                "output_limit",
                                "imsg output exceeds 16 MiB; use a smaller limit",
                                retry_safe=False,
                            )
                    await child.process.wait()
                    await child.stderr_task
                raw = output.decode("utf-8", errors="replace")
                if child.process.returncode:
                    try:
                        data = records(raw)
                    except APIError:
                        data = [raw[:MAX_STDERR]]
                    raise APIError(
                        502,
                        "imsg_failed",
                        "imsg command failed; inspect diagnostics before retrying",
                        exit_code=child.process.returncode,
                        data=data,
                        stderr=child.diagnostics(),
                        retry_safe=False,
                    )
                return {
                    "data": [raw] if COMMANDS[command]["mode"] == "text" else records(raw),
                    "stderr": child.diagnostics(),
                }
        except TimeoutError as exc:
            raise APIError(
                504,
                "timeout",
                "imsg timed out; a mutation may have completed. Do not retry automatically.",
                retry_safe=False,
            ) from exc

    async def rpc(self, request, options):
        validate_rpc(request, require_id=True)
        if request["method"] in {"watch.subscribe", "watch.unsubscribe", "bridge.events.subscribe"}:
            raise ValueError(
                "Subscriptions require /v1/rpc/ws and stay within that WebSocket session"
            )
        try:
            async with self.spawn(build_argv("rpc", {"options": options})) as child:
                async with asyncio.timeout(self.settings.command_timeout):
                    child.process.stdin.write(json.dumps(request).encode() + b"\n")
                    await child.process.stdin.drain()
                    while True:
                        response = await child.line()
                        if isinstance(response, dict) and response.get("id") == request["id"]:
                            return response
        except TimeoutError as exc:
            raise APIError(
                504,
                "timeout",
                "imsg RPC timed out; outcome may be unknown. Do not retry automatically.",
                retry_safe=False,
            ) from exc


def validate_rpc(request, require_id=False):
    if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
        raise ValueError("Expected one JSON-RPC 2.0 object")
    if not isinstance(request.get("method"), str) or not request["method"]:
        raise ValueError("RPC method must be a nonempty string")
    if "params" in request and not isinstance(request["params"], dict):
        raise ValueError("RPC params must be an object")
    if require_id and "id" not in request:
        raise ValueError("REST RPC requires an id; use WebSocket for notifications")
    if "id" in request and type(request["id"]) not in (str, int, float, type(None)):
        raise ValueError("Invalid RPC id")
