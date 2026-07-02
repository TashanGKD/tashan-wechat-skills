#!/usr/bin/env bash
# Install the self-contained skills into an agent skill directory.
# Safe defaults: installs to ./.claude/skills (project-local, NOT global),
# and never overwrites an existing skill unless --force is given.
#
# Usage:
#   bash scripts/install.sh                     # -> ./.claude/skills
#   bash scripts/install.sh ~/.claude/skills    # global (Claude Code)
#   bash scripts/install.sh .cursor/skills      # Cursor
#   bash scripts/install.sh <target> --force    # overwrite same-named skills
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$REPO_ROOT/skills"

TARGET="./.claude/skills"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    *) TARGET="$arg" ;;
  esac
done

if [ ! -d "$SRC" ]; then
  echo "ERROR: skills/ not found at $SRC" >&2; exit 1
fi

mkdir -p "$TARGET"
echo "Installing skills from: $SRC"
echo "Into target:            $TARGET"
[ "$FORCE" = "1" ] && echo "Mode: --force (will overwrite same-named skills)" || echo "Mode: safe (skip existing same-named skills; use --force to overwrite)"
echo

installed=0; skipped=0
for dir in "$SRC"/*/; do
  name="$(basename "$dir")"
  dest="$TARGET/$name"
  if [ -e "$dest" ] && [ "$FORCE" != "1" ]; then
    echo "  skip   $name (already exists; --force to overwrite)"
    skipped=$((skipped+1)); continue
  fi
  rm -rf "$dest"
  cp -R "$dir" "$dest"
  echo "  install $name"
  installed=$((installed+1))
done

echo
echo "Done. installed=$installed skipped=$skipped"
echo "Reminder: start a NEW agent session so the skills are discovered."
echo "Illustration needs an API key: export DASHSCOPE_API_KEY=..."
