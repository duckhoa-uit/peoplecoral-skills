---
name: peoplecoral-store-assets
description: Captures, composes and uploads PeopleCoral wpseoai store screenshots and the Play feature graphic in the approved house style for App Store Connect and Google Play. User-scope skill in ~/.agents/skills, not the workhub repo. Use for "update screenshots", "store listing images", "ảnh store", "feature graphic", "screenshots not updated on Play/App Store", or the listing-assets step of peoplecoral-release. Use it instead of the generic asc-shots-pipeline or asc-screenshot-resize for this app. Not for bug-report screenshots or QA evidence.
---

# PeopleCoral store assets

The approved look is the **house style**: soft blue gradient, navy headline, subtitle, phone frame.
`scripts/compose_house.py` renders it from raw device captures.

```bash
S=$HOME/.agents/skills/peoplecoral-release/scripts                  # shared store scripts; $S/check-configs.sh store first
A=$HOME/.agents/skills/peoplecoral-store-assets/scripts
WORK=~/Documents/peoplecoral-review-artifacts/releases/<run>/assets   # or a standalone dir under releases/
```

A capture or preview request does not authorize uploads. Inside an authorized full release, upload only
the sets whose screens changed and report the checks.

## Gotchas

- Byte-identical output depends on the Pillow and font versions too: compare hashes, do not assume.
- Play `images sync --confirm` replaces **all** images of each type it finds in the directory.
- Play listing changes go through review and, with Managed publishing on, wait for Publish; when it is off or unknown, they may go live on approval. Check before uploading.
- Play image upload needs the service account permission **Manage store presence**; without it: `403 PERMISSION_DENIED`.
- ASC screenshots attach to one App Store version; the live version keeps its images until the new one is released.
- Demo data still shows names and messages: look at every image before upload. Skip Profile (personal data).

## 1. Capture raw screens

Build the `demo` flavor (demo backend, never production data) from the release's target commit.
The bundle id is `com.peoplecoral.demo`. Use that for open, uninstall, and install.
Do not use `com.wpseoai.peoplecoral`.
Load `verify-peoplecoral` and run doctor and open with flavor `demo`.

```bash
$HOME/.agents/skills/verify-peoplecoral/scripts/doctor.sh ios <udid> demo
$HOME/.agents/skills/verify-peoplecoral/scripts/doctor.sh android <serial> demo
agent-device open com.peoplecoral.demo --platform ios --udid <udid> --session <name> --foreground
agent-device open com.peoplecoral.demo --platform android --serial <serial> --session <name> --foreground
```

Use a disposable named session on an unclaimed device.
Log in with `$S/review-account-fill.sh` only when the App Store review account exists on the demo backend.
Do not use the ASC review account when it is missing on the demo backend. Ask the user for a demo employee or manager account instead.
For the manager account, ask the user to type it on the device.
Never put credentials in commands or chat.

- iOS: 6.9" simulator (iPhone 17 Pro Max, 1320×2868). Status bar:
  `xcrun simctl status_bar <udid> override --time "9:41" --dataNetwork wifi --wifiMode active --wifiBars 3 --cellularMode active --cellularBars 4 --batteryState charged --batteryLevel 100`
  Capture: `xcrun simctl io <udid> screenshot $WORK/raw/ios/<name>.png`
- Android: Pixel emulator (1080×2400). Status bar:
  ```bash
  d(){ adb -s <serial> shell am broadcast -a com.android.systemui.demo -e command "$@" >/dev/null; }
  adb -s <serial> shell settings put global sysui_demo_allowed 1; d enter; d clock -e hhmm 0941
  d battery -e level 100 -e plugged false; d network -e wifi show -e level 4
  d network -e mobile show -e datatype none -e level 4; d notifications -e visible false
  ```
  Capture: `adb -s <serial> exec-out screencap -p > $WORK/raw/android/<name>.png`

File names the composer expects: `01_home`, `02_timeoff_approved`, `05_payslips`, `09_attendance`,
`06_expenses`, `07_chat_list`, `10_notifications`, `12_manager_home`.
`09_attendance` is the Calendar tab (`/attendance_history`).
`12_manager_home` needs a manager account. That Home shows Approvals and Chat only.
Recapture only screens whose UI changed since the live baseline; copy the rest from the previous set
(`~/Documents/peoplecoral-review-artifacts/screenshots/raw/` on this machine) so unchanged slides stay the same.
A changed screen may need new copy: edit `SLIDES` (headline, subtitle) in the composer.

## 2. Compose and review

```bash
python3 $A/compose_house.py $WORK
```

Needs Pillow; fonts come from the repo `assets/fonts`. Writes `out/ios` (1320×2868), `out/ios65`
(1284×2778), `out/android` (1080×1920) and `out/android/feature_graphic.png` (1024×500). Make a contact
sheet and look at it: order, cropping, text overflow, personal data. Standalone: show the contact sheet
and get approval before any upload.

## 3. Upload to App Store Connect

Target version: `python3 $S/resolve_store_version.py --version <x.y.z>` (`--create --confirm` only when
creating the draft is authorized). Then dry-run, upload, verify:

```bash
for spec in APP_IPHONE_69:ios APP_IPHONE_65:ios65; do
  ASC_WRITE=1 $S/asc.sh screenshots upload --app 6756572980 --version <x.y.z> --locale en-US \
    --path "$WORK/out/${spec#*:}" --device-type "${spec%%:*}" --replace --dry-run
done
# then the same with --replace --confirm
$S/asc.sh screenshots list --version-id <versionId> --locale en-US --output json   # 8 per set, COMPLETE
```

Upload before the version is submitted for review.

## 4. Upload to Google Play

```bash
mkdir -p $WORK/play/en-US/phoneScreenshots $WORK/play/en-US/featureGraphic
i=1; for f in $(ls $WORK/out/android/0*.png | sort); do cp "$f" $WORK/play/en-US/phoneScreenshots/$i.png; i=$((i+1)); done
cp $WORK/out/android/feature_graphic.png $WORK/play/en-US/featureGraphic/1.png
$S/gpc.sh images sync --dir $WORK/play --dry-run --confirm   # preview ("would replace ...")
$S/gpc.sh images sync --dir $WORK/play --confirm
$S/gpc.sh images list --locale en-US --type phoneScreenshots   # sha1 must match the local files
```

Do not press Publish here; the user publishes listing changes together with the matching release.

## Cleanup

Keep raw/out hashes, Pillow version, target version and upload read-backs in `$WORK`. Remove status-bar
overrides and close the session only on devices this run started. Share only the reviewed contact sheet.

Not covered: store text (description, keywords), App Privacy and Data safety are edited on the web consoles
(Data safety drafts: `~/Documents/peoplecoral-review-artifacts/data_safety_*.csv`).
