---
name: commit-push-pr
description: Commit, push, and create a pull request in one workflow. Use when the user invokes /commit-push-pr or asks to commit and create a PR. Separates changes into purpose-based commits with conventional commit messages in English, pushes to remote, and opens a PR to the upstream repository with English title and Korean body.
---

# Commit, Push, and Create PR

## Workflow

### 1. Analyze Changes

Run `git status` and `git diff` (staged + unstaged) to understand all pending changes. Group related changes by purpose (feature, bugfix, refactor, docs, chore, etc.).

### 2. Create Purpose-Separated Commits

For each logical group of changes, stage only the relevant files and create a commit.

Commit message format (English):
```
<type>: <concise description>
```

Types: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `ci`, `cicd`, `build`

Examples:
- `feat: add user authentication endpoint`
- `fix: resolve null pointer in payment processing`
- `docs: update API usage examples`
- `chore: bump dependency versions`

Rules:
- One commit per logical purpose. Do NOT bundle unrelated changes.
- Commit message must be in **English**.
- Use imperative mood ("add", not "added" or "adds").
- Use HEREDOC for commit messages to ensure proper formatting.

### 3. Push to Remote

Push the current branch to the remote with `-u` flag:
```bash
git push -u origin <branch-name>
```

### 4. Create PR (unless `--no-pr` is passed or no upstream exists)

**If `--no-pr` argument is passed**, skip PR creation entirely. Just inform the user that commits have been pushed.

Otherwise, check remotes:
```bash
git remote -v
```

- If an `upstream` remote exists → create a PR targeting the upstream repository using `--repo <upstream-owner>/<repo>`.
- If **no** `upstream` remote exists → **ask the user** whether:
  1. There is an upstream repository they want to add (if so, ask for the URL, add it with `git remote add upstream <url>`, and create a PR targeting it).
  2. They want to open the PR on the current (`origin`) repository (create a PR without the `--repo` flag).

When creating a PR, use `gh pr create`. Title must follow the **conventional commit format** (`<type>: <description>`) in **English**, body must be in **Korean**.

PR title format:
```
<type>: <concise description>
```

Types are the same as commit messages: `feat`, `fix`, `chore`, `docs`, `refactor`, `test`, `style`, `perf`, `ci`, `cicd`, `build`.

PR title examples:
- `feat: add user authentication endpoint`
- `fix: resolve null pointer in payment processing`
- `chore: bump dependency versions`

```bash
# When targeting upstream:
gh pr create --repo <upstream-owner>/<repo> --title "<type>: <English description>" --body "$(cat <<'EOF'
## 요약
- <변경사항 요약 bullet points>

## 변경 내용
- <상세 변경 내용>

## 테스트
- <테스트 관련 내용>
EOF
)"

# When targeting origin (no upstream):
gh pr create --title "<type>: <English description>" --body "$(cat <<'EOF'
## 요약
- <변경사항 요약 bullet points>

## 변경 내용
- <상세 변경 내용>

## 테스트
- <테스트 관련 내용>
EOF
)"
```

Rules:
- If `--no-pr` is passed, do NOT create a PR. Only commit and push.
- PR title must use **conventional commit format** (`<type>: <description>`) in **English**.
- PR body must be in **Korean**.
- When upstream exists, use `--repo` flag to target the upstream repository.
- When no upstream exists, ask the user before deciding the PR target.
- Return the PR URL to the user when done.
