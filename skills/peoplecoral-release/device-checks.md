# Device checks: bound build and reviewer login

Commands and gotchas for step 4 of `SKILL.md`.
Load `verify-peoplecoral` first. Follow its Launch, Doctor, and Drive for selectors and the employee smoke.
Load `agent-device` as that skill says.
Results go to `$RUN/evidence/<platform>.json`, screenshots to `$RUN/evidence/<platform>/`.
Fields live in `run-context.md` (`level`, `firstLaunch`, artifact SHA, device/session, per-screen results).
Use a dedicated emulator or simulator and a named session owned by this run.
Never uninstall an app from a user's physical device, erase their data, or stop another session without explicit permission.

Reviewer login still uses `$S/review-account-fill.sh`. This skill owns the credentials. Never pass the password to `agent-device fill`.
Snapshots show the username in the field. Do not paste raw snapshot output or agent-device logs into reports.

Doctor and smoke (flavor `wpseoai`):

```bash
$HOME/.agents/skills/verify-peoplecoral/scripts/doctor.sh <platform> <id> wpseoai
python3 $HOME/.agents/skills/verify-peoplecoral/scripts/smoke.py --platform ios --udid <id> --session <name> --out $RUN/evidence/ios
python3 $HOME/.agents/skills/verify-peoplecoral/scripts/smoke.py --platform android --serial <id> --session <name> --out $RUN/evidence/android
```

## Android (derived from the uploaded AAB)

```bash
# release_context.py already copied and verified this AAB.
bundletool build-apks --bundle="$RUN/artifacts/android-<code>.aab" \
  --output="$RUN/artifacts/android-<code>.apks" --mode=universal
unzip -q "$RUN/artifacts/android-<code>.apks" universal.apk -d "$RUN/artifacts/android-<code>"
```

- Start the emulator with Execute `fireAndForget` (`emulator -avd PC_16K_API36 -no-snapshot-save -no-boot-anim`). A shell `&` dies with the command. Wait for `sys.boot_completed`.
- Fresh install on this run's emulator: `adb -s <serial> uninstall com.wpseoai.peoplecoral`, then install the derived universal APK using agent-device's explicit device/session selection. bundletool signs with the debug key. This does not verify Play split delivery or Play signing. Never use unscoped adb when multiple devices exist.
- Launcher activity: `com.wpseoai.peoplecoral/com.relia.people.coral.MainActivity` (the Java package differs from the app id). `adb shell pm grant com.wpseoai.peoplecoral android.permission.POST_NOTIFICATIONS` skips the prompt for timing runs. For the reviewer run accept it like a reviewer would (`press 'label="Allow"'`).
- When the host is overloaded (load average far above the core count), the emulator's adb stops answering. Do not record that as an app result. Stop, report `not-verified (host load)`, and retry later.

## iOS

- The TestFlight binary only runs on a real iPhone. Without one, build the tagged commit for the simulator and record `same-source-simulator`:
  ```bash
  $(scripts/resolve_flutter_sdk.sh) build ios --simulator --flavor wpseoai --dart-define=flavor=wpseoai -t lib/main.dart
  xcrun simctl install <udid> build/ios/iphonesimulator/Runner.app
  ```
  Build it after the iOS upload has finished, not during it. Compare the simulator's bundled env and Firebase configuration to the bound IPA, not merely its commit. Never report it as a TestFlight pass.
- Pick a free simulator. `DEVICE_IN_USE` means another workspace's session holds it. Do not close that session and do not install on that simulator. Boot another (`xcrun simctl boot <udid>`), then open `com.wpseoai.peoplecoral` with `--session <name>` on every command.
- Fresh install: `xcrun simctl uninstall <udid> com.wpseoai.peoplecoral` before installing.
- Measured with agent-device 0.21.8. On iOS, `fill` text lands in `~/.agent-device/sessions/<s>/runner.log` and the runner's `.xcresult` logs even with `--record-as`. Text pasted from the simulator pasteboard (`simctl pbcopy` via stdin) did not reach disk. On Android, `fill` text did not reach disk or logcat. `review_account_fill.py` uses paste on iOS and fill on Android, then scans for the password. Re-measure after upgrading agent-device.
- The edit menu after a long press lists three nodes labelled `Paste` (container, item, text). Only the `MenuItem` (iOS 27) or cell (iOS 26) takes the press.
- Simulators may carry agent-device claims from other workspaces even when shut down (`~/.agent-device/device-claims/`). Pick an unclaimed simulator.

## Artifact configuration

`prepare_verify_inputs.py` extracts the one `flutter_assets/configs/env/wpseoai.env` inside the bound
AAB (`base/assets/...`) or IPA (`Payload/Runner.app/Frameworks/App.framework/...`) and fetches a fresh
Remote Config template. Use those files, never the checkout's current `configs/env/wpseoai.env`.
For a simulator build, compare its bundled env hash with the IPA's.

## Cleanup

Close only this run's named agent-device session. Uninstall only on the disposable device owned by this
run. Use `adb -s <serial> emu kill` or `xcrun simctl shutdown <udid>` only for a device this run started.
Restore status-bar overrides on those devices. Keep bound artifacts and private evidence for resume.
Do not use wildcard cleanup or touch another run's data.
