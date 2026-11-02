# Phase 2 — First usable coding slice

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

<a id="p2-1"></a>
## P2.1 — First-slice configuration and CLI contract

- **Depends on:** [P1.7](01-integration.md#p1-7)
- **Deliverable and boundary:** Fix minimal config format/location/precedence, environment key reference, prompt-input syntax, explicit mode/model selection, exits, deadlines, headless coding permissions and preview semantics. Specify enforceable read/write/shell scope and unsupported-policy refusal before the first coding launch. Add validation without generalizing later schemas.
- **Acceptance evidence:** Config/input validation fixtures and a decision entry specify success/failure/known-cancelled/uncertain exits. Empty/conflicting inputs and unsupported permission policies reject before launch; literal keys are excluded from serializable config. Record how the selected coding permissions are enforced, rather than inheriting the text-only probe policy.
- **Decision/readiness gate:** AC04–AC07; no unsupported mode or optional metadata can silently widen policy.
- **Contract:** [docs/CONFIGURATION.md](../docs/CONFIGURATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-3"></a>
## P2.3 — Managed project configuration transaction

- **Depends on:** [P2.1](02-first-slice.md#p2-1)
- **Deliverable and boundary:** Plan/validate project provider changes; preserve unrelated/global settings and environment references. Implement conflict/concurrent-write handling, atomic replacement and no-sync validation.
- **Acceptance evidence:** Temp-project fixtures cover manual conflicts, malformed/commented config, concurrent/interrupted writes, global preservation, native-route isolation prerequisites and absence of a sentinel secret.
- **Decision/readiness gate:** AC04; select transaction/ownership rules before writing user configuration.
- **Contract:** [docs/CONFIGURATION.md](../docs/CONFIGURATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-2"></a>
## P2.2 — Local-only single coding run

- **Depends on:** [P2.1](02-first-slice.md#p2-1), [P2.3](02-first-slice.md#p2-3)
- **Deliverable and boundary:** Wire prompt input, project/model selection, policy, project preparation and selected OpenCode adapter into ah single. Support inline/file/stdin; reject unimplemented modes. Runtime owns tool turns. Before any real coding prompt, implement and verify the P2.1 permission contract and minimum bounded cancellation/cleanup with failure/uncertainty handling; P2.4 completes progress, outcome and adversarial hardening. Never temporarily launch with unenforced permissions or the probe supervisor treated as production-ready.
- **Acceptance evidence:** CLI/integration checks show a validated LiteLLM-only route and a real project task path rather than a text-only completion; prompt-source errors cannot start work. Include controlled permission-denial and cleanup checks before exercising authorized edit/test tools.
- **Decision/readiness gate:** AC01, AC02, AC05; no cloud fallback in this slice.
- **Contract:** [docs/SPECIFICATION.md](../docs/SPECIFICATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-4"></a>
## P2.4 — Progress, outcomes and bounded supervision

- **Depends on:** [P2.2](02-first-slice.md#p2-2)
- **Deliverable and boundary:** Expose run/attempt identity, progress, source-attributed usage or unknown, meaningful exits, permission responses, deadlines/cancellation and cleanup certainty. Keep buffers bounded.
- **Acceptance evidence:** Controlled children/protocol fixtures exercise backpressure, noisy/truncated output, unexpected exit, headless permission requests and cleanup. Uncertain effects get a distinct exit and stderr diagnostic.
- **Decision/readiness gate:** AC02, AC06, AC07; no inference of success from text, ACK or EOF.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-7"></a>
## P2.7 — Prerequisite diagnostics and read-only preview

- **Depends on:** [P2.4](02-first-slice.md#p2-4)
- **Deliverable and boundary:** Add compact dependency/version/config diagnosis and resolved route/constraint/sync preview. Reuse the actual resolver/planner instead of a separate policy implementation.
- **Acceptance evidence:** Fixtures show no model turn or file write in preview, redacted sources/changes, actionable missing-runtime/model/key errors, and explicit handling of any permitted non-spending health checks.
- **Decision/readiness gate:** AC09; freeze exact diagnostic syntax before first-slice release.
- **Contract:** [docs/CONFIGURATION.md](../docs/CONFIGURATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-8"></a>
## P2.8 — Dirty-project preservation

- **Depends on:** [P2.4](02-first-slice.md#p2-4)
- **Deliverable and boundary:** Report existing edits/untracked files and ensure harness setup/failure/cancellation never performs automatic stash/reset/clean/commit/rollback. Keep authorized runtime edits distinct.
- **Acceptance evidence:** Use temp projects with baseline edits/untracked files; demonstrate harness setup/recovery preserves them on launch failure/cancellation. Do not promise perfect attribution or rollback of runtime actions.
- **Decision/readiness gate:** AC05; no tests reset the user repository.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-5"></a>
## P2.5 — First installable binary

- **Depends on:** [P2.7](02-first-slice.md#p2-7), [P2.8](02-first-slice.md#p2-8)
- **Deliverable and boundary:** Choose minimum release tooling and publish an executable artifact for the initial tested target. Write installation, version/help and separate OpenCode/LiteLLM prerequisite instructions.
- **Acceptance evidence:** Install/smoke-test the actual artifact without a Rust/Python toolchain requirement for binary users; record checksum/target, limitations and setup instructions.
- **Decision/readiness gate:** AC10; broader targets wait for evidence, not language portability assumptions.
- **Contract:** [docs/OPERATIONS.md](../docs/OPERATIONS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-6"></a>
## P2.6 — First-slice real-use gate

- **Depends on:** [P2.5](02-first-slice.md#p2-5)
- **Deliverable and boundary:** Use the installed binary for a small real edit-and-test task. Compare direct OpenCode, exercise unavailable LiteLLM and cancellation, then record friction and immediate corrective tasks.
- **Acceptance evidence:** All preceding Phase 2 implementation/evidence tasks and first-slice columns AC01–AC11 are assessed, with later-only items explicitly N/A. Link tested versions, verification, interventions and outcome; required review is complete.
- **Decision/readiness gate:** All Phase 2 dependencies are gates; no Phase 3 expansion until first-use evidence is recorded.
- **Contract:** [docs/SPECIFICATION.md](../docs/SPECIFICATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p2-9"></a>
## P2.9 — Phase review: holistic findings and remediation

- **Depends on:** [P2.6](02-first-slice.md#p2-6)
- **Deliverable and boundary:** Review all Phase 2 deliverables together, accumulated changes since its accepted entry baseline, acceptance/live evidence, Rust architecture/contracts, tests, regressions and operational limits. The preceding task prepares evidence; it does not close the phase.
- **Acceptance evidence:** A phase-numbered report under docs/reviews/ records the reviewed commit/PR scope, goal/feature/acceptance coverage, test/live evidence, findings, remediation and verification. A pass requires no unresolved finding; review/fix PRs follow the Git workflow.
- **Decision/readiness gate:** Dependent phase work remains gated until the whole-phase review passes, all findings are resolved/verified, and required review/fix PRs merge. Do not substitute a set of individual PR approvals.
- **Contract:** [Phase review procedure](../docs/PHASE_REVIEW.md) and [report template](PHASE_REVIEW_TEMPLATE.md); canonical status/evidence in [PROJECT.md](../PROJECT.md).
