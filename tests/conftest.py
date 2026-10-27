import shlex
import sys
from pathlib import Path

import pytest

from omsg_bridge.config import Settings
from omsg_bridge.server import create_app


@pytest.fixture
def fake_imsg(tmp_path):
    # A real executable subprocess, always pinned to this test interpreter.
    executable = tmp_path / "imsg"
    fixture = Path(__file__).with_name("fake_imsg.py").resolve()
    executable.write_text(
        f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(fixture))} "$@"\n'
    )
    executable.chmod(0o700)
    return str(executable)


@pytest.fixture
async def client(aiohttp_client, fake_imsg):
    return await aiohttp_client(create_app(Settings(imsg=fake_imsg, auth_enabled=False)))
