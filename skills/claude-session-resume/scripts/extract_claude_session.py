#!/usr/bin/env python3
"""Extract Claude Code session context for a Codex resume handoff."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


TEXT_EXTENSIONS = {
    ".jsonl",
    ".json",
    ".log",
    ".txt",
    ".md",
    ".yaml",
    ".yml",
}

SKIP_DIRS = {
    ".git",
    "__pycache__",
    "Cache",
    "Cache_Data",
    "Code Cache",
    "DawnGraphiteCache",
    "DawnWebGPUCache",
    "GPUCache",
    "IndexedDB",
    "node_modules",
    "Service Worker",
}

DEFAULT_MAX_FILE_SIZE = 50 * 1024 * 1024

SECRET_PATTERNS = [
    re.compile(
        r"(?i)\b(api[_-]?key|authorization|bearer|password|secret|token)\b"
        r"(\s*[:=]\s*)([^\s'\"`]+)"
    ),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{20,})\b"),
    re.compile(r"\b(gh[pousr]_[A-Za-z0-9_]{20,})\b"),
]


@dataclass
class Candidate:
    path: Path
    reasons: list[str] = field(default_factory=list)
    score: int = 0


@dataclass
class Event:
    index: int
    path: Path
    timestamp: str
    role: str
    text: str
    cwd: str = ""


@dataclass
class ToolCall:
    index: int
    path: Path
    timestamp: str
    name: str
    detail: str


@dataclass
class TextSnippet:
    path: Path
    text: str


def default_roots() -> list[Path]:
    home = Path.home()
    return [
        home / ".claude" / "projects",
        home / ".claude",
        home / "Library" / "Application Support" / "Claude" / "claude-code-sessions",
        home / "Library" / "Application Support" / "Claude" / "local-agent-mode-sessions",
        home / "Library" / "Logs" / "Claude",
        home / "Library" / "Caches" / "claude-cli-nodejs",
        home / ".config" / "claude",
        home / ".cache" / "claude",
    ]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Find local Claude Code logs by session ID and emit Markdown context."
    )
    parser.add_argument("session_id", help="Claude Code session ID or unique session fragment")
    parser.add_argument(
        "--root",
        action="append",
        default=[],
        help="Additional root directory to search. Can be supplied more than once.",
    )
    parser.add_argument(
        "--output",
        help="Write Markdown report to this file instead of stdout.",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=350,
        help="Maximum transcript events to include. Keeps the beginning and latest events.",
    )
    parser.add_argument(
        "--event-chars",
        type=int,
        default=3500,
        help="Maximum characters to include for each transcript event.",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=DEFAULT_MAX_FILE_SIZE,
        help="Maximum file size in bytes to scan.",
    )
    parser.add_argument(
        "--no-redact",
        action="store_true",
        help="Disable common secret redaction in generated output.",
    )
    return parser.parse_args()


def normalize_session_id(value: str) -> str:
    return value.strip().strip("'\"")


def iter_search_roots(extra_roots: Iterable[str]) -> list[Path]:
    roots: list[Path] = []
    seen: set[Path] = set()
    for root in [*default_roots(), *(Path(item).expanduser() for item in extra_roots)]:
        try:
            resolved = root.resolve()
        except OSError:
            resolved = root.expanduser()
        if resolved.exists() and resolved not in seen:
            roots.append(resolved)
            seen.add(resolved)
    return roots


def should_skip_dir(path: Path) -> bool:
    return path.name in SKIP_DIRS or path.name.endswith(".indexeddb.leveldb")


def is_text_candidate(path: Path, session_id: str) -> bool:
    if session_id in str(path):
        return True
    return path.suffix in TEXT_EXTENSIONS


def contains_bytes(path: Path, needle: bytes, max_file_size: int) -> bool:
    try:
        if path.stat().st_size > max_file_size:
            return False
        with path.open("rb") as handle:
            previous = b""
            while True:
                chunk = handle.read(1024 * 1024)
                if not chunk:
                    return False
                data = previous + chunk
                if needle in data:
                    return True
                previous = data[-len(needle) :] if needle else b""
    except (OSError, ValueError):
        return False


def find_candidates(
    session_id: str,
    roots: list[Path],
    max_file_size: int,
) -> list[Candidate]:
    candidates: dict[Path, Candidate] = {}
    needle = session_id.encode("utf-8")

    for root in roots:
        for current, dir_names, file_names in os.walk(root):
            current_path = Path(current)
            dir_names[:] = [
                name for name in dir_names if not should_skip_dir(current_path / name)
            ]
            for file_name in file_names:
                path = current_path / file_name
                if not is_text_candidate(path, session_id):
                    continue
                candidate = candidates.setdefault(path, Candidate(path=path))
                path_text = str(path)
                if session_id in path_text:
                    candidate.reasons.append("session id appears in path")
                    candidate.score += 50
                if path.name == f"{session_id}.jsonl" or path.stem == session_id:
                    candidate.reasons.append("filename exactly matches session id")
                    candidate.score += 100
                if contains_bytes(path, needle, max_file_size):
                    candidate.reasons.append("session id appears in file content")
                    candidate.score += 75

    found = [candidate for candidate in candidates.values() if candidate.reasons]
    return sorted(found, key=lambda item: (-item.score, str(item.path)))


def read_text(path: Path, max_file_size: int) -> str:
    if path.stat().st_size > max_file_size:
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def load_json_records(path: Path, max_file_size: int) -> list[dict[str, Any]]:
    try:
        text = read_text(path, max_file_size)
    except OSError:
        return []
    if not text:
        return []

    if path.suffix == ".jsonl":
        records = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return records

    if path.suffix == ".json":
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            return []
        if isinstance(value, dict):
            return [value]
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


def redact(text: str, enabled: bool) -> str:
    if not enabled:
        return text
    redacted = text
    for pattern in SECRET_PATTERNS:
        if pattern.groups >= 3:
            redacted = pattern.sub(r"\1\2[REDACTED]", redacted)
        else:
            redacted = pattern.sub("[REDACTED]", redacted)
    return redacted


def compact_json(value: Any, limit: int = 1200) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    except TypeError:
        text = str(value)
    return truncate(text, limit)


def extract_content_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts = [extract_content_text(item) for item in value]
        return "\n".join(part for part in parts if part)
    if isinstance(value, dict):
        item_type = value.get("type")
        if item_type == "text" and isinstance(value.get("text"), str):
            return value["text"]
        if item_type == "tool_use":
            name = value.get("name", "tool")
            detail = compact_json(value.get("input", {}))
            return f"[tool_use: {name}] {detail}"
        if item_type == "tool_result":
            content = extract_content_text(value.get("content"))
            if content:
                return f"[tool_result]\n{content}"
            return "[tool_result]"
        if "content" in value:
            return extract_content_text(value.get("content"))
        if "text" in value:
            return extract_content_text(value.get("text"))
        if "message" in value:
            return extract_content_text(value.get("message"))
    return ""


def extract_record_text(record: dict[str, Any]) -> tuple[str, str]:
    message = record.get("message")
    record_type = str(record.get("type", "event"))

    if isinstance(message, dict):
        role = str(message.get("role") or record_type)
        text = extract_content_text(message.get("content"))
        return role, text

    if isinstance(message, str):
        return record_type, message

    text = extract_content_text(record.get("content"))
    if text:
        return record_type, text

    if record_type in {"summary", "system"}:
        summary = record.get("summary") or record.get("text")
        if isinstance(summary, str):
            return record_type, summary

    return record_type, ""


def extract_events(
    records_by_path: dict[Path, list[dict[str, Any]]],
    redaction_enabled: bool,
) -> list[Event]:
    events: list[Event] = []
    for path, records in records_by_path.items():
        for record in records:
            role, text = extract_record_text(record)
            if not text:
                continue
            events.append(
                Event(
                    index=len(events) + 1,
                    path=path,
                    timestamp=str(record.get("timestamp") or record.get("createdAt") or ""),
                    role=role,
                    text=redact(text, redaction_enabled),
                    cwd=str(record.get("cwd") or ""),
                )
            )
    return events


def extract_tool_calls(
    records_by_path: dict[Path, list[dict[str, Any]]],
    redaction_enabled: bool,
) -> list[ToolCall]:
    calls: list[ToolCall] = []
    for path, records in records_by_path.items():
        for record in records:
            message = record.get("message")
            if not isinstance(message, dict):
                continue
            content = message.get("content")
            if not isinstance(content, list):
                continue
            for item in content:
                if not isinstance(item, dict) or item.get("type") != "tool_use":
                    continue
                name = str(item.get("name") or "tool")
                detail = compact_json(item.get("input", {}), limit=900)
                calls.append(
                    ToolCall(
                        index=len(calls) + 1,
                        path=path,
                        timestamp=str(record.get("timestamp") or ""),
                        name=name,
                        detail=redact(detail, redaction_enabled),
                    )
                )
    return calls


def extract_metadata(records_by_path: dict[Path, list[dict[str, Any]]]) -> dict[str, list[str]]:
    keys = [
        "sessionId",
        "cwd",
        "originCwd",
        "gitBranch",
        "version",
        "model",
        "title",
        "createdAt",
        "lastActivityAt",
        "permissionMode",
        "transcriptUnavailable",
    ]
    metadata: dict[str, list[str]] = {key: [] for key in keys}
    for records in records_by_path.values():
        for record in records:
            for key in keys:
                if key not in record:
                    continue
                value = record[key]
                if value is None:
                    continue
                text = str(value)
                if text not in metadata[key]:
                    metadata[key].append(text)
    return {key: values for key, values in metadata.items() if values}


def extract_text_snippets(
    candidates: list[Candidate],
    records_by_path: dict[Path, list[dict[str, Any]]],
    session_id: str,
    max_file_size: int,
    redaction_enabled: bool,
    limit: int = 20,
    context_chars: int = 650,
) -> list[TextSnippet]:
    snippets: list[TextSnippet] = []
    for candidate in candidates:
        if len(snippets) >= limit:
            break
        if candidate.path in records_by_path and candidate.path.suffix in {".json", ".jsonl"}:
            continue
        try:
            text = read_text(candidate.path, max_file_size)
        except OSError:
            continue
        if not text:
            continue
        start = 0
        while len(snippets) < limit:
            index = text.find(session_id, start)
            if index == -1:
                break
            snippet_start = max(0, index - context_chars)
            snippet_end = min(len(text), index + len(session_id) + context_chars)
            snippet = text[snippet_start:snippet_end].strip()
            snippets.append(TextSnippet(path=candidate.path, text=redact(snippet, redaction_enabled)))
            start = index + len(session_id)
    return snippets


def select_events(events: list[Event], max_events: int) -> list[Event | None]:
    if max_events <= 0 or len(events) <= max_events:
        return events
    head_count = min(50, max(1, max_events // 4))
    tail_count = max_events - head_count
    return [*events[:head_count], None, *events[-tail_count:]]


def truncate(text: str, limit: int) -> str:
    if limit <= 0 or len(text) <= limit:
        return text
    return text[:limit].rstrip() + f"\n[truncated {len(text) - limit} chars]"


def fence(text: str) -> str:
    delimiter = "```"
    if delimiter in text:
        delimiter = "````"
    return f"{delimiter}text\n{text}\n{delimiter}"


def format_size(size: int) -> str:
    units = ["B", "KiB", "MiB", "GiB"]
    value = float(size)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} B"
        value /= 1024
    return f"{size} B"


def format_mtime(path: Path) -> str:
    try:
        modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone()
    except OSError:
        return ""
    return modified.isoformat(timespec="seconds")


def markdown_table_row(values: Iterable[str]) -> str:
    escaped = [value.replace("|", "\\|").replace("\n", " ") for value in values]
    return "| " + " | ".join(escaped) + " |"


def build_report(
    session_id: str,
    roots: list[Path],
    candidates: list[Candidate],
    records_by_path: dict[Path, list[dict[str, Any]]],
    max_events: int,
    event_chars: int,
    max_file_size: int,
    redaction_enabled: bool,
) -> str:
    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    metadata = extract_metadata(records_by_path)
    events = extract_events(records_by_path, redaction_enabled)
    tool_calls = extract_tool_calls(records_by_path, redaction_enabled)
    text_snippets = extract_text_snippets(
        candidates=candidates,
        records_by_path=records_by_path,
        session_id=session_id,
        max_file_size=max_file_size,
        redaction_enabled=redaction_enabled,
    )

    lines = [
        "# Claude Code Session Extraction",
        "",
        f"- Session ID: `{session_id}`",
        f"- Generated: `{now}`",
        f"- Matching files: `{len(candidates)}`",
        f"- Parsed JSON records: `{sum(len(records) for records in records_by_path.values())}`",
        f"- Transcript events with text: `{len(events)}`",
        "",
        "## Searched Roots",
        "",
    ]
    if roots:
        lines.extend(f"- `{root}`" for root in roots)
    else:
        lines.append("- No existing default roots found.")

    lines.extend(["", "## Matching Files", ""])
    if candidates:
        lines.extend(
            [
                "| Score | Size | Modified | Path | Reasons |",
                "| ---: | ---: | --- | --- | --- |",
            ]
        )
        for candidate in candidates:
            try:
                size = format_size(candidate.path.stat().st_size)
            except OSError:
                size = ""
            lines.append(
                markdown_table_row(
                    [
                        str(candidate.score),
                        size,
                        format_mtime(candidate.path),
                        str(candidate.path),
                        "; ".join(candidate.reasons),
                    ]
                )
            )
    else:
        lines.append("No matching files were found.")

    lines.extend(["", "## Session Metadata", ""])
    if metadata:
        for key, values in metadata.items():
            joined = ", ".join(f"`{value}`" for value in values[:8])
            if len(values) > 8:
                joined += f" and {len(values) - 8} more"
            lines.append(f"- {key}: {joined}")
    else:
        lines.append("No structured metadata was parsed.")

    lines.extend(["", "## Matched Text Snippets", ""])
    if text_snippets:
        for index, snippet in enumerate(text_snippets, start=1):
            lines.extend(
                [
                    f"### Snippet {index}",
                    "",
                    f"- Source: `{snippet.path}`",
                    "",
                    fence(truncate(snippet.text, 1800)),
                    "",
                ]
            )
    else:
        lines.append("No text snippets were extracted from non-JSON logs.")

    lines.extend(["", "## Tool Calls", ""])
    if tool_calls:
        lines.extend(["| # | Time | Tool | Detail |", "| ---: | --- | --- | --- |"])
        for call in tool_calls[:200]:
            lines.append(
                markdown_table_row(
                    [
                        str(call.index),
                        call.timestamp,
                        call.name,
                        truncate(call.detail, 300),
                    ]
                )
            )
        if len(tool_calls) > 200:
            lines.append("")
            lines.append(f"Skipped {len(tool_calls) - 200} additional tool calls.")
    else:
        lines.append("No tool calls were parsed.")

    lines.extend(["", "## Transcript Events", ""])
    if events:
        for event in select_events(events, max_events):
            if event is None:
                omitted = len(events) - max_events
                lines.extend(["", f"_Omitted {omitted} middle events._", ""])
                continue
            title = f"### {event.index}. {event.role}"
            if event.timestamp:
                title += f" - {event.timestamp}"
            lines.extend([title, ""])
            lines.append(f"- Source: `{event.path}`")
            if event.cwd:
                lines.append(f"- CWD: `{event.cwd}`")
            lines.extend(["", fence(truncate(event.text, event_chars)), ""])
    else:
        lines.append(
            "No transcript text was parsed. If metadata says `transcriptUnavailable`, "
            "the local app may only have session metadata for this ID."
        )

    lines.extend(
        [
            "",
            "## Codex Resume Prompt Draft",
            "",
            "Use the extracted Claude Code context above to continue this work in Codex.",
            "First verify the live repository state, especially `git status --short` and files mentioned in the transcript.",
            "Summarize what was already done, what remains open, and the next concrete commands or edits.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    session_id = normalize_session_id(args.session_id)
    if not session_id:
        print("Session ID is empty.", file=sys.stderr)
        return 2

    roots = iter_search_roots(args.root)
    candidates = find_candidates(session_id, roots, args.max_file_size)
    records_by_path = {
        candidate.path: load_json_records(candidate.path, args.max_file_size)
        for candidate in candidates
    }
    records_by_path = {path: records for path, records in records_by_path.items() if records}

    report = build_report(
        session_id=session_id,
        roots=roots,
        candidates=candidates,
        records_by_path=records_by_path,
        max_events=args.max_events,
        event_chars=args.event_chars,
        max_file_size=args.max_file_size,
        redaction_enabled=not args.no_redact,
    )

    if args.output:
        output_path = Path(args.output).expanduser()
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(output_path)
    else:
        print(report, end="")

    return 0 if candidates else 1


if __name__ == "__main__":
    raise SystemExit(main())
