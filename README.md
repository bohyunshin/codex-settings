# Codex Settings

Personal Codex configuration and skills.

## Layout

- `AGENTS.md` - global guidance loaded by Codex.
- `config.toml` - stable Codex config template.
- `skills/` - personal skills sourced from `~/.claude_personal/skills` and adapted for Codex discovery.

## Usage

```bash
codex-p
```

`codex-p` loads this repository as the personal Codex profile and keeps runtime
state under `~/.codex_personal`.

Do not symlink these skills into the default `~/.codex` or `~/.agents/skills`
paths. Those paths are shared with the default/company Codex environment, so
installing personal skills there makes the two environments overlap.
