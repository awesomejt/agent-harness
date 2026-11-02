# Phase 1 — Integration experiment

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

<a id="p1-1"></a>
## P1.1 — Minimal Rust package and toolchain

- **Depends on:** Phase 0 documentation/review complete.
- **Deliverable and boundary:** Create one Cargo package with the ah binary and minimal testable module boundary. Select a nonconflicting package name, edition/MSRV and initial target. Do not implement later commands or a workspace framework.
- **Acceptance evidence:** Build/version smoke plus formatting/lint/test commands appropriate to the scaffold; record toolchain/target and package decision. No live model call is needed.
- **Decision/readiness gate:** Phase 0 complete; select only the minimum toolchain/dependencies needed for the experiment.
- **Contract:** [docs/DESIGN.md](../docs/DESIGN.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p1-6"></a>
## P1.6 — Permission policy before live execution

- **Depends on:** [P1.1](01-integration.md#p1-1)
- **Deliverable and boundary:** Specify allowed/denied/prompted actions, noninteractive behavior and permission-response handling for the experiment before sending a live prompt. This extracts the decision portion of P1.3.
- **Acceptance evidence:** A decision entry and fake/request fixture demonstrate explicit grants/denials and no silent approval or hanging TUI. Live execution remains gated until this is recorded.
- **Decision/readiness gate:** Required before P1.2 live work, regardless of which transport is selected.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p1-2"></a>
## P1.2 — OpenCode transport experiment

- **Depends on:** [P1.6](01-integration.md#p1-6)
- **Deliverable and boundary:** Connect to installed OpenCode in a disposable project; exercise ACP first. Compare structured native output only if evidence warrants it. Use an existing LiteLLM alias; no custom coding loop.
- **Acceptance evidence:** Record exact versions and a repeatable prompt/event/terminal example with project/model selection. An unavailable proxy is recorded as an external blocker, not a successful integration.
- **Decision/readiness gate:** Permission decision P1.6 must be recorded before the first live run; prompt/model service use must remain within session authorization.
- **Contract:** [docs/ARCHITECTURE.md](../docs/ARCHITECTURE.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p1-4"></a>
## P1.4 — Evaluate smallest reusable adapter/process layer

- **Depends on:** [P1.2](01-integration.md#p1-2)
- **Deliverable and boundary:** Compare direct SDK/runtime use with a narrow reusable component for the selected transport. Inspect a pinned release, license/attribution, platform constraints and defaults. Do not benchmark every framework.
- **Acceptance evidence:** A concise dependency decision cites working experiment evidence, required features, rejected alternative and known lifecycle gaps.
- **Decision/readiness gate:** Adopt only what saves implementation without taking control of route/permission policy.
- **Contract:** [docs/FRAMEWORKS.md](../docs/FRAMEWORKS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p1-3"></a>
## P1.3 — Lifecycle and effective-route evidence

- **Depends on:** [P1.4](01-integration.md#p1-4)
- **Deliverable and boundary:** Validate project instructions, model selection, permission callbacks, streaming, termination, cancellation and descendant cleanup. Decision work is now P1.6; this task proves behavior.
- **Acceptance evidence:** Fake-child/protocol checks and explicit live evidence cover required behaviors, including an unavailable service and denied action. List unresolved backend/platform limitations.
- **Decision/readiness gate:** Do not infer effective model routing or cleanup solely from accepted flags or EOF.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p1-5"></a>
## P1.5 — Close integration experiment

- **Depends on:** [P1.3](01-integration.md#p1-3)
- **Deliverable and boundary:** Select the transport/minimal dependencies and confirm proposed Rust boundaries using the experiment. Write exact tested versions, results, limitations and follow-up work.
- **Acceptance evidence:** Phase 1 exit evidence is linked from PROJECT.md; decisions and DESIGN/FRAMEWORKS/EXECUTION docs match what was actually tested. Required review is complete.
- **Decision/readiness gate:** All Phase 1 tasks and required live evidence must be complete; unavailable LiteLLM blocks this gate.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

