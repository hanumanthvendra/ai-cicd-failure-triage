"""Parse a unified diff into per-file hunks."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class FileDiff:
    path: str
    added: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    raw: str = ""


def parse_diff(text: str) -> list[FileDiff]:
    files: list[FileDiff] = []
    current: FileDiff | None = None
    chunks: list[str] = []
    for line in text.splitlines(keepends=True):
        m = re.match(r"^diff --git a/(.+) b/(.+)$", line.rstrip("\n"))
        plus = re.match(r"^\+\+\+ b/(.+)$", line.rstrip("\n"))
        if m:
            if current is not None:
                current.raw = "".join(chunks)
                files.append(current)
            current = FileDiff(path=m.group(2))
            chunks = [line]
            continue
        if plus and current is None:
            current = FileDiff(path=plus.group(1))
            chunks = [line]
            continue
        if current is None:
            continue
        chunks.append(line)
        if line.startswith("+") and not line.startswith("+++"):
            current.added.append(line[1:].rstrip("\n"))
        elif line.startswith("-") and not line.startswith("---"):
            current.removed.append(line[1:].rstrip("\n"))
    if current is not None:
        current.raw = "".join(chunks)
        files.append(current)
    return files


def read_diff(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""
