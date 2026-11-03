# Rust software design

Status: implementation blueprint for the accepted Rust direction. Module/type names below are proposed internal vocabulary, not published Rust APIs, wire schemas or existing files. Phase 1 validates responsibilities with the first integration; D023 selects its transport/dependency stack, summarized below. [Architecture diagrams](ARCHITECTURE.md) describe control and model traffic; [specification](SPECIFICATION.md) owns the first-slice/core-MVP requirements.

## Delivery and design priorities

Deliver a small modular CLI whose first usable run edits/tests a real project through OpenCode and LiteLLM. Then add all route modes and canonical agents for the core MVP. Sequences and Ralph reuse the same validated execution path later. Favor visible, testable behavior over speculative framework abstractions.

Rust and prebuilt binaries are accepted. A Python scaffold, embedded Python agent runtime, and dependency on ai-queue are not part of the design. Port selected behavior and fixtures rather than wrapping Python. Existing coding CLIs and LiteLLM remain external prerequisites.

## Proposed package structure

Start with one Cargo package, a thin executable entry point and a library/module boundary usable by tests. Do not create a multi-crate workspace solely to mirror this table. P1.1 selects `awesomejt-agent-harness`, the `ah` binary, Rust 2024 / initial MSRV 1.85 (raised to 1.88 by D023), and `aarch64-apple-darwin` as the initial verified development target (D019). The initial scaffold had `src/main.rs` over a testable `src/lib.rs` informational argument boundary. Phase 2 adds production modules and the selected SDK/Tokio dependencies; the concrete mapping below distinguishes them from the proposed vocabulary in the table. Remaining modules are introduced only when their consuming task needs them.

| Proposed module | Responsibility | Dependency direction / first phase |
|---|---|---|
| `main` / `cli` | Parse flags/input, drive application, map outcomes to output/exits | Calls application; no routing logic / 2 |
| `domain` | Modes, routes, plans, IDs, capabilities, errors and outcomes | Independent of CLI/backend SDK types / 1–2 |
| `config` | Load/validate config and source provenance | Produces domain values / 2 |
| `policy` | Select permitted route and fallback eligibility | Pure decisions over domain data / 2–3 |
| `application` | Resolve, validate, prepare and supervise ordered attempts | Calls policy, project services and adapters / 2 |
| `project` | Project identity/baseline and managed config transaction/preview | No automatic Git cleanup or tool loop / 2 |
| `adapters::opencode` | Capabilities, invocation, permissions and backend event mapping | Owns supported interface details / 1–2 |
| `process` / `transport` | Streams, connection/process lifetime, cancellation and cleanup | OS/backend I/O behind adapter / 1–2 |
| `output` | Human progress, redaction, final result and later machine events | Consumes domain events; cannot choose route / 2, 4 |
| `agents` | Canonical YAML/Markdown validation and backend mapping | Produces constrained requests/emission plans / 4 |
| `workflows` / `state` | Sequence/Ralph outer coordination and durable records | Calls application; no direct provider bypass / 5–6 |

Additional adapters arrive in Phases 7–8. Add traits only where fakes or real alternative implementations justify them; do not freeze an interface around every imagined backend. File placement can change with experiment evidence without altering policy ownership.

## Domain model and invariants

| Concept | Required information / invariant |
|---|---|
| `OperationalMode` | local-only, cloud-only, local-first; distinct from runtime selection |
| `ModelRoute` | Tagged LiteLLM alias/endpoint reference or native target/model reference; route-specific fields do not share an ambiguous string |
| `RunRequest` | Project, one prompt source, mode, selected model/runtime, constraints, supported limits and optional canonical agent |
| `ExecutionPlan` | Validated route/runtime mapping, source provenance, capabilities, permission policy and planned project writes |
| `RunId` / `AttemptId` | Stable invocation identity; a fallback/retry creates a new attempt, not a replacement record |
| `Capabilities` | Tested version/features and unsupported/unverified mappings; requested restrictions must be enforceable |
| `AttemptOutcome` | Backend execution result, cleanup state, side-effect certainty and error classification; uncertainty cannot masquerade as success |
| `RunOutcome` | Ordered attempt outcomes and final disposition; shell behavior does not depend on parsing provider prose |
| `UsageObservation` | Optional metric with units/source; missing usage is unknown, never fabricated zero |
| `VerificationOutcome` | Separate check identity/result added with workflows; agent success is not proof tests passed |

Prefer Rust enums/newtypes to overloaded flags or provider-name strings for policy decisions. Construct validated plans through one application path. Configuration deserialization creates untrusted input values; validation and capability checking are still required before execution. Rust type safety alone does not establish runtime routing, permissions or provider terms compliance.

Do not place literal credentials inside diagnostic/serializable domain values. Carry key references until the narrow runtime-auth boundary; avoid blanket debug/serialization of secret-bearing objects. Limit prompt/tool-output collection rather than claiming universal secret scrubbing.

## Control, I/O and resource lifetime

Keep pure policy/config transformations separate from subprocess/network I/O. The application coordinator owns attempt ordering and cancellation scope. One supervisor owns the active child/connection, stream readers, permission-response channel and shutdown outcome. Dropping a stream/future must not be treated as evidence that descendants stopped; termination and reaping need explicit confirmation or uncertainty reporting.

