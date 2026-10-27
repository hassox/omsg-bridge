import argparse
import asyncio
import hmac
import logging
import shutil
from urllib.parse import urlsplit

from aiohttp import BasicAuth, web
from swagger_ui_bundle import swagger_ui_path

from . import __version__
from .catalog import CATALOG, COMMANDS, openapi, query_payload
from .config import DEFAULT_CONFIG, Settings, load_settings
from .errors import APIError
from .process import Bridge
from .streams import SOCKETS, close_socket, stream

SETTINGS = web.AppKey("settings", Settings)
BRIDGE = web.AppKey("bridge", Bridge)
REQUESTS = web.AppKey("requests", set)


@web.middleware
async def resources(request, handler):
    if request.path == "/health":
        return await handler(request)
    active = request.app[REQUESTS]
    if request.app[BRIDGE].closing or len(active) >= 8:
        return web.json_response(
            {
                "error": {
                    "code": "busy",
                    "message": "Server is busy or shutting down",
                    "retry_safe": True,
                }
            },
            status=503,
        )
    task = asyncio.current_task()
    active.add(task)
    try:
        response = await handler(request)
        if not isinstance(response, web.WebSocketResponse):
            try:
                async with asyncio.timeout(10):
                    await response.prepare(request)
                    await response.write_eof()
            except TimeoutError:
                if request.transport is not None:
                    request.transport.close()
            finally:
                # aiohttp retains the last response while its connection is idle.
                if isinstance(response, web.Response):
                    response.body = None
        return response
    finally:
        active.discard(task)


@web.middleware
async def boundary(request, handler):
    try:
        origin = request.headers.get("Origin")
        if origin and (
            urlsplit(origin).scheme != request.scheme or urlsplit(origin).netloc != request.host
        ):
            raise APIError(403, "cross_origin", "Cross-origin browser requests are not allowed")
        settings = request.app[SETTINGS]
        if settings.auth_enabled:
            try:
                auth = BasicAuth.decode(request.headers.get("Authorization", ""), encoding="utf-8")
                valid = hmac.compare_digest(
                    auth.login.encode(), settings.username.encode()
                ) & hmac.compare_digest(auth.password.encode(), settings.password.encode())
            except ValueError:
                valid = False
            if not valid:
                return web.json_response(
                    {"error": {"code": "unauthorized", "message": "Basic Auth required"}},
                    status=401,
                    headers={
                        "WWW-Authenticate": 'Basic realm="omsg-bridge", charset="UTF-8"',
                        "Cache-Control": "no-store",
                    },
                )
        response = await handler(request)
    except APIError as exc:
        response = web.json_response(exc.payload, status=exc.status)
    except (ValueError, TypeError) as exc:
        response = web.json_response(
            {"error": {"code": "invalid_request", "message": str(exc)}}, status=400
        )
    except web.HTTPException as exc:
        response = web.json_response(
            {"error": {"code": "http_error", "message": exc.reason}}, status=exc.status
        )
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


async def health(request):
    return web.json_response(
        {
            "status": "ok",
            "version": __version__,
            "imsg_available": shutil.which(request.app[SETTINGS].imsg) is not None,
        }
    )


async def spec(request):
    return web.json_response(openapi())


async def commands(request):
    return web.json_response(CATALOG)


async def docs(request):
    return web.Response(
        text="""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>omsg-bridge API</title><meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/docs/assets/swagger-ui.css"></head><body>
<div id="swagger-ui"></div><script src="/docs/assets/swagger-ui-bundle.js"></script>
<script src="/docs/init.js"></script></body></html>""",
        content_type="text/html",
    )


async def docs_init(request):
    return web.Response(
        text="""SwaggerUIBundle({url: "/docs/openapi.json", dom_id: "#swagger-ui",
validatorUrl: null, persistAuthorization: false});""",
        content_type="text/javascript",
    )


async def json_body(request):
    if request.content_type != "application/json":
        raise web.HTTPUnsupportedMediaType(reason="Use Content-Type: application/json")
    try:
        async with asyncio.timeout(10):
            return await request.json()
    except TimeoutError as exc:
        raise web.HTTPRequestTimeout(
            reason="Request body did not arrive within 10 seconds"
        ) from exc


async def command(request):
    name = request.match_info["command"]
    payload = (
        query_payload(name, request.query) if request.method == "GET" else await json_body(request)
    )
    return web.json_response(await request.app[BRIDGE].execute(name, payload))


async def rpc(request):
    payload = await json_body(request)
    options = query_payload("rpc", request.query)["options"]
    return web.json_response(await request.app[BRIDGE].rpc(payload, options))


async def watch(request):
    return await stream(request, request.app[BRIDGE])


async def rpc_websocket(request):
    return await stream(request, request.app[BRIDGE], rpc=True)


async def shutdown(app):
    app[BRIDGE].closing = True
    try:
        await asyncio.gather(
            *(close_socket(ws, transport) for ws, transport in tuple(app[SOCKETS].items()))
        )
    finally:
        await app[BRIDGE].close()


def create_app(settings):
    settings.validate()
    app = web.Application(middlewares=[resources, boundary], client_max_size=1024 * 1024)
    app[SETTINGS] = settings
    app[BRIDGE] = Bridge(settings)
    app[SOCKETS] = {}
    app[REQUESTS] = set()
    app.on_shutdown.append(shutdown)
    app.add_routes(
        [
            web.get("/health", health),
            web.get("/v1/commands", commands),
            web.get("/docs/openapi.json", spec),
            web.get("/docs/ui", docs),
            web.get("/docs/init.js", docs_init),
        ]
    )
    app.router.add_static("/docs/assets", swagger_ui_path)
    app.router.add_post("/v1/rpc", rpc)
    app.router.add_get("/v1/watch", watch)
    app.router.add_get("/v1/rpc/ws", rpc_websocket)
    for name, definition in COMMANDS.items():
        if definition["mode"] == "stream":
            continue
        path = "/v1/{command:" + name + "}"
        app.router.add_post(path, command)
        if definition["read_only"]:
            app.router.add_get(path, command)
    return app


def main():
    parser = argparse.ArgumentParser(description="Async REST/WebSocket bridge over imsg")
    parser.add_argument("--config", default=DEFAULT_CONFIG, help="Settings TOML path")
    args = parser.parse_args()
    try:
        settings = load_settings(args.config)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    logging.basicConfig(level=logging.WARNING)
    web.run_app(
        create_app(settings),
        host=settings.host,
        port=settings.port,
        access_log=None,
        print=None,
        handler_cancellation=True,
    )


if __name__ == "__main__":
    main()
