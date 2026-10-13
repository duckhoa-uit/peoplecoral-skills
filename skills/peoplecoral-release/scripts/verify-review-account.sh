#!/usr/bin/env bash
# Explicit version, current Remote Config snapshot and artifact-derived env required.
# No implicit latest-version lookup, credential files or runtime package installs.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "$DIR/verify_review_account.py" "$@"
