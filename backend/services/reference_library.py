"""
本地文献库（轻量版）

目的：
- 在不依赖外部检索/付费 API 的前提下，让本地 LLM 能引用用户提供的资料。

约束：
- 仅读取 references/ 目录下的 .txt / .md
- 不做复杂向量检索（避免额外依赖与长时间初始化）
- 通过简单关键词匹配抽取少量上下文片段注入 prompt
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ReferenceSnippet:
    source: str
    text: str


def _repo_root() -> Path:
    # backend/services/reference_library.py -> parents[2] = repo root (StarBuddy/)
    return Path(__file__).resolve().parents[2]


def _iter_reference_files() -> Iterable[Path]:
    root = _repo_root() / "references"
    if not root.exists() or not root.is_dir():
        return []
    files = []
    for ext in (".txt", ".md"):
        files.extend(root.rglob(f"*{ext}"))
    # avoid huge scans
    return sorted(files)[:200]


def find_reference_snippets(query: str, max_snippets: int = 3, window: int = 220, max_total_chars: int = 900) -> list[ReferenceSnippet]:
    q = (query or "").strip()
    if not q:
        return []

    tokens = [t.strip() for t in q.replace("，", " ").replace("。", " ").split() if len(t.strip()) >= 2]
    tokens = tokens[:8]
    if not tokens:
        return []

    snippets: list[ReferenceSnippet] = []
    total = 0

    for path in _iter_reference_files():
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        lower = text.lower()
        hit_pos = None
        for token in tokens:
            pos = lower.find(token.lower())
            if pos != -1:
                hit_pos = pos
                break
        if hit_pos is None:
            continue

        start = max(0, hit_pos - window)
        end = min(len(text), hit_pos + window)
        excerpt = text[start:end].strip()
        if not excerpt:
            continue

        rel = str(path.relative_to(_repo_root())).replace("\\", "/")
        candidate = ReferenceSnippet(source=rel, text=excerpt)

        if total + len(candidate.text) > max_total_chars:
            break

        snippets.append(candidate)
        total += len(candidate.text)
        if len(snippets) >= max_snippets:
            break

    return snippets


def format_snippets_for_prompt(snippets: list[ReferenceSnippet]) -> str:
    if not snippets:
        return ""
    lines = ["【参考资料摘录（来自本地 references/，仅供参考，不要臆造引用）】"]
    for snip in snippets:
        lines.append(f"- 来源：{snip.source}")
        lines.append(snip.text.replace("\r\n", "\n").replace("\r", "\n").strip())
    return "\n".join(lines)

