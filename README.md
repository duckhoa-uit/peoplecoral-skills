# PeopleCoral agent skills

User-scope skills for the PeopleCoral Flutter app (`peoplecoral-workhub`): device verify, store release, notes, status, and listing assets.

This repo is playbooks and scripts only. It does **not** ship `configs/`, signing keys, or store credentials. Each machine keeps those next to its checkout (or in `PEOPLECORAL_CONFIGS`).

Compatible with Claude Code, Cursor, and any agent that reads `SKILL.md`.

## Skills

| Skill | Use |
|---|---|
| `verify-peoplecoral` | Drive the app on a simulator/emulator, doctor, smoke, evidence |
| `maintain-verify-peoplecoral` | Upkeep loop for that feature map (source wave on workhub, live drive, one PR here) |
| `peoplecoral-release` | Build, verify, submit, promote `wpseoai` |
| `peoplecoral-release-notes` | App Store / Play / TestFlight notes |
| `peoplecoral-release-status` | Read-only live / review / rollout state |
| `peoplecoral-store-assets` | House-style screenshots and Play feature graphic |

## Install

```bash
npx skills add duckhoa-uit/peoplecoral-skills -g -y
```

That copies the skills into `~/.agents/skills/` and links the agents it finds (Cursor, Claude Code, …). Do **not** pass `--agent '*'` — that tries every agent backend and is noisy.

List without installing:

```bash
npx skills add duckhoa-uit/peoplecoral-skills -l
```

One skill only:

```bash
npx skills add duckhoa-uit/peoplecoral-skills -g -s verify-peoplecoral -y
```

Update later:

```bash
npx skills update -g
```

### Clone + symlink (authors)

If you are editing the skills, keep a clone and point user-scope at it:

```bash
git clone https://github.com/duckhoa-uit/peoplecoral-skills.git
cd peoplecoral-skills
./install.sh --replace
```

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
