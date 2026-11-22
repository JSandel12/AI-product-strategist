"""Local hybrid knowledge base (lexical BM25 + link-graph traversal) with provenance & revocation.

Enforces strict trust separation:
  - methodology: curated files under knowledge/
  - project_input / verified_source: primary sources with explicit URI/file+page
  - agent_output: past generated drafts (explicitly flagged; NEVER treated as verified fact)
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from tools.common import KNOWLEDGE_DIR, PROJECTS_DIR, read_json, utc_now_iso, write_json

TOKEN_RE = re.compile(r"[a-zA-Zа-яА-ЯёЁ0-9_-]{2,}")
LINK_RE = re.compile(r"(SRC-\d+|ADR-\d+|OPT-\d+|\[[^\]]+\]\(([^)]+)\))")


@dataclass
class KBDocument:
    """Indexed document chunk with provenance tier and outgoing links."""

    doc_id: str
    path: str
    trust_tier: str
    title: str
    text: str
    links: list[str]
    revoked: bool = False
    revocation_reason: str = ""
    superseded_by: str = ""


def tokenize(text: str) -> list[str]:
    """Lowercase tokenizer supporting Russian and English terms."""
    return [t.lower() for t in TOKEN_RE.findall(text)]


def _load_revocations(project_slug: str | None) -> dict[str, dict[str, str]]:
    if not project_slug:
        return {}
    rev_path = PROJECTS_DIR / project_slug / "research" / "revocations.json"
    data = read_json(rev_path, default={})
    return data if isinstance(data, dict) else {}


def revoke_record(
    project_slug: str,
    record_id: str,
    reason: str,
    superseded_by: str = "",
) -> dict[str, Any]:
    """Mark an outdated knowledge record or claim ID as revoked/superseded."""
    rev_path = PROJECTS_DIR / project_slug / "research" / "revocations.json"
    revocations = _load_revocations(project_slug)
    entry = {
        "record_id": record_id,
        "reason": reason,
        "superseded_by": superseded_by,
        "revoked_at": utc_now_iso(),
    }
    revocations[record_id] = entry
    write_json(rev_path, revocations)
    return entry


def collect_documents(project_slug: str | None = None, include_agent_outputs: bool = False) -> list[KBDocument]:
    """Collect chunks from methodology, project inputs/research, and optionally past outputs."""
    docs: list[KBDocument] = []
    revocations = _load_revocations(project_slug)

    def add_markdown_file(path: Path, trust_tier: str, prefix: str) -> None:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return
        sections = re.split(r"(?=^#{1,3}\s+)", content, flags=re.MULTILINE)
        for idx, sec in enumerate(sections):
            clean = sec.strip()
            if not clean:
                continue
            first_line = clean.splitlines()[0].lstrip("# ").strip()
            doc_id = f"{prefix}:{path.name}#sec{idx}"
            links = sorted({m.group(1) for m in LINK_RE.finditer(clean)})
            rev_info = revocations.get(doc_id) or revocations.get(path.name) or {}
            docs.append(
                KBDocument(
                    doc_id=doc_id,
                    path=str(path),
                    trust_tier=trust_tier,
                    title=first_line[:120],
                    text=clean,
                    links=links,
                    revoked=bool(rev_info),
                    revocation_reason=rev_info.get("reason", ""),
                    superseded_by=rev_info.get("superseded_by", ""),
                )
            )

    if KNOWLEDGE_DIR.exists():
        for md in sorted(KNOWLEDGE_DIR.rglob("*.md")):
            add_markdown_file(md, "methodology", "kb")

    if project_slug:
        proj_dir = PROJECTS_DIR / project_slug
        for sub, tier in (("inputs", "project_input"), ("research", "verified_source"), ("decisions", "decision_ledger")):
            sub_dir = proj_dir / sub
            if sub_dir.exists():
                for f in sorted(sub_dir.rglob("*")):
                    if f.is_file() and f.suffix.lower() in {".md", ".yaml", ".yml", ".txt"}:
                        add_markdown_file(f, tier, sub)

        if include_agent_outputs:
            out_dir = proj_dir / "outputs"
            if out_dir.exists():
                for f in sorted(out_dir.rglob("*.md")):
                    add_markdown_file(f, "agent_output_UNVERIFIED", "outputs")

    return docs


def search_kb(
    query: str,
    project_slug: str | None = None,
    top_k: int = 5,
    include_agent_outputs: bool = False,
    include_revoked: bool = False,
) -> list[dict[str, Any]]:
    """Hybrid BM25 lexical + link-boost search across separated knowledge tiers."""
    docs = collect_documents(project_slug=project_slug, include_agent_outputs=include_agent_outputs)
    if not include_revoked:
        docs = [d for d in docs if not d.revoked]
    if not docs:
        return []

    q_tokens = tokenize(query)
    if not q_tokens:
        return []

    tokenized_docs = [tokenize(f"{d.title} {d.text}") for d in docs]
    n_docs = len(docs)
    avgdl = sum(len(t) for t in tokenized_docs) / max(n_docs, 1)

    df: Counter[str] = Counter()
    for toks in tokenized_docs:
        df.update(set(toks))

    k1, b = 1.5, 0.75
    scores: list[float] = []
    q_upper = query.upper()

    for doc, toks in zip(docs, tokenized_docs):
        tf = Counter(toks)
        dl = len(toks) or 1
        bm25 = 0.0
        for qt in q_tokens:
            freq = tf.get(qt, 0)
            if freq == 0:
                continue
            idf = math.log(1.0 + (n_docs - df[qt] + 0.5) / (df[qt] + 0.5))
            bm25 += idf * (freq * (k1 + 1.0)) / (freq + k1 * (1.0 - b + b * dl / avgdl))
        # Link / ID graph boost when query references SRC-xx / ADR-xx / OPT-xx
        link_boost = sum(1.5 for lnk in doc.links if lnk.upper() in q_upper)
        tier_boost = 0.2 if doc.trust_tier in {"verified_source", "project_input"} else 0.0
        scores.append(bm25 + link_boost + tier_boost)

    ranked = sorted(
        [(s, d) for s, d in zip(scores, docs) if s > 0],
        key=lambda item: item[0],
        reverse=True,
    )[:top_k]

    results: list[dict[str, Any]] = []
    for score, doc in ranked:
        payload = asdict(doc)
        payload["score"] = round(score, 4)
        payload["excerpt"] = doc.text[:350] + ("..." if len(doc.text) > 350 else "")
        del payload["text"]
        if doc.trust_tier == "agent_output_UNVERIFIED":
            payload["warning"] = "Past agent output is NOT a verified fact; confirm against primary SRC-* sources."
        results.append(payload)
    return results
