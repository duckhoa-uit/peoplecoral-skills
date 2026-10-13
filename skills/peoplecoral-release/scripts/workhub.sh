# Resolve this app's checkout and its gitignored configs/ on whatever
# machine or worktree the skill is running in. Skills live in
# ~/.agents/skills (outside any clone). No host-specific or Orca paths.
#
# Checkout: cwd (including a git worktree), then PEOPLECORAL_WORKHUB.
# Configs:  PEOPLECORAL_CONFIGS if set, else <checkout>/configs.
# If a required file is missing, stop and name it. Do not guess another clone.

is_workhub() {
  local dir="${1:-}"
  [[ -n "$dir" && -f "$dir/pubspec.yaml" ]] || return 1
  grep -q '^name: peoplecoral_mobile_app$' "$dir/pubspec.yaml"
}

git_toplevel() {
  git -C "${1:-.}" rev-parse --show-toplevel 2>/dev/null
}

# Walk from start up to filesystem root. Works for a normal clone and for a
# `git worktree` (`.git` is a file). Accepts a subdirectory of the checkout.
discover_from() {
  local start="${1:-}"
  [[ -n "$start" ]] || return 1
  local dir
  dir="$(cd "$start" 2>/dev/null && pwd -P)" || return 1
  local cand="$dir"
  while true; do
    if is_workhub "$cand"; then
      local top
      if top="$(git_toplevel "$cand")" && is_workhub "$top"; then
        printf '%s\n' "$top"
        return 0
      fi
      printf '%s\n' "$cand"
      return 0
    fi
    [[ "$cand" == "/" ]] && break
    cand="$(dirname "$cand")"
  done
  local top
  if top="$(git_toplevel "$dir")" && is_workhub "$top"; then
    printf '%s\n' "$top"
    return 0
  fi
  return 1
}

canonical_dir() {
  local dir="${1:-}"
  [[ -n "$dir" && -d "$dir" ]] || return 1
  printf '%s\n' "$(cd "$dir" && pwd -P)"
}

workhub() {
  local root
  if root="$(discover_from "${PWD:-.}")"; then
    printf '%s\n' "$root"
    return 0
  fi
  if [[ -n "${PEOPLECORAL_WORKHUB:-}" ]] && is_workhub "$PEOPLECORAL_WORKHUB"; then
    printf '%s\n' "$(cd "$PEOPLECORAL_WORKHUB" && pwd -P)"
    return 0
  fi
  echo "peoplecoral-workhub checkout not found from ${PWD:-.}. Run from a clone or worktree of this app, or set PEOPLECORAL_WORKHUB to it." >&2
  return 2
}

# Directory that holds env/, ios/configs/, android/configs/. Independent of
# the checkout so a machine can keep secrets in one place and point at it.
configs_root() {
  local root
  if [[ -n "${PEOPLECORAL_CONFIGS:-}" ]]; then
    if root="$(canonical_dir "$PEOPLECORAL_CONFIGS")"; then
      printf '%s\n' "$root"
      return 0
    fi
    echo "PEOPLECORAL_CONFIGS is not a directory: $PEOPLECORAL_CONFIGS" >&2
    return 2
  fi
  root="$(workhub)" || return 2
  printf '%s\n' "$root/configs"
}

missing_config() {
  echo "missing $1" >&2
  echo "Place that file on this machine, or set PEOPLECORAL_CONFIGS to a configs/ directory that contains it." >&2
  return 2
}

require_config() {
  local rel="${1:?}"
  local root file
  root="$(configs_root)" || return 2
  file="$root/$rel"
  if [[ ! -f "$file" ]]; then
    missing_config "$file"
    return 2
  fi
  printf '%s\n' "$file"
}
