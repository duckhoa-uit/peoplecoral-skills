#!/usr/bin/env bash
# Link the PeopleCoral skills into user scope on this machine.
# Canonical: ~/.agents/skills/<name>
# Claude/Cursor: ~/.claude/skills/<name> and ~/.cursor/skills/<name>
#   -> ../../.agents/skills/<name>
#
# Usage: ./install.sh [--replace]
#   --replace  overwrite an existing real directory of the same name
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC="$REPO/skills"
AGENTS="${HOME}/.agents/skills"
CLAUDE="${HOME}/.claude/skills"
CURSOR="${HOME}/.cursor/skills"
REPLACE=0
[[ "${1:-}" == "--replace" ]] && REPLACE=1

mkdir -p "$AGENTS" "$CLAUDE" "$CURSOR"

link_relative() {
  local name="$1" dest="$2"
  ln -sfn "../../.agents/skills/${name}" "$dest/$name"
}

for skill in "$SRC"/*; do
  [[ -d "$skill" && -f "$skill/SKILL.md" ]] || continue
  name="$(basename "$skill")"
  dest="$AGENTS/$name"
  if [[ -e "$dest" && ! -L "$dest" ]]; then
    if [[ "$REPLACE" -eq 1 ]]; then
      rm -rf "$dest"
    else
      echo "refusing to replace $dest (not a symlink). Re-run with --replace after this repo has the copy." >&2
      exit 1
    fi
  fi
  ln -sfn "$skill" "$dest"
  link_relative "$name" "$CLAUDE"
  link_relative "$name" "$CURSOR"
  echo "linked $name"
done
