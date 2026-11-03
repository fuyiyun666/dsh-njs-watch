#!/usr/bin/env bash
# install.sh -- one-shot installer for dsh-njs-watch (macOS / Linux)
# Usage:  bash install.sh [profile]
set -e
PROFILE="${1:-desktop}"
SPEC="https://github.com/fuyiyun666/dsh-njs-watch/releases/download/v0.1.0/dsh-njs-watch-0.1.0.tgz"

echo "[1/3] Python dependencies..."
PY="$(command -v python3 || command -v python)"
[ -n "$PY" ] || { echo "Python not found. Install Python 3.10+ first."; exit 1; }
"$PY" -m pip install --upgrade numpy pillow opencv-python

echo "[2/3] Installing plugin into profile '$PROFILE'..."
dsh plugin --profile "$PROFILE" add "$SPEC"

echo "[3/3] Enabling in profile patch..."
DIR="$HOME/.dsh/profiles/$PROFILE"
PATCH="$DIR/cordis.patch.yml"
mkdir -p "$DIR"
if ! grep -q "njs-watch" "$PATCH" 2>/dev/null; then
  cat >> "$PATCH" <<'YAML'
- insert:
    - id: njs-watch
      name: 'dsh-njs-watch'
      config:
        ocr: true
        maxSeconds: 120
YAML
  echo "  added entry to $PATCH"
else
  echo "  entry already present in $PATCH"
fi

echo ""
echo "Done. Restart DSH, then check for tools: watch_screen / watch_file / watch_note / watch_clean"
