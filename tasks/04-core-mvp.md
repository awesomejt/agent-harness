# Phase 4 — Named agents and core MVP

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

<a id="p4-1"></a>
## P4.1 — Canonical schema and destination contract

- **Depends on:** [P3.6](03-routing.md#p3-6)
- **Deliverable and boundary:** Choose canonical YAML fields and validate Markdown/body, names, duplicates, tools/permissions, effort/model aliases and actual OpenCode destinations.
- **Acceptance evidence:** Schema/parser fixtures reject malformed/ambiguous/traversal inputs; decision entry and examples reflect a tested backend version.
- **Decision/readiness gate:** AC08; do not promote speculative provider formats into guarantees.
- **Contract:** [docs/CONFIGURATION.md](../docs/CONFIGURATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-2"></a>
## P4.2 — Named emission and agent selection

- **Depends on:** [P4.1](04-core-mvp.md#p4-1)
- **Deliverable and boundary:** Emit/map by canonical name, preview output, preserve user-owned agents and reject conflicts. Wire agent selection into validated requests.
- **Acceptance evidence:** Golden fixtures and temp-project tests cover deterministic emission, name collisions, ownership and no writes in preview.
- **Decision/readiness gate:** AC08; reuse existing project transaction rules.
- **Contract:** [docs/CONFIGURATION.md](../docs/CONFIGURATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-3"></a>
## P4.3 — Constrained primary and specialized execution

- **Depends on:** [P4.2](04-core-mvp.md#p4-2)
- **Deliverable and boundary:** Implement primary/specialized invocation with supported model/effort/tool/permission mappings; report approximations and refuse unsupported required restrictions.
- **Acceptance evidence:** Runtime mapping tests demonstrate an enforceable constrained role and no route/permission widening through defaults, helper agents or unsupported effort.
- **Decision/readiness gate:** AC07, AC08; prompt text alone cannot enforce read-only behavior.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-7"></a>
## P4.7 — Versioned machine and CI contract

- **Depends on:** [P4.3](04-core-mvp.md#p4-3)
- **Deliverable and boundary:** Specify and implement final-result/event envelope, ordering/IDs, redaction and version compatibility. Preserve exits and stdout/stderr behavior; cover headless input/permissions.
- **Acceptance evidence:** Machine-consumer fixtures and CLI tests check terminal outcomes including uncertainty, diagnostics separation, unknown metric representation and no hidden interactive wait.
- **Decision/readiness gate:** AC06; machine output is public contract, not automatic serialization of internal Rust enums. Evaluate the [Phase 3 review](../docs/reviews/phase-03.md) recommendation R03-REC1 (post-submission terminal error with zero grants and zero completed tool calls reported as exit 1, never fallback) before freezing the exit contract. Adopt it only with a decision entry and fixtures; until then the conservative exit 4 stands.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-8"></a>
## P4.8 — Inherited backend capabilities

- **Depends on:** [P4.3](04-core-mvp.md#p4-3)
- **Deliverable and boundary:** Document/test skills, MCP, project instructions, context and helper behavior relevant to supported runs. Keep context/compaction and inner tools runtime-owned.
- **Acceptance evidence:** Versioned capability matrix distinguishes tested/unsupported/unverified behavior; route/permission tests cover enabled helper/tool paths or refuse them.
- **Decision/readiness gate:** AC11; no replacement MCP server or context engine.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-4"></a>
## P4.4 — Primary and reviewer acceptance

- **Depends on:** [P4.7](04-core-mvp.md#p4-7), [P4.8](04-core-mvp.md#p4-8)
- **Deliverable and boundary:** Run a named coding task and a constrained review task through supported routes. Include an explicit prohibited operation and unsupported-restriction case.
- **Acceptance evidence:** Live and fixture evidence show the constrained role is enforced, machine/headless contracts hold and unsupported restrictions fail visibly.
- **Decision/readiness gate:** AC05, AC07, AC08, AC11; document unavailable capabilities rather than silently broadening.
- **Contract:** [docs/SPECIFICATION.md](../docs/SPECIFICATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-5"></a>
## P4.5 — MVP artifacts and setup polish

- **Depends on:** [P4.4](04-core-mvp.md#p4-4)
- **Deliverable and boundary:** Declare supported platform/runtime matrix, build/smoke-test every artifact, and complete sample config/agents, diagnostics, CI guidance and install/upgrade instructions.
- **Acceptance evidence:** Every advertised target has artifact/install evidence; docs separate ah from CLI/proxy prerequisites and preserve secrets/config on setup/upgrade.
- **Decision/readiness gate:** AC09, AC10; no platform claim from compilation alone. Per the [Phase 3 review](../docs/reviews/phase-03.md) R03-REC2, the published `v0.1.0-alpha.1` predates native/local-first routing, the OpenCode 2.2.5 pin and D030 cleanup; artifacts here must package current source.
- **Contract:** [docs/OPERATIONS.md](../docs/OPERATIONS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-6"></a>
## P4.6 — Prepare core MVP acceptance evidence

- **Depends on:** [P4.5](04-core-mvp.md#p4-5)
- **Deliverable and boundary:** Assess all G1–G5 and AC01–AC11 against linked evidence, including all supporting Phase 2–4 implementation/evidence tasks; final holistic review P4.9 remains the exit gate. Record repeated real use, limitations and next priorities.
- **Acceptance evidence:** Acceptance matrix has evidence per row; required checks/review complete; no unverified restriction/platform advertised. First MVP release/use notes identify residual issues.
- **Decision/readiness gate:** All Phase 4 dependencies complete; sequences/Ralph and more providers are not MVP blockers.
- **Contract:** [docs/SPECIFICATION.md](../docs/SPECIFICATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p4-9"></a>
## P4.9 — Phase review: holistic findings and remediation

- **Depends on:** [P4.6](04-core-mvp.md#p4-6)
- **Deliverable and boundary:** Review all Phase 4 deliverables together, accumulated changes since its accepted entry baseline, acceptance/live evidence, Rust architecture/contracts, tests, regressions and operational limits. The preceding task prepares evidence; it does not close the phase.
- **Acceptance evidence:** A phase-numbered report under docs/reviews/ records the reviewed commit/PR scope, goal/feature/acceptance coverage, test/live evidence, findings, remediation and verification. A pass requires no unresolved finding; review/fix PRs follow the Git workflow.
- **Decision/readiness gate:** Dependent phase work remains gated until the whole-phase review passes, all findings are resolved/verified, and required review/fix PRs merge. Do not substitute a set of individual PR approvals.
- **Contract:** [Phase review procedure](../docs/PHASE_REVIEW.md) and [report template](PHASE_REVIEW_TEMPLATE.md); canonical status/evidence in [PROJECT.md](../PROJECT.md).
