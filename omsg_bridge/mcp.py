"""Optional stdio MCP adapter: discover actions on demand, execute via the HTTP bridge."""

import argparse
import base64
import json
import os
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

from aiohttp import ClientSession, ClientTimeout
from mcp.server.fastmcp import Context, FastMCP

from .config import DEFAULT_CONFIG, load_settings


def create_mcp(url, settings):
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.hostname
        or parsed.username
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("URL must be http(s) with no credentials, query or fragment")
    url = url.rstrip("/")
    headers = {}
    if settings.auth_enabled:
        token = base64.b64encode(f"{settings.username}:{settings.password}".encode()).decode()
        headers["Authorization"] = f"Basic {token}"

    async def request(session, path, payload=None):
        async with session.request(
            "GET" if payload is None else "POST", url + path, json=payload, allow_redirects=False
        ) as response:
            # Bound even an accidental response from the wrong service.
            data = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                data.extend(chunk)
                if len(data) > 20 * 1024 * 1024:
                    raise ValueError("Bridge response exceeds 20 MiB")
            if response.status != 200:
                raise ValueError(
                    f"Bridge HTTP {response.status}: {data[:65536].decode(errors='replace')}"
                )
            return json.loads(data)

    @asynccontextmanager
    async def lifespan(_):
        async with ClientSession(
            headers=headers, timeout=ClientTimeout(total=settings.command_timeout + 5)
        ) as session:
            catalog = await request(session, "/v1/commands")
            spec = await request(session, "/docs/openapi.json")
            yield {"session": session, "commands": catalog["commands"], "spec": spec}

    mcp = FastMCP(
        "omsg-bridge",
        lifespan=lifespan,
        log_level="WARNING",
        instructions="Search actions, describe the selected action, then execute. "
        "Actions can send/delete messages and access server files. "
        "Never retry a mutation after an uncertain result without checking history.",
    )

    @mcp.tool(annotations={"readOnlyHint": True})
    async def search_actions(ctx: Context, query: str = "", limit: int = 10) -> list[dict]:
        """Find imsg actions by name or description without loading every input schema."""
        if not 1 <= limit <= 38:
            raise ValueError("limit must be between 1 and 38")
        commands = ctx.request_context.lifespan_context["commands"]
        terms = query.casefold().split()
        return [
            {
                "name": name,
                "summary": spec["description"].split("\n")[0],
                "read_only": spec["read_only"],
                "stream": spec["mode"] == "stream",
            }
            for name, spec in commands.items()
            if all(term in (name + " " + spec["description"]).casefold() for term in terms)
        ][:limit]

    @mcp.tool(annotations={"readOnlyHint": True})
    async def describe_action(name: str, ctx: Context) -> dict:
        """Get one action's exact input schema, CLI options and safety notes."""
        state = ctx.request_context.lifespan_context
        if name not in state["commands"]:
            raise ValueError("Unknown action; use search_actions")
        result = dict(state["commands"][name])
        if name == "watch":
            result["transport"] = "WebSocket /v1/watch (not a finite MCP tool call)"
        else:
            operation = state["spec"]["paths"][f"/v1/{name}"]["post"]
            result["input_schema"] = operation["requestBody"]["content"]["application/json"][
                "schema"
            ]
        if name == "rpc":
            result["discovery"] = (
                'Execute {"jsonrpc":"2.0","id":1,"method":"status"} to discover live methods. '
                "Subscriptions use /v1/rpc/ws."
            )
            result["reference"] = "https://github.com/openclaw/imsg/blob/v0.19.1/docs/rpc.md"
        return result

    @mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "idempotentHint": False})
    async def execute_action(name: str, payload: dict, ctx: Context) -> dict:
        """Execute one discovered action. May send/change/delete messages. No automatic retries."""
        state = ctx.request_context.lifespan_context
        if name not in state["commands"]:
            raise ValueError("Unknown action; use search_actions")
        if name == "watch":
            raise ValueError("Use WebSocket /v1/watch for streams; MCP calls are finite")
        return await request(state["session"], f"/v1/{name}", payload)

    return mcp


def main():
    parser = argparse.ArgumentParser(description="omsg-bridge discovery-based stdio MCP adapter")
    parser.add_argument("--url", default=os.environ.get("OMSG_URL"))
    parser.add_argument("--config", default=DEFAULT_CONFIG)
    args = parser.parse_args()
    try:
        settings = load_settings(args.config)
        mcp = create_mcp(args.url or f"http://127.0.0.1:{settings.port}", settings)
    except (ValueError, OSError) as exc:
        parser.exit(2, f"Configuration error: {exc}\n")
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
