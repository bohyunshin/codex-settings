---
name: claude-session-resume
description: Find and summarize local Claude Code session logs from a Claude session ID, then produce a Codex-ready handoff so work can continue in a Codex session. Use when the user provides a Claude Code session ID, asks to recover or inspect a Claude Code transcript, wants to migrate context from Claude Code to Codex, or says to restart/resume Claude work in Codex.
---

# Claude Session Resume

Use this skill to convert a Claude Code session ID into a concise, actionable Codex continuation plan. It cannot import Claude's private runtime state directly; instead, it reconstructs the useful context from local logs and verifies the live repository state before continuing.

## Workflow

1. Extract the Claude session context:
   ```bash
   python3 skills/claude-session-resume/scripts/extract_claude_session.py <session-id> --output /tmp/claude-session-<session-id>.md
   ```
   Use `--root <path>` if the user gives a custom Claude data directory or if the default search misses the session.

2. Read the generated Markdown report. If no transcript is found, use any discovered metadata and tell the user which searched roots had no matching transcript.

3. Summarize the session into a Codex handoff. Prefer this structure:
   ```markdown
   # Codex Resume Handoff

   ## Session
   - Claude session ID:
   - Source log files:
   - Working directory:
   - Branch:

   ## User Goal
   - ...

   ## What Claude Already Did
   - ...

   ## Current Repository State
   - ...

   ## Important Decisions And Constraints
   - ...

   ## Open Work
   - ...

   ## Recommended Codex Start
   1. ...
   2. ...
   3. ...
   ```

4. Verify the repository state before acting:
   ```bash
   git -C <working-directory> status --short
   ```
   Also inspect relevant files mentioned in the transcript. Treat the transcript as historical context, not as proof of the current filesystem state.

5. Continue in Codex only after summarizing the handoff and checking the live state. If the user only asked for a summary, stop after the handoff.

## Log Locations

The helper searches these common locations by default:

- `~/.claude/projects`
- `~/.claude`
- `~/Library/Application Support/Claude/claude-code-sessions`
- `~/Library/Application Support/Claude/local-agent-mode-sessions`
- `~/Library/Logs/Claude`
- `~/Library/Caches/claude-cli-nodejs`
- `~/.config/claude`
- `~/.cache/claude`

Claude Code CLI transcripts are often JSONL files under `~/.claude/projects`. Claude desktop/local-agent metadata may appear under `~/Library/Application Support/Claude/claude-code-sessions` and can identify a session even when the transcript itself is unavailable.

## Summary Rules

- Preserve task intent, constraints, user preferences, file paths, commands, test results, errors, and explicit decisions.
- Separate "observed in transcript" from "verified in current repo".
- Do not include secrets. The helper redacts common token patterns by default, but still scan summaries before sharing them.
- Keep the handoff concise enough to paste into a fresh Codex prompt.
- If multiple matching log files exist, prefer exact `sessionId` matches and JSONL transcript files over metadata-only JSON files.
