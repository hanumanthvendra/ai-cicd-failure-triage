from __future__ import annotations

from .models import Diagnosis


def to_markdown(d: Diagnosis) -> str:
    lines = [
        "# CI/CD Failure Triage",
        "",
        f"**Job:** `{d.failed_job}` · **Narrator:** `{d.generator}`",
        "",
        "> Read-only diagnosis. This assistant does not patch git, retrigger Jenkins, or deploy.",
        "",
        "## Likely causes",
        "",
    ]
    if not d.likely_causes:
        lines.append("No Dockerfile COPY or Kubernetes replicas failure matched.")
    for c in d.likely_causes:
        lines += [
            f"### {c.id} — {c.title}",
            "",
            f"`{c.severity.upper()}` · files: {', '.join(f'`{p}`' for p in c.files)}",
            "",
            c.summary,
            "",
            "**Evidence**",
            "",
        ]
        for e in c.evidence:
            lines.append(f"- `{e.kind}` `{e.source}` `{e.locator}`")
            lines.append("")
            lines.append("```")
            lines.append(e.snippet.rstrip())
            lines.append("```")
            lines.append("")
        lines += ["**Remediation**", "", c.remediation, ""]
    lines += ["## Narrative", "", d.narrative, ""]
    if d.suggested_patch.strip():
        lines += ["## Suggested patch (human apply)", "", "```diff", d.suggested_patch.rstrip(), "```", ""]
    return "\n".join(lines)
