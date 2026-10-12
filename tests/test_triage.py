from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from triage.cli import main
from triage.engine import triage_bundle
from triage.validate import check_workspace

DEMO = ROOT / "demo"
CONSOLE = DEMO / "jenkins" / "console.log"
JUNIT = DEMO / "jenkins" / "junit.xml"
DIFF = DEMO / "jenkins" / "git.diff"
FAILED = DEMO / "failed"
GREEN = DEMO / "green"


class TestDemoFailure(unittest.TestCase):
    def setUp(self) -> None:
        self.d = triage_bundle(CONSOLE, JUNIT, DIFF, workspace=FAILED)
        self.by_id = {c.id: c for c in self.d.likely_causes}

    def test_flags_dockerfile_and_k8s(self) -> None:
        self.assertIn("CI-DOCKER-001", self.by_id)
        self.assertIn("CI-K8S-002", self.by_id)
        self.assertIn("reqirements", self.by_id["CI-DOCKER-001"].summary)
        self.assertIn("three", self.by_id["CI-K8S-002"].summary)

    def test_evidence_from_log_junit_and_diff(self) -> None:
        for cid in ("CI-DOCKER-001", "CI-K8S-002"):
            kinds = {e.kind for e in self.by_id[cid].evidence}
            self.assertTrue({"log", "diff"} <= kinds, msg=kinds)
            self.assertIn("junit", kinds)

    def test_failed_workspace_would_fail_ci(self) -> None:
        errs = check_workspace(FAILED)
        self.assertTrue(any("COPY" in e for e in errs))
        self.assertTrue(any("replicas" in e for e in errs))

    def test_green_workspace_would_pass_ci(self) -> None:
        self.assertEqual(check_workspace(GREEN), [])

    def test_suggested_patch_clears_ci(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dest = Path(tmp)
            self.assertEqual(main(["apply-suggested", "--out", str(dest)]), 0)
            self.assertEqual(check_workspace(dest), [])

    def test_never_rebuilds_or_deploys(self) -> None:
        forbidden = ("subprocess", "docker.api", "jenkinsapi")
        for path in (ROOT / "triage").rglob("*.py"):
            text = path.read_text(encoding="utf-8").lower()
            for phrase in forbidden:
                self.assertNotIn(phrase, text, msg=f"{path} mentions {phrase}")


if __name__ == "__main__":
    unittest.main()
