# Documentation map

Start with the [specification](SPECIFICATION.md), [feature review](FEATURE_REVIEW.md), and [implementation plan](IMPLEMENTATION.md). [PROJECT.md](../PROJECT.md) owns task status; [DECISIONS.md](../DECISIONS.md) owns accepted and deferred decisions.

These documents are implementation contracts and planning records. No CLI, serialized schema, tested platform matrix, or operational procedure is claimed implemented yet.

| Document | Coverage | What remains phase-gated |
|---|---|---|
| [Specification](SPECIFICATION.md) | G1–G9, AC01–AC11 MVP checks, Rust constraints and milestones | Product choices may evolve through recorded decisions |
| [Feature review](FEATURE_REVIEW.md) | Upstream evidence and F01–F26 dispositions | Candidate features require promotion; integration evidence is separate |
| [Rust design](DESIGN.md) / [Architecture](ARCHITECTURE.md) | Proposed module/domain model and six system/component/behavior/deployment diagrams | Proposed vocabulary becomes concrete Rust APIs after Phase 1 validation |
| [Consistency review](CONSISTENCY_REVIEW.md) | Scope, MVP acceptance, Rust direction and document agreement | Refresh after design-changing phases |
| [Frameworks](FRAMEWORKS.md) | Library and example shortlist | Version/license/platform validation on adoption |
| [Execution contract](EXECUTION.md) | Requests, lifecycle, events, outcomes, capabilities, fallback, headless execution | Transport/permissions 1; exits 2; machine schema 4 |
| [Configuration contract](CONFIGURATION.md) | Resolution, preview, sync, secrets, canonical-agent mapping | Format/precedence 2; model groups 3; agent schema 4 |
| [Workflow state](WORKFLOWS.md) | Sequence/Ralph recovery, context and verification contracts | Durable schema/resume 5; completion/limits 6 |
| [Validation plan](TESTING.md) | Policy, adapter, lifecycle, sync, release and live acceptance evidence | Executable tests and commands as implementation appears |
| [Operations](OPERATIONS.md) | Installation, diagnostics, data handling, troubleshooting and release expectations | Concrete install/upgrade/runbook commands and supported targets 2/4 |
| [Implementation plan](IMPLEMENTATION.md) | Dependencies, phase exit evidence and decision timing | Tasks complete only with evidence |
| [Git workflow](GIT_WORKFLOW.md) | Branch/PR/review/merge rules | Existing mandatory repository workflow |

Before implementing a phase, finalize its designated choices in DECISIONS.md and update the relevant contracts with concrete schemas, flags, examples, and supported versions. Later unresolved choices do not block the first slice. Before closing a phase, replace planned instructions with tested ones and link evidence from PROJECT.md.
