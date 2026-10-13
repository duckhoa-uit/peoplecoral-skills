#!/usr/bin/env bash
# Run asc (App Store Connect CLI) with the API key from configs/ios/configs/.env,
# passed through the environment only. Nothing is written to the keychain.
# Read-only by default; set ASC_WRITE=1 for a command that changes App Store Connect.
# Usage: asc.sh status --app 6756572980 --platform IOS --output json
#        ASC_WRITE=1 asc.sh localizations update --version <id> --locale en-US --whats-new "..."
set -euo pipefail

if [[ -z "${ASC_ENV_FILE:-}" ]]; then
  # shellcheck source=workhub.sh
  source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/workhub.sh"
  ENV_FILE="$(require_config ios/configs/.env)"
else
  ENV_FILE="$ASC_ENV_FILE"
  [[ -f "$ENV_FILE" ]] || { echo "missing $ENV_FILE" >&2; exit 2; }
fi
command -v asc >/dev/null || { echo "asc is not installed" >&2; exit 2; }

set -a
# shellcheck disable=SC1090
. "$ENV_FILE" >/dev/null 2>&1
set +a

export ASC_BYPASS_KEYCHAIN=1
export ASC_KEY_ID="${ASC_API_KEY_ID:?ASC_API_KEY_ID missing in $ENV_FILE}"
export ASC_ISSUER_ID="${ASC_API_ISSUER_ID:?ASC_API_ISSUER_ID missing in $ENV_FILE}"
unset ASC_PRIVATE_KEY ASC_PRIVATE_KEY_B64 ASC_PRIVATE_KEY_PATH
case "${ASC_API_KEY_CONTENT:?ASC_API_KEY_CONTENT missing in $ENV_FILE}" in
  *BEGIN*) export ASC_PRIVATE_KEY="$(printf '%b' "$ASC_API_KEY_CONTENT")" ;;
  *) export ASC_PRIVATE_KEY_B64="$ASC_API_KEY_CONTENT" ;;
esac
unset ASC_API_KEY_CONTENT KEYCHAIN_PASSWORD
if [[ "${ASC_WRITE:-0}" == "1" ]]; then
  export ASC_READ_ONLY=0
else
  export ASC_READ_ONLY=1
fi

asc "$@"
