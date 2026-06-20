# Codex Settings

Personal Codex configuration and skills.

## Layout

- `AGENTS.md` - global guidance loaded by Codex.
- `config.toml` - stable Codex config template.
- `skills/` - personal skills sourced from `~/.claude_personal/skills` and adapted for Codex discovery.
- `install.sh` - symlinks this repo into the standard local Codex paths.

## Install

```bash
./install.sh
```

The installer links:

- `AGENTS.md` -> `~/.codex/AGENTS.md`
- each entry in `skills/` -> `~/.agents/skills/`

`config.toml` is intentionally not force-linked by default because existing
`~/.codex/config.toml` files often contain machine-local plugin, project trust,
and notification settings. Review and copy the stable settings manually when
needed.
