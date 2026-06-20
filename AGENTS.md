# Global Codex Instructions

## Language & Communication

- All code, comments, and commit messages must be in English.
- PR titles must be in English.
- PR bodies must be in Korean.

## Python

- Use Python 3.10 or 3.11.
- Use `uv` or `poetry` for dependency management.
- Use `pyproject.toml` for project configuration; avoid `setup.py` and `setup.cfg`.
- Prefer type hints for function signatures.
- Follow PEP 8 naming conventions:
  - `snake_case` for functions and variables.
  - `PascalCase` for classes.
  - `UPPER_SNAKE_CASE` for constants.

## Git

- Use conventional commits: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:`, `perf:`, `ci:`, `build:`.
- Separate unrelated changes into distinct commits.
- Never force-push or reset shared branches unless explicitly requested.

## General Practices

- Read existing code before modifying it.
- Keep changes minimal and focused on the task at hand.
- Do not add unnecessary abstractions, comments, or error handling.
- Prefer editing existing files over creating new ones.
