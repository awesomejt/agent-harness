# Project tracker

Last updated: 2026-11-01. Status is maintained here; phase contracts are in [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Current state

- Active phase: 1 — integration experiment ready to start; no implementation started.
- Active implementation task/PR: none. Default work-in-progress limit: one focused task/PR.
- Next ready task: P1.1. Next dependency chain: P1.6 permission policy → P1.2 transport experiment.
- External prerequisites: CLI versions, LiteLLM/model availability and login are unverified; no external blocker has been diagnosed by this planning pass.
- Remaining implementation backlog: 50 tasks across Phases 1–9; Phase 9 increments remain demand-gated.
- Phase 0 review: PR #1 received 0 blockers, 2 concerns, and 2 nits; all four addressed. No critical/high findings; no re-review required under docs/GIT_WORKFLOW.md.
- Implementation: none yet.
- Direction: Rust CLI with prebuilt binaries; OpenCode first, LiteLLM route plus native route.
- Execution plan: [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md); per-task dependencies, boundaries and evidence: [tasks/README.md](tasks/README.md). Feature/contract review (PR #2) and Rust architecture/alignment review (PR #3) are complete; task-planning review (PR #4) is complete: 0 blockers, 1 concern and 2 nits addressed; no critical/high findings.
- Feature coverage: docs/FEATURE_REVIEW.md records eight upstream projects and F01–F26 dispositions; docs/README.md indexes technical contracts. No implementation has started.
- First usable milestone: end of Phase 2. Core MVP: end of Phase 4.
- Task IDs are stable references, not execution order; phase validation/closeout depends on every other task in that phase.
- Phase order is dependency-based, without calendar estimates. Phases 7–8 can follow Phase 4 independently of workflow expansion.

## Phase 0 — Scope and roadmap

- [x] P0.1 Draft complete goals, boundaries, and milestone success criteria.
- [x] P0.2 Separate first slice, core MVP, sequences, Ralph, and broader integrations.
- [x] P0.3 Record Rust direction, route/transport clarification, and deferred decisions.
- [x] P0.4 Capture reuse candidates and validation criteria without adopting them prematurely.
- [x] P0.5 Complete documentation consistency checks and required PR review (PR #1; four minor findings addressed).
- [x] P0.6 Compare upstream feature families and classify committed, backend-owned, candidate and excluded scope.
- [x] P0.7 Draft execution/configuration/workflow/testing/operations contracts and documentation index with phase-owned finalization.
- [x] P0.8 Validate feature/task/doc traceability and complete PR review for the feature/contract pass (PR #2; 0 blockers, 2 concerns and 1 nit addressed; no critical/high findings).
- [x] P0.9 Align full scope and AC01–AC11 acceptance with the Rust software blueprint, architecture diagrams and detailed contracts.
- [x] P0.10 Validate diagrams/document consistency and complete PR review of the Rust architecture pass (PR #3; 0 blockers, 2 concerns and 3 nits addressed; no critical/high findings).
- [x] P0.11 Draft the remaining-phase execution plan, dependency gates, detailed task cards and immediate ready queue.
- [x] P0.12 Validate task/dependency/contract consistency and complete required PR review of the planning structure (PR #4; all three minor findings addressed; completion effective on merge).

## Phase 1 — Integration experiment

Detailed scope, dependencies and evidence: [Phase 1 cards](tasks/01-integration.md).

- [ ] P1.1 Create a minimal Rust package on a feature branch; select a nonconflicting package name, Rust edition/MSRV and initial development target ([card](tasks/01-integration.md#p1-1)).
- [ ] P1.6 Define and test permission-request policy/noninteractive behavior before the first live integration run (decision subtask extracted from P1.3) ([card](tasks/01-integration.md#p1-6)).
- [ ] P1.2 Exercise OpenCode ACP with a disposable project; compare native structured output if needed ([card](tasks/01-integration.md#p1-2)).
- [ ] P1.4 Evaluate a small reusable adapter/process dependency against direct SDK/runtime use; inspect license, release/API compatibility, and platform behavior ([card](tasks/01-integration.md#p1-4)).
- [ ] P1.3 After the P1.6 permission decision, verify no implicit widening, LiteLLM model selection, project instructions, progress, cancellation, and child cleanup ([card](tasks/01-integration.md#p1-3)).
- [ ] P1.5 Record tested versions, live evidence, selected transport/dependencies, validated Rust module/type boundaries, and unresolved limitations ([card](tasks/01-integration.md#p1-5)).

## Phase 2 — First usable slice

Detailed scope, dependencies and evidence: [Phase 2 cards](tasks/02-first-slice.md).

- [ ] P2.1 Define minimal config, precedence, environment key reference, and exit conventions ([card](tasks/02-first-slice.md#p2-1)).
- [ ] P2.3 Implement project provider sync that preserves unrelated settings; test conflicts, interrupted writes, global-config preservation, absence of literal LiteLLM keys (use a sentinel secret), and `--no-sync` route validation ([card](tasks/02-first-slice.md#p2-3)).
- [ ] P2.2 Implement `ah single` with `local-only`, project selection, model alias, visible resolved route, and unambiguous inline/file/stdin prompt input ([card](tasks/02-first-slice.md#p2-2)).
- [ ] P2.4 Stream progress, identify attempts and reported usage, classify failures, handle deadlines/cancellation and headless permissions, and verify no cloud-native fallback ([card](tasks/02-first-slice.md#p2-4)).
- [ ] P2.7 Add basic prerequisite/version diagnostics and read-only resolved-plan/sync preview without model turns or writes; fix exact syntax before release ([card](tasks/02-first-slice.md#p2-7)).
- [ ] P2.8 Report dirty-worktree state and preserve pre-existing edits/untracked files; test failed/cancelled runs without automatic Git mutations ([card](tasks/02-first-slice.md#p2-8)).
- [ ] P2.5 Produce an initial platform binary with installation/setup instructions ([card](tasks/02-first-slice.md#p2-5)).
- [ ] P2.6 Use it for a real edit-and-test task; compare direct OpenCode and record friction before expanding ([card](tasks/02-first-slice.md#p2-6)).

## Phase 3 — Routing and fallback

Detailed scope, dependencies and evidence: [Phase 3 cards](tasks/03-routing.md).

- [ ] P3.1 Define eligible failures, retry limits, and partial-work recovery policy ([card](tasks/03-routing.md#p3-1)).
- [ ] P3.2 Add explicit native OpenCode target/model and cloud-only execution isolated from managed LiteLLM routing ([card](tasks/03-routing.md#p3-2)).
- [ ] P3.3 Add model-group references with explicit proxy-configuration handoff/validation and configured local-first fallback ([card](tasks/03-routing.md#p3-3)).
- [ ] P3.4 Test all mode boundaries, discovery requests, inherited runtime settings, and uncertain outcomes ([card](tasks/03-routing.md#p3-4)).
- [ ] P3.5 Demonstrate each route and eligible fallback in use; record findings ([card](tasks/03-routing.md#p3-5)).

## Phase 4 — Agents and core MVP

Detailed scope, dependencies and evidence: [Phase 4 cards](tasks/04-core-mvp.md).

- [ ] P4.1 Define/validate canonical YAML schema and actual OpenCode agent destinations ([card](tasks/04-core-mvp.md#p4-1)).
- [ ] P4.2 Add name-based emission, collision handling, and `--agent` selection ([card](tasks/04-core-mvp.md#p4-2)).
- [ ] P4.3 Implement primary/specialized execution and enforce supported model/effort/tool/permission constraints, documenting unsupported effort mappings ([card](tasks/04-core-mvp.md#p4-3)).
- [ ] P4.7 Define/version machine result/event output, preserve stdout/stderr and exit contracts, and document headless/CI use ([card](tasks/04-core-mvp.md#p4-7)).
- [ ] P4.8 Document/test inherited skills, MCP, instructions and context capabilities without bypassing route/agent restrictions ([card](tasks/04-core-mvp.md#p4-8)).
- [ ] P4.4 Verify a coding agent and constrained reviewer; refuse unsupported restrictions ([card](tasks/04-core-mvp.md#p4-4)).
- [ ] P4.5 Declare MVP platform support; build artifacts, setup diagnostics, sample agents/config, and usage documentation ([card](tasks/04-core-mvp.md#p4-5)).
- [ ] P4.6 Record repeated real-use results and close core MVP against G1–G5 and AC01–AC11, including all supporting Phase 2–4 tasks ([card](tasks/04-core-mvp.md#p4-6)).

## Phase 5 — Sequences

Detailed scope, dependencies and evidence: [Phase 5 cards](tasks/05-sequences.md).

- [ ] P5.1 Decide ordering, context, failure policy, metadata precedence, state schema, and resume interface ([card](tasks/05-sequences.md#p5-1)).
- [ ] P5.5 Define explicit trusted verification commands/gates and record agent success separately from verified success ([card](tasks/05-sequences.md#p5-5)).
- [ ] P5.2 Execute an ordered prompt folder through existing single-run policy ([card](tasks/05-sequences.md#p5-2)).
- [ ] P5.3 Persist step outcomes and handle cancellation/restart without silent replay ([card](tasks/05-sequences.md#p5-3)).
- [ ] P5.4 Validate on a real multi-step task and test recovery cases ([card](tasks/05-sequences.md#p5-4)).

## Phase 6 — Ralph

Detailed scope, dependencies and evidence: [Phase 6 cards](tasks/06-ralph.md).

- [ ] P6.1 Evaluate Rust Ralph examples; decide completion verification, limits, and recovery ([card](tasks/06-ralph.md#p6-1)).
- [ ] P6.2 Implement fresh-context iterations and durable filesystem progress ([card](tasks/06-ralph.md#p6-2)).
- [ ] P6.3 Enforce completion verification, iteration/time bounds, and cancellation ([card](tasks/06-ralph.md#p6-3)).
- [ ] P6.4 Demonstrate completion, bounded non-completion, and interrupted-run recovery ([card](tasks/06-ralph.md#p6-4)).

## Phase 7 — Native adapter increments

Detailed scope, dependencies and evidence: [Phase 7 cards](tasks/07-native-adapters.md).

Choose order from use; finish one adapter's contract before starting the next.

- [ ] P7.1 Choose first additional native CLI and record its supported integration/authentication ([card](tasks/07-native-adapters.md#p7-1)).
- [ ] P7.2 Claude adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-2)).
- [ ] P7.3 Codex adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-3)).
- [ ] P7.4 Grok adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-4)).
- [ ] P7.5 Gemini adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-5)).
- [ ] P7.6 Audit final capability/version/install coverage after all four committed adapters pass; incremental docs belong to each adapter task ([card](tasks/07-native-adapters.md#p7-6)).

## Phase 8 — Pi

Detailed scope, dependencies and evidence: [Phase 8 cards](tasks/08-pi.md).

- [ ] P8.1 Decide supported transport, agent/skill mapping, and permission handling ([card](tasks/08-pi.md#p8-1)).
- [ ] P8.2 Implement Pi behind the same route policy and capability checks ([card](tasks/08-pi.md#p8-2)).
- [ ] P8.3 Demonstrate Pi primary/specialized single-run parity and document capability limits; initial Pi milestone may precede sequences/Ralph ([card](tasks/08-pi.md#p8-3)).
- [ ] P8.4 Validate Pi sequence/Ralph parity and recovery after both P8.3 and P6.4; close full Phase 8 only after this follow-up ([card](tasks/08-pi.md#p8-4)).

## Phase 9 — Optional resource-aware features

Detailed scope, dependencies and evidence: [Phase 9 cards](tasks/09-resource-awareness.md).

Demand-driven, independently scoped additions; not blockers for earlier milestones.

- [ ] P9.1 Reassess ai-queue usage readers and introduce non-spending quota visibility where supported ([card](tasks/09-resource-awareness.md#p9-1)).
- [ ] P9.2 Decide whether optional allocation-aware selection adds value; keep it inside permitted routes ([card](tasks/09-resource-awareness.md#p9-2)).
- [ ] P9.3 Decide scheduling/storage/recovery semantics before adding prompt delays or a durable queue ([card](tasks/09-resource-awareness.md#p9-3)).
- [ ] P9.4 Validate unknown quota, cooldown, scheduling, and restart behavior per selected increment; quota/ranking and scheduling have conditional independent prerequisites, not a requirement to implement all optional scope ([card](tasks/09-resource-awareness.md#p9-4)).

## Feature candidates

Native session continuation/fork, richer history/export, workflow recipes/templates, hooks/plugins and diff summaries are considered but not committed tasks. Their promotion rules and current exclusions are in [docs/FEATURE_REVIEW.md](docs/FEATURE_REVIEW.md). No exhaustive feature-parity promise is made.

## Deferred decisions

See the owner phase and decision triggers in [DECISIONS.md](DECISIONS.md). Open choices do not block unrelated earlier work.

## Use observations and blockers

No Rust implementation runs recorded yet. The earlier ai-queue review passed 59 mocked tests; that does not validate this project's live integrations or current CLI compatibility.

When a milestone is used, add date, task, tested versions, route/model, outcome, manual intervention, direct-tool comparison, and resulting task/decision IDs here. Record external blockers with their next validation action.
