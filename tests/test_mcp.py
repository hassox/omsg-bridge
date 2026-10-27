import json
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_real_stdio_discovery_and_execution(client, tmp_path):
    config = tmp_path / "settings.toml"
    config.write_text("[auth]\nenabled = false\n")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "omsg_bridge.mcp", "--url", str(client.make_url("/")), "--config", str(config)],
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            listed = await session.list_tools()
            assert {tool.name for tool in listed.tools} == {
                "search_actions",
                "describe_action",
                "execute_action",
            }
            result = await session.call_tool("search_actions", {"query": "reaction"})
            assert not result.isError
            text = " ".join(block.text for block in result.content)
            assert "react" in text
            result = await session.call_tool("describe_action", {"name": "send"})
            assert "chat-id" in str(result)
            result = await session.call_tool(
                "execute_action", {"name": "chats", "payload": {"options": {"limit": 2}}}
            )
            assert not result.isError
            body = json.loads(result.content[0].text)
            assert len(body["data"]) == 2
            result = await session.call_tool("execute_action", {"name": "watch", "payload": {}})
            assert result.isError
            result = await session.call_tool(
                "execute_action", {"name": "history", "payload": {"options": {"db": "fail"}}}
            )
            assert result.isError
            assert "Full Disk Access" in str(result)
