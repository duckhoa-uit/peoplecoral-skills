---
name: maintain-verify-peoplecoral
description: "Keeps verify-peoplecoral and its feature map honest: one source reader per feature against peoplecoral-workhub, one live agent-device pass, at most one PR of proven corrections on PeopleCoral-HR/peoplecoral-ai-toolkit. Use for /maintain-verify-peoplecoral, /maintain-verification-skill when this repo is the workspace, or \"audit the verify skill\"."
disable-model-invocation: true
compatibility: macOS with a peoplecoral-workhub checkout and the verify-peoplecoral harness (agent-device, Xcode simulator or Android emulator).
---

# Maintain verify-peoplecoral

A feature map rots when the Flutter app changes. This is the upkeep loop for `verify-peoplecoral` only. The unit of rigor is the feature file, not every sentence.

This is not the generic pstack locator. Do not search for `.cursor/skills/verify-*` in workhub. Do not run `/create-verification-skill`.

## Locate (fixed)

| What | Where |
|---|---|
| Skill to edit | `skills/verify-peoplecoral/` in this repo, or `~/.agents/skills/verify-peoplecoral` after install |
| Feature map | that skill's `features/README.md` plus sibling `features/*.md` |
| Product source (read-only) | a `peoplecoral_mobile_app` checkout: cwd if that `pubspec.yaml` is present, else `PEOPLECORAL_WORKHUB` |
| PRs | `PeopleCoral-HR/peoplecoral-ai-toolkit` only |

If product source is missing, stop `blocked` and say so. Source wave cannot run against this skills repo.

## Outcomes

Pick one, and say which:

- **clean** — every feature got source and live coverage; nothing worth shipping. No branch, no PR.
- **changed** — one PR on this repo ships proven doc, harness, or map corrections.
- **blocked** — coverage could not finish or a proven fix could not ship safely. Say exactly what blocked it.

## Edit scope

Only edit `verify-peoplecoral` (its `SKILL.md`, `features/`, and harness scripts it owns). Never edit workhub product code: a behavior the map describes that the app no longer does is either doc drift (fix the map here) or a product regression (report it, don't paper over it in docs).

## Pass

0. **Confirm the target.** The skill above. Load `agent-device` and `verify-peoplecoral` before driving.

1. **Index hygiene.** Read `features/README.md` and glob sibling files. Fix missing, extra, duplicate, or dead entries. Lightweight; no generated inventory.

2. **Source wave.** One read-only subagent per feature file, launched concurrently, reading **workhub** source. Each explains "how does this user-facing feature work?", flags likely doc drift with citations, and returns one concise live-verification recipe. Children never drive the app and never edit files. Return shape: feature summary / source entry points / likely drift or none / one recipe.

3. **Reconcile.** Every feature file has a returned summary. Merge overlapping recipes into as few app states as practical. Spot-check cited drift; don't re-prove clean claims. Sweep recent workhub churn for user-facing surfaces missing from the map — require a concrete source path before calling one missing.

4. **Live pass.** Required even when source looks clean. Follow `verify-peoplecoral`: doctor before first drive, `check-configs.sh flavor <flavor>` before `make run_*`, one long-lived device session, smoke plus any features not in the sweep (login, home, approvals when the account is manager/HR). Hold three invariants: (1) never drive an instance you haven't health-checked since it last did something surprising — doctor before first drive, doctor on each fresh session, doctor again after any failed drive; a wedged UI on a healthy process is a reset or relaunch, not hope; (2) evidence captured so far survives cleanup, checked at its named location; (3) nothing a drive started outlives that drive's usefulness. A doctor failure caused by skill drift is drift: fix it under edit scope and retry once. A feature that can't be reached is `verified-unreachable` only with the concrete prerequisite and the route attempted; if the map omits that prerequisite, that's drift. Any harness fix gets re-driven live before it ships. Final teardown after the last drive; evidence stays.

5. **Triage.** Wrong or missing user-POV description → doc drift, fix it. Working behavior the harness can't drive → harness gap, fix it (scripts executable, invocation in `verify-peoplecoral`). App behavior that's actually broken → product gap; record it for the user, keep it out of this PR.

6. **Ship or stop.** For changed: one PR on `peoplecoral-ai-toolkit` of proven corrections, re-read every changed file first. For clean or blocked: no PR, report the outcome and the coverage honestly.

Keep concise run notes in a scratch location; don't commit them.
