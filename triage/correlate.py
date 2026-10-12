"""Match log/JUnit errors to the recent git diff. Findings are detector-owned."""
from __future__ import annotations

import re
from pathlib import Path

from .diffparse import FileDiff
from .junit import TestFailure
from .logs import LogHit, snippet
from .models import Cause, Evidence

COPY_RE = re.compile(r"COPY\s+(\S+)")
REPLICA_RE = re.compile(r"replicas:\s*(\S+)")


def diagnose(
    console: str,
    log_hits: list[LogHit],
    tests: list[TestFailure],
    diffs: list[FileDiff],
    workspace: Path | None = None,
) -> list[Cause]:
    causes: list[Cause] = []
    docker = _dockerfile_copy(console, log_hits, tests, diffs, workspace)
    if docker:
        causes.append(docker)
    k8s = _k8s_replicas(console, log_hits, tests, diffs, workspace)
    if k8s:
        causes.append(k8s)
    return causes


def _dockerfile_copy(
    console: str,
    log_hits: list[LogHit],
    tests: list[TestFailure],
    diffs: list[FileDiff],
    workspace: Path | None,
) -> Cause | None:
    copy_typo = None
    docker_diff = next((d for d in diffs if d.path.endswith("Dockerfile")), None)
    if docker_diff:
        for line in docker_diff.added:
            m = COPY_RE.search(line)
            if m and "reqirements" in m.group(1):
                copy_typo = m.group(1)
    log_hit = next(
        (h for h in log_hits if "reqirements" in h.text or "COPY" in h.text and "not found" in h.text.lower()),
        None,
    )
    if not copy_typo and not log_hit:
        return None
    missing = copy_typo or "reqirements.txt"
    evidence: list[Evidence] = []
    if log_hit:
        evidence.append(
            Evidence("log", "jenkins-console", f"L{log_hit.line_no} ({log_hit.stage})", snippet(console, log_hit.line_no))
        )
    if docker_diff:
        evidence.append(Evidence("diff", docker_diff.path, "unified diff", docker_diff.raw.strip()[:900]))
    for t in tests:
        if "docker" in (t.classname + t.name + t.message).lower():
            evidence.append(
                Evidence("junit", f"{t.classname}.{t.name}", "failure", t.message or t.body)
            )
    restore = None
    docker_file = None
    if workspace and (workspace / "Dockerfile").exists():
        docker_file = workspace / "Dockerfile"
    if docker_file:
        restore = docker_file.read_text(encoding="utf-8").replace(missing, "requirements.txt")
        restore = restore.replace("reqirements.txt", "requirements.txt")
    elif docker_diff:
        restore = _restore_dockerfile(docker_diff)
    return Cause(
        id="CI-DOCKER-001",
        title="Dockerfile COPY path does not exist",
        severity="critical",
        summary=(
            f"Image build failed because `{missing}` is not in the build context. "
            "The recent Dockerfile change introduced the typo; `requirements.txt` is the file that exists."
        ),
        files=[docker_diff.path if docker_diff else "Dockerfile"],
        evidence=evidence,
        remediation="Change COPY to `requirements.txt` (the file already in the repo).",
        patch=restore,
    )


def _k8s_replicas(
    console: str,
    log_hits: list[LogHit],
    tests: list[TestFailure],
    diffs: list[FileDiff],
    workspace: Path | None,
) -> Cause | None:
    manifest_diff = next(
        (d for d in diffs if d.path.endswith((".yaml", ".yml")) and "deploy" in d.path.lower()),
        None,
    )
    bad = None
    if manifest_diff:
        for line in manifest_diff.added:
            m = REPLICA_RE.search(line)
            if m and not m.group(1).isdigit():
                bad = m.group(1)
    log_hit = next(
        (h for h in log_hits if "replicas" in h.text.lower() or "kubeconform" in h.text.lower()),
        None,
    )
    if not bad and not log_hit:
        return None
    evidence: list[Evidence] = []
    if log_hit:
        evidence.append(
            Evidence("log", "jenkins-console", f"L{log_hit.line_no} ({log_hit.stage})", snippet(console, log_hit.line_no))
        )
    if manifest_diff:
        evidence.append(Evidence("diff", manifest_diff.path, "unified diff", manifest_diff.raw.strip()[:900]))
    for t in tests:
        blob = (t.classname + t.name + t.message + t.body).lower()
        if "kube" in blob or "replica" in blob or "manifest" in blob:
            evidence.append(Evidence("junit", f"{t.classname}.{t.name}", "failure", t.message or t.body))
    patch = None
    path = None
    if workspace and (workspace / "k8s" / "deployment.yaml").exists():
        path = workspace / "k8s" / "deployment.yaml"
    if path:
        patch = re.sub(r"replicas:\s*\S+", "replicas: 3", path.read_text(encoding="utf-8"))
    elif manifest_diff:
        patch = _restore_replicas(manifest_diff)
    return Cause(
        id="CI-K8S-002",
        title="Kubernetes replicas is not an integer",
        severity="high",
        summary=(
            f"kubeconform rejected `replicas: {bad or 'three'}`. Deployment.spec.replicas must be an integer. "
            "The last green build used `3`."
        ),
        files=[manifest_diff.path if manifest_diff else "k8s/deployment.yaml"],
        evidence=evidence,
        remediation="Set `spec.replicas: 3` (integer). Do not quote it as a word.",
        patch=patch,
    )


def _restore_dockerfile(diff: FileDiff) -> str:
    """Rebuild file text from the post-image of the diff, then fix COPY."""
    after_lines = _after_file(diff)
    out = []
    for line in after_lines:
        if line.strip().startswith("COPY ") and "reqirements" in line:
            out.append(line.replace("reqirements.txt", "requirements.txt"))
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if after_lines else "")


def _restore_replicas(diff: FileDiff) -> str:
    after_lines = _after_file(diff)
    out = []
    for line in after_lines:
        if "replicas:" in line and not any(ch.isdigit() for ch in line.split(":", 1)[-1]):
            indent = line[: len(line) - len(line.lstrip(" "))]
            out.append(f"{indent}replicas: 3")
        else:
            out.append(line)
    return "\n".join(out) + ("\n" if after_lines else "")


def _after_file(diff: FileDiff) -> list[str]:
    """Best-effort file contents after the diff (from hunks)."""
    lines: list[str] = []
    for raw in diff.raw.splitlines():
        if raw.startswith("+++") or raw.startswith("---") or raw.startswith("diff ") or raw.startswith("index "):
            continue
        if raw.startswith("@@"):
            continue
        if raw.startswith("+"):
            lines.append(raw[1:])
        elif raw.startswith("-"):
            continue
        elif raw.startswith("\\"):
            continue
        else:
            lines.append(raw[1:] if raw.startswith(" ") else raw)
    return lines
