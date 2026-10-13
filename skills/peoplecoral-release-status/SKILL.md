---
name: peoplecoral-release-status
description: Reports what is live, in review, approved or uploaded for the PeopleCoral wpseoai app (com.wpseoai.peoplecoral) on Google Play and the App Store. User-scope skill in ~/.agents/skills, not the workhub repo. Use for "bản nào đang live", "Android approved chưa", "đã submit chưa", "TestFlight có build mới chưa", rollout percentage, or the store state before a release. Read-only. For building, uploading, submitting, promoting or rollout changes, the user runs /peoplecoral-release.
---

# PeopleCoral release status

Read-only. Never build, upload, log in, write metadata or change a track from this skill.

```bash
S=$HOME/.agents/skills/peoplecoral-release/scripts
$S/store-status.sh                      # Play production + internal, ASC latest build, TestFlight, live iOS, review
python3 $S/release_context.py history --root ~/Documents/peoplecoral-review-artifacts/releases   # recent release runs
```

`store-status.sh` exits 1 when a read failed: report that part as UNKNOWN, not as "nothing there".
It already asks ASC for `--include builds,testflight,appstore,submission,review` and for the live iOS version.

## Reading the answer

- Play `completed` on production means configured, not approved and not live. With Managed publishing on, an approved release waits in Play Console → Publishing overview until someone presses Publish. The API has no review state: ask the user for the release page or Publishing overview when "approved" or "live" matters.
- The public Play listing shows only the version name. Two builds with the same name cannot be told apart from outside.
- The live iOS version is the `live` line from `store-status.sh`. That script runs `$S/asc.sh versions list --app 6756572980 --platform IOS --state READY_FOR_SALE --latest --output json` (rows under `items`). Older versions also say `READY_FOR_SALE`.
- A version `WAITING_FOR_REVIEW` or `IN_REVIEW` is not live; users still have the previous `READY_FOR_SALE` one.

Report per store: live version/build, what is in review or waiting for Publish, what is only on testing tracks, and which parts are UNKNOWN and why.

If the user wants to act on what they see (release, submit, promote, rollout, replace a build), tell them to run `/peoplecoral-release <what to do>`. That skill is manual on purpose: it writes to the stores.
