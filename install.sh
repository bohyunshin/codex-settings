#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
codex_home="${CODEX_HOME:-$HOME/.codex}"
skills_home="${CODEX_SKILLS_HOME:-$HOME/.agents/skills}"

mkdir -p "$codex_home" "$skills_home"

ln -sfn "$repo_dir/AGENTS.md" "$codex_home/AGENTS.md"

find "$repo_dir/skills" -mindepth 1 -maxdepth 1 | while IFS= read -r entry; do
  name="$(basename "$entry")"
  case "$name" in
    .system|.venv|__pycache__)
      continue
      ;;
  esac
  ln -sfn "$entry" "$skills_home/$name"
done

echo "Linked AGENTS.md to $codex_home/AGENTS.md"
echo "Linked skills to $skills_home"
echo "Review config.toml before linking or copying it to $codex_home/config.toml"
