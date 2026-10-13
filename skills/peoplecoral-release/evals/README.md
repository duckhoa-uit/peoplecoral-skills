# Validate this bundle

## Deterministic offline contracts

From the current worktree root:

```bash
python3 -B -m unittest discover -s $HOME/.agents/skills/peoplecoral-release/tests -v
bash scripts/release/test_release_tooling.sh
```

The tests use fake accounts, response fixtures and temporary files. No live stores, devices, signing,
backend logins or credentials. Syntax checks are included. The existing release-tooling suite is a
separate layer; it does not substitute for tests of these new helpers.

Five user-scope skills live in `$HOME/.agents/skills/`: `peoplecoral-release`, `peoplecoral-release-notes`,
`peoplecoral-release-status`, `peoplecoral-store-assets`, and `verify-peoplecoral`.
They are not in the workhub repo. `skill-creator/scripts/quick_validate.py` is not required.
Skip it, or run it only when that validator is present. Do not silently install a global Python
dependency or claim validator success when only YAML parsing ran.

## Behavioral evaluation

`evals.json` contains realistic English/Vietnamese requests, edge cases and an RN near-miss. Each has
expected behavior and objective safety assertions. It uses the `skill-creator` eval shape with
additional names/safety metadata.

Run in an isolated agent with **no store credentials, network, device control or deployment tools**.
Supply fixtures as facts and ask for a proposed next-action trace, not real execution. Tool mentions in
the resulting trace are simulated. Never run a sample prompt against the real release environment.

For a smoke evaluation, read the five skills, respond to each scenario with scope, next actions,
blocked actions and required approvals, then grade each assertion against that trace.
This measures instruction-following with a loaded skill, not automatic trigger accuracy or real-store correctness.

For a comparative benchmark, snapshot the old skill before editing, run with-old/with-new in separate
fresh contexts per case, record outputs/tokens/timing, grade blind where useful and use skill-creator's
review viewer. Do not call a grouped one-model smoke pass an independent A/B benchmark.

## Trigger (routing) evaluation

`trigger_queries.json` holds realistic requests with the skill that should load first, or `null`.
The near-misses matter most: the RN app, dev/demo uploads, bug-report screenshots, PR changelogs, another
app's submission, production verify vs device smoke, and requests the generic `asc-*` skills also match.
A cheap check: give a fresh agent the names and descriptions of these five skills plus the competing
installed skills, and ask which it would load for each query. The real measure is invocation in fresh sessions (skill-creator `run_loop.py`, or
`claude plugin eval` with a `tool_used: Skill` grader). Re-run after every description change.

## When to update

Add a contract test for every script bug before fixing it, an eval case for every behavior a real run got
wrong, and a Gotchas line in SKILL.md for every new failure mode.

Keep evaluation outputs outside the skill folders in a private run workspace, with no session transcripts
or real account data. Record failures, including tests that cannot run, and turn reproducible script bugs
into contract tests before claiming they are fixed.
