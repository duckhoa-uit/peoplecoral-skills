---
name: peoplecoral-release
description: Builds, verifies, submits and promotes PeopleCoral Flutter wpseoai releases (com.wpseoai.peoplecoral) on TestFlight/App Store and Play internal/production, including the App Review demo-account login check. User-scope skill in ~/.agents/skills, not the workhub repo. Invoke as /peoplecoral-release for "release app", "phát hành", "upload TestFlight / Play internal", "submit review", "promote", "rollout", or replacing a build in review. Read-only store status questions use peoplecoral-release-status. Not for the React Native app, dev/demo flavor uploads, or release notes alone.
disable-model-invocation: true
compatibility: macOS with Xcode, the Flutter version in .fvmrc, asc, gpc, bundletool, firebase CLI, agent-device, and the gitignored configs/ directory of this repo.
---

# PeopleCoral release

Production flavor `wpseoai`, bundle/package `com.wpseoai.peoplecoral`, ASC app `6756572980`. From the current checkout (`git rev-parse --show-toplevel` — any clone or worktree):

```bash
S=$HOME/.agents/skills/peoplecoral-release/scripts
R=~/Documents/peoplecoral-review-artifacts/releases
$S/check-configs.sh store    # fail if this machine has no store configs
# Checkout: cwd or PEOPLECORAL_WORKHUB. Configs: <checkout>/configs or PEOPLECORAL_CONFIGS.
```

Siblings: `peoplecoral-release-notes`, `peoplecoral-store-assets`, `peoplecoral-release-status` (read-only).

## Scope and autonomy

Do only what the request covers:

| Request | Do | Stop before |
|---|---|---|
| Upload to TestFlight / Play internal | steps 1–3 for the named platforms | production, listing changes |
| Verify an existing build | bind it, step 4 | rebuild, metadata, submit |
| Submit/promote an existing build | bind, step 4, step 5 | any rebuild |
| Rollout/halt | read that release, step 5 for that one action | anything else |
| Full release | steps 1–6 for the named platforms | Publish / Release buttons |

Once version and scope are agreed (step 1), do without asking: build and upload to testing, push release tags, create the draft App Store version, write What's New, upload changed screenshots. Always ask first, per platform: submit for review, promote, rollout change, halt, cancelling a submission. Never press Publish or Release.

Copy every row below into the todo list. A row that does not apply stays, marked `skip: <reason>`. Log each decision that changes the plan with `release_context.py log`.

```text
- [ ] Version + scope confirmed (or quoted from the request); run initialized
- [ ] Preflight clean; notes drafted against the verified live baseline
- [ ] Uploaded per platform; actual build bound to the run
- [ ] API account check, first-launch device login, smoke QA recorded
- [ ] Authorized metadata written to the resolved versionId and read back
- [ ] Dry runs shown; per-platform approval recorded with release_context.py approve
- [ ] Approved actions executed and read back; hand-back report
```

## What enforces what

Rules here are checked by code. Do not work around a check; report it.

| Rule | Enforced by |
|---|---|
| Production writes need the user's approval for that exact build | lanes: `confirm=yes` also needs `approval=$RUN/approvals.json` |
| Never promote/halt production with `gpc` directly | `gpc.sh` refuses production track writes (exit 3) |
| A fix to a live release gets a new version name | `upload_app` refuses a version name already live (`ALLOW_LIVE_VERSION_REBUILD=1` overrides) |
| Production uses the uploaded binary | lanes check the release record hash; `release_context.py bind` copies and hashes it |
| Build from a clean tree | `build_app.sh` refuses a dirty tree |
| Review credentials never reach logs | `review-account-fill.sh` pastes on iOS, scans for the password afterwards (exit 3) |

## Gotchas

- Play `completed` is not approved or live; the API has no review state (details: `peoplecoral-release-status`).
- A fresh install's first launch falls back to the bundled `.env` backend when Remote Config is slow. If the review account does not exist there, reviewers fail to log in; a relaunch pass never upgrades a first-launch failure.
- agent-device `fill` text on iOS lands in XCTest logs even with `--record-as`; credentials go only through `review-account-fill.sh`.
- `flutter clean` deletes the AAB still needed for verification. Exit 80 from `build_app.sh` = uploaded, record failed: repair the record, never re-upload.
- Simulators can be claimed by another workspace's agent-device session even when shut down: pick an unclaimed one.
- Under heavy host load (load average far above the core count) agent-device times out: record `not-verified (host load)`, never a fail or pass.

