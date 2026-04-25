"""Split markdown text into byte-bounded, semantically meaningful chunks."""

from __future__ import annotations

import re

_HEADER_RE = re.compile(r"^#{1,6}\s")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?。！？])\s+|\n+")


def byte_len(s: str) -> int:
    return len(s.encode("utf-8"))


def _split_into_blocks(text: str) -> list[str]:
    """Break markdown into semantic blocks: headers, paragraphs, code fences, lists."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.split("\n")

    blocks: list[str] = []
    current: list[str] = []
    in_code = False

    def flush() -> None:
        if current:
            joined = "\n".join(current).strip()
            if joined:
                blocks.append(joined)
            current.clear()

    for line in lines:
        stripped = line.lstrip()

        if stripped.startswith("```"):
            current.append(line)
            in_code = not in_code
            if not in_code:
                flush()
            continue

        if in_code:
            current.append(line)
            continue

        if _HEADER_RE.match(line):
            flush()
            blocks.append(line.rstrip())
        elif line.strip() == "":
            flush()
        else:
            current.append(line)

    flush()
    return blocks


def _hard_split(s: str, max_bytes: int) -> list[str]:
    """Last-resort byte-safe split by characters."""
    parts: list[str] = []
    cur = ""
    for ch in s:
        if byte_len(cur) + byte_len(ch) > max_bytes:
            if cur:
                parts.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        parts.append(cur)
    return parts


def _split_long_block(block: str, max_bytes: int) -> list[str]:
    """Split a single oversized block by sentence/line, then characters if needed."""
    units = [u for u in _SENTENCE_SPLIT.split(block) if u.strip()]
    if not units:
        return _hard_split(block, max_bytes)

    parts: list[str] = []
    cur: list[str] = []
    cur_bytes = 0

    for unit in units:
        ub = byte_len(unit)
        if ub > max_bytes:
            if cur:
                parts.append(" ".join(cur))
                cur = []
                cur_bytes = 0
            parts.extend(_hard_split(unit, max_bytes))
            continue

        sep = 1 if cur else 0
        if cur_bytes + sep + ub <= max_bytes:
            cur.append(unit)
            cur_bytes += sep + ub
        else:
            parts.append(" ".join(cur))
            cur = [unit]
            cur_bytes = ub

    if cur:
        parts.append(" ".join(cur))
    return parts


def chunk_markdown(text: str, max_bytes: int = 1000) -> list[str]:
    """Split markdown into chunks each <= max_bytes (utf-8), preserving block structure."""
    if not text or not text.strip():
        return []
    if max_bytes <= 0:
        raise ValueError("max_bytes must be positive")

    blocks = _split_into_blocks(text)

    safe: list[str] = []
    for b in blocks:
        if byte_len(b) <= max_bytes:
            safe.append(b)
        else:
            safe.extend(_split_long_block(b, max_bytes))

    chunks: list[str] = []
    cur = ""
    for b in safe:
        if not cur:
            cur = b
            continue
        candidate = cur + "\n\n" + b
        if byte_len(candidate) <= max_bytes:
            cur = candidate
        else:
            chunks.append(cur)
            cur = b
    if cur:
        chunks.append(cur)

    return chunks
