"""Parse JUnit XML without extra dependencies."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TestFailure:
    classname: str
    name: str
    message: str
    body: str


def parse_junit(path: Path) -> list[TestFailure]:
    if not path.exists():
        return []
    root = ET.parse(path).getroot()
    failures: list[TestFailure] = []
    for case in root.iter("testcase"):
        fail = case.find("failure")
        if fail is None:
            fail = case.find("error")
        if fail is None:
            continue
        failures.append(
            TestFailure(
                classname=case.get("classname") or "",
                name=case.get("name") or "",
                message=fail.get("message") or "",
                body=(fail.text or "").strip(),
            )
        )
    return failures
