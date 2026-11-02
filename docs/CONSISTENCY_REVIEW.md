# Rust documentation consistency review

Review date: 2026-11-01. Scope: every repository Markdown document, including historical decisions, feature inventory, roadmap and technical contracts. This records a design/document audit; no Rust implementation or live adapter behavior is validated by it.

## Scope verdict

The product feature boundary is clear enough to begin Phase 1. First usable slice is Phase 2: real project coding through OpenCode + LiteLLM in local-only mode. Core MVP closes Phase 4: single execution, all three route modes, configured eligible fallback, named constrained OpenCode agents, diagnostics/preview, machine/headless behavior and supported binary distribution. AC01–AC11 in [SPECIFICATION.md](SPECIFICATION.md) are the acceptance checklist.

Sequences and workflow recovery arrive in Phase 5, Ralph in Phase 6, additional native CLIs and Pi in Phases 7–8, and optional resource-aware increments in Phase 9. Candidate features in FEATURE_REVIEW.md are not implementation commitments. No new feature family is promoted by the architecture pass.

## Alignment checks and resolutions

| Topic | Finding / resolution | Authoritative record |
|---|---|---|
| Rust direction | Explicitly accepted language; a single Cargo package/module blueprint replaces generic rationale. Python is mentioned only as prior work or an avoided runtime requirement. | D008, D015; DESIGN.md |
| MVP scope | Add AC01–AC11 to make supporting input, diagnostics, supervision, automation and release criteria explicit. Core-MVP closure depends on all Phase 2–4 tasks. | SPECIFICATION.md; IMPLEMENTATION.md; PROJECT.md |
| Model route versus runtime | Preserve two policy paths; an OpenCode process may use either. No raw HTTP completion is presented as a coding agent. | D010; ARCHITECTURE.md |
| LiteLLM ownership | Distinguish desired policy/group configuration from external proxy operation; define any configuration handoff in Phase 3. No automatic service privileges implied. | D016; CONFIGURATION.md |
| Lifecycle / outcomes | Diagrams include validation, active work, cleanup and uncertainty. Distinct uncertainty exit behavior begins in Phase 2; successful runtime exit does not prove workflow verification. | EXECUTION.md; ARCHITECTURE.md |
| Human versus machine output | Resolve the ambiguous F13 phase label: human progress in Phase 2, versioned machine result/events in Phase 4. | FEATURE_REVIEW.md; P4.7 |
| Agent portability | Canonical Markdown + YAML remains fixed; exact schema/destinations and effort/permission mapping remain Phase 4 choices. No provider-format guess is a Rust constraint. | CONFIGURATION.md; D006 |
| Async/process design | A supervisor owns child/connection/readers and cleanup; pure policy remains independent of I/O/backend types. Library/runtime choice remains experimental. | DESIGN.md; EXECUTION.md |
| State/storage | Single attempts can remain in memory. Workflow state is filesystem-based, versioned in Phase 5; no inherited SQLite queue or mandatory daemon. | WORKFLOWS.md; ARCHITECTURE.md |
| Project preservation | Harness setup/recovery never automatically stashes/resets/cleans/commits. Authorized runtime edits can change project files; no transactional rollback or OS sandbox is claimed. | EXECUTION.md; OPERATIONS.md |
| Historical decisions | D007 remains explicitly superseded by D009; D004 conceptual types are clarified by D010; earlier entries are not deleted or treated as current implementation. | DECISIONS.md |
| Release prerequisites | Harness binaries need no Rust/Python toolchain. Existing coding CLIs and proxy remain external prerequisites, with platform behavior validated before support claims. | OPERATIONS.md; ARCHITECTURE.md |

## Documents inspected

- README.md and AGENTS.md: product entry point, current status, accepted language and agent guidance.
- PROJECT.md and DECISIONS.md: stable task/decision references, current milestones and deferred choices.
- docs/SPECIFICATION.md, FEATURE_REVIEW.md and IMPLEMENTATION.md: goal/feature/acceptance/phase agreement.
- docs/DESIGN.md and ARCHITECTURE.md: Rust blueprint, six diagrams, ownership and dependency boundaries.
- docs/CONFIGURATION.md, EXECUTION.md and WORKFLOWS.md: detailed contract agreement with the design.
- docs/TESTING.md and OPERATIONS.md: evidence requirements, support and release boundaries.
- docs/FRAMEWORKS.md: reuse candidates remain candidates; no implied locked dependencies.
- docs/README.md: links and decision owners; docs/GIT_WORKFLOW.md: existing PR/review rules remain unchanged.

## Deliberately unresolved

Rust package/toolchain baseline, transport/library choice and permission callback behavior require Phase 1 evidence. Harness config format/precedence, exact flag syntax, exits, limits and sync transactions are Phase 2 choices. Fallback classification and model-group handoff are Phase 3 choices. Canonical-agent schema, public machine schema and platform matrix are Phase 4 choices. Durable schemas, verification trust and Ralph completion belong to Phases 5–6.

A proposed module name or diagram participant is not a frozen Rust trait, wire schema, provider API or package selection. These deferred choices do not conflict with Rust or block the integration experiment. Update this review when a design-changing decision modifies the scope/ownership boundaries; use PROJECT.md for actual phase completion and evidence.

## Validation

Check local Markdown links, balanced fences, unique G/F/AC/P/D references, task/phase coverage and actual Mermaid parser acceptance for all six diagrams. Preserve a clean PR with the required Grok review before merge. Diagram/parser tooling used to validate documentation does not become a harness runtime dependency. No cargo tests are claimed before Cargo files exist.
