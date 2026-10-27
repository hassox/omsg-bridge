import importlib.util
import plistlib
import stat
from pathlib import Path

import pytest


@pytest.fixture
def installer():
    spec = importlib.util.spec_from_file_location("installer", "scripts/configure.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_install_creates_private_settings_and_preserves_existing(tmp_path, installer):
    path = tmp_path / ".config/omsg-bridge/settings.toml"
    installer.configure(tmp_path, "/opt/homebrew/bin/imsg")
    original = path.read_bytes()
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert b'username = "bridge"' in original
    installer.configure(tmp_path, "/different/imsg")
    assert path.read_bytes() == original
    assert not list(tmp_path.glob("Library/LaunchAgents/*"))


def test_login_plist_is_safe_and_contains_no_credentials(tmp_path, installer):
    executable = tmp_path / "path with spaces" / "omsg-bridge"
    installer.configure(tmp_path, "/opt/homebrew/bin/imsg", executable)
    path = tmp_path / "Library/LaunchAgents/local.omsg-bridge.plist"
    data = plistlib.loads(path.read_bytes())
    assert data["ProgramArguments"] == [str(executable)]
    assert data["RunAtLoad"] and data["KeepAlive"]
    assert "password" not in path.read_text()
    assert Path(data["StandardErrorPath"]).is_relative_to(tmp_path)
    assert stat.S_IMODE(path.stat().st_mode) == 0o600
