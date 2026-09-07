#!/usr/bin/env bash
set -euo pipefail

REPO="seanbman/dreadnought"
APP="dreadnought"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${HOME}/.local/bin"
MAN_HOME="$DATA_HOME/man/man1"
APP_HOME="$DATA_HOME/$APP"
VENV="$APP_HOME/venv"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOCAL_INSTALL=0

if [[ "${1:-}" == "--local" ]]; then
  LOCAL_INSTALL=1
  shift
fi
if [[ $# -gt 0 ]]; then
  echo "usage: $0 [--local]" >&2
  exit 2
fi

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
if [[ "$LOCAL_INSTALL" -eq 0 ]]; then
  command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }
fi

mkdir -p "$APP_HOME" "$BIN_HOME" "$MAN_HOME"
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip

if [[ "$LOCAL_INSTALL" -eq 1 ]]; then
  echo "Installing Dreadnought from local checkout: $SCRIPT_DIR"
  "$VENV/bin/python" -m pip install --upgrade "$SCRIPT_DIR"
  INSTALLED_LABEL="local checkout"
else
  TAG="${DREADNOUGHT_VERSION:-}"
  if [[ -z "$TAG" ]]; then
    TAG="$(python3 - <<'PY'
import json, urllib.request
url='https://api.github.com/repos/seanbman/dreadnought/releases?per_page=20'
with urllib.request.urlopen(url, timeout=8) as r:
    releases=json.load(r)
for rel in releases:
    if not rel.get('draft'):
        print(rel['tag_name'])
        break
else:
    raise SystemExit('No published Dreadnought release found')
PY
)"
  fi
  echo "Installing Dreadnought $TAG"
  "$VENV/bin/python" -m pip install --upgrade "git+https://github.com/$REPO.git@$TAG"
  INSTALLED_LABEL="$TAG"
fi

ln -sfn "$VENV/bin/dreadnought" "$BIN_HOME/dreadnought"

MAN_SOURCE="$VENV/share/man/man1/dreadnought.1"
if [[ -f "$MAN_SOURCE" ]]; then
  install -m 0644 "$MAN_SOURCE" "$MAN_HOME/dreadnought.1"
elif [[ "$LOCAL_INSTALL" -eq 1 && -f "$SCRIPT_DIR/man/dreadnought.1" ]]; then
  install -m 0644 "$SCRIPT_DIR/man/dreadnought.1" "$MAN_HOME/dreadnought.1"
fi

cat <<EOF
Installed Dreadnought $INSTALLED_LABEL
Launcher: $BIN_HOME/dreadnought
Manual: $MAN_HOME/dreadnought.1

Ensure $BIN_HOME is on PATH. Then run:
  dreadnought
  dreadnought help
  man dreadnought
EOF
