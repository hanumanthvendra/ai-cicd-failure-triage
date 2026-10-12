from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Severity = Literal["critical", "high", "medium", "low"]
Kind = Literal["log", "junit", "diff", "file"]


@dataclass(frozen=True)
class Evidence:
    kind: Kind
    source: str
    locator: str
    snippet: str


@dataclass
class Cause:
    id: str
    title: str
    severity: Severity
    summary: str
    files: list[str]
    evidence: list[Evidence]
    remediation: str
    patch: str | None = None


@dataclass
class Diagnosis:
    failed_job: str
    likely_causes: list[Cause]
    suggested_patch: str
    narrative: str
    generator: str
    sources: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
