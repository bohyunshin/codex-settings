---
name: refactor
description: Medium-scale code refactoring with user-guided direction selection. Use when the user wants to refactor code, clean up a module, reduce duplication, modularize functions, unify pipeline patterns, or improve code structure. Triggers on mentions of /refactor, "refactor this", "clean up this code", "deduplicate", "modularize", or similar requests. This is NOT for large-scale rewrites — it targets focused, scoped improvements that do not break surrounding code.
---

# Refactor

Medium-scale, direction-guided code refactoring. Analyze the target code, suggest refactoring directions, let the user choose, then apply changes scoped strictly to the selected area.

## Refactoring Directions

When analyzing code, look for these patterns and suggest the applicable ones:

| Direction | When to suggest | Example |
|-----------|----------------|---------|
| **Remove duplication** | 2+ code blocks share >60% similar logic | Multiple functions with near-identical loops differing only in a filter condition |
| **Extract function/method** | A block inside a function does a distinct sub-task (>10 lines) | Data validation logic inlined in a request handler |
| **Unify pipeline** | Multiple processing paths follow the same structure with minor variations | Several ETL functions that load/transform/save with different sources |
| **Simplify conditionals** | Deeply nested if/else, complex boolean chains, or repeated guard clauses | 4+ levels of nesting that can be flattened with early returns |
| **Consolidate constants** | Magic numbers/strings scattered across files | Hardcoded URLs, thresholds, or config values repeated in multiple places |
| **Improve naming** | Variables/functions with unclear, abbreviated, or misleading names | `d`, `tmp2`, `process_data` (too vague) |
| **Reduce coupling** | A function depends on many external details it shouldn't know about | A utility function importing from 5 different domain modules |
| **Standardize patterns** | Mixed styles for the same task within the same codebase | Some functions use dict, others use dataclass for the same kind of data |

## Workflow

### Step 1: Identify Target Scope

Determine what to refactor. The user may specify:
- A file or directory (`refactor src/utils/`)
- A function or class (`refactor the DataProcessor class`)
- A vague area (`refactor the data loading code`)

If vague, use `Grep` and `Glob` to locate the relevant code, then confirm the scope with the user.

Read all files within the target scope thoroughly before proceeding.

### Step 2: Analyze and Suggest Directions

Analyze the target code against the refactoring directions table above. For each applicable direction, provide:

```
## Refactoring Options

1. **Remove duplication** (3 occurrences found)
   - `src/loaders/csv_loader.py:45-80` and `src/loaders/json_loader.py:30-65`
     share ~70% identical parsing logic
   - `src/loaders/xml_loader.py:50-85` follows the same pattern

2. **Extract function** (2 candidates)
   - `src/pipeline.py:120-155` — validation block can be a standalone function
   - `src/pipeline.py:200-230` — retry logic repeated inline

3. **Unify pipeline** (1 opportunity)
   - All 3 loaders follow load → validate → transform → save
     but implement it independently
```

Ask the user to pick one or more directions. Allow multi-select when the interface supports it; otherwise accept a short text response.

### Step 3: Plan Changes

After the user selects direction(s), create a concrete plan:

1. List every file that will be modified
2. For each file, describe what changes will be made
3. Explicitly state which files will NOT be touched

Present the plan and confirm before proceeding.

### Step 4: Apply Changes

Execute the refactoring with these constraints:

**Scope rules:**
- Only modify files listed in the plan from Step 3
- Do not change function signatures that are called from outside the target scope (preserve public API)
- Do not alter behavior — inputs and outputs must remain identical
- Do not rename symbols imported by files outside the target scope unless the user explicitly approves

**Change style:**
- Keep changes minimal and readable
- Match the existing code style (indentation, naming convention, import style)
- Do not add comments explaining the refactoring itself
- Do not add type hints, docstrings, or error handling beyond what already exists

### Step 5: Verify

After applying changes:

1. If the project has tests, run them to confirm nothing is broken:
   ```bash
   # Detect and run the project's test command
   # e.g., pytest, npm test, cargo test, go test ./...
   ```
2. If the project has a linter, run it on the modified files only
3. Report the result:

```
## Refactoring Complete

Direction: <selected direction>
Files modified: <count>
  - src/loaders/base.py (new — extracted common logic)
  - src/loaders/csv_loader.py (simplified, uses base)
  - src/loaders/json_loader.py (simplified, uses base)

Files NOT modified (verified untouched):
  - src/pipeline.py
  - src/main.py
  - tests/*

Tests: PASS (42 passed, 0 failed)
```

## Safety Guardrails

- Never modify files outside the agreed scope
- Never change public interfaces without explicit user approval
- If a refactoring would require changes beyond the target scope (e.g., updating callers in other modules), stop and inform the user instead of proceeding
- If tests fail after refactoring, revert the changes and report what went wrong
