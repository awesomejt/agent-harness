# Phase 9 — Optional resource-aware increments

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

D068 changes P7.7’s portfolio, not these conditional dependencies: quota still waits for P7.7, scheduling for P5.6, and each selected increment for P9.4/P9.5. Subscription account-control checks do not activate quota/ranking work.

All work here is demand-driven. Conditional selection gates below remain authoritative; no optional feature is activated merely because prerequisites finish.

<a id="p9-1"></a>
## P9.1 — Optional non-spending quota visibility

- **Depends on:** [P7.7](07-native-adapters.md#p7-7), plus demand selection and a relevant supported non-spending usage path.
- **Deliverable and boundary:** When demand selects this increment, reassess ai-queue usage readers for at least one relevant supported native adapter. Add read-only measurements with units/source/freshness.
- **Acceptance evidence:** Fixtures and an authorized non-spending read show unknown/unsupported usage remains unknown; official auth retained and no prompt spent by default.
- **Decision/readiness gate:** Demand gate after the selected-portfolio Phase 7 holistic review P7.7 (D068) passes; a relevant supported usage path is still required. This supersedes the earlier first-adapter shortcut under D018.
- **Contract:** [docs/OPERATIONS.md](../docs/OPERATIONS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p9-2"></a>
## P9.2 — Optional allocation-aware selection

- **Depends on:** [P9.1](09-resource-awareness.md#p9-1)
- **Deliverable and boundary:** Decide whether ranking/cooldowns solve an observed problem; if selected, implement only within mode-permitted targets with explicit policy.
- **Acceptance evidence:** Decision plus tests cover stale/unknown limits, cooldowns, ties and policy invariants. If not selected, record deferral rather than implement speculative ranking.
- **Decision/readiness gate:** Demand gate; quotas cannot widen modes or invent balances. Dependency readiness is not approval to enable ranking.
- **Contract:** [docs/SPECIFICATION.md](../docs/SPECIFICATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p9-3"></a>
## P9.3 — Optional scheduling/storage decision and increment

- **Depends on:** [P5.6](05-sequences.md#p5-6)
- **Deliverable and boundary:** From observed demand, define delay/due-time, storage/retention, claim/retry/recovery and multi-process semantics before adding queue execution. Split decision and implementation PRs if needed.
- **Acceptance evidence:** Schedule/clock/crash tests and a real selected example cover due work, cancellation and uncertain outcomes without exactly-once claims or a mandatory daemon.
- **Decision/readiness gate:** Demand gate independent of quota work; no scheduler needed for core workflows.
- **Contract:** [docs/WORKFLOWS.md](../docs/WORKFLOWS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p9-4"></a>
## P9.4 — Validate selected resource-aware increments

- **Depends on:** Conditional: [P9.1](09-resource-awareness.md#p9-1) for quota/ranking OR [P9.3](09-resource-awareness.md#p9-3) for scheduling; also [P9.2](09-resource-awareness.md#p9-2) if ranking is selected.
- **Deliverable and boundary:** For each actually selected quota/ranking/scheduling increment, verify unknown metrics, cooldowns, due-time behavior and restart rules; publish limitations.
- **Acceptance evidence:** Per-increment evidence is recorded before that increment is called complete. This cross-cutting closeout applies only to selected scope; unselected P9.2/P9.3 remain deferred rather than blocking quota-only use.
- **Decision/readiness gate:** Dependencies are conditional: completed P9.1 for quota/ranking validation OR completed P9.3 for scheduling validation; P9.2 also required when ranking is selected. No full Phase 9 completion claim for unselected scope.
- **Contract:** [docs/TESTING.md](../docs/TESTING.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p9-5"></a>
## P9.5 — Phase review: holistic findings and remediation

- **Depends on:** Conditional: [P9.4](09-resource-awareness.md#p9-4) for every increment selected for this review snapshot; unselected optional scope stays deferred.
- **Deliverable and boundary:** Review the entire selected Phase 9 increment set and its integration with earlier phases. Repeat the gate when additional optional scope is activated; never claim unselected functionality is complete.
- **Acceptance evidence:** A phase-numbered report under docs/reviews/ records the reviewed commit/PR scope, goal/feature/acceptance coverage, test/live evidence, findings, remediation and verification. A pass requires no unresolved finding; review/fix PRs follow the Git workflow.
- **Decision/readiness gate:** No selected increment is released/accepted or consumed by later work until this review snapshot passes. New selected scope unchecks the same P9.5 task in PROJECT.md, retains prior report links and creates phase-09-r2.md (then -r3.md, etc.); recheck only after accepted review/merge.
- **Contract:** [Phase review procedure](../docs/PHASE_REVIEW.md) and [report template](PHASE_REVIEW_TEMPLATE.md); canonical status/evidence in [PROJECT.md](../PROJECT.md).
