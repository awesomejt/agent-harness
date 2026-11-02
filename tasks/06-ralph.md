# Phase 6 — Bounded Ralph loops

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

<a id="p6-1"></a>
## P6.1 — Ralph completion and limit decisions

- **Depends on:** [P5.6](05-sequences.md#p5-6)
- **Deliverable and boundary:** Study relevant Rust examples; choose completion signal/verification, fresh-context handoff, iteration/wall-time limits and interrupted-run policy.
- **Acceptance evidence:** Decision entry specifies stale/false completion handling, exhausted bounds and measurable usage limits without inventing cost guarantees.
- **Decision/readiness gate:** Outer loop only; do not replace runtime inner agent behavior.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p6-2"></a>
## P6.2 — Fresh-context durable iterations

- **Depends on:** [P6.1](06-ralph.md#p6-1)
- **Deliverable and boundary:** Implement a thin loop coordinator reusing single-run policy and workflow records; persist explicit filesystem progress and per-iteration attempts.
- **Acceptance evidence:** Tests show each iteration has fresh runtime context, preserved progress and traceable route/config identities; interrupted iterations remain recoverable/uncertain.
- **Decision/readiness gate:** No unbounded recursive retry or invisible shared provider session.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p6-3"></a>
## P6.3 — Completion, bounds and cancellation

- **Depends on:** [P6.2](06-ralph.md#p6-2)
- **Deliverable and boundary:** Verify the selected completion signal and configured checks, enforce iteration/time bounds, and stop/cancel descendants with an explicit terminal outcome.
- **Acceptance evidence:** False/stale signal, failing check, non-completion, cancellation and exhausted-limit tests prevent success from mere prose or clean exit.
- **Decision/readiness gate:** Usage budgets apply only where reporting/enforcement is trustworthy.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p6-4"></a>
## P6.4 — Ralph use gate

- **Depends on:** [P6.3](06-ralph.md#p6-3)
- **Deliverable and boundary:** Demonstrate one verified completion, one bounded non-completion and one interrupted/resumed task. Record iteration evidence and limitations.
- **Acceptance evidence:** All preceding Phase 6 implementation/evidence tasks/checks/review complete; actual runs show completion verification and no silent replay. Queue Pi workflow-parity follow-up when Pi is available.
- **Decision/readiness gate:** No milestone completion from mocked loop iterations alone.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p6-5"></a>
## P6.5 — Phase review: holistic findings and remediation

- **Depends on:** [P6.4](06-ralph.md#p6-4)
- **Deliverable and boundary:** Review all Phase 6 deliverables together, accumulated changes since its accepted entry baseline, acceptance/live evidence, Rust architecture/contracts, tests, regressions and operational limits. The preceding task prepares evidence; it does not close the phase.
- **Acceptance evidence:** A phase-numbered report under docs/reviews/ records the reviewed commit/PR scope, goal/feature/acceptance coverage, test/live evidence, findings, remediation and verification. A pass requires no unresolved finding; review/fix PRs follow the Git workflow.
- **Decision/readiness gate:** Dependent phase work remains gated until the whole-phase review passes, all findings are resolved/verified, and required review/fix PRs merge. Do not substitute a set of individual PR approvals.
- **Contract:** [Phase review procedure](../docs/PHASE_REVIEW.md) and [report template](PHASE_REVIEW_TEMPLATE.md); canonical status/evidence in [PROJECT.md](../PROJECT.md).
