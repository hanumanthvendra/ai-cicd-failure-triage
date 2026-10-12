"""Pluggable narration. Causes stay detector-owned; the LLM only writes prose."""
from __future__ import annotations

import json
import os

from .models import Diagnosis

SYSTEM = (
    "You are a staff CI engineer triaging a Jenkins failure. Explain ONLY the "
    "causes JSON. Cite log line numbers, JUnit names, and diff files. "
    "Do not invent causes. Do not retrigger CI or deploy. "
    "A human applies the patch and reruns Jenkins."
)


def backend() -> str:
    return "claude" if os.environ.get("ANTHROPIC_API_KEY") else "mock"


def narrate(diagnosis: Diagnosis) -> str:
    if backend() == "claude":
        return _claude(diagnosis)
    return _mock(diagnosis)


def _mock(diagnosis: Diagnosis) -> str:
    lines = [
        f"Jenkins job **{diagnosis.failed_job}** failed. Likely causes:",
        "",
    ]
    for c in diagnosis.likely_causes:
        cites = ", ".join(f"{e.source} {e.locator}" for e in c.evidence[:3])
        lines.append(f"- **{c.id}** ({c.severity}): {c.summary}")
        lines.append(f"  Evidence: {cites}")
        lines.append(f"  Fix: {c.remediation}")
    lines += [
        "",
        "A suggested patch is attached for a human to apply. This assistant does "
        "not change git, retrigger Jenkins, or deploy.",
        "",
        "(mock narrator — set ANTHROPIC_API_KEY to phrase this with Claude. "
        "The causes, evidence, and patch are identical either way.)",
    ]
    return "\n".join(lines)


def _claude(diagnosis: Diagnosis) -> str:
    import anthropic

    payload = {
        "failed_job": diagnosis.failed_job,
        "causes": [
            {
                "id": c.id,
                "title": c.title,
                "severity": c.severity,
                "summary": c.summary,
                "files": c.files,
                "evidence": [
                    {"kind": e.kind, "source": e.source, "locator": e.locator, "snippet": e.snippet[:400]}
                    for e in c.evidence
                ],
                "remediation": c.remediation,
            }
            for c in diagnosis.likely_causes
        ],
    }
    try:
        resp = anthropic.Anthropic().messages.create(
            model=os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            max_tokens=900,
            system=SYSTEM,
            messages=[{"role": "user", "content": json.dumps(payload, indent=2)}],
        )
        return next((b.text for b in resp.content if b.type == "text"), "").strip()
    except Exception as exc:
        return _mock(diagnosis) + f"\n\n[LLM error: {exc}. Causes and patch are unchanged.]"
