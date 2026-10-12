# AI CI/CD Failure Triage Assistant

> **The problem:** a Jenkins job goes red and an engineer scrolls a 4,000-line console, a JUnit file, and a PR diff hoping they line up. **The fix:** a **read-only** assistant that reads those three artifacts, **points at the log lines**, names the likely cause, and **drafts a patch**. A human applies it and retriggers Jenkins. The assistant never changes git and never rebuilds.

Complements [AI GitOps Release Guardian](https://github.com/hanumanthvendra/ai-gitops-release-guardian): one reviews changes **before** merge; this one diagnoses failures **during CI**.

Runs on a laptop. No Jenkins controller required for the demo (fixtures are checked in). `ci/Jenkinsfile` is the shape you would run in a real platform.

---

## What it does

```
Jenkins FAILURE
  ├── console.log     (Build image · Validate manifests)
  ├── junit.xml       (test_image_builds · test_kubeconform_checkout)
  └── git.diff        (PR vs last green)
        │
        ▼
  Parsers → correlate to the change → evidence locators
        │
        ├── LLM narrator (mock | Claude) — explains, does not invent
        └── suggested patch — human apply only
        │
        ▼
  Engineer applies patch → retriggers Jenkins
```

| Piece | Why it matters | How it works here |
|---|---|---|
| **Log parser** | The smoking gun is usually one line | Jenkins console → stage + line number |
| **JUnit parser** | Tests name the check that failed | `ci.docker.test_image_builds`, `ci.k8s.test_kubeconform_checkout` |
| **Diff correlate** | Trace the error to *this* PR | Dockerfile `COPY reqirements.txt` · `replicas: three` |
| **Suggested patch** | Faster than “please look at the log” | Restore `requirements.txt` and `replicas: 3` |
| **Read-only** | Safer than an agent that rebuilds prod CI | No git write, no Jenkins retrigger, no deploy |

---

## Run it

```bash
make test            # parsers + patch + read-only contract
make demo            # failed job → diagnose → patch a copy → local re-check PASS
```

Optional narration:

```bash
export ANTHROPIC_API_KEY=sk-...
make demo            # same causes, Claude writes the narrative
```

### What `make demo` proves

Jenkins `checkout/PR-47` failed because the PR did two things:

1. **Dockerfile** — `COPY requirements.txt` became `COPY reqirements.txt` (file not in the build context)
2. **Kubernetes** — `replicas: 3` became `replicas: three` (kubeconform: expected integer)

The assistant **cites console L# + JUnit + the diff**, drafts a patch. Applying it to a copy and re-running the local stand-in for those two stages goes **PASS**. Jenkins is still the thing that would rebuild — a human clicks retry.

---

## Layout

```
demo/failed/              # the workspace that broke CI
demo/green/               # last green (for contrast)
demo/jenkins/console.log  # captured Jenkins console
demo/jenkins/junit.xml
demo/jenkins/git.diff
ci/Jenkinsfile            # docker build + kubeconform + triage (advisory)
triage/                   # parsers + correlate + patch (never applies)
```

---

## Portfolio title

**AI CI/CD Failure Triage: Evidence-Based Jenkins Diagnosis from Logs, Tests, and Diffs**
