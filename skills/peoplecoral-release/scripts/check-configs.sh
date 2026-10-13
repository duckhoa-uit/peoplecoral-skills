#!/usr/bin/env bash
# Report which gitignored config files this machine is missing.
# Usage: check-configs.sh flavor <dev|demo|wpseoai>
#        check-configs.sh store
#        check-configs.sh all
# Exit 0 all present. Exit 2 something is missing (paths on stderr).
set -euo pipefail

# shellcheck source=workhub.sh
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/workhub.sh"

usage() {
  echo "Usage: check-configs.sh flavor <dev|demo|wpseoai> | store | all" >&2
  exit 2
}

MODE="${1:-}"
[[ -n "$MODE" && "$MODE" != "-h" && "$MODE" != "--help" ]] || usage

FAILED=0
need() {
  if ! require_config "$1" >/dev/null; then
    FAILED=2
  fi
}

check_flavor() {
  local flavor="${1:-}"
  case "$flavor" in
    dev|demo|wpseoai) ;;
    *) echo "unknown flavor: $flavor (dev|demo|wpseoai)" >&2; exit 2 ;;
  esac
  need "env/${flavor}.env"
}

check_store() {
  need "ios/configs/.env"
  need "android/configs/.env"
  need "android/configs/peoplecoral-prod-3dafe7d42ce0.json"
}

case "$MODE" in
  flavor)
    [[ -n "${2:-}" ]] || usage
    check_flavor "$2"
    ;;
  store) check_store ;;
  all)
    check_flavor dev
    check_flavor demo
    check_flavor wpseoai
    check_store
    ;;
  *) usage ;;
esac

exit "$FAILED"
