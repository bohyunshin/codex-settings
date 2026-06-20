---
name: generate-subagent
description: Create or update Claude Code-compatible subagent (.md files in agents/ directories). Use when the user wants to create a new subagent, add a custom agent, generate an agent definition, or mentions /generate-subagent. Scans existing agents for similar functionality - integrates into an existing agent if overlap is found, otherwise creates a new one. Asks whether to place the agent globally (~/.claude_personal/agents/) or project-level (.claude/agents/).
---

# Generate Subagent

Create Claude Code subagent definitions by scanning for similar existing agents and either integrating or creating new ones.

## Subagent File Format

Subagent files are Markdown with YAML frontmatter, stored as `.md` files:

```markdown
---
name: kebab-case-name
description: When Claude should delegate to this agent. Include "use proactively" for automatic delegation.
tools: Read, Grep, Glob, Bash, Edit, Write
model: sonnet | opus | haiku | inherit
permissionMode: default | acceptEdits | dontAsk | bypassPermissions | plan
skills:
  - skill-name-to-preload
memory: user | project | local
---

System prompt goes here as markdown body.
```

### Frontmatter Fields

| Field | Required | Description |
|-------|----------|-------------|
| `name` | Yes | Unique kebab-case identifier |
| `description` | Yes | When Claude should delegate to this agent |
| `tools` | No | Allowed tools (defaults to all). Options: `Read`, `Grep`, `Glob`, `Bash`, `Edit`, `Write`, `WebFetch`, `WebSearch`, `Task`, `NotebookEdit` |
| `disallowedTools` | No | Tools to deny from inherited set |
| `model` | No | Model to use (default: `inherit`) |
| `permissionMode` | No | Permission handling mode |
| `skills` | No | Skills to preload into agent context |
| `memory` | No | Persistent memory scope |
| `hooks` | No | Lifecycle hooks (PreToolUse, PostToolUse, Stop) |

### Storage Locations

| Location | Scope | Use case |
|----------|-------|----------|
| `.claude/agents/` | Current project only | Project-specific agents (commit to VCS) |
| `~/.claude_personal/agents/` | All projects | Personal agents reusable across projects |

## Workflow

### Step 1: Gather Requirements

Ask the user what the subagent should do. Collect:
- **Purpose**: What tasks should the agent handle?
- **Trigger**: When should Claude delegate to it?
- **Capabilities**: What tools does it need? Read-only or read-write?
- **Model**: Does it need a specific model (sonnet for balance, haiku for speed, opus for capability)?

If the user provides a brief description, infer reasonable defaults and confirm.

### Step 2: Scan Existing Agents

Check both agent directories for existing agents:

```bash
ls ~/.claude_personal/agents/ 2>/dev/null
ls .claude/agents/ 2>/dev/null
```

For each existing agent file found, read its full content (name, description, and system prompt body) to perform a **full content analysis**. Compare:
- Does the existing agent's purpose overlap with the requested agent?
- Would the new functionality fit naturally as an extension of an existing agent?
- Are there conflicting tool permissions or model choices?

### Step 3: Decide — Integrate or Create

Present findings to the user:

**If a similar agent exists:**

```
Found existing agent with overlapping functionality:

  Agent: <name>
  File: <path>
  Overlap: <description of functional overlap>

Options:
  1. Integrate into existing agent (extend its prompt and capabilities)
  2. Create a separate new agent anyway
```

Ask the user which option to use.

**If integrating**: Read the existing agent file, merge the new capabilities into its system prompt, and update tools/model if needed. Preserve the existing agent's structure and style.

**If no similar agent exists**: Proceed to create a new agent.

### Step 4: Choose Placement

Ask the user:

```
Where should this agent be placed?

  1. Global (~/.claude_personal/agents/) - available in all projects
  2. Project (.claude/agents/) — only this project
```

Create the target directory if it does not exist:

```bash
mkdir -p <chosen-directory>
```

### Step 5: Write the Agent File

Write the `.md` file with proper frontmatter and system prompt.

Guidelines for writing effective agents:
- **Description**: Be specific about when to delegate. Include "use proactively" if the agent should auto-trigger.
- **Tools**: Only include tools the agent actually needs. Use read-only tools (`Read`, `Grep`, `Glob`) for review/analysis agents. Add `Edit`, `Write` for agents that modify code.
- **System prompt**: Be concise and focused. Include specific instructions for what the agent should do when invoked. Include output format expectations.
- **Model**: Use `haiku` for fast read-only tasks, `sonnet` for balanced analysis+modification, `opus` for complex reasoning, `inherit` to match parent.

### Step 6: Verify

After writing the file:

1. Read back the created/modified file to confirm correctness
2. Report the result:

```
Subagent created:
  Name: <name>
  File: <path>
  Tools: <tool list>
  Model: <model>

The agent is available immediately (no restart needed if using /agents, otherwise restart the session).
```
