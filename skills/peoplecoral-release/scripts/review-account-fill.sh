#!/usr/bin/env bash
# Fill the App Store Connect review account into the app's login form.
# Usage: review-account-fill.sh --version-id <id> --platform ios|android --session <name> [--udid <sim>] [--submit]
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$DIR/review_account_fill.py" "$@"
