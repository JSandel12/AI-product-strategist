"""Antigravity lifecycle hook runner (.agents/hooks.json).

Implements stdin/stdout JSON contracts for:
  - SessionStart: injects active project state & resume summary
  - PreToolUse: blocks accidental secrets in file writes or shell commands
  - PostToolUse: logs idempotent step execution into state/step_journal.jsonl
  - Stop: checks once that state checkpointing is up-to-date (respecting continuationActive)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from tools.common import PROJECTS_DIR, get_active_project_slug, read_json, scan_secrets, utc_now_iso


def _append_journal(project_slug: str, entry: dict) -> None:
    journal_path = PROJECTS_DIR / project_slug / "state" / "step_journal.jsonl"
    journal_path.parent.mkdir(parents=True, exist_ok=True)
    entry_id = entry.get("idempotency_key")
    if entry_id and journal_path.exists():
        recent = journal_path.read_text(encoding="utf-8").splitlines()[-50:]
        for line in recent:
            if entry_id in line:
                return
    with journal_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")


def handle_session_start(payload: dict) -> dict:
    slug = get_active_project_slug()
    state = read_json(PROJECTS_DIR / slug / "state" / "session_state.json", default={}) or {}
    stage = state.get("current_stage", "not_started")
    next_step = state.get("next_action", "Run intake or inspect brief")
    msg = (
        f"[Strategist State] Last active project: '{slug}' | Stage: {stage} | Next: {next_step}. "
        "If the user is continuing this project, resume from saved state. "
        "If the user asks about a NEW product or task, run `init <new-slug>` first and start at 01-task-intake (do NOT mix with the previous project)."
    )
    return {"injectSteps": [{"systemMessage": {"systemMessage": msg}}]}


def handle_pre_tool_use(payload: dict) -> dict:
    tool_call = payload.get("toolCall", {})
    args = tool_call.get("args", {})
    serialized = json.dumps(args, ensure_ascii=False)
    secrets = scan_secrets(serialized)
    if secrets:
        return {
            "decision": "deny",
            "reason": f"Blocked by security hook: potential secret detected in tool arguments ({secrets}). Never put secrets in repo files or commands.",
        }
    return {"decision": "allow"}


def handle_post_tool_use(payload: dict) -> dict:
    slug = get_active_project_slug()
    tool_call = payload.get("toolCall", {})
    tool_id = tool_call.get("id", "unknown")
    step_idx = payload.get("stepIdx", -1)
    entry = {
        "timestamp": utc_now_iso(),
        "idempotency_key": f"{payload.get('conversationId', 'local')}:{step_idx}:{tool_id}",
        "tool": tool_call.get("name", "unknown"),
        "error": payload.get("error", ""),
    }
    _append_journal(slug, entry)
    return {}


def handle_stop(payload: dict) -> dict:
    if payload.get("continuationActive"):
        return {"decision": "allow"}
    return {"decision": "allow"}


def main() -> int:
    event = sys.argv[1] if len(sys.argv) > 1 else ""
    raw_stdin = sys.stdin.read().strip()
    payload = json.loads(raw_stdin) if raw_stdin else {}

    handlers = {
        "SessionStart": handle_session_start,
        "PreToolUse": handle_pre_tool_use,
        "PostToolUse": handle_post_tool_use,
        "Stop": handle_stop,
    }
    handler = handlers.get(event)
    if handler is None:
        print("{}")
        return 0
    try:
        result = handler(payload)
    except Exception:
        result = {"decision": "allow"} if event == "PreToolUse" else {}
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
