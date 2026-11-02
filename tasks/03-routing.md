# Phase 3 — Dual-route execution

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

<a id="p3-1"></a>
## P3.1 — Failure and recovery decision

- **Depends on:** [P2.6](02-first-slice.md#p2-6)
- **Deliverable and boundary:** Define eligible deterministic failures, retry bounds, native fallback policy and handling of possible side effects. Define validation/auth/rate-limit/transport classifications.
- **Acceptance evidence:** Decision table and tests distinguish pre-execution failure from uncertainty, forbid blind replay and ensure cancellation/unsupported constraints do not trigger fallback.
- **Decision/readiness gate:** AC03; recovery policy must precede automatic native attempts.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p3-2"></a>
## P3.2 — Isolated native OpenCode route

- **Depends on:** [P3.1](03-routing.md#p3-1)
- **Deliverable and boundary:** Add explicit native target/model for cloud-only using official authentication. Validate effective settings without rewriting the managed LiteLLM provider block.
- **Acceptance evidence:** Tests show no LiteLLM discovery or model traffic in cloud-only and no inherited managed-model selection; native login/version requirements are documented.
- **Decision/readiness gate:** AC02, AC04; runtime selection and route selection remain distinct.
- **Contract:** [docs/CONFIGURATION.md](../docs/CONFIGURATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p3-3"></a>
## P3.3 — Model groups and configured local-first fallback

- **Depends on:** [P3.2](03-routing.md#p3-2)
- **Deliverable and boundary:** First define/implement group references and proxy handoff/validation; then add the configured fallback coordinator as a second small PR if needed. Do not assume service restart/reconfiguration privileges.
- **Acceptance evidence:** Fixtures cover group resolution, effective routing and new attempt identity. Eligible local failure uses only the configured native target with the same required constraints.
- **Decision/readiness gate:** AC03, AC04; no implicit allocation-ranked provider pool.
- **Contract:** [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p3-4"></a>
## P3.4 — Three-mode boundary matrix

- **Depends on:** [P3.3](03-routing.md#p3-3)
- **Deliverable and boundary:** Verify mode restrictions including inherited/helper/subagent choices, discovery requests, retry bounds, invalid fallback config and uncertain completion.
- **Acceptance evidence:** Mode-matrix and controlled failure tests prove forbidden launches/requests stay absent; ambiguous side effects stop with uncertainty.
- **Decision/readiness gate:** AC02, AC03; test effective behavior, not just selected enum values.
- **Contract:** [docs/TESTING.md](../docs/TESTING.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p3-5"></a>
## P3.5 — Dual-route use gate

- **Depends on:** [P3.4](03-routing.md#p3-4)
- **Deliverable and boundary:** Demonstrate local-only, native cloud-only and local-first eligible fallback. Capture route explanations, native-config isolation and recovery limits.
- **Acceptance evidence:** Live examples, exact versions and known limitations close Phase 3; docs/decisions match behavior and required review is complete.
- **Decision/readiness gate:** All Phase 3 tasks complete; use evidence may reorder later backlog, not weaken mode policy.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