Add a gotcha only when a failure repeats or costs a release, and only after asking whether code (a script check, a lane guard, the app) can prevent it instead. Log one-off incidents in `reference.md`.

## 1. Confirm version and scope

Read `pubspec.yaml`, `$S/store-status.sh`, `.release-records/` and `python3 $S/release_context.py history --root $R`. State version name, platforms, destinations, tag push, and each store's live baseline (UNKNOWN when unproven). Build numbers come from the lanes; quote forecasts as forecasts. If the request names version and scope, record it; otherwise AskUser before any build. A version change goes through a reviewed commit, never a silent `pubspec.yaml` edit.

```bash
RUN=$R/<version>-<yyyymmdd>-<scope>
python3 $S/release_context.py init --directory $RUN --version <x.y.z> --commit <full-sha> \
  --platform android --platform ios --scope full-release --approval-ref <user-message-id>
```

Scopes: `full-release`, `testing`, `verify`, `submit`, `promote`, `rollout`. To act on an existing build, reuse its run from `history`. Run layout and resume rules: `run-context.md`.

## 2. Preflight and notes

Toolchain and configs per `reference.md`; `make check_firebase_config`. A dirty `ios/.../Package.resolved` usually means the SwiftPM ephemeral package lags `pubspec.lock`: diagnose and report. Load `peoplecoral-release-notes` and write `$RUN/notes/{android,ios}.txt`.

## 3. Build and upload to testing

One platform at a time, in the background task facility (log to a file, read the real exit status):

```bash
RELEASE_TAG=1 RELEASE_TAG_PUSH=1 ./build_app.sh -s wpseoai -p android -r "$(cat $RUN/notes/android.txt)"
RELEASE_TAG=1 RELEASE_TAG_PUSH=1 ./build_app.sh -s wpseoai -p ios     -r "$(cat $RUN/notes/ios.txt)"
python3 $S/release_context.py bind --directory $RUN --platform android \
  --record .release-records/wpseoai-android-aab-<version>+<code>.json \
  --artifact build/app/outputs/bundle/wpseoaiRelease/app-wpseoai-release.aab
python3 $S/release_context.py bind --directory $RUN --platform ios \
  --record .release-records/wpseoai-ios-ipa-<version>+<build>.json \
  --artifact build/ios/ipa/<ipa>
```

The iOS record name is `wpseoai-ios-ipa-<version>+<build>.json`. The upload lane binds the single IPA it found in `build/ios/ipa`. Read that path from the lane log or the record. Do not guess the filename.

Bind right after each upload, before the next build overwrites `build/`. Report actual build numbers and check the bound build finished processing. Unknown exit or timeout: read store state before retrying.

## 4. Verify the bound build

```bash
python3 $S/prepare_verify_inputs.py --run $RUN --platform android --artifact $RUN/artifacts/android-<code>.aab
python3 $S/verify_review_account.py --version-id <reviewDetailsVersionId> \
  --remote-config $RUN/inputs/remote-config.json --bundled-env $RUN/inputs/android-bundled.env \
  --approved-hosts-file $R/config.json
```

`<reviewDetailsVersionId>`: the target version from `resolve_store_version.py`, or the current one from `$S/asc.sh versions list --app 6756572980 --platform IOS --latest`. Exit 4: ask whether the printed host is an expected PeopleCoral backend; only on yes add it to `approvedBackendHosts` in `$R/config.json` and rerun. Exit 5: the account works on Remote Config but not on the bundled fallback; continue, and show it at the approval gate.

Device check. Load `verify-peoplecoral` for doctor, session, selectors, and smoke. Follow `device-checks.md` for release-only rules.

```bash
$HOME/.agents/skills/verify-peoplecoral/scripts/doctor.sh <platform> <id> wpseoai
python3 $HOME/.agents/skills/verify-peoplecoral/scripts/smoke.py --platform ios --udid <id> --session <name> --out $RUN/evidence/ios
python3 $HOME/.agents/skills/verify-peoplecoral/scripts/smoke.py --platform android --serial <id> --session <name> --out $RUN/evidence/android
```

Fresh install of the bound AAB or IPA, first launch, then
`$S/review-account-fill.sh --version-id <id> --platform ios --udid <sim> --session <name> --submit` (Android: `--serial`).

