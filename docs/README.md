# Documentation map

Start with the [specification](SPECIFICATION.md), [feature review](FEATURE_REVIEW.md), and [implementation plan](IMPLEMENTATION.md). [PROJECT.md](../PROJECT.md) owns task status; [DECISIONS.md](../DECISIONS.md) owns accepted and deferred decisions.

These documents are implementation contracts and planning records. Phase 2 implements local-only OpenCode coding runs, project routing ownership, bounded supervision, preview and dirty-project reporting; the Apple Silicon pre-release is published. [First-use evidence](evidence/p2-6-first-use.md) assesses the installed release and direct OpenCode comparison. [P2.9 holistic review](reviews/phase-02.md) records a pass with verified remediation. Phase 3 adds native OpenCode cloud-only, LiteLLM model groups, the configured local-first fallback and the OpenCode 2.2.5 baseline, with [live dual-route use](evidence/p3-5-dual-route-use.md); its acceptance is the P3.6 [review](reviews/phase-03.md). D030 cleanup corrections are in source; published alpha.1 retains its recorded best-effort private-state deletion. [Phase 1 acceptance preparation](evidence/p1-5-integration-acceptance.md) records selected transport/dependencies and the tested macOS boundary.

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
| [Phase reviews](PHASE_REVIEW.md) / [report template](../tasks/PHASE_REVIEW_TEMPLATE.md) | Whole-phase findings, remediation, verification and progression gates | Every phase must pass; reports live in docs/reviews/ |
| [Project execution plan](PROJECT_PLAN.md) / [task cards](../tasks/README.md) | Recommended work/PR order, dependencies, readiness gates and evidence | Status stays only in PROJECT.md; task cards refine before execution |
| [Implementation plan](IMPLEMENTATION.md) | Dependencies, phase exit evidence and decision timing | Tasks complete only with evidence |
| [Git workflow](GIT_WORKFLOW.md) | Branch/PR/review/merge rules | Existing mandatory repository workflow |

Before implementing a phase, finalize its designated choices in DECISIONS.md and update the relevant contracts with concrete schemas, flags, examples, and supported versions. Later unresolved choices do not block the first slice. Before closing a phase, replace planned instructions with tested ones and link evidence from PROJECT.md.
