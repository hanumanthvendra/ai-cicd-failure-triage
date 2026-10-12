"""Parse a Jenkins console log into error spans with line numbers."""
from __future__ import annotations

import re
from dataclasses import dataclass

ERROR_MARKERS = (
    "ERROR",
    "error:",
    "failed to",
    "FAILED",
    "not found",
    "kubeconform",
    "exit code 1",
    "Copy failed",
    "COPY failed",
)


@dataclass(frozen=True)
class LogHit:
    line_no: int
    text: str
    stage: str


def parse_console(text: str) -> list[LogHit]:
    hits: list[LogHit] = []
    stage = "unknown"
    for i, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        stage_m = re.search(r"\{ \(([^)]+)\) \}", line) or re.search(
            r"Stage ['\"]([^'\"]+)", line
        )
        if stage_m:
            stage = stage_m.group(1)
        low = line.lower()
        if any(m.lower() in low for m in ERROR_MARKERS) and line.strip():
            hits.append(LogHit(line_no=i, text=line, stage=stage))
    return hits


def snippet(text: str, line_no: int, radius: int = 2) -> str:
    lines = text.splitlines()
    start = max(0, line_no - 1 - radius)
    end = min(len(lines), line_no + radius)
    out = []
    for i in range(start, end):
        mark = ">" if i + 1 == line_no else " "
        out.append(f"{mark} {i + 1:4d} | {lines[i]}")
    return "\n".join(out)
