#!/usr/bin/env bash
# Build the v0.1.0 retail zip. Does NOT publish anywhere.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$(tr -d '[:space:]' < "$ROOT/VERSION" 2>/dev/null || echo 0.1.0)"
NAME="tokenguard-CODING-AGENT-TOKEN-GUARD-v${VERSION}"
DIST="$ROOT/dist"
STAGE="$(mktemp -d "${TMPDIR:-/tmp}/tokenguard-release.XXXXXX")"
trap 'rm -rf "$STAGE"' EXIT

mkdir -p "$DIST"
DEST="$STAGE/$NAME"
mkdir -p "$DEST"

tar -C "$ROOT" \
  --exclude='.venv' \
  --exclude='data' \
  --exclude='dist' \
  --exclude='.git' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='*.db' \
  --exclude='.pytest_cache' \
  --exclude='*.egg-info' \
  -cf - . | tar -C "$DEST" -xf -

chmod +x "$DEST/install.sh" "$DEST/run.sh" \
  "$DEST/hooks/pre_tool_use.sh" \
  "$DEST/claude-plugin/scripts/pre_tool_use.sh" \
  "$DEST/packaging/build_release.sh" \
  "$DEST/vendor/loop_stop/hooks/pre_tool_use.sh" \
  "$DEST/claude-plugin/vendor/loop_stop/hooks/pre_tool_use.sh" 2>/dev/null || true

ZIP="$DIST/${NAME}.zip"
rm -f "$ZIP"

python3 - "$STAGE" "$NAME" "$ZIP" <<'PY'
import os, stat, sys, zipfile
from pathlib import Path
stage, name, zip_path = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
root = stage / name
with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        arc = str(path.relative_to(stage))
        info = zipfile.ZipInfo.from_file(path, arcname=arc)
        mode = path.stat().st_mode
        # Create Unix file with mode in high 16 bits
        info.create_system = 3  # Unix
        info.external_attr = (stat.S_IFREG | (mode & 0o7777)) << 16
        with open(path, "rb") as f:
            zf.writestr(info, f.read())
size = os.path.getsize(zip_path)
print(f"Built: {zip_path}")
print(f"Size: {size} bytes ({size/1024:.1f} KiB)")
zf = zipfile.ZipFile(zip_path)
bad = [i.filename for i in zf.infolist()
       if "/.venv/" in i.filename or i.filename.endswith(".db") or "__pycache__" in i.filename]
if bad:
    raise SystemExit("ERROR: zip contains excluded paths: " + ", ".join(bad[:5]))
print("Exclusions OK")
print(f"Files: {len(zf.namelist())}")
for n in zf.namelist()[:25]:
    print(" ", n)
print(" ...")
PY
ls -lh "$ZIP"
