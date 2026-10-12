# Architecture — AI CI/CD Failure Triage

```mermaid
flowchart LR
  J[Jenkins FAILURE] --> Log[console.log]
  J --> Test[junit.xml]
  J --> Diff[git.diff vs last green]
  Log --> P[Parsers]
  Test --> P
  Det[Deterministic correlate] --> LLM[Narrator mock/Claude]
  P --> Det
  Diff --> Det
  LLM --> Report[triage.md]
  Det --> Patch[suggested.patch]
  Report --> Human[Engineer reviews]
  Patch --> Human
  Human -->|apply + retry| J
  Det -.->|never retriggers| J
```

| Layer | Owns | Must not |
|---|---|---|
| Log / JUnit / diff parsers | What failed, where | Talk to the cluster |
| Correlate | Whether a cause exists | Invent a file that is not in the diff |
| LLM | Wording | Add causes, rebuild Jenkins |
| Human | Apply patch + retry the job | Skip the evidence |