Read stdout and stderr concurrently with bounded buffers and record/frame limits. Preserve mandatory lifecycle/permission/terminal events under backpressure; do not hold locks across blocking I/O or call synchronous child reads on the async execution thread. D023 selects Tokio 1.48.0 with caller-owned pipes, ACP SDK 3.6.0 without optional features and tokio-util compatibility adapters; P2.4 fixes production channels/budgets in [the execution contract](EXECUTION.md#p24-selected-supervision-and-human-output). Reusable process engines must prove these properties with fake-child integration tests.

A transport-level success acknowledgement may precede model work. Normalize events only after identifying backend semantics. Distinguish child exit, session completion and cleanup; EOF alone is not success. End all live activity within documented cancellation/cleanup bounds or expose the unresolved condition.

## Configuration and project changes

Resolution produces source-attributed values, then policy/capability validation, then a read-only change plan. Preview applies nothing and launches no model work. Execution rechecks conflicts/effective routing before applying managed project settings. `--no-sync` skips mutation, not validation.

Managed writes are scoped, conflict-aware and atomic per file; D025 fixes advisory locking, stale-snapshot refusal and interrupted-receipt conflicts in Phase 2. Preserve unrelated/global content and environment key references. Native plans cannot inherit harness-managed LiteLLM model selection. The first slice uses an existing proxy alias; Phase 3 defines desired model-group configuration/handoff without assuming service-management privileges.

Project baselines support dirty-worktree diagnostics and later evidence, not perfect edit attribution or transactional rollback. Runtime edits are subject to the selected permissions. Never reset/stash/commit user work as automatic setup or error recovery.

## Failure and compatibility strategy

Typed failure classifications feed policy rather than output-string guesses where the backend provides structured errors. Preserve sanitized provider details for diagnosis. Phase 3 chooses deterministic fallback eligibility and retry bounds; ambiguous side effects stop or use explicit recovery, never blind replay. Cancellation does not trigger native fallback.

Serialize only intentionally supported shapes. Internal enums can change while the external contract stays stable. Numeric exits are fixed in Phase 2; uncertainty has distinct shell behavior immediately. Version machine events/results in Phase 4 and workflow state in Phase 5. Unknown versions must not be silently interpreted. Rust types do not automatically become public JSON APIs.

## Reuse and alternatives

Evaluate ACP before native structured output in Phase 1. ACP/process adapter libraries, CLI parsing, async runtime, HTTP, serialization and release tools remain candidates in [FRAMEWORKS.md](FRAMEWORKS.md). A modular monolith avoids premature workspace/plugin overhead; an existing runtime avoids owning a new inner agent loop. A general LLM framework is not required merely to talk to an OpenAI-compatible proxy.

Borrow ai-queue's test injection, error/HTTP patterns and later quota readers as behavior to port. Do not import allocation-ranked mode semantics, isolated tools-disabled sends, simplified YAML parsing or its SQLite queue as architectural defaults. Preserve required attribution for actual reused code.

## Validation and open choices

The [test plan](TESTING.md) covers policy, fixtures, fake children, sync conflicts/secrets, CLI output, releases and live use. Each core-MVP acceptance row in [SPECIFICATION.md](SPECIFICATION.md) maps to tracked tasks and concrete evidence.

Phase 1 fixes package/toolchain, transport, libraries and permission handling. Phase 2 fixes harness config/CLI/exits, transactional writes, deadlines and initial packaging. Phase 3 fixes fallback eligibility, native isolation and model groups. Phase 4 fixes agent schema, machine output and declared platform support. Workflow schemas and completion protocols stay deferred to Phases 5–6. Record choices and superseded assumptions in DECISIONS.md before shipping their consumers.

## Phase 1 validated boundaries

[D023](../DECISIONS.md#2026-11-02--d023-select-acp-and-the-tested-rust-integration-boundaries) selects ACP protocol 1 and Rust 1.88.0. The [P1.5 evidence](evidence/p1-5-integration-acceptance.md) maps tested responsibilities to the proposed modules. `src/permission.rs` remains SDK-independent; OpenCode callback validation, option-kind mapping and sticky protocol failures belong in the adapter. The supervisor owns child/group identity, connection progress, cancellation, bounded I/O and explicit cleanup; application owns outcome/uncertainty and eventual retry policy. SDK schema types stop at the adapter boundary.

The isolated probe confirms these responsibility boundaries, not all proposed domain types. The probe's raw JSON parsing, discarded stderr, marker assertions, Python recorder and fixed 300 ms shutdown delay are historical experiment behavior, not production contracts. Phase 2 supplies the production consumers and independent verification below. Keep other table entries proposed until their consuming implementation supplies evidence.

## Phase 2 implemented mapping

The single Cargo package retains a thin `main`/`lib` boundary. `config` owns strict input/domain values and numeric exits; `single` orchestrates one explicitly selected local-only or native cloud-only attempt. `project_config` owns the project transaction/route plan, `preview` renders that same plan, and `worktree` provides read-only Git observation. `native` constructs and checks the separate built-in native routing snapshot without project I/O. `runtime` owns isolated OpenCode setup and capability preflight; `acp` owns SDK event/permission mapping and terminal classification; `process` owns child/group supervision; `progress` owns bounded human diagnostics. `permission` stays SDK-independent. The concrete file layout implements the table's responsibilities without speculative traits or a second coding loop.

[P2.6 first use](evidence/p2-6-first-use.md) and [P2.9 review](reviews/phase-02.md) assess integration and recorded limits. Public JSON remains the version-1 input schema; P3.2/D032 adds native OpenCode API-key routing with separate route-specific model defaults; local-first coordination, machine output, canonical agents and durable workflow state remain gated. Packaging uses a native locked build and a published Apple Silicon archive; the standalone experiment remains separate regression tooling.
