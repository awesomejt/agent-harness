# Phase 9 — Optional resource-aware increments

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

All work here is demand-driven. OR/selection gates below take precedence over the combined dependency summary; no optional feature is activated merely because prerequisites finish.

<a id="p9-1"></a>
## P9.1 — Optional non-spending quota visibility

- **Depends on:** Conditional: any one relevant completed adapter [P7.2](07-native-adapters.md#p7-2) OR [P7.3](07-native-adapters.md#p7-3) OR [P7.4](07-native-adapters.md#p7-4) OR [P7.5](07-native-adapters.md#p7-5), plus demand selection.
- **Deliverable and boundary:** When demand selects this increment, reassess ai-queue usage readers for at least one relevant supported native adapter. Add read-only measurements with units/source/freshness.
- **Acceptance evidence:** Fixtures and an authorized non-spending read show unknown/unsupported usage remains unknown; official auth retained and no prompt spent by default.
- **Decision/readiness gate:** Demand gate plus at least one relevant adapter P7.2/P7.3/P7.4/P7.5 complete; do not require the entire portfolio.
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

- **Depends on:** [P5.4](05-sequences.md#p5-4)
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

