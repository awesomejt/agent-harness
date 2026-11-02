# Phase 5 — Ordered prompt sequences

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

<a id="p5-1"></a>
## P5.1 — Sequence and durable-state decisions

- **Depends on:** [P4.6](04-core-mvp.md#p4-6)
- **Deliverable and boundary:** Choose folder ordering/filtering, context policy, failure behavior, metadata precedence, state version/location/retention, concurrency and resume syntax.
- **Acceptance evidence:** Decision entry and WORKFLOWS contract define changed-input handling, uncertain attempts, locking and schema compatibility before persistence ships.
- **Decision/readiness gate:** No generic scheduler/database is required; explicit invocation mode remains authoritative.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p5-5"></a>
## P5.5 — Trusted verification gates

- **Depends on:** [P5.1](05-sequences.md#p5-1)
- **Deliverable and boundary:** Define command trust/permissions, identity, execution directory, bounds and separate verification outcomes. Decide stop/repair behavior without executing model-suggested commands automatically.
- **Acceptance evidence:** Fake-command tests distinguish agent success, no verification, passed/failed/timed-out verification and untrusted command rejection.
- **Decision/readiness gate:** Gate semantics must be fixed before sequence dependent-step behavior ships.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p5-2"></a>
## P5.2 — Ordered prompt execution

- **Depends on:** [P5.5](05-sequences.md#p5-5)
- **Deliverable and boundary:** Resolve a deterministic folder snapshot and execute steps through the same single-run service, agent resolution and route policy. Use the chosen context/failure rules.
- **Acceptance evidence:** Ordering/input/constraint tests cover empty folders, changed files, metadata conflicts and stopping dependent steps after failure.
- **Decision/readiness gate:** No scheduling/queue machinery as a substitute for sequence semantics.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p5-3"></a>
## P5.3 — Durable resume and inspection

- **Depends on:** [P5.2](05-sequences.md#p5-2)
- **Deliverable and boundary:** Persist versioned step/attempt/verification outcomes atomically. Add read-only inspection and explicit resume/retry choices for changed or uncertain work.
- **Acceptance evidence:** Crash-window, competing-writer, changed-input/schema and cancellation tests prove completed steps are not silently repeated and uncertain effects are surfaced.
- **Decision/readiness gate:** Retain minimal sanitized evidence; no exactly-once side-effect or rollback promise.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p5-4"></a>
## P5.4 — Sequence use gate

- **Depends on:** [P5.3](05-sequences.md#p5-3)
- **Deliverable and boundary:** Use an ordered multi-step project task, interrupt it, inspect records and resume under documented rules. Update docs with tested behavior.
- **Acceptance evidence:** Phase 5 evidence covers order, verification, failure and recovery in a real task; all tasks/review complete and state/version limitations are recorded.
- **Decision/readiness gate:** A successful queue drain is not evidence of correct sequence semantics.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

