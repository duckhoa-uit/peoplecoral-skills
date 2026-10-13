---
name: verify-peoplecoral
description: Drives the PeopleCoral Flutter app on an iOS simulator or Android emulator the way a user does and captures evidence that a change works. User-scope skill in ~/.agents/skills, not the workhub repo. Use to verify a fix or feature on a device, reproduce a bug report, run a smoke QA of the main screens, or check a release build before submitting. Covers launch, doctor, reviewer login, per-feature driving, evidence and cleanup. Not for unit tests, store uploads, or the React Native app.
compatibility: macOS with Xcode simulators or an Android emulator, agent-device, Python 3; the Flutter version in .fvmrc to build.
---

# Verify PeopleCoral on a device

```bash
V=$HOME/.agents/skills/verify-peoplecoral/scripts
OUT=<evidence dir>
# Run launch/build from the current checkout (any clone or worktree).
# check-configs.sh flavor <dev|demo|wpseoai> before make run_*.
# Configs: <checkout>/configs or PEOPLECORAL_CONFIGS. Missing file = stop, do not guess another clone.
```

## Read first

Load `agent-device`. This repo has no e2e. Config is this skill plus `features/README.md`. The sweep driver is `scripts/smoke.py`. Upkeep is `/maintain-verify-peoplecoral` (or `/maintain-verification-skill` when the workspace is `peoplecoral-ai-toolkit`).

## Gotchas

- Another workspace may hold a simulator claim even when it is shut down. Pick an unclaimed device. Never close another session.
- Several booted devices need `--udid` or `--serial` on every agent-device command, even inside a session, or it fails with `AMBIGUOUS_MATCH`.
- Host overload (load average far above the core count) makes agent-device time out and the app look frozen. Record `not-verified (host load)`. Never a pass or fail.
- After a host reboot the first app launch on an iOS simulator can stay white for a minute. Relaunch before judging.
- One review account at a time.
- `make run_*` uses one pid at `.dart_tool/flutter_run.pid`. A second `make run_*` replaces the first.
- Three flavor ids can coexist on one device. Doctor must get the matching flavor.
- Login fields have no `Semantics.identifier`. Select by title or label only.
- The login error banner is always the unrecognized-username string.
- Do not use `DashboardRouterState.routeToIndex`. It still counts a removed AI tab.
- Tap the visible 4-tab bar or `UiHandles` (`bottom-tab-home`, `bottom-tab-history`, `bottom-tab-notifications`, `bottom-tab-profile`).

## Launch

Pass both `--flavor` and `--dart-define=flavor=` on iOS and Android.

| flavor | bundle id |
| --- | --- |
| dev | com.peoplecoral.dev |
| demo | com.peoplecoral.demo |
| wpseoai | com.wpseoai.peoplecoral |

Resolve the id with `source $V/flavors.sh` then `bundle_id <flavor>`. Default flavor is wpseoai. Open that bundle id.

```bash
source $V/flavors.sh
APP="$(bundle_id wpseoai)"
# iOS release-style install
$(scripts/resolve_flutter_sdk.sh) build ios --simulator --flavor wpseoai --dart-define=flavor=wpseoai -t lib/main.dart
xcrun simctl boot <udid>
xcrun simctl uninstall <udid> "$APP"
xcrun simctl install <udid> build/ios/iphonesimulator/Runner.app
agent-device open "$APP" --platform ios --udid <udid> --session <name> --foreground
# Android release-style install
$(scripts/resolve_flutter_sdk.sh) build apk --flavor wpseoai --dart-define=flavor=wpseoai -t lib/main.dart
adb -s <serial> install build/app/outputs/flutter-apk/app-wpseoai-release.apk
agent-device open "$APP" --platform android --serial <serial> --session <name> --foreground
```

A day-to-day feature branch may use `make run_<flavor> d=<udid>` instead of a release build and install. That still needs both flavor flags. Open the matching bundle id after it is running.

Ready means login or Home. Login shows `Log In` or `Username or email`. Home shows `Hi `. Time Off list is not Home. Accept the notification prompt like a user (`press 'label="Allow"'`).

The review account lives on the production or Remote Config backend. First launch can fall back to the bundled `.env` after a 5s Remote Config wait.

## Doctor

```bash
$V/doctor.sh ios <udid> [flavor]
$V/doctor.sh android <serial> [flavor]
```

Checks boot, install of that flavor's bundle id, claims, and host load. Doctor does not open the app. Exit 0 ready. Exit 1 not ready. Exit 2 usage or unknown flavor. After `agent-device open`, pin the landmark yourself (login or `Hi `).

## Drive

Log in with the reviewer account through `$HOME/.agents/skills/peoplecoral-release/scripts/review-account-fill.sh` (`features/login.md`). Other accounts are typed by the user.

- One feature. Follow its file in `features/`. Select by `id=` from `UiHandles` when the snapshot has it, else by label. Coordinates last.
- Broad check. `python3 $V/smoke.py --platform ios --udid <udid> --session <name> --out $OUT` walks the employee sweep in `features/README.md` from Home, read-only. Exit 0 all pass or valid-empty. Exit 1 a screen failed. Exit 2 blocked. Exit 3 not-verified. `--only payslips chat` narrows it.

Smoke is employee-only. Login and Home are preconditions, not sweep rows. Approvals is not in the sweep. Drive Approvals only when the account is manager or HR. If Time Off is missing on those roles, that is role, not a fail. Overtime, sick leave, chat, and expenses hide on policy flags. A missing tile there is `valid-empty`, not a sweep fail.

Never submit forms, send messages, check in or out, or download in a verification run unless that is the feature under test.

## Evidence

`smoke.py` writes `<feature>.png`, `<feature>.txt`, and `results.json`. There is no `.e2e/` tree. Capture a real user path. Pair each action with the resulting state. For a bug fix, reproduce on the old build first, then show the same path on the new one. Make a contact sheet of the screenshots and look at it before reporting. A launcher screenshot means the app was not in front. Evidence stays private. Never attach raw snapshots or agent-device logs to PRs.

## Bug bash

There is no e2e explore. Charters in the feature files are live `agent-device` walks (one area, one posture, one sentence). A finding is a bug only when you encode it as a failing assertion. Use smoke classify, or a new offline test, or a screenshot plus snapshot that fails the feature Proof. Without a model, bug bash is unproven as an explorer run.

## Cleanup

Close only your session (`agent-device close --session <name>` with the device selector). On devices you booted, uninstall the app, then `xcrun simctl shutdown <udid>` or `adb -s <serial> emu kill`. Keep the evidence directory.

## Helpers

```bash
S=$HOME/.agents/skills/peoplecoral-release/scripts
$S/check-configs.sh flavor demo
source $V/flavors.sh
bundle_id wpseoai
bundle_id dev
bundle_id demo
$V/doctor.sh ios <udid>
$V/doctor.sh ios <udid> wpseoai
$V/doctor.sh android <serial> demo
python3 $V/smoke.py --platform ios --udid <udid> --session <name> --out $OUT
python3 $V/smoke.py --platform android --serial <serial> --session <name> --out $OUT --only payslips
python3 -B -m unittest discover -s $HOME/.agents/skills/verify-peoplecoral/tests -v
make run_dev d=<udid>
make run_demo d=<udid>
make run_wpseoai d=<udid>
```

## Keeping the map honest

When a UI change moves an entry point or a label, update its feature file in the same PR. Never weaken a journey to make it pass. If seed data lacks something, record it in that file's Gotchas. Upkeep is `/maintain-verification-skill`.
