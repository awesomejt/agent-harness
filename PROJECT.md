# Project tracker

Last updated: 2026-11-01. Status is maintained here; phase contracts are in [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Current state

- Active phase: 1 — integration experiment ready to start; no implementation started.
- Phase 0 review: PR #1 received 0 blockers, 2 concerns, and 2 nits; all four addressed. No critical/high findings; no re-review required under docs/GIT_WORKFLOW.md.
- Implementation: none yet.
- Direction: Rust CLI with prebuilt binaries; OpenCode first, LiteLLM route plus native route.
- Next implementation task: P1.1, a narrow OpenCode integration experiment, after the feature/technical-contract documentation review closes.
- Feature coverage: docs/FEATURE_REVIEW.md records eight upstream projects and F01–F26 dispositions; docs/README.md indexes technical contracts. No implementation has started.
- First usable milestone: end of Phase 2. Core MVP: end of Phase 4.
- Phase order is dependency-based, without calendar estimates. Phases 7–8 can follow Phase 4 independently of workflow expansion.

## Phase 0 — Scope and roadmap

- [x] P0.1 Draft complete goals, boundaries, and milestone success criteria.
- [x] P0.2 Separate first slice, core MVP, sequences, Ralph, and broader integrations.
- [x] P0.3 Record Rust direction, route/transport clarification, and deferred decisions.
- [x] P0.4 Capture reuse candidates and validation criteria without adopting them prematurely.
- [x] P0.5 Complete documentation consistency checks and required PR review (PR #1; four minor findings addressed).

- [x] P0.6 Compare upstream feature families and classify committed, backend-owned, candidate and excluded scope.
- [x] P0.7 Draft execution/configuration/workflow/testing/operations contracts and documentation index with phase-owned finalization.
- [ ] P0.8 Validate feature/task/doc traceability and complete PR review for the feature/contract pass.

## Phase 1 — Integration experiment

- [ ] P1.1 Create a minimal Rust package on a feature branch; select a nonconflicting package name and initial development target.
- [ ] P1.2 Exercise OpenCode ACP with a disposable project; compare native structured output if needed.
- [ ] P1.3 Define permission-request handling and its non-interactive default before the first live run; verify no implicit widening, LiteLLM model selection, project instructions, progress, cancellation, and child cleanup.
- [ ] P1.4 Evaluate a small reusable adapter/process dependency against direct SDK/runtime use; inspect license, release/API compatibility, and platform behavior.
- [ ] P1.5 Record tested versions, live evidence, selected transport/dependencies, and unresolved limitations.

## Phase 2 — First usable slice

- [ ] P2.1 Define minimal config, precedence, environment key reference, and exit conventions.
- [ ] P2.2 Implement `ah single` with `local-only`, project selection, model alias, visible resolved route, and unambiguous inline/file/stdin prompt input.
- [ ] P2.3 Implement project provider sync that preserves unrelated settings; test conflicts, interrupted writes, global-config preservation, absence of literal LiteLLM keys (use a sentinel secret), and `--no-sync` route validation.
- [ ] P2.4 Stream progress, identify attempts and reported usage, classify failures, handle deadlines/cancellation and headless permissions, and verify no cloud-native fallback.
- [ ] P2.5 Produce an initial platform binary with installation/setup instructions.
- [ ] P2.6 Use it for a real edit-and-test task; compare direct OpenCode and record friction before expanding.

- [ ] P2.7 Add basic prerequisite/version diagnostics and read-only resolved-plan/sync preview without model turns or writes; fix exact syntax before release.
- [ ] P2.8 Report dirty-worktree state and preserve pre-existing edits/untracked files; test failed/cancelled runs without automatic Git mutations.

## Phase 3 — Routing and fallback

- [ ] P3.1 Define eligible failures, retry limits, and partial-work recovery policy.
- [ ] P3.2 Add explicit native OpenCode target/model and cloud-only execution isolated from managed LiteLLM routing.
- [ ] P3.3 Add model-group references and configured local-first fallback.
- [ ] P3.4 Test all mode boundaries, discovery requests, inherited runtime settings, and uncertain outcomes.
- [ ] P3.5 Demonstrate each route and eligible fallback in use; record findings.

## Phase 4 — Agents and core MVP

- [ ] P4.1 Define/validate canonical YAML schema and actual OpenCode agent destinations.
- [ ] P4.2 Add name-based emission, collision handling, and `--agent` selection.
- [ ] P4.3 Implement primary/specialized execution and enforce supported model/effort/tool/permission constraints, documenting unsupported effort mappings.
- [ ] P4.4 Verify a coding agent and constrained reviewer; refuse unsupported restrictions.
- [ ] P4.5 Declare MVP platform support; build artifacts, setup diagnostics, sample agents/config, and usage documentation.
- [ ] P4.6 Record repeated real-use results and close core MVP against G1–G5.

- [ ] P4.7 Define/version machine result/event output, preserve stdout/stderr and exit contracts, and document headless/CI use.
- [ ] P4.8 Document/test inherited skills, MCP, instructions and context capabilities without bypassing route/agent restrictions.

## Phase 5 — Sequences

- [ ] P5.1 Decide ordering, context, failure policy, metadata precedence, state schema, and resume interface.
- [ ] P5.2 Execute an ordered prompt folder through existing single-run policy.
- [ ] P5.3 Persist step outcomes and handle cancellation/restart without silent replay.
- [ ] P5.4 Validate on a real multi-step task and test recovery cases.

- [ ] P5.5 Define explicit trusted verification commands/gates and record agent success separately from verified success.

## Phase 6 — Ralph

- [ ] P6.1 Evaluate Rust Ralph examples; decide completion verification, limits, and recovery.
- [ ] P6.2 Implement fresh-context iterations and durable filesystem progress.
- [ ] P6.3 Enforce completion verification, iteration/time bounds, and cancellation.
- [ ] P6.4 Demonstrate completion, bounded non-completion, and interrupted-run recovery.

## Phase 7 — Native adapter increments

Choose order from use; finish one adapter's contract before starting the next.

- [ ] P7.1 Choose first additional native CLI and record its supported integration/authentication.
- [ ] P7.2 Claude adapter: execution, events, constraints, named mapping, tests, and live example.
- [ ] P7.3 Codex adapter: execution, events, constraints, named mapping, tests, and live example.
- [ ] P7.4 Grok adapter: execution, events, constraints, named mapping, tests, and live example.
- [ ] P7.5 Gemini adapter: execution, events, constraints, named mapping, tests, and live example.
- [ ] P7.6 Maintain adapter capability/version matrix and installation instructions as each ships.

## Phase 8 — Pi

- [ ] P8.1 Decide supported transport, agent/skill mapping, and permission handling.
- [ ] P8.2 Implement Pi behind the same route policy and capability checks.
- [ ] P8.3 Demonstrate primary/specialized runs and supported sequence/Ralph parity when available.

## Phase 9 — Optional resource-aware features

Demand-driven, independently scoped additions; not blockers for earlier milestones.

- [ ] P9.1 Reassess ai-queue usage readers and introduce non-spending quota visibility where supported.
- [ ] P9.2 Decide whether optional allocation-aware selection adds value; keep it inside permitted routes.
- [ ] P9.3 Decide scheduling/storage/recovery semantics before adding prompt delays or a durable queue.
- [ ] P9.4 Validate unknown quota, cooldown, scheduling, and restart behavior for each increment delivered.

## Feature candidates

Native session continuation/fork, richer history/export, workflow recipes/templates, hooks/plugins and diff summaries are considered but not committed tasks. Their promotion rules and current exclusions are in [docs/FEATURE_REVIEW.md](docs/FEATURE_REVIEW.md). No exhaustive feature-parity promise is made.

## Deferred decisions

See the owner phase and decision triggers in [DECISIONS.md](DECISIONS.md). Open choices do not block unrelated earlier work.

## Use observations and blockers

No Rust implementation runs recorded yet. The earlier ai-queue review passed 59 mocked tests; that does not validate this project's live integrations or current CLI compatibility.

When a milestone is used, add date, task, tested versions, route/model, outcome, manual intervention, direct-tool comparison, and resulting task/decision IDs here. Record external blockers with their next validation action.
