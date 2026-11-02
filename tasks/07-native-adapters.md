# Phase 7 — Additional native CLI adapters

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

Adapter tasks share the core dependency but are activated one at a time by a recorded target selection. Each adapter is independently usable; portfolio closeout waits for all four.

<a id="p7-1"></a>
## P7.1 — Select next native adapter

- **Depends on:** [P4.6](04-core-mvp.md#p4-6)
- **Deliverable and boundary:** Choose one of the four committed native targets from real-use needs and verify supported authentication/integration terms, interface and version baseline.
- **Acceptance evidence:** Decision entry names the selected target and capability/permission/model/event questions. Other adapters stay deferred until explicitly selected.
- **Decision/readiness gate:** Only one new adapter active at a time by default; no fixed provider ordering implied by task IDs.
- **Contract:** [docs/FRAMEWORKS.md](../docs/FRAMEWORKS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-2"></a>
## P7.2 — Claude native adapter

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Claude, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Activation gate: Claude is the currently selected target from P7.1 or a later recorded selection. Reuse official authentication; no token scraping or prohibited proxying.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-3"></a>
## P7.3 — Codex native adapter

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Codex, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Activation gate: Codex is the currently selected target from P7.1 or a later recorded selection. Reuse official authentication; no token scraping or prohibited proxying.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-4"></a>
## P7.4 — Grok native adapter

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Grok, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Activation gate: Grok is the currently selected target from P7.1 or a later recorded selection. Reuse official authentication; no token scraping or prohibited proxying.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-5"></a>
## P7.5 — Gemini native adapter

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Gemini, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Activation gate: Gemini is the currently selected target from P7.1 or a later recorded selection. Reuse official authentication; no token scraping or prohibited proxying.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-6"></a>
## P7.6 — Native adapter portfolio closeout

- **Depends on:** [P7.2](07-native-adapters.md#p7-2), [P7.3](07-native-adapters.md#p7-3), [P7.4](07-native-adapters.md#p7-4), [P7.5](07-native-adapters.md#p7-5)
- **Deliverable and boundary:** Audit aggregate capability/version/install coverage across the complete committed four-target portfolio. Incremental per-adapter docs/tests remain mandatory inside each adapter task; this task is only the final portfolio audit/closeout.
- **Acceptance evidence:** Each committed adapter has linked fixture/live evidence and setup/capability docs; select the next target only after current adapter review/use. Portfolio closure waits for all four.
- **Decision/readiness gate:** Partial adapter milestones are usable independently; Phase 7 as a whole is not complete until all committed targets pass.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

