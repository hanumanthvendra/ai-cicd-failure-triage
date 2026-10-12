"""Local stand-ins for Jenkins stages. Used to confirm a human-applied patch."""
from __future__ import annotations

import re
from pathlib import Path


def check_workspace(root: Path) -> list[str]:
    """Return remaining errors. Empty list == the pipeline would go green."""
    errors: list[str] = []
    docker = root / "Dockerfile"
    if docker.exists():
        text = docker.read_text(encoding="utf-8")
        for m in re.finditer(r"^COPY\s+(\S+)", text, re.M):
            src = m.group(1)
            if src.startswith("--"):
                continue
            if not (root / src).exists():
                errors.append(f"docker: COPY {src} — file not in build context")
    manifest = root / "k8s" / "deployment.yaml"
    if manifest.exists():
        text = manifest.read_text(encoding="utf-8")
        m = re.search(r"replicas:\s*(\S+)", text)
        if m:
            val = m.group(1).strip().strip('"').strip("'")
            if not val.isdigit():
                errors.append(f"kubeconform: spec.replicas expected integer, got {val}")
    return errors
