from __future__ import annotations

from pathlib import Path

from .correlate import diagnose
from .diffparse import parse_diff, read_diff
from .explain import backend, narrate
from .junit import parse_junit
from .logs import parse_console
from .models import Diagnosis
from .patch import suggested_unified_diff


def triage_bundle(
    console_path: Path,
    junit_path: Path | None,
    diff_path: Path,
    job: str = "checkout/PR-47",
    workspace: Path | None = None,
) -> Diagnosis:
    console = console_path.read_text(encoding="utf-8")
    diff_text = read_diff(diff_path)
    diffs = parse_diff(diff_text)
    tests = parse_junit(junit_path) if junit_path else []
    hits = parse_console(console)
    causes = diagnose(console, hits, tests, diffs, workspace)
    diagnosis = Diagnosis(
        failed_job=job,
        likely_causes=causes,
        suggested_patch=suggested_unified_diff(diffs, causes, workspace),
        narrative="",
        generator=backend(),
        sources={
            "console": str(console_path),
            "junit": str(junit_path) if junit_path else "",
            "diff": str(diff_path),
        },
    )
    diagnosis.narrative = narrate(diagnosis)
    return diagnosis
