"""Exercise the installer shell in a private HOME with mock host commands."""

import os
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest


@pytest.fixture
def host(tmp_path):
    home = tmp_path / "home with spaces"
    home.mkdir()
    binary = tmp_path / "bin"
    binary.mkdir()
    log = tmp_path / "commands.txt"

    def executable(name, text):
        path = binary / name
        path.write_text(text)
        path.chmod(0o700)

    executable("uname", "#!/bin/sh\nprintf 'Darwin\\n'\n")
    executable(
        "brew",
        """#!/bin/sh
printf 'brew %s\\n' "$*" >> "$TEST_LOG"
printf '#!/bin/sh\\nprintf "synthetic-imsg\\\\n"\\n' > "$TEST_BIN/imsg"
chmod +x "$TEST_BIN/imsg"
""",
    )
    executable(
        "launchctl",
        """#!/bin/sh
printf 'launchctl %s\\n' "$*" >> "$TEST_LOG"
case "$1" in print) [ "${TEST_LOADED:-0}" = 1 ] ;; *) exit 0 ;; esac
""",
    )
    executable(
        "python3",
        f"""#!{sys.executable}
import os, pathlib, shutil, sys
if sys.argv[1:3] == ["-m", "venv"]:
    binary = pathlib.Path(sys.argv[3]) / "bin"
    binary.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(__file__, binary / "python")
    (binary / "python").chmod(0o700)
    (binary / "omsg-bridge").write_text("#!/bin/sh\\nexit 0\\n")
elif sys.argv[1:3] == ["-m", "pip"]:
    with open(os.environ["TEST_LOG"], "a") as log:
        log.write("pip " + " ".join(sys.argv[2:]) + "\\n")
else:
    os.execv(sys.executable, [sys.executable, *sys.argv[1:]])
""",
    )
    env = {
        **os.environ,
        "HOME": str(home),
        "PATH": f"{binary}:/usr/bin:/bin",
        "TEST_BIN": str(binary),
        "TEST_LOG": str(log),
    }
    env.pop("PORT", None)
    env.pop("OMSG_USERNAME", None)
    env.pop("OMSG_PASSWORD", None)
    return home, binary, log, env


def run_install(env, *args):
    return subprocess.run(
        ["/bin/sh", str(Path("scripts/install.sh").resolve()), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=15,
    )


def test_install_checks_brew_preserves_settings_and_restarts_only_own_job(host):
    home, _, log, env = host
    result = run_install(env)
    assert result.returncode == 0, result.stderr
    settings = home / ".config/omsg-bridge/settings.toml"
    original = settings.read_bytes()
    assert "brew install steipete/tap/imsg" in log.read_text()
    assert "launchctl" not in log.read_text()
    assert (home / ".local/bin/omsg-bridge").is_symlink()
    result = run_install({**env, "TEST_LOADED": "1"}, "--login")
    assert result.returncode == 0, result.stderr
    assert settings.read_bytes() == original
    calls = log.read_text()
    assert calls.count("brew install") == 1
    assert "launchctl bootout gui/" in calls and "/local.omsg-bridge" in calls
    assert "launchctl bootstrap gui/" in calls
    assert tomllib.loads(settings.read_text())["auth"]["password"] not in result.stdout


def test_install_refuses_to_overwrite_unrelated_executable(host):
    home, _, _, env = host
    link = home / ".local/bin/omsg-bridge"
    link.parent.mkdir(parents=True)
    link.write_text("existing user data")
    result = run_install(env)
    assert result.returncode == 1
    assert "Refusing to overwrite" in result.stderr
    assert link.read_text() == "existing user data"
