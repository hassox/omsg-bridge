"""Import harmless `imsg completions llm` output; never executes imsg itself."""

import json
import re
import sys
from pathlib import Path

READ_ONLY = {
    "chats",
    "history",
    "group",
    "stats",
    "search",
    "status",
    "scheduled",
    "chat-background",
    "completions",
}


def parse(reference):
    commands = {}
    for block in re.split(r"^### ", reference, flags=re.M)[1:]:
        name, _, body = block.partition("\n")
        description = body.split("Usage:", 1)[0].strip()
        options = {}
        for names, help_text in re.findall(r"^- `([^`]+)`: (.*)$", body, flags=re.M):
            longs = re.findall(r"--([\w-]+)", names)
            if not longs or "json" in longs:
                continue
            options[longs[0]] = {
                "type": "value" if "<value>" in names else "flag",
                "description": help_text,
                "aliases": longs[1:],
            }
        args = re.findall(r"^- `(\w+)`( optional)?: (.*)$", body, flags=re.M)
        commands[name] = {
            "description": description,
            "options": options,
            "arguments": [{"name": a, "optional": bool(b), "description": c} for a, b, c in args],
            "read_only": name in READ_ONLY,
            "mode": "stream"
            if name in {"watch", "rpc"}
            else "text"
            if name == "completions"
            else "json",
        }
    if len(commands) != 38 or not commands["poll"]["arguments"]:
        raise ValueError("Unexpected imsg reference format; review upstream changes")
    return commands


if __name__ == "__main__":
    result = {
        "upstream": "imsg v0.19.1 (Homebrew release)",
        "commands": parse(Path(sys.argv[1]).read_text()),
    }
    Path(sys.argv[2]).write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
