# Verity Security, Quality, and Remediation Report

**Assessment date:** 2026-08-24

**Report prepared:** 2026-08-25

**System:** Verity — autonomous AI/ML claim verification

**Audit baseline:** `696cdfd3989633e80e7fd0b98c6e21794cabcd1d`

## Executive summary

Verity accepts a public AI/ML claim, extracts a structured benchmark claim, executes the
associated repository in an isolated environment, makes at most three transparent repair
attempts, and produces an evidence-backed verdict. The audit reviewed that flow end to end:
source acquisition, parsing, sandbox execution, retry behavior, persistence, queueing, GitHub
reporting, the web interface, Docker isolation, CI, deployment configuration, and project
documentation.

The audit found and corrected a broad set of correctness and security defects. The most
important completed protections now prevent failed executions from being reported as measured
results, pin all retries to one repository revision, constrain model-provided regular
expressions, neutralize untrusted Markdown in GitHub reports, validate redirects and typed URLs,
distinguish infrastructure failure from claim failure, and make Firestore completion updates
atomic.

The audit also found a critical cloud trust-boundary flaw: the proposed Cloud Run sandbox could
execute untrusted repository code while holding a project identity capable of accessing
Firestore and while retaining outbound network access. That design is **not considered safe for
production**. Cloud deployment is therefore intentionally blocked by fail-closed configuration
and deployment guards until the sandbox receives no privileged credentials and the revised
boundary passes real isolation tests.

Current assessment:

| Area | Status |
|---|---|
| Local application and API | Ready for demonstration |
| Correctness and failure honesty | Strong and regression-tested |
| Local Docker isolation | Tested against a live Docker daemon |
| CI quality gates | Implemented |
| Public GitHub reporting artifacts | Available |
| Cloud architecture | Prototype; production deployment blocked |
| Arbitrary untrusted cloud execution | Not yet approved as safe |

## What was built

Verity is composed of four logical agents and a durable orchestration layer:

1. **Parser:** extracts a typed metric, claimed value, dataset, conditions, source location,
   repository, and evaluation instructions.
2. **Environment:** resolves the repository revision and runs setup and evaluation in a fresh
   sandbox.
3. **Debug:** analyzes a failed attempt, proposes a bounded repair, and retries without exceeding
   the three-repair limit.
4. **Reporter:** compares the claim with reproducible evidence and creates a structured verdict
   suitable for a GitHub Issue.

The supporting system provides FastAPI endpoints, a minimal browser UI, SQLite and Firestore
storage implementations, in-memory and Pub/Sub dispatch implementations, Docker and Cloud Run
Job sandbox backends, claim-memory deduplication, and structured execution traces.

## How the audit was performed

The assessment combined source review with adversarial and runtime testing. It did not rely only
on reading implementation code.

### Static and structural review

- Traced untrusted data from submitted URLs and model output into HTTP requests, shell commands,
  regular expressions, persisted records, and GitHub Markdown.
- Compared the declared architecture with the executable runtime and deployment scripts.
- Reviewed state transitions, retry limits, cache behavior, Firestore write ordering, queue
  failure handling, and reporter side effects.
- Examined Docker arguments, filesystem mounts, capabilities, networking, process limits, and
  repository revision handling.
- Checked configuration defaults, production guards, secret transport, service-account roles,
  and public endpoint authentication assumptions.
- Reconciled documentation claims with committed databases, GitHub artifacts, and executable
  commands.

### Dynamic verification

- Ran the complete Python test suite, including Docker-marked integration tests.
- Built and probed both the local runner image and the minimal cloud sandbox image.
- Executed eight standalone container-isolation probes against a live Docker daemon.
- Performed an exact-revision smoke test using a public Git commit and confirmed that the
  evaluated revision matched the recorded revision.
- Exercised local health, submission, cached-result, verdict, trace, and static-page endpoints.
- Ran Ruff linting and formatting checks, MyPy type analysis, dependency checks, YAML parsing,
  and documentation-link checks.
- Added focused regression tests for each safely repairable defect.

## Findings and remediation

### Critical and release-blocking findings

| Finding | Risk | How it was detected | Resolution or containment | Status |
|---|---|---|---|---|
| Untrusted cloud code inherited a Firestore-capable service identity and outbound networking | Repository code could query the metadata service, obtain credentials, and access project resources | Followed the Cloud Run Job service account and Firestore handoff through configuration and deployment code | Production settings and deployment now fail closed; a credential-free/no-role sandbox boundary is required | **Blocked safely; redesign required** |
| Pub/Sub authentication mixed OIDC with a secret in the callback URL, while the application did not validate the asserted OIDC identity | URL secrets can leak through logs and do not prove the caller identity | Compared Pub/Sub push configuration with the API authentication path | Remove URL secrets, verify issuer/audience/service-account identity, and separate the worker boundary | **Open before cloud deployment** |
| Deployment script could continue after failed native commands and could mishandle secret and service-account output | A partial deployment could be reported as successful or use malformed configuration | Reviewed PowerShell native-command error behavior and variable capture | A fail-closed guard prevents unsafe deployment; checked command wrappers are still required | **Contained** |
| Four executions could consume the entire Cloud Run pipeline timeout | Parser, repair, persistence, and reporting could be terminated without a reliable final state | Compared per-attempt and total timeout budgets | Add a global job deadline and smaller per-attempt budget | **Open before cloud deployment** |

