"""Create private per-user settings and an optional launchd plist (never sends messages)."""

import argparse
import json
import os
import plistlib
import secrets
from pathlib import Path


def configure(home, imsg, executable=None):
    home = Path(home)
    settings = home / ".config/omsg-bridge/settings.toml"
    settings.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    try:
        fd = os.open(settings, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        print(f"Preserving existing settings: {settings}")
    else:
        with os.fdopen(fd, "w") as stream:
            stream.write(
                'host = "127.0.0.1"\nport = 8787\n'
                f"imsg = {json.dumps(str(imsg))}\ncommand_timeout = 60\n\n"
                '[auth]\nenabled = true\nusername = "bridge"\n'
                f'password = "{secrets.token_urlsafe(32)}"\n'
            )
        print(f"Created private credentials in {settings}; password is not printed.")
    if executable:
        logs = home / "Library/Logs/omsg-bridge"
        logs.mkdir(parents=True, exist_ok=True, mode=0o700)
        path = home / "Library/LaunchAgents/local.omsg-bridge.plist"
        path.parent.mkdir(parents=True, exist_ok=True)
        # Only this application's plist is updated, never another launch agent.
        data = {
            "Label": "local.omsg-bridge",
            "ProgramArguments": [str(executable)],
            "RunAtLoad": True,
            "KeepAlive": True,
            "ThrottleInterval": 10,
            "EnvironmentVariables": {"PATH": "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin"},
            "StandardOutPath": str(logs / "stdout.log"),
            "StandardErrorPath": str(logs / "stderr.log"),
        }
        with open(path, "wb") as stream:
            os.chmod(path, 0o600)
            plistlib.dump(data, stream)
        print(f"Login service configured: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--imsg", required=True)
    parser.add_argument("--executable")
    args = parser.parse_args()
    configure(Path.home(), args.imsg, args.executable)
