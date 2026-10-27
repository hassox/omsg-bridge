#!/bin/sh
set -eu
umask 077
login=false
case "${1:-}" in
  '') ;;
  --login) login=true ;;
  *) printf 'Usage: %s [--login]\n' "$0" >&2; exit 2 ;;
esac
[ "$#" -le 1 ] || exit 2
[ "$(uname -s)" = Darwin ] || { echo 'The server installer requires macOS.' >&2; exit 1; }
command -v brew >/dev/null || { echo 'Install Homebrew from https://brew.sh first.' >&2; exit 1; }
if ! command -v imsg >/dev/null; then
  brew install steipete/tap/imsg
fi
imsg_path=$(command -v imsg)
"$imsg_path" --version
python=python3
if ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
  brew install python@3.13
  python="$(brew --prefix python@3.13)/bin/python3.13"
fi
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
venv="$HOME/.local/share/omsg-bridge/venv"
"$python" -m venv "$venv"
"$venv/bin/python" -m pip install "$repo"
mkdir -p "$HOME/.local/bin"
link="$HOME/.local/bin/omsg-bridge"
if [ -e "$link" ] || [ -L "$link" ]; then
  [ "$(readlink "$link" || true)" = "$venv/bin/omsg-bridge" ] || {
    echo "Refusing to overwrite existing $link" >&2; exit 1;
  }
else
  ln -s "$venv/bin/omsg-bridge" "$link"
fi
if [ "$login" = true ]; then
  "$venv/bin/python" "$repo/scripts/configure.py" --imsg "$imsg_path" --executable "$venv/bin/omsg-bridge"
  "$venv/bin/python" -c 'from omsg_bridge.config import load_settings; load_settings()'
  service="gui/$(id -u)/local.omsg-bridge"
  if launchctl print "$service" >/dev/null 2>&1; then
    launchctl bootout "$service"
  fi
  launchctl bootstrap "gui/$(id -u)" "$HOME/Library/LaunchAgents/local.omsg-bridge.plist"
else
  "$venv/bin/python" "$repo/scripts/configure.py" --imsg "$imsg_path"
fi
printf '\nInstalled. Run: %s\nSettings: %s\n' "$link" "$HOME/.config/omsg-bridge/settings.toml"
printf 'Grant Full Disk Access to the actual service executable/launcher in System Settings.\n'
printf 'No messages were sent. Private IMCore features were not enabled.\n'
