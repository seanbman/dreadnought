#!/usr/bin/env bash
set -euo pipefail

REPO="seanbman/dreadnought"
APP="dreadnought"
DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
BIN_HOME="${HOME}/.local/bin"
APP_HOME="$DATA_HOME/$APP"
VENV="$APP_HOME/venv"

command -v python3 >/dev/null 2>&1 || { echo "python3 is required" >&2; exit 1; }
command -v curl >/dev/null 2>&1 || { echo "curl is required" >&2; exit 1; }

mkdir -p "$APP_HOME" "$BIN_HOME"

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
python3 -m venv "$VENV"
"$VENV/bin/python" -m pip install --upgrade pip
"$VENV/bin/python" -m pip install --upgrade "git+https://github.com/$REPO.git@$TAG"
ln -sfn "$VENV/bin/dreadnought" "$BIN_HOME/dreadnought"

cat <<EOF
Installed Dreadnought $TAG
Launcher: $BIN_HOME/dreadnought

Ensure $BIN_HOME is on PATH. Then run:
  dreadnought
EOF
