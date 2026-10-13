# PeopleCoral release reference

Stable identifiers, procedures and known failure modes. Current store state is never recorded here: read it with `scripts/store-status.sh`. Change history lives in git and the PRs, not in this file.

## Contents
- Apps and identities
- Replace an in-review iOS build
- Reading Play state
- Permissions that matter
- Known failure modes
- CLI notes: gpc, asc, fastlane/scripts
- Store review notes

## Apps and identities

| | Value |
|---|---|
| Production flavor | `wpseoai` |
| iOS bundle / Android package | `com.wpseoai.peoplecoral` |
| App Store Connect app id | `6756572980` |
| Apple team | `V57UWUJ455` (HR Rebels B.V.) |
| Play service account | `agent-automation-deployment@peoplecoral-prod.iam.gserviceaccount.com` |
| Firebase projects | `peoplecoral-dev`, `peoplecoral-demo`, `peoplecoral-prod` (aliases in tracked `.firebaserc`) |
| Other flavors | `dev` `com.peoplecoral.dev`, `demo` `com.peoplecoral.demo` (TestFlight + Firebase App Distribution) |

Changing a bundle id or package creates a new store app: existing users get no update. Keep `com.wpseoai.peoplecoral`.

## Replace an in-review iOS build

A version not yet on the App Store keeps its version name; only the build changes. Order matters, so the
version is never left pulled with nothing to submit:

1. Upload, bind and verify the replacement build; get production approval for it **and** for cancelling the current submission.
2. Find the submission id (`$S/asc.sh review submissions-list --app 6756572980`), check current flags with `--help`, then `ASC_WRITE=1 $S/asc.sh submit cancel --id <submissionId> --confirm`. The version becomes `DEVELOPER_REJECTED` and editable.
3. `resolve_store_version.py --version <x.y.z>` must return the same versionId; rewrite and read back What's New if approved notes changed.
4. `release_context.py approve --platform ios --action submit ...`, then `make submit_ios ... build=<new> confirm=yes approval=$RUN/approvals.json` attaches the new build to the same version and submits.

Android needs only a higher version code: `promote_android code=<new>` replaces the production release.
If a step fails, keep the run and report the partial state; do not loop through rebuilds or cancellations.

## Reading Play state

`gpc tracks get` shows `completed` for in review, ready to publish and live alike; the API has no review state. With Managed publishing on, users have the last *published* release, which can be far behind the production track. Ask the user for Play Console → Test and release → Production → the release page: "Ready to publish" means approved and waiting for **Publish** in Publishing overview; "Percentage of install base on this release 0.00%" means not live.

## Permissions that matter

Play Console → Users and permissions → service account → **App permissions**:
- Release to production, exclude devices, and use Play App Signing.
- Release apps to testing tracks.
- **Manage store presence** (store listing text and images). Without it, image upload returns `403 PERMISSION_DENIED`. Source: https://support.google.com/googleplay/android-developer/answer/9844686
- Manage policy declarations (Data safety) only if agents should edit Data safety.

App Store Connect API key (`configs/ios/configs/.env`) must be a Team key with Admin or App Manager; Admin is needed to create certificates or profiles. Creating a new app record has no public API (web only).

## Known failure modes

Only failures a script or lane does not already prevent. When code starts preventing one, delete its row.

| Symptom | Cause | What to do |
|---|---|---|
| `build_app.sh` exit 3, dirty tree | often `ios/.../Package.resolved` re-resolved by Xcode after a pull: the gitignored ephemeral SwiftPM package (`ios/Flutter/ephemeral/Packages/FlutterGeneratedPluginSwiftPackage/Package.swift`) still points at old plugin versions | compare it with `pubspec.lock`; if they differ, report it and ask before restoring; `make init`, `flutter build ios --config-only`, `xcodebuild -resolvePackageDependencies` refreshes it. Never hide user files to get a clean tree |
| Play API `403 PERMISSION_DENIED` | service account lacks a permission | grant it in Play Console (above) |
| Flutter/Gradle build fails on Java | JDK newer than 17 picked up | `flutter config --jdk-dir <jdk-17>` is machine-wide: ask first |
| `bundle install` fails | macOS system Ruby | release scripts pick Homebrew Ruby; `brew install ruby` |
| Lane hangs on the first iOS signing | keychain access prompt | the user clicks **Always Allow** once on that machine |
| Reviewer cannot log in | review account has 2FA, or does not exist on a backend the build can reach | keep the account without 2FA and present on both the Remote Config and the bundled `.env` backend (`verify_review_account.py` checks both) |
| First login fails only on a fresh install, relaunch works | the first launch waits a few seconds for Remote Config, then falls back to the bundled `.env` backend | the account must exist on the fallback too (exit 5 of the verifier); a relaunch pass never upgrades the first-launch result |
| Account check says "invalid credentials" while it works | `asc` prints the password as `(redacted)` unless `--include-sensitive` | the verifier reads review details with `--include-sensitive` into memory only |
| Store shows the old app name after a rename in code | the code rename changes only the icon label; Play listing title and ASC App Information name are store metadata | step 4 compares store names with the build's `app_name`; the ASC name changes only with an editable version |
| Typed passwords end up on disk | agent-device `fill` on iOS (with or without `--record-as`) logs the text to `runner.log` / `.xcresult`; simulator pasteboard paste and Android `fill` do not (measured on agent-device 0.21.8) | credentials only through `review-account-fill.sh`; re-measure after upgrading agent-device |
| Notes describe the wrong delta | compared against the last upload, not the live build | see `peoplecoral-release-notes` |

## CLI notes

### gpc (Play Console CLI)
- Use `scripts/gpc.sh`; it builds a throwaway profile from the service account key and deletes it. It refuses production track writes.
- Read: `gpc.sh tracks list`, `gpc.sh tracks get --track production`, `gpc.sh images list --locale en-US --type phoneScreenshots`.
- `images sync --dir <dir> --confirm` replaces all images of each populated type.

### asc (App Store Connect CLI)
- Use `scripts/asc.sh`; read-only unless `ASC_WRITE=1`.
- `asc.sh status --app 6756572980 --platform IOS --include builds,testflight,appstore,submission,review --output json`
- `asc.sh versions list --app 6756572980 --platform IOS --state READY_FOR_SALE --latest --output json`: the live version. Older versions also say `READY_FOR_SALE`. With `--latest` the rows are under `items`, not `data`.
- `asc.sh localizations list --version <versionId> --output json` (What's New lives here)
- `asc.sh review details-for-version --version-id <versionId>` (demo account, notes; never print the password)
- `asc.sh screenshots list --version-id <versionId> --locale en-US --output json`

### Fastlane / scripts
- `scripts/release/run_lane.sh <ios|android> <lane>` stages `configs/`, picks the release Ruby and cleans up.
- Offline tests of the tooling: `./scripts/release/test_release_tooling.sh` and `ruby scripts/release/release_lanes_test.rb`.
- Offline tests of this skill bundle: `python3 -B -m unittest discover -s $HOME/.agents/skills/peoplecoral-release/tests -v`.
- Background builds: write logs to a file and poll; do not stream thousands of lines.

## Store review notes

- Every App Store version and every Play production/closed/open release is reviewed. TestFlight internal and Play internal are not.
- Apple review usually takes hours to 1–2 days. Play review takes hours to days.
- The app is internal workforce software; review notes say so and give a demo account. Remote Config/backend changes need no review but must not hide features from review.