### High-impact correctness and security findings

| Finding | Impact | Implemented remediation | Verification |
|---|---|---|---|
| Failed commands could retain a parsed numeric value | A failed run might look like a reproduced measurement | Clear `actual_value` unless the process succeeds and an assertion is valid | Regression tests cover failure output containing numbers |
| Timing metrics were compared without equivalent hardware/runtime conditions | A claim could be labeled contradicted using incomparable evidence | Added `conditions_not_comparable` for condition-sensitive metrics | Claim-quality and pipeline tests cover the new verdict |
| Model-provided regexes could backtrack catastrophically, use ambiguous captures, select an early value, or return NaN/Infinity | Denial of service or incorrect metric extraction | Run matching in a disposable process with a two-second limit; require one capture; select the final match; require a finite float | Dedicated matcher and model-validation tests |
| A rejected patch remained in the cumulative retry bundle | One bad repair could poison every later attempt | Persist only successfully applied repair state and its replacement command | Orchestrator recovery regression tests |
| Infrastructure/control-plane failures entered the model debug loop | Cloud outages could become dishonest claim verdicts and waste model calls | Classify infrastructure failure as job failure, not claim failure | Production-guardrail and pipeline tests |
| Typed URL validation was bypassed using unchecked model copies | Invalid or unsafe URL strings could cross trust boundaries | Reconstruct Pydantic models so validation runs on parser and publisher output | Response-schema and parser tests |
| Untrusted text was inserted into GitHub Issue Markdown | Mentions, malformed code fences, or presentation injection could affect published reports | Neutralize mentions, escape inline data, and generate collision-safe code fences | Issue-precision tests |
| README discovery followed redirects before guarded validation | Redirects could bypass the intended URL safety loop | Disable automatic redirect following and validate each destination before requesting it | URL/parser-source tests |
| Models accepted non-finite numeric values | NaN/Infinity can break ordering, serialization, and comparisons | Require finite claimed and observed scalar values | Model and response-schema tests |
| Retries could execute a moving branch or unreliable SHA clone | Evidence from multiple revisions could be combined into one verdict | Resolve and persist the first full commit; fetch it detached; require every retry to use it; fail on drift | Revision-integrity and Docker tests |
| A queue publication failure marked the job terminally failed | A transient broker problem could destroy recoverable work | Keep the job queued and republish the same job ID on repeat submission | Orchestrator recovery tests |
| Firestore completed the job and updated claim memory in separate writes | Readers could observe a completed job with no dedup pointer | Commit both updates in one Firestore transaction | Firestore store tests |
| Cached terminal responses still started polling and UI failures left inconsistent state | Needless traffic and misleading browser state | Centralized interval start/stop behavior and terminal-state handling | Frontend contract tests |
| Inspecting the shipped SQLite fixture could create WAL sidecars | A read operation could mutate protected evidence | Open the fixture in immutable read-only mode | Demo-cache tests verify no sidecars |

## Security controls now in place

### Execution isolation

The local runner uses a fresh container per attempt with dropped Linux capabilities,
`no-new-privileges`, a read-only root filesystem, constrained writable temporary storage,
resource limits, bounded execution time, and no evaluation-phase network. Exact repository
revision pinning prevents branch movement from changing evidence between attempts.

These controls materially reduce risk, but Docker isolation is not a proof that every arbitrary
repository is harmless. The host must keep Docker and its kernel patched, and the cloud runtime
must be evaluated against its own platform constraints.

### Input and output handling

- URLs and redirects are validated at trust boundaries.
- Claimed and measured numbers must be finite.
- Model-produced metric patterns execute with strict shape and time limits.
- Failed processes cannot publish an observed metric.
- GitHub report text treats source and model content as untrusted.
- Revision identity is captured once and enforced across all retries.

### State and failure integrity

- The debug loop remains capped at three repair attempts.
- Control-plane failure does not become a factual verdict about a claim.
- Firestore completion and dedup publication are atomic.
- Queue publication failure preserves recoverable work.
- The read-only demonstration database remains immutable.
- Production configuration rejects the known-unsafe cloud topology.

## Validation evidence

