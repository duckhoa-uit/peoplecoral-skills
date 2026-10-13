#!/usr/bin/env bash
# Run gpc (Play Console CLI) against com.wpseoai.peoplecoral with the release
# service account, using a throwaway profile that is deleted on exit.
# Usage: gpc.sh tracks list
#        gpc.sh tracks get --track production
set -euo pipefail

# Production track writes go through the make lanes, which check the release
# record hash and the recorded approval. `tracks update` alone defaults to
# completed at 100%.
if [[ "${1:-}" == "tracks" && " update promote complete halt " == *" ${2:-} "* \
      && "${GPC_PRODUCTION_WRITE:-0}" != "1" ]]; then
  for arg in "$@"; do
    if [[ "$arg" == *production* ]]; then
      echo "BLOCKED gpc tracks $2 on production: use make promote_android / rollout_android" >&2
      exit 3
    fi
  done
fi

if [[ -z "${PLAY_STORE_JSON_KEY:-}" ]]; then
  # shellcheck source=workhub.sh
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/workhub.sh"
  KEY="$(require_config android/configs/peoplecoral-prod-3dafe7d42ce0.json)"
else
  KEY="$PLAY_STORE_JSON_KEY"
  [[ -f "$KEY" ]] || { echo "missing $KEY" >&2; exit 2; }
fi
PACKAGE="${GPC_PACKAGE:-com.wpseoai.peoplecoral}"
command -v gpc >/dev/null || { echo "gpc is not installed (brew install gpc)" >&2; exit 2; }

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
CONFIG="$TMP/gpc.json"
gpc --config "$CONFIG" auth login --name release --credentials "$KEY" \
  --default-package "$PACKAGE" -q >/dev/null
chmod 600 "$CONFIG"
gpc --config "$CONFIG" --profile release -p "$PACKAGE" "$@"