- Android: universal APK from the bound AAB. iOS: TestFlight on a device when available, else a same-source simulator build, recorded as `same-source-simulator` (accepted; do not ask about it).
- A first-launch failure on the fallback backend when exit 5 already showed that account gap: record `fail (fallback backend)` and show it at the gate as a warning, not a block. Any other first-launch failure blocks that platform.
- Evidence: `$RUN/evidence/<platform>.json` (fields in `run-context.md`), screenshots in `$RUN/evidence/<platform>/`. API-only is not enough for production.

Metadata (full release): `python3 $S/resolve_store_version.py --version <x.y.z>` (add `--create --confirm` to create the draft), write What's New to that versionId and read it back. Compare the store names with the build's `app_name`; report a mismatch. Upload only changed images. Flag new SDKs, data types or permissions for App Privacy / Data safety.

## 5. Approval, then submit/promote

Dry-run each selected platform:

```bash
SUBMISSION_EXPORT_COMPLIANCE=false SUBMISSION_CONTENT_RIGHTS=false SUBMISSION_ADDS_IDFA=false \
  make submit_ios flavor=wpseoai build=<build> version=<x.y.z> sha=<bound-ipa-sha>
RELEASE_NOTES="$(cat $RUN/notes/android.txt)" \
  make promote_android flavor=wpseoai code=<code> version=<x.y.z> sha=<bound-aab-sha> rollout=<fraction>
make rollout_android flavor=wpseoai code=<n> rollout=<f>
make rollout_android flavor=wpseoai code=<n> rollout=<f> halt=1
```

AskUser with one decision per platform: version, build, commit, hash, notes, metadata changes, evidence levels and warnings (exit 5), rollout, iOS release mode. Propose Play `rollout=1`, iOS `manual-phased`. Re-check the submission answers if ads, tracking or encryption changed. Record each yes, then rerun that platform's command with `confirm=yes approval=$RUN/approvals.json`:

```bash
python3 $S/release_context.py approve --directory $RUN --platform ios --action submit \
  --release-mode manual-phased --ref <user-message-id>
python3 $S/release_context.py approve --directory $RUN --platform android --action promote \
  --rollout 1 --ref <user-message-id>
```

Read back that the selected build is submitted / the selected code is promoted. A changed build, notes, assets, rollout or release mode needs a new approval. Replacing a build in review: `reference.md`.

## 6. Hand back, then stop

Report per platform: version/build/commit, state reached, evidence level and warnings, notes/assets changed, blockers, run path. Then what a person still does: Play **Publish** in Publishing overview (publishes every pending change), iOS **Release this version** unless automatic. Mention Crashlytics (`peoplecoral-prod`), Play vitals, and where Remote Config `base_url` points. Do not Publish, Release, change rollout or halt afterwards unless asked.

## Scripts (`$S`)

| Script | Does | Exit codes |
|---|---|---|
| `store-status.sh` | read-only Play + ASC snapshot | 0 ok, 1 some read failed |
| `release_context.py init/bind/check/approve/log/history` | run ledger, approvals the lanes read, decision log, past runs | 0 ok, 2 blocked |
| `prepare_verify_inputs.py` | env from the artifact + fresh Remote Config | 0 ok, 2 blocked |
| `verify_review_account.py` | API login, `/me`, logout on both backends | 0 pass, 1 fail, 2 blocked, 4 host needs approval, 5 fallback-only failure |
| `review-account-fill.sh` | fill + log in on device from ASC, leak scan | 0 Home, 1 fail, 2 blocked, 3 password on disk |
| `resolve_store_version.py` | exact editable iOS versionId; `--create --confirm` | 0 ok, 2 blocked |
| `asc.sh`, `gpc.sh` | CLIs with the release keys; asc read-only unless `ASC_WRITE=1`; gpc refuses production track writes | 3 refused, else CLI's own |

Every script takes `--help`. Tests: `python3 -B -m unittest discover -s $S/../tests`.

## References

- `run-context.md`: run layout, bind/resume, evidence and approval records.
- `device-checks.md`: bound AAB/IPA, first-launch evidence, TestFlight vs same-source-simulator, cleanup.
- `../verify-peoplecoral/SKILL.md`: doctor, session, selectors, employee smoke.
- `reference.md`: identities, permissions, incidents, CLI notes, replacing an in-review build, dated store history.
- `evals/`: contract tests, behavioral and trigger evals.
