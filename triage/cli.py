from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

from .engine import triage_bundle
from .patch import suggested_unified_diff
from .report import to_markdown
from .validate import check_workspace

ROOT = Path(__file__).resolve().parents[1]
DEMO = ROOT / "demo"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="triage", description="Diagnose a Jenkins failure (read-only)")
    sub = p.add_subparsers(dest="cmd", required=True)

    t = sub.add_parser("diagnose", help="Read logs + tests + diff; write a report and patch")
    t.add_argument("--console", type=Path, default=DEMO / "jenkins" / "console.log")
    t.add_argument("--junit", type=Path, default=DEMO / "jenkins" / "junit.xml")
    t.add_argument("--diff", type=Path, default=DEMO / "jenkins" / "git.diff")
    t.add_argument("--job", default="checkout/PR-47")
    t.add_argument("--workspace", type=Path, default=DEMO / "failed")
    t.add_argument("--out", type=Path, default=ROOT / "out")
    t.add_argument("--json", action="store_true")

    s = sub.add_parser("apply-suggested", help="Write patched files under --out (not git, not Jenkins)")
    s.add_argument("--console", type=Path, default=DEMO / "jenkins" / "console.log")
    s.add_argument("--junit", type=Path, default=DEMO / "jenkins" / "junit.xml")
    s.add_argument("--diff", type=Path, default=DEMO / "jenkins" / "git.diff")
    s.add_argument("--workspace", type=Path, default=DEMO / "failed")
    s.add_argument("--out", type=Path, default=ROOT / "out" / "patched")

    v = sub.add_parser("check", help="Local Jenkins-stage stand-in (docker COPY + kubeconform replicas)")
    v.add_argument("--workspace", type=Path, required=True)

    args = p.parse_args(argv)
    if args.cmd == "diagnose":
        return _diagnose(args)
    if args.cmd == "apply-suggested":
        return _apply(args)
    if args.cmd == "check":
        return _check(args)
    return 2


def _diagnose(args) -> int:
    junit = args.junit if args.junit.exists() else None
    d = triage_bundle(args.console, junit, args.diff, args.job, args.workspace)
    args.out.mkdir(parents=True, exist_ok=True)
    md = to_markdown(d)
    (args.out / "triage.md").write_text(md, encoding="utf-8")
    (args.out / "triage.json").write_text(json.dumps(d.to_dict(), indent=2), encoding="utf-8")
    (args.out / "suggested.patch").write_text(d.suggested_patch, encoding="utf-8")
    print(json.dumps(d.to_dict(), indent=2) if args.json else md)
    return 0 if d.likely_causes else 1


def _apply(args) -> int:
    junit = args.junit if args.junit.exists() else None
    d = triage_bundle(args.console, junit, args.diff, workspace=args.workspace)
    if args.out.exists():
        shutil.rmtree(args.out)
    shutil.copytree(args.workspace, args.out, ignore=shutil.ignore_patterns(".git"))
    from .diffparse import parse_diff

    diffs = parse_diff(args.diff.read_text(encoding="utf-8"))
    patch_text = suggested_unified_diff(diffs, d.likely_causes, args.workspace)
    # Overlay cause.patch files
    for cause in d.likely_causes:
        if not cause.patch:
            continue
        for rel in cause.files:
            dest = args.out / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(cause.patch, encoding="utf-8")
    print(f"Wrote patched copy under {args.out} ({len(d.likely_causes)} files). Not a Jenkins rerun.")
    _ = patch_text
    return 0


def _check(args) -> int:
    errors = check_workspace(args.workspace)
    if errors:
        print("FAIL — remaining CI errors:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("PASS — docker COPY paths exist; kubeconform replicas is an integer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
