# Meishe Agent Skills

[中文说明](READMECN.md)

This repository contains Agent Skills for Meishe products.

The repository catalog can grow over time. Always use `--list` to discover the
skills available in the current version.

## Agent Compatibility

The skills use the open Agent Skills format and do not require a
provider-specific runtime API. They can be installed with the `skills` CLI for
Codex, Cursor, Qoder, Claude Code, and other mainstream agents.

Common agent identifiers:

| Agent | `--agent` value |
| --- | --- |
| Codex | `codex` |
| Cursor | `cursor` |
| Qoder | `qoder` |
| Claude Code | `claude-code` |

When `--agent` is omitted, the CLI detects installed agents and presents an
interactive selection.

## Requirements

- Node.js 18 or later
- `npx`
- The development toolchain required by the selected skill, such as Xcode for
  iOS or Android Studio and Java for Android
- Any SDK package, license, credentials, or signing material required by the
  selected Meishe product

Product-specific prerequisites and restrictions are documented inside each
skill.

## Discover Available Skills

Run this command in the project where the skills will be used:

```sh
npx skills add MeiShe-Skills/meishe-skills --list
```

The full GitHub URL is also supported:

```sh
npx skills add https://github.com/MeiShe-Skills/meishe-skills --list
```

Treat this command's output as the authoritative catalog for the current
repository version.

## Interactive Installation

Let the CLI detect an agent and select skills interactively:

```sh
npx skills add MeiShe-Skills/meishe-skills
```

The default scope is the current project. Add `--global` to make the selected
skills available across projects:

```sh
npx skills add MeiShe-Skills/meishe-skills --global
```

## Install for a Specific Agent

Install every skill currently available in the repository for one agent:

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill '*' \
  --agent codex
```

Replace `codex` with `cursor`, `qoder`, `claude-code`, or another identifier
supported by the CLI. Add `--global` for a global installation and `--yes` for
a non-interactive installation.

Install the complete repository catalog for several agents:

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill '*' \
  --agent codex \
  --agent cursor \
  --agent qoder \
  --agent claude-code
```

Install every available skill to every agent supported by the local CLI:

```sh
npx skills add MeiShe-Skills/meishe-skills --all
```

## Install Selected Skills

First run the `--list` command, then replace `SKILL_NAME` with a name from its
output:

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill SKILL_NAME \
  --agent cursor
```

Repeat `--skill` to install several selected skills:

```sh
npx skills add MeiShe-Skills/meishe-skills \
  --skill SKILL_NAME_1 \
  --skill SKILL_NAME_2 \
  --agent claude-code
```

## Download from Meishe

If access to GitHub is slow or unavailable, download the latest Meishe Agent
Skills package from the
[Meishe Developer Center](https://www.meishesdk.com/developers/), then extract
it to a local directory.

List the skills in the downloaded package:

```sh
npx skills add /absolute/path/to/meishe-skills --list
```

Install interactively from the local package:

```sh
npx skills add /absolute/path/to/meishe-skills
```

Install all skills in the local package for a specific agent:

```sh
npx skills add /absolute/path/to/meishe-skills \
  --skill '*' \
  --agent cursor
```

The local-path installation supports the same `--global`, `--agent`, `--skill`,
`--all`, and `--yes` options as the GitHub installation.

## Verify Installation

List installed skills:

```sh
npx skills list
```

Filter by agent:

```sh
npx skills list --agent codex
npx skills list --agent cursor
npx skills list --agent qoder
npx skills list --agent claude-code
```

List only globally installed skills:

```sh
npx skills list --global
```

## Update

Update all project-level skills:

```sh
npx skills update --project
```

Update all global skills:

```sh
npx skills update --global
```

Update one selected skill:

```sh
npx skills update SKILL_NAME
```

## Notes

- Each skill must include its own `SKILL.md`, scripts, references, and assets.
- Use only the official package type and version supported by the selected
  skill.
- Follow the selected skill's device requirements. Mobile SDK demos may require
  a physical Android or iOS device and may not support emulators or simulators.

## Links

- [Meishe Developer Center](https://www.meishesdk.com/developers/)
- [Repository](https://github.com/MeiShe-Skills/meishe-skills)
- [skills CLI documentation](https://skills.sh/docs/cli)
- [skills CLI source](https://github.com/vercel-labs/skills)
