# PeopleCoral agent skills

User-scope skills for the PeopleCoral Flutter app (`peoplecoral-workhub`): device verify, store release, notes, status, and listing assets.

This repo is playbooks and scripts only. It does **not** ship `configs/`, signing keys, or store credentials. Each machine keeps those next to its checkout (or in `PEOPLECORAL_CONFIGS`).

Compatible with Claude Code, Cursor, and any agent that reads `SKILL.md` from `~/.agents/skills`, `~/.claude/skills`, or `~/.cursor/skills`.

## Skills

| Skill | Use |
|---|---|
| `verify-peoplecoral` | Drive the app on a simulator/emulator, doctor, smoke, evidence |
| `peoplecoral-release` | Build, verify, submit, promote `wpseoai` |
| `peoplecoral-release-notes` | App Store / Play / TestFlight notes |
| `peoplecoral-release-status` | Read-only live / review / rollout state |
| `peoplecoral-store-assets` | House-style screenshots and Play feature graphic |

## Install

The repo is private. Clone it, then link into user scope (not into a workhub checkout):

```bash
git clone git@github.com:duckhoa-uit/peoplecoral-skills.git
cd peoplecoral-skills
./install.sh
```

`install.sh` points:

- `~/.agents/skills/<name>` → this clone
- `~/.claude/skills/<name>` and `~/.cursor/skills/<name>` → `~/.agents/skills/<name>`

Re-run after `git pull`. Use `./install.sh --replace` only if a real directory is already sitting at `~/.agents/skills/<name>`.

## Checkout and configs

Skills resolve the app from the current working directory (any clone or git worktree), or `PEOPLECORAL_WORKHUB`.

Gitignored configs live at `<checkout>/configs`, or at `PEOPLECORAL_CONFIGS` if this machine keeps secrets elsewhere.

```bash
# from a peoplecoral-workhub checkout or worktree
$HOME/.agents/skills/peoplecoral-release/scripts/check-configs.sh flavor demo
$HOME/.agents/skills/peoplecoral-release/scripts/check-configs.sh store
```

A missing file is a stop. The skill will not guess another clone.

## Tests

```bash
python3 -B -m unittest discover -s skills/peoplecoral-release/tests -v
python3 -B -m unittest discover -s skills/verify-peoplecoral/tests -v
```
