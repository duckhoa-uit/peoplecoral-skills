# peoplecoral-ai-toolkit

User-scope agent skills for the PeopleCoral Flutter app. Product code lives in `peoplecoral-workhub`, not here.

## Verification upkeep

Target is always `skills/verify-peoplecoral/` (also linked as `.cursor/skills/verify-peoplecoral` so `/maintain-verification-skill` finds it when this repo is the workspace).

Run `/maintain-verify-peoplecoral`. Product source is a `peoplecoral-workhub` checkout (`PEOPLECORAL_WORKHUB` if cwd is this skills repo). Edits and PRs stay in this repo.

```bash
# from a workhub checkout, or set PEOPLECORAL_WORKHUB
npx skills add PeopleCoral-HR/peoplecoral-ai-toolkit -g -y
```
