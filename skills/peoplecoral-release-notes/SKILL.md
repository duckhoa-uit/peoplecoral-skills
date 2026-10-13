---
name: peoplecoral-release-notes
description: Drafts and applies PeopleCoral wpseoai store release notes (App Store What's New, Play release notes, TestFlight What to Test), measured from the version live on each store. User-scope skill in ~/.agents/skills, not the workhub repo. Use for "release notes", "What's New", "store changelog", "viết notes", "what changed since production", notes between two versions or tags, or the notes step of peoplecoral-release. Use it instead of the generic asc-whats-new-writer for this app. Not for PR descriptions or commit-level changelogs. Drafting alone never authorizes uploads, metadata writes or a release.
---

# PeopleCoral release notes

Notes describe the change **from the version live on that store** to the target build. Android and iOS
often have different live versions, so they usually get different notes.

```bash
S=$HOME/.agents/skills/peoplecoral-release/scripts                  # shared scripts; checkout is cwd or PEOPLECORAL_WORKHUB
R=~/Documents/peoplecoral-review-artifacts/releases
```

Inside a release, use its `$RUN` (fixed version and commit; see the release skill's `run-context.md`).
Standalone, use a private workspace under `$R` and an explicit target commit. Writing notes needs no build,
upload or new store version. Apply only when the user asked for it or the parent run authorizes metadata.

## Gotchas

- Play production `completed` may be approved-but-unpublished or still in review (Managed publishing). Users have the last *published* release: ask for Publishing overview → Last published when unsure.
- `asc versions list` marks old versions `READY_FOR_SALE` too; only `--latest` gives the live one, and with `--latest` the JSON rows are under `items`, not `data` (asc 5.8.1). Parsing `data` silently finds nothing.
- A rebuild under the same version name (a higher build of a version already live) still needs delta notes on the store that already has that version.
- Commit subjects overstate: "feat(x)" may be invisible to users, and a "chore" can change behavior. Check each line against the code.

## 1. Live baseline per store

```bash
$S/gpc.sh tracks get --track production                     # Android: codes on production (not proof of live)
$S/asc.sh versions list --app 6756572980 --platform IOS --state READY_FOR_SALE --latest --output json
```

Record source, observation time and confidence per store in `baseline.json`. Unknown publication means a
draft labeled provisional, never an invented baseline.

## 2. Baseline commit

Prefer the release tag or record of that exact build: `git tag -l 'release/wpseoai/*' 'v*'`. For older,
untagged builds:

- the commit that set it: `git log --format='%h %ad %s' --date=short -G'^version: 1\.2\.1\+155' -- pubspec.yaml`;
- or the last `origin/main` commit before the build's upload date: `git rev-list -1 --first-parent --before='<date>' origin/main`;
- confirm with the screens that existed: `git ls-tree -r --name-only <sha> lib/presentation/views`.

Say in the report when a baseline is approximate.

## 3. User-visible changes

```bash
git log --no-merges --format='%ad %s' --date=short <baseline>..<target-commit>
```

Use subjects to find candidates, then read the diff. Drop internal tooling, CI, tests and docs. Group by
what users see (Requests, Time off, Approvals, Payslips, Expenses, Chat, Contacts, Notifications, sign-in).

## 4. Write

- English, `en-US` (default listing language on both stores; `PLAY_CHANGELOG_LOCALE` must match).
- `What's new in <version>`, then short bullets, biggest first, only as many as the verified delta has. A one-fix hotfix gets one honest bullet, not filler.
- Plain user language: no ticket ids, internal names or "refactor". Same wording on both stores for shared features.
- Play allows 500 characters per language, counting the heading and newlines: `python3 -c 'import sys;print(len(open(sys.argv[1]).read()))' <file>`.

Example, a one-fix patch over a live x.y.0:

```text
What's new in 2.0.1
- Signing in works on the first launch after installing the app.
```

Save to `$RUN/notes/android.txt` and `$RUN/notes/ios.txt` (selected platforms only). Changing notes after
production approval voids that platform's approval.

## 5. Apply

| Where | How | Can change until |
|---|---|---|
| TestFlight "What to Test", Play internal | the parent's upload: `build_app.sh -r "$(cat $RUN/notes/<platform>.txt)"` | testers only; never rebuild just for notes |
| App Store "What's New" | `ASC_WRITE=1 $S/asc.sh localizations update --version <versionId> --locale en-US --whats-new "$(cat $RUN/notes/ios.txt)"`, then read back with `localizations list` | the version is submitted |
| Play production | `RELEASE_NOTES="$(cat $RUN/notes/android.txt)" make promote_android ...` at the approved promote | Publish |

Get `<versionId>` from `python3 $S/resolve_store_version.py --version <x.y.z>` (add `--create --confirm`
only when creating the draft is authorized). Never use the generic `status` versionId: it can point at the
live or in-review version. A version in review follows the release skill's replacement steps.

Avoid `gpc tracks update` for notes: it defaults to `--status completed --rollout 100`.
