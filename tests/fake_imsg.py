#!/usr/bin/env python3
"""Only synthetic data. Never imports or launches the real imsg."""

import json
import os
import signal
import sys
import time


def emit(value):
    print(json.dumps(value), flush=True)


command = sys.argv[1]
options = dict(arg[2:].split("=", 1) for arg in sys.argv[2:] if arg.startswith("--") and "=" in arg)
scenario = options.get("db", "")
if scenario == "ignore-term":
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if scenario == "large-json":
    emit({"text": "x" * (8 * 1024 * 1024)})
    sys.exit(0)
if scenario == "descendant":
    read_fd, write_fd = os.pipe()
    descendant = os.fork()
    if descendant == 0:
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        os.close(read_fd)
        for fd in (0, 1, 2):
            os.close(fd)
        os.write(write_fd, b"ready")
        os.close(write_fd)
        while True:
            time.sleep(1)
    os.close(write_fd)
    os.read(read_fd, 5)
    os.close(read_fd)
    emit({"descendant": descendant})
    sys.exit(0)
if scenario == "fail":
    emit({"success": False, "error": "synthetic refusal"})
    print("Full Disk Access required (synthetic)", file=sys.stderr)
    sys.exit(1)
if scenario == "malformed":
    print("not json")
    sys.exit(0)
if scenario == "large":
    print("x" * (17 * 1024 * 1024))
    sys.exit(0)
if scenario == "slow":
    time.sleep(5)
if scenario == "stderr":
    sys.stderr.write("x" * (128 * 1024))
    sys.stderr.flush()
if command == "watch":
    emit({"id": 1, "text": "synthetic", "pid": os.getpid()})
    for event in (
        {"id": 2, "is_reaction": True},
        {"id": 1, "type": "edited"},
        {"id": 1, "type": "unsent"},
        {"kind": "bridge-event", "event": "started-typing", "data": {}},
    ):
        emit(event)
    if scenario == "exit":
        sys.exit(1)
    while True:
        time.sleep(1)
elif command == "rpc":
    for line in sys.stdin:
        request = json.loads(line)
        if "id" not in request:
            continue
        method = request["method"]
        emit(
            {
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {"method": method, "pid": os.getpid()},
            }
        )
        if method == "watch.subscribe":
            emit(
                {
                    "jsonrpc": "2.0",
                    "method": "message",
                    "params": {"subscription": "s", "message": {"id": 2}},
                }
            )
elif command == "completions":
    print("# synthetic completions")
elif command == "chats":
    emit({"id": 1, "name": "Synthetic chat"})
    emit({"id": 2, "name": "Synthetic chat two"})
else:
    emit({"command": command, "argv": sys.argv[2:], "status": "synthetic"})
