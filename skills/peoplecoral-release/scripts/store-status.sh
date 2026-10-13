#!/usr/bin/env bash
# Read-only snapshot of the wpseoai release state on both stores.
# Play "completed" means configured on the track. With Managed publishing on,
# it is only live after someone presses Publish in Publishing overview.
set -uo pipefail
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  echo "Usage: store-status.sh   Read-only Play (production, internal) + App Store Connect snapshot (builds, TestFlight, version, review, live iOS)."
  echo "Exit 0 all reads succeeded; 1 a read failed and that part is UNKNOWN."
  exit 0
fi
umask 077
FAILED=0

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "== Google Play (com.wpseoai.peoplecoral)"
for track in production internal; do
  if "$DIR/gpc.sh" tracks get --track "$track" > "$TMP/$track.json" 2>/dev/null; then
    python3 - "$track" "$TMP/$track.json" <<'PY' || FAILED=1
import json, sys
track, path = sys.argv[1], sys.argv[2]
for r in json.load(open(path)).get("releases", []):
    fraction = r.get("userFraction")
    rollout = "%g%%" % (float(fraction) * 100) if fraction is not None else ("100%" if r.get("status") == "completed" else "unspecified")
    notes = "notes" if r.get("releaseNotes") else "no notes"
    print("  %-10s %-12s codes=%s %s %s %s" % (
        track, r.get("name"), r.get("versionCodes"), r.get("status"), rollout, notes))
PY
  else
    echo "  $track: UNKNOWN (read failed)"
    FAILED=1
  fi
done

echo "== App Store Connect (app 6756572980)"
if "$DIR/asc.sh" status --app 6756572980 --platform IOS \
    --include builds,testflight,appstore,submission,review --output json > "$TMP/asc.json" 2>/dev/null; then
  python3 - "$TMP/asc.json" <<'PY' || FAILED=1
import json, sys
d = json.load(open(sys.argv[1]))
b = (d.get("builds") or {}).get("latest") or {}
a = d.get("appstore") or {}
r = d.get("review") or {}
t = d.get("testflight") or {}
tf = t.get("latest") if isinstance(t.get("latest"), dict) else t
print("  latest build  %s (%s) %s" % (b.get("version"), b.get("buildNumber"), b.get("processingState")))
print("  testflight    %s (%s) %s" % (
    tf.get("version"), tf.get("buildNumber") or tf.get("build"),
    tf.get("state") or tf.get("internalState") or tf.get("processingState")))
print("  version       %s %s" % (a.get("version"), a.get("state")))
print("  review        %s submitted=%s" % (r.get("state"), r.get("submittedDate")))
print("  next action   %s" % (d.get("summary") or {}).get("nextAction"))
PY
else
  echo "  status UNKNOWN (read failed)"
  FAILED=1
fi
if "$DIR/asc.sh" versions list --app 6756572980 --platform IOS \
    --state READY_FOR_SALE --latest --output json > "$TMP/live.json" 2>/dev/null; then
  python3 - "$TMP/live.json" <<'PY' || FAILED=1
import json, sys
d = json.load(open(sys.argv[1]))
rows = d.get("items") or d.get("data") or []
if isinstance(rows, dict):
    rows = [rows]
for v in rows[:1]:
    a = v.get("attributes", v)
    print("  live          %s %s" % (a.get("versionString"), a.get("appStoreState") or a.get("appVersionState")))
if not rows:
    print("  live          UNKNOWN (empty READY_FOR_SALE --latest)")
PY
else
  echo "  live UNKNOWN (read failed)"
  FAILED=1
fi
if "$DIR/asc.sh" versions list --app 6756572980 --platform IOS --paginate --output json > "$TMP/versions.json" 2>/dev/null; then
  python3 - "$TMP/versions.json" <<'PY' || FAILED=1
import json, sys
d = json.load(open(sys.argv[1]))
rows = d.get("data", d) if isinstance(d, dict) else d
for v in rows[:4]:
    a = v.get("attributes", v)
    print("  version list  %s %s" % (a.get("versionString"), a.get("appStoreState") or a.get("appVersionState")))
PY
else
  echo "  version list UNKNOWN (read failed)"
  FAILED=1
fi
echo "Play review/publication state is UNKNOWN from track API alone."
exit "$FAILED"