| Check | Result |
|---|---|
| Ordinary suite | 212 collected; 9 Docker tests deselected |
| Docker-inclusive suite | **221 passed** |
| Standalone isolation probes | **8 of 8 passed** |
| Ruff lint and format checks | Passed |
| MyPy analysis | Passed across application, scripts, and core package |
| Dependency consistency | `pip check` passed |
| Exact revision smoke | Evaluated and recorded `octocat/Hello-World@7fd1a60b01f91b314f59955a4e4d4e80d8edf11d` |
| Local HTTP smoke | Health, pages, five submissions, verdicts, and traces returned successfully |
| Container cleanup | No audit containers remained after testing |

The full evidence inventory and historical caveats are recorded in
[AUDIT-2026-08-24.md](AUDIT-2026-08-24.md).

## Remaining known risks

The following limitations are documented rather than hidden:

- **Cloud identity boundary:** a no-project-role service account sharply reduces credential
  impact, but it is not sufficient by itself to declare arbitrary untrusted execution safe. The
  deployment must also prove that no inherited organization/folder permissions, invoker
  capabilities, secrets, sensitive environment data, or privileged result channel are reachable.
- **Network exposure:** repository acquisition and dependency installation can execute build
  hooks with network access. Evaluation is offline locally, but cloud prepare/evaluate isolation
  and private/link-local/metadata behavior require platform-specific testing.
- **DNS rebinding:** DNS is checked before the HTTP client resolves independently, leaving a
  time-of-check/time-of-use gap.
- **Evidence provenance:** repository commits are pinned, but datasets, checkpoints, dependency
  graphs, hardware, precision modes, and source bytes are not yet cryptographically bound to a
  verdict.
- **Recovery:** there is no claimed-job lease, heartbeat, or recovery sweep; an interrupted worker
  can strand a job.
- **Delivery durability:** republishing repairs common queue failure, but a transactional outbox
  is still needed for robust automatic recovery.
- **Artifact size:** Firestore trace and job payloads have no offload strategy for the 1 MiB
  document limit.
- **Mutable runner image:** repository revisions are immutable, but the sandbox runner is not yet
  pinned by image digest for the entire job.
- **Model budget:** internal transport retries can multiply the visible repair attempts; there is
  no global model-call or token budget.
- **Historical evidence:** previously filed issues remain historical artifacts and were not
  silently rewritten after fixes.

## Recommended next steps

### Priority 0 — prove the cloud trust boundary

1. Create a sandbox service account with no project, folder, or organization roles.
2. Ensure no GitHub, Firestore, Vertex, Pub/Sub, Secret Manager, deployment, or application
   credential reaches sandbox environment variables, files, arguments, volumes, or logs.
3. Define a minimal trusted request/result exchange so the sandbox never writes directly to
   Firestore.
4. Run an adversarial staging repository that steals its metadata token and attempts Firestore,
   Secret Manager, Pub/Sub, Cloud Run, Artifact Registry, and other relevant APIs. Every privileged
   operation must be denied.
5. Test private, link-local, metadata, and public egress behavior during both preparation and
   evaluation.
6. Remove the fail-closed deployment guard only after this evidence is reviewed and accepted.

### Priority 1 — reliability and provenance

1. Add fenced leases, heartbeats, a recovery sweep, and a transactional delivery outbox.
2. Bind source bytes, dataset/checkpoint identity, dependency lock, runner digest, hardware, and
   evaluation protocol to the verdict evidence.
3. Offload large logs and artifacts to bounded object storage with hashes in Firestore.
4. Enforce one global job deadline and explicit model-call/token budgets.

### Priority 2 — deployment proof

1. Configure the credit-backed Google Cloud project and billing alerts.
2. Deploy first to staging with least-privilege identities and verified Pub/Sub OIDC.
3. Run the malicious isolation suite before submitting real claims.
4. Run the full catalogue into a fresh database, including the historical Whisper failure case.
5. Submit one previously unseen source through the complete cloud path and capture the Cloud Run
   URL, Firestore state, Pub/Sub delivery, logs/traces, revision evidence, and filed GitHub Issue.

## Reproducing the quality gates

From the repository root in the locked Python 3.11 environment:

```powershell
powershell -File scripts/test.ps1
powershell -File scripts/test.ps1 -Docker
python -m pip check
```

Build and probe the runner directly when validating container behavior:

```powershell
docker build -f Dockerfile.runner -t verity-sandbox-runner:1 .
python -m pytest -q -m docker
```

Do not place API keys, GitHub tokens, service-account keys, or other credentials in the
repository, issue bodies, logs, or chat. Use local authentication and secret-management controls.

## Conclusion

The audit materially improved Verity's correctness, evidence integrity, and local security. Its
local MVP is credible because failures remain failures, retries are reproducible, high-risk input
paths are constrained, and the behavior is backed by executable tests. The project is not being
presented as production-safe cloud infrastructure: the unsafe cloud path is blocked, its residual
risks are explicit, and deployment has concrete security acceptance criteria.

This separation between verified capability and unfinished infrastructure is intentional. It
protects users, preserves the honesty of the verdicts, and gives the project a defensible path
from a strong local demonstration to a secure cloud deployment.
