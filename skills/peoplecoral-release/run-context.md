# Release context and resume

One private directory per approved version/commit/scope, under the runs root
`R=~/Documents/peoplecoral-review-artifacts/releases` (outside the repo, never `/tmp`), e.g.
`$R/<version>-<yyyymmdd>-<scope>`. `$S` is `$HOME/.agents/skills/peoplecoral-release/scripts`, run from the current worktree root.
The three skills share the run. Notes/assets-only tasks use their own private workspace under `$R`.

`$R/config.json` holds settings the user decided once, read by the scripts:

```json
{"approvedBackendHosts": ["<api host the user confirmed>", "<fallback host>"]}
```

Add a host only after the user confirms it (`verify_review_account.py` exit 4). It stays outside git
because host names are private. `release_context.py history --root $R` lists recent runs from their own files.

## Initialize after scope/version approval

```bash
python3 "$S/release_context.py" init --directory "$RUN" \
  --version 2.0.1 --commit <full-approved-sha> \
  --platform android --platform ios --scope full-release --approval-ref <user-message-id>
```

Only include selected platforms. Scope values: `full-release`, `testing`, `verify` (check an existing build, no writes), `submit`, `promote`, `rollout`. Pick the narrowest one the user asked for: "verify before promote" is `verify`, not `promote`.
For an existing build, resolve version/commit from its record before initializing.
The command refuses an existing run directory; it does not overwrite another session's run.
`context.json` is an identity ledger, **not proof of user approval or proof of store state**.
`scopeApprovalRef` points to the actual conversation authorization; never paste credentials or whole transcripts.

Layout:

```text
context.json             # immutable target + append-only platform bindings
notes/ios.txt
notes/android.txt
artifacts/               # copied and hashed uploaded AAB/IPA
inputs/                  # prepare_verify_inputs.py: remote-config.json, <platform>-bundled.env, <platform>-inputs.json
evidence/                # QA report and sanitized screenshots
baseline.json            # live version/code/commit per store, source, confidence, observed time
target-ios.json          # resolved app/version/versionId/editable state
approvals.json           # written by `release_context.py approve`; the lanes require it with confirm=yes
decisions.tsv            # `release_context.py log`: one row per decision that changed the plan; read it on resume
```

## Bind immediately after each upload

```bash
python3 "$S/release_context.py" bind --directory "$RUN" --platform android \
  --record "$REPO/.release-records/wpseoai-android-aab-2.0.1+163.json" \
  --artifact "$REPO/build/app/outputs/bundle/wpseoaiRelease/app-wpseoai-release.aab"
python3 "$S/release_context.py" bind --directory "$RUN" --platform ios \
  --record "$REPO/.release-records/wpseoai-ios-ipa-2.0.1+167.json" \
  --artifact "$REPO/build/ios/ipa/<ipa>"
python3 "$S/release_context.py" check --directory "$RUN" --require-all
```

Use the actual numbers/paths, not these examples. The iOS record name is `wpseoai-ios-ipa-<version>+<build>.json`. Bind the single IPA the upload lane found in `build/ios/ipa`. Read that path from the lane log or the record.
The helper checks app/flavor/platform/version/clean commit/upload outcome and artifact hash, copies
the binary privately, serializes updates with a file lock and refuses changing a bound build.
It allows re-binding the same record/artifact to recover an interrupted run.
Record promotions may be appended by the existing lanes; identity changes are rejected.
Missing platforms appear in `check` output; `--require-all` blocks when any selected platform is missing.

The existing `.release-records` remains the source of upload attribution. Do not create a second
manifest format for uploads. The context only links records to this workflow.

## Evidence and approvals

Keep a per-platform `evidence/<platform>.json` with:

- version/build, commit, artifact SHA-256, device/session ID and timestamp;
- `level`: `testflight-installed`, `aab-derived-universal`, `same-source-simulator`,
  `api-only`, or `not-verified`;
- `firstLaunch`: `pass`, `fail`, `not-verified` (`history` shows `level` and `firstLaunch`, keep those key names);
- API check exit/result, plus the hashes and fetch time from `inputs/<platform>-inputs.json`;
- each screen's `pass`, `valid-empty`, `fail`, `not-verified`, with fixture expectations;
- screenshot/contact-sheet paths and any limitations.

Screenshots and snapshots may contain personal data even with a review account: store privately,
redact before sharing, never attach raw evidence to a PR or upload it without permission.

Record each production yes with `release_context.py approve` right after the user gives it. The entry binds
platform, action, version, the bound build and its hash, plus rollout (Android) or release mode (iOS), the
user's message reference, and a 24-hour expiry. The lanes refuse `confirm=yes` without a matching entry.
Only record what the user actually approved: the entry is the evidence the lane trusts. A changed build,
rollout or release mode needs a new approval; changed notes or listing assets need the user's yes again too.

## Resume / partial failures

1. Read the existing context, baseline, evidence, approvals and build logs. Do not initialize a replacement
   run just because the chat resumed.
2. Check identity and selected store builds. Never infer the target from `latest`.
3. If upload succeeded but record failed (exit 80), repair that record and bind the same artifact.
   If upload outcome is unknown, inspect the store before rerunning anything.
4. Keep the successful platform when the other failed. Do not re-upload the successful one.
5. Re-fetch Remote Config before production verification/approval. If endpoint/template or bundled config
   differs from verified inputs, invalidate related verification and rerun it.
6. If a desired version/build/commit changes, create a new run and obtain the relevant approval again.
   If notes/assets/rollout/release mode change, invalidate the affected production approval.
7. Missing original artifact blocks artifact-backed verification. Do not rebuild and claim it is the
   uploaded artifact. Report the limitation and recover the original or ask how to proceed.

Do not delete runs automatically. They provide release evidence and may contain private data.
Any later retention cleanup must be explicitly scoped and authorized.
