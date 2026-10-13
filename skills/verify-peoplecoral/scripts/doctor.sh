#!/usr/bin/env bash
# Read-only: is this device and app instance worth driving?
# Usage: doctor.sh ios <udid> [flavor] | doctor.sh android <serial> [flavor]
# flavor is dev|demo|wpseoai (default wpseoai). Exit 0 ready, 1 not ready, 2 usage.
# This check is boot + install + host load. Pin login or Home after agent-device open.
set -uo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=flavors.sh
source "$DIR/flavors.sh"
# shellcheck source=../../peoplecoral-release/scripts/workhub.sh
source "$DIR/../../peoplecoral-release/scripts/workhub.sh"

PLATFORM="${1:-}"; DEVICE="${2:-}"; FLAVOR="${3:-wpseoai}"
if [[ -z "$PLATFORM" || -z "$DEVICE" || "$PLATFORM" == "-h" || "$PLATFORM" == "--help" ]]; then
  echo "Usage: doctor.sh ios <udid> [flavor] | doctor.sh android <serial> [flavor]"
  echo "flavor: dev|demo|wpseoai (default wpseoai)"
  exit 2
fi
APP="$(bundle_id "$FLAVOR")" || exit 2
FAIL=0
no() { echo "NOT READY $*"; FAIL=1; }

if env_file="$(require_config "env/${FLAVOR}.env" 2>/dev/null)"; then
  echo "OK flavor env $env_file"
else
  echo "WARN flavor env missing for $FLAVOR. Launch/build on this machine will fail until the file exists under configs/env/ or PEOPLECORAL_CONFIGS."
fi

load=$(sysctl -n vm.loadavg 2>/dev/null | awk '{print int($2)}')
cores=$(sysctl -n hw.ncpu 2>/dev/null || echo 8)
if [[ -n "$load" && "$load" -gt $((cores * 4)) ]]; then
  echo "WARN host load $load on $cores cores: agent-device commands may time out; results would be not-verified"
fi

claims=$(cat ~/.agent-device/device-claims/*.json 2>/dev/null | grep -o "\"id\":\"$DEVICE\"" | head -1)
[[ -n "$claims" ]] && echo "INFO $DEVICE has an agent-device claim; use it only if that session is yours (agent-device session list)"

if [[ "$PLATFORM" == ios ]]; then
  state=$(xcrun simctl list devices | grep "$DEVICE" | grep -o '(Booted)\|(Shutdown)')
  [[ "$state" == "(Booted)" ]] || no "simulator $DEVICE is not booted (xcrun simctl boot $DEVICE)"
  path=$(xcrun simctl get_app_container "$DEVICE" "$APP" 2>/dev/null)
  if [[ -z "$path" ]]; then
    no "$APP is not installed on $DEVICE"
  else
    version=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleShortVersionString' "$path/Info.plist" 2>/dev/null)
    build=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleVersion' "$path/Info.plist" 2>/dev/null)
    echo "OK installed $APP $version ($build)"
  fi
elif [[ "$PLATFORM" == android ]]; then
  [[ "$(adb -s "$DEVICE" shell getprop sys.boot_completed 2>/dev/null | tr -d '\r')" == 1 ]] \
    || no "emulator $DEVICE is not booted or adb does not answer"
  info=$(adb -s "$DEVICE" shell dumpsys package "$APP" 2>/dev/null | grep -m2 -E 'versionName|versionCode' | tr -d ' \r' | paste -sd' ' -)
  [[ -n "$info" ]] && echo "OK installed $APP $info" || no "$APP is not installed on $DEVICE"
else
  echo "Usage: doctor.sh ios <udid> [flavor] | doctor.sh android <serial> [flavor]"; exit 2
fi
[[ $FAIL -eq 0 ]] && echo "READY $PLATFORM $DEVICE $APP"
exit $FAIL
