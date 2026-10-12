"""Assemble one suggested unified diff. Never applied to git or Jenkins."""
from __future__ import annotations

import difflib
from pathlib import Path

from .diffparse import FileDiff
from .models import Cause


def suggested_unified_diff(
    diffs: list[FileDiff],
    causes: list[Cause],
    workspace: Path | None = None,
) -> str:
    by_path = {d.path: d for d in diffs}
    parts: list[str] = []
    seen: set[str] = set()
    for cause in causes:
        if not cause.patch:
            continue
        for path in cause.files:
            if path in seen:
                continue
            seen.add(path)
            on_disk = workspace / path if workspace else None
            if on_disk and on_disk.exists():
                current = on_disk.read_text(encoding="utf-8")
            else:
                current = _after_text(by_path.get(path))
            if current == cause.patch:
                continue
            parts.append(
                "".join(
                    difflib.unified_diff(
                        current.splitlines(keepends=True),
                        cause.patch.splitlines(keepends=True),
                        fromfile=f"a/{path}",
                        tofile=f"b/{path}",
                    )
                )
            )
    return "".join(parts)


def _after_text(diff: FileDiff | None) -> str:
    if diff is None:
        return ""
    from .correlate import _after_file

    lines = _after_file(diff)
    return "\n".join(lines) + ("\n" if lines else "")
