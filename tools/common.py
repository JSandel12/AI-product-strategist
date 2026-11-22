"""Shared helpers: strict reproducibility (SEED=42), progress logging, security scanners."""

from __future__ import annotations

import json
import os
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEED = 42

REPO_ROOT = Path(__file__).resolve().parent.parent
PROJECTS_DIR = REPO_ROOT / "projects"
KNOWLEDGE_DIR = REPO_ROOT / "knowledge"
ACTIVE_PROJECT_MARKER = PROJECTS_DIR / ".active_project"

SECRET_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("OpenAI/Anthropic-style key", re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b")),
    ("Google/Gemini API key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("GitHub token", re.compile(r"\b(?:ghp|gho|ghu|ghs|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("AWS Access Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Bearer/JWT token", re.compile(r"Bearer\s+[A-Za-z0-9\-._~+/]+=*", re.IGNORECASE)),
    ("Private key block", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
]

INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("Override system rules", re.compile(r"ignore\s+(all\s+)?(previous|prior|system)\s+instructions", re.IGNORECASE)),
    ("Russian rule override", re.compile(r"игнорируй\s+(все\s+)?(предыдущие|системные)\s+инструкции", re.IGNORECASE)),
    ("Exfiltrate secrets", re.compile(r"(print|reveal|send|exfiltrate)\s+.*(\.env|api[_\s]?key|secret|token)", re.IGNORECASE)),
    ("Role hijack", re.compile(r"you\s+are\s+now\s+(in\s+developer\s+mode|unrestricted|DAN)", re.IGNORECASE)),
]


def set_global_seed(seed: int = SEED) -> int:
    """Fix deterministic seed across Python runtime and optional scientific libraries."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    for mod_name in ("numpy", "torch"):
        if mod_name in sys.modules:
            mod = sys.modules[mod_name]
            if mod_name == "numpy" and hasattr(mod, "random"):
                mod.random.seed(seed)
            elif mod_name == "torch" and hasattr(mod, "manual_seed"):
                mod.manual_seed(seed)
    return seed


def utc_now_iso() -> str:
    """Return ISO-8601 UTC timestamp."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log_progress(step: int, total: int, label: str) -> None:
    """Emit live flushed progress line for long-running CLI/benchmark steps."""
    pct = int(round((step / max(total, 1)) * 100))
    print(f"[{pct:3d}% | {step}/{total}] {label}", file=sys.stderr, flush=True)


def scan_secrets(text: str) -> list[dict[str, str]]:
    """Detect accidental credentials or private keys in text."""
    findings: list[dict[str, str]] = []
    for name, pattern in SECRET_PATTERNS:
        for match in pattern.finditer(text):
            snippet = match.group(0)
            masked = f"{snippet[:6]}...{snippet[-4:]}" if len(snippet) > 12 else "***"
            findings.append({"type": name, "masked_match": masked})
    return findings


def scan_prompt_injection(text: str) -> list[dict[str, str]]:
    """Detect suspicious command-injection strings inside untrusted external inputs."""
    findings: list[dict[str, str]] = []
    for name, pattern in INJECTION_PATTERNS:
        for match in pattern.finditer(text):
            findings.append({"pattern": name, "excerpt": match.group(0)[:80]})
    return findings


def get_active_project_slug(explicit_slug: str | None = None) -> str:
    """Resolve explicit project slug, .active_project marker, or fallback to megafon-family-devices."""
    if explicit_slug:
        return explicit_slug
    if ACTIVE_PROJECT_MARKER.exists():
        slug = ACTIVE_PROJECT_MARKER.read_text(encoding="utf-8").strip()
        if slug and (PROJECTS_DIR / slug).exists():
            return slug
    return "megafon-family-devices"


def set_active_project_slug(slug: str) -> Path:
    """Persist active project pointer so new chats resume seamlessly."""
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_PROJECT_MARKER.write_text(slug.strip(), encoding="utf-8")
    return ACTIVE_PROJECT_MARKER


def read_json(path: Path, default: Any = None) -> Any:
    """Read UTF-8 JSON file or return default if missing."""
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: Any) -> None:
    """Write formatted UTF-8 JSON file creating parents as needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
