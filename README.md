# DMAD

A minimal, **AI-provider-agnostic** persona-agent framework — a learning clone of the BMad reusable agent pattern.

One agent definition, written once, installed into any project and rendered for whichever AI tool you use: Claude Code, GitHub Copilot in VS Code, or anything else that reads Markdown.

## How it works

An agent is split into three layers, and only the first is tool-specific:

```
dmad/agents/<agent-id>/agent.md   provider-neutral activation protocol  (the behaviour)
dmad/agents/<agent-id>/customize.toml  persona data: role, tone, principles, menu  (the personality)
dmad/manifest.toml                 where each AI tool expects its file  (the plumbing)
```

`install.py` copies the shared parts into a target project under `_dmad/`, then renders a thin
wrapper file per provider. The wrappers differ only in **location and YAML frontmatter** — the
body is byte-identical, so every tool runs the same agent.

| Provider | Generated file |
|---|---|
| `claude` | `.claude/skills/<agent-id>/SKILL.md` |
| `copilot` | `.github/agents/<agent-id>.agent.md` |
| `claude-subagent` | `.claude/agents/<agent-id>.md` |
| `generic` | `.dmad-agents/<agent-id>.md` (no frontmatter) |

Adding a new AI tool is a config change in `dmad/manifest.toml`, not code.

## Install into your project

```bash
git clone https://github.com/<you>/DMAD.git ~/tools/DMAD
cd ~/my-app
python ~/tools/DMAD/install.py --target . --providers claude copilot \
    --project-name "My App" --user-name "Your Name"
```

Then commit `_dmad/` and the generated adapter files.

Available flags:

| Flag | Purpose |
|---|---|
| `--providers` | Which tools to generate for, or `all`. Omit to reuse the recorded selection. |
| `--project-name`, `--user-name` | Seed `_dmad/config.toml` on first install only. |
| `--prune` | Delete adapter files left behind when you drop a provider. |
| `--list-providers` | Show every provider and its target path. |

## Update / re-sync

```bash
cd ~/tools/DMAD && git pull
cd ~/my-app && python ~/tools/DMAD/install.py --target .
```

Re-running is safe and idempotent:

- **Overwritten** — `_dmad/scripts/`, `_dmad/agents/*/customize.toml`, and all generated adapter files. Treat these as build output.
- **Seeded once, never clobbered** — `_dmad/config.toml`, `_dmad/config.user.toml`, and everything in `_dmad/custom/`. Your edits survive upgrades.

With no `--providers`, the installer reads `_dmad/install.toml` and regenerates exactly what you had.

## Installed layout

```
_dmad/
  config.toml                 project settings (seeded once, yours to edit)
  config.user.toml            personal overrides        [gitignored]
  install.toml                what was installed — used to re-sync
  agents/<agent-id>/customize.toml   base persona       [overwritten on update]
  custom/
    config.toml               team config overrides
    config.user.toml          personal config overrides [gitignored]
    <agent-id>.toml           team persona overrides
    <agent-id>.user.toml      personal persona overrides [gitignored]
  scripts/                    resolver scripts          [overwritten on update]
```

## Customizing a persona

Never edit the installed `customize.toml` — an update overwrites it. Put changes in
`_dmad/custom/<agent-id>.toml` (team, committed) or `<agent-id>.user.toml` (personal, gitignored):

```toml
[agent]
name = "Ravi"
principles = ["Every assumption gets an owner."]   # appends to the base list

[[agent.menu]]
code = "brief"                                     # matches base -> deep-merged in place
description = "Write a project brief using the ACME template"

[[agent.menu]]
code = "premortem"                                 # new code -> appended
description = "Run a pre-mortem risk workshop"
prompt = "Assume the project failed. Ask why."
```

Re-run the installer afterwards so the generated adapters pick up name/title/icon changes.

### Merge rules

Layers merge base → team → personal via `structural_merge()`:

- dict + dict → merged recursively
- list of tables where every entry has `code`/`id` → merged by that key; matches deep-merge in place, new entries append, order preserved
- list + list without `code`/`id` → concatenated
- anything else → override wins

## Resolvers

The agent calls these at activation; you can run them yourself to debug a merge:

```bash
python _dmad/scripts/resolve_config.py --project-root . --key runtime.user_name
python _dmad/scripts/resolve_customization.py --agent dmad-agent-business-analyst --project-root . --key agent
```

Config layers: `_dmad/config.toml` → `config.user.toml` → `custom/config.toml` → `custom/config.user.toml`.

## Agents

| Id | Persona | Role |
|---|---|---|
| `dmad-agent-business-analyst` | Nova 🔍 | Turns vague ideas into evidence-backed problem statements and requirements |

Activate by asking your AI tool to **"talk to Nova"** or **"I need the business analyst"**.
In VS Code, Copilot also exposes it in the agents dropdown.

## Requirements

Python 3.11+ (uses `tomllib`; falls back to `tomli` on older versions). No other dependencies.

## Developing the framework

This repo dogfoods itself — `python install.py --target . --providers all` installs DMAD into
its own root. The generated `_dmad/`, `.claude/`, `.github/agents/`, and `.dmad-agents/` folders
are gitignored, since here they are build output rather than source.
