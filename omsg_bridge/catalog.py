import json
import math
from importlib.resources import files

from . import __version__

CATALOG = json.loads(files("omsg_bridge").joinpath("commands.json").read_text())
COMMANDS = CATALOG["commands"]


def build_argv(command, payload):
    if command not in COMMANDS:
        raise ValueError(f"Unknown command: {command}")
    if not isinstance(payload, dict) or set(payload) - {"args", "options"}:
        raise ValueError("Expected an object with args and/or options")
    spec = COMMANDS[command]
    args, options = payload.get("args", []), payload.get("options", {})
    if (
        not isinstance(args, list)
        or len(args) > len(spec["arguments"])
        or any(not isinstance(arg, str) or arg.startswith("-") or "\0" in arg for arg in args)
    ):
        raise ValueError("Invalid positional args; see command discovery")
    if not isinstance(options, dict) or set(options) - spec["options"].keys():
        raise ValueError("Unknown options; use documented long names without --")
    argv = [command] + ([] if command == "completions" else ["--json"])
    for name, value in options.items():
        if spec["options"][name]["type"] == "flag":
            if type(value) is not bool:
                raise ValueError(f"{name} must be a boolean")
            if value:
                argv.append(f"--{name}")
        else:
            values = value if isinstance(value, list) else [value]
            if not values:
                raise ValueError(f"{name} cannot be an empty array")
            for item in values:
                if type(item) not in (str, int, float) or (
                    isinstance(item, float) and not math.isfinite(item)
                ):
                    raise ValueError(f"{name} must be a string, number, or array of those")
                if "\0" in str(item):
                    raise ValueError(f"{name} contains a NUL byte")
                # Equals prevents values such as --help from becoming CLI flags.
                argv.append(f"--{name}={item}")
    return argv + (["--", *args] if args else [])


def query_payload(command, query):
    options = {}
    for name in query:
        if name == "arg":
            continue
        if name not in COMMANDS[command]["options"]:
            raise ValueError(f"Unknown option: {name}")
        values = query.getall(name)
        if COMMANDS[command]["options"][name]["type"] == "flag":
            if len(values) != 1 or values[0] not in {"true", "false"}:
                raise ValueError(f"{name} must be true or false")
            options[name] = values[0] == "true"
        else:
            options[name] = values[0] if len(values) == 1 else values
    return {"args": query.getall("arg", []), "options": options}


def input_schema(name):
    if name == "rpc":
        return {
            "type": "object",
            "required": ["jsonrpc", "id", "method"],
            "properties": {
                "jsonrpc": {"type": "string", "enum": ["2.0"]},
                "id": {"oneOf": [{"type": "string", "nullable": True}, {"type": "number"}]},
                "method": {"type": "string"},
                "params": {"type": "object"},
            },
        }
    properties = {}
    for key, option in COMMANDS[name]["options"].items():
        properties[key] = {"description": option["description"]}
        if option["type"] == "flag":
            properties[key]["type"] = "boolean"
        else:
            properties[key]["oneOf"] = [
                {"type": "string"},
                {"type": "number"},
                {
                    "type": "array",
                    "minItems": 1,
                    "items": {"oneOf": [{"type": "string"}, {"type": "number"}]},
                },
            ]
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "args": {
                "type": "array",
                "items": {"type": "string"},
                "maxItems": len(COMMANDS[name]["arguments"]),
                "description": "; ".join(a["description"] for a in COMMANDS[name]["arguments"]),
            },
            "options": {"type": "object", "additionalProperties": False, "properties": properties},
        },
    }


def openapi():
    responses = {
        "200": {
            "description": "Success; upstream records are not rewritten",
            "content": {"application/json": {"schema": {"type": "object"}}},
        }
    }
    for status, description in {
        400: "Invalid request",
        401: "Basic Auth required",
        403: "Cross-origin request rejected",
        408: "Request body timeout",
        413: "Request payload too large",
        415: "Use application/json",
        502: "imsg failed or returned invalid output",
        503: "imsg unavailable, busy (8 slots), or shutting down",
        504: "Timed out; mutation outcome may be unknown",
    }.items():
        responses[str(status)] = {
            "description": description,
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "required": ["error"],
                        "properties": {
                            "error": {
                                "type": "object",
                                "properties": {
                                    "code": {"type": "string"},
                                    "message": {"type": "string"},
                                    "retry_safe": {"type": "boolean"},
                                },
                            }
                        },
                    }
                }
            },
        }
    paths = {
        "/health": {"get": {"summary": "Liveness; no database access", "responses": responses}},
        "/v1/commands": {"get": {"summary": "Command discovery", "responses": responses}},
    }
    for name, spec in COMMANDS.items():
        command_responses = (
            responses
            if name == "rpc"
            else {
                **responses,
                "200": {
                    "description": "Unmodified upstream records; completions returns one string",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "required": ["data", "stderr"],
                                "properties": {
                                    "data": {"type": "array", "items": {}},
                                    "stderr": {
                                        "type": "string",
                                        "description": "Diagnostics (at most 64 KiB)",
                                    },
                                },
                            }
                        }
                    },
                },
            }
        )
        path = f"/v1/{name}"
        if name == "watch":
            paths[path] = {
                "get": {
                    "summary": "WebSocket: imsg watch NDJSON",
                    "responses": {"101": {"description": "WebSocket upgraded"}, **responses},
                }
            }
        else:
            paths[path] = {
                "post": {
                    "summary": spec["description"].split("\n")[0],
                    "description": spec["description"],
                    "operationId": name.replace("-", "_"),
                    "requestBody": {
                        "required": True,
                        "content": {"application/json": {"schema": input_schema(name)}},
                    },
                    "responses": command_responses,
                }
            }
        if spec["read_only"] or name == "watch":
            parameters = [
                {
                    "name": key,
                    "in": "query",
                    "description": option["description"],
                    "schema": {"type": "boolean" if option["type"] == "flag" else "string"},
                }
                for key, option in spec["options"].items()
            ]
            if spec["arguments"]:
                parameters.append(
                    {
                        "name": "arg",
                        "in": "query",
                        "schema": {"type": "string"},
                        "description": spec["arguments"][0]["description"],
                    }
                )
            paths[path]["get"] = {
                **paths[path].get("get", {}),
                "summary": spec["description"].split("\n")[0],
                "parameters": parameters,
                "responses": paths[path].get("get", {}).get("responses", command_responses),
            }
    paths["/v1/rpc"]["post"]["parameters"] = [
        {
            "name": key,
            "in": "query",
            "description": option["description"],
            "schema": {"type": "boolean" if option["type"] == "flag" else "string"},
        }
        for key, option in COMMANDS["rpc"]["options"].items()
    ]
    paths["/v1/rpc/ws"] = {
        "get": {
            "summary": "WebSocket: bidirectional JSON-RPC with subscriptions",
            "parameters": paths["/v1/rpc"]["post"]["parameters"],
            "responses": {"101": {"description": "WebSocket upgraded"}, **responses},
        }
    }
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "omsg-bridge",
            "version": __version__,
            "description": "Thin imsg wrapper. Basic Auth over HTTP needs a trusted LAN or TLS. "
            "File paths refer to the server. Mutations are never retried.",
        },
        "security": [{"basicAuth": []}],
        "components": {"securitySchemes": {"basicAuth": {"type": "http", "scheme": "basic"}}},
        "paths": paths,
    }
