# Project tracker

Last updated: 2026-11-02. Status is maintained here; phase contracts are in [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md).

## Current state

- Active phase: 2 — first usable slice. Phase 1 P1.7 is accepted after [PR #13](https://github.com/awesomejt/agent-harness/pull/13) merged; all six review findings are resolved/verified in the [report](docs/reviews/phase-01.md).
- Active implementation task/PR: P2.4 on `feature/02/p2-4-progress-supervision`; implementation/evidence verified, required PR review and merge pending. Proposed completion is effective on merge; next: P2.7 diagnostics/preview, then P2.8 dirty-project preservation. Default work-in-progress limit: one focused task/PR.
- Phase 0 holistic review P0.13: pass recorded in [review report](docs/reviews/phase-00.md), effective on PR #5 merge. P1.5 selects ACP protocol 1, the tested SDK/Tokio stack and Rust 1.88 baseline ([D023](DECISIONS.md#2026-11-02--d023-select-acp-and-the-tested-rust-integration-boundaries)); [acceptance preparation](docs/evidence/p1-5-integration-acceptance.md) and [dependency inventory](docs/evidence/p1-5-dependencies.md) feed P1.7. Production adapter dependencies enter with Phase 2 consumers.
- External prerequisites (2026-11-01): corrected API base `http://litellm:4000/v1`, supplied by the user, supports authenticated discovery and a live ACP prompt using the existing `macmini-qwen3-coder-30b` alias. The prior localhost blocker described a different endpoint. Credential source is `.zshrc`; values are not recorded. Remote server version remains unreported. See [live P1.2 evidence](docs/evidence/p1-2-live-acp.md).
- Remaining implementation/review backlog after P2.4 merge: 48 tasks across Phases 1–9; Phase 9 increments remain demand-gated.
- Phase 0 PR #1 review: received 0 blockers, 2 concerns, and 2 nits; all four addressed. No critical/high findings; no re-review required under docs/GIT_WORKFLOW.md.
- Implementation: Rust package with strict config/input validation, `ah single` local-only ACP coding adapter and permission policy. Production uses the selected SDK/Tokio stack on Rust 1.88, with isolated effective routing, exact allow-once grants and bounded macOS process-group cleanup. Managed project transactions, progress/usage reporting, bounded cooperative cancellation and output supervision are verified; preview, dirty-project reporting and release remain open. P2.4 records a live uncertain terminal after observed edit/test effects, with no replay/fallback.
- Direction: Rust CLI with prebuilt binaries; OpenCode first, LiteLLM route plus native route.
- Execution plan: [docs/PROJECT_PLAN.md](docs/PROJECT_PLAN.md); per-task dependencies, boundaries and evidence: [tasks/README.md](tasks/README.md). Feature/contract review (PR #2) and Rust architecture/alignment review (PR #3) are complete; task-planning review (PR #4) is complete: 0 blockers, 1 concern and 2 nits addressed; explicit holistic phase-review gates are recorded in PR #5 (two Grok reviews; all findings resolved).
- Feature coverage: docs/FEATURE_REVIEW.md records eight upstream projects and F01–F26 dispositions; docs/README.md indexes technical contracts. P1.1 introduces the minimal Rust scaffold.
- First usable milestone: end of Phase 2. Core MVP: end of Phase 4.
- Task IDs are stable references, not execution order. Every phase ends with a holistic phase-review task; evidence-preparation tasks do not close a phase. Dependent phases wait for an accepted review with no unresolved findings.
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
- [x] P0.13 Phase review: scope/design/plan baseline assessed; ten findings resolved/verified, [report accepted on PR #5 merge](docs/reviews/phase-00.md), before P1.1 starts ([card](tasks/00-scope.md#p0-13)).

## Phase 1 — Integration experiment

Detailed scope, dependencies and evidence: [Phase 1 cards](tasks/01-integration.md).

- [x] P1.1 Create a minimal Rust package; select package name, edition/MSRV and initial target. Proposed completion on [PR #6](https://github.com/awesomejt/agent-harness/pull/6) merge; [evidence](docs/evidence/p1-1-rust-scaffold.md), [D019](DECISIONS.md#2026-11-01--d019-minimal-rust-scaffold-baseline).
- [x] P1.6 Define and test permission-request policy/noninteractive behavior before the first live integration run. Completion effective on [PR #7](https://github.com/awesomejt/agent-harness/pull/7) merge; [D020](DECISIONS.md#2026-11-01--d020-fail-closed-experiment-permissions), [evidence](docs/evidence/p1-6-permission-policy.md), [card](tasks/01-integration.md#p1-6).
- [x] P1.2 Exercise OpenCode ACP with a disposable project; compare native structured output if needed ([card](tasks/01-integration.md#p1-2)). Live discovery, effective deny-all/tool-disable preflight, session/model selection, streamed text and `end_turn` marker passed against the supplied LiteLLM host. Completion effective on [PR #9](https://github.com/awesomejt/agent-harness/pull/9) merge ([evidence](docs/evidence/p1-2-live-acp.md)); P1.3 supplies the subsequent instruction-loading/callback/lifecycle evidence below.
- [x] P1.4 Evaluate a small reusable adapter/process dependency against direct SDK/runtime use; inspect license, release/API compatibility, and platform behavior ([card](tasks/01-integration.md#p1-4)). Completion effective on [PR #10](https://github.com/awesomejt/agent-harness/pull/10) merge; [pinned evidence](docs/evidence/p1-4-dependency-evaluation.md), [D021](DECISIONS.md#2026-11-01--d021-keep-process-policy-owned-evaluate-sdk-wire-reuse). No production dependency adopted; P1.3 evaluates SDK wire reuse below and P1.5 finalizes adoption.
- [x] P1.3 Verify no implicit widening, actual LiteLLM alias selection, project instructions, permission denial callbacks, streamed progress, cancellation, unavailable-service failure and child/descendant cleanup ([card](tasks/01-integration.md#p1-3)). Completion effective on [PR #11](https://github.com/awesomejt/agent-harness/pull/11) merge; [Rust/live/fake-child evidence](docs/evidence/p1-3-lifecycle.md), [D022](DECISIONS.md#2026-11-02--d022-validate-sdk-wire-reuse-in-an-isolated-lifecycle-experiment). macOS-only experiment; P1.5 selection follows below, and P1.7 review remains open.
- [x] P1.5 Record tested versions, live evidence, selected transport/dependencies, validated Rust module/type boundaries, and unresolved limitations ([card](tasks/01-integration.md#p1-5)). Completion effective on [PR #12](https://github.com/awesomejt/agent-harness/pull/12) merge; [acceptance preparation](docs/evidence/p1-5-integration-acceptance.md), [dependency/license inventory](docs/evidence/p1-5-dependencies.md), D023. P1.7 still gates phase exit.
- [x] P1.7 Phase review: integrated Phase 1 scope assessed; findings resolved/verified in [review report](docs/reviews/phase-01.md). Proposed acceptance on [PR #13](https://github.com/awesomejt/agent-harness/pull/13) merge; dependent work waits for that merge ([card](tasks/01-integration.md#p1-7)).

## Phase 2 — First usable slice

Detailed scope, dependencies and evidence: [Phase 2 cards](tasks/02-first-slice.md).

- [x] P2.1 Define minimal config, precedence, environment key reference, and exit conventions; completion effective on [PR #15](https://github.com/awesomejt/agent-harness/pull/15) merge ([card](tasks/02-first-slice.md#p2-1), [evidence](docs/evidence/p2-1-config-contract.md), D024).
- [x] P2.3 Implement project provider sync and ownership transactions; preserve unrelated settings and verify conflicts, interrupted/stale writes, secret absence and no-sync/effective routing. Completion effective on [PR #16](https://github.com/awesomejt/agent-harness/pull/16) merge; [evidence](docs/evidence/p2-3-managed-config.md), [card](tasks/02-first-slice.md#p2-3).
- [x] P2.2 Implement `ah single` local-only coding run with inline/file/stdin, effective route/permission checks and bounded cleanup. Controlled runtime read/edit/shell/external access plus live LiteLLM code fix and independent test passed; completion effective on [PR #17](https://github.com/awesomejt/agent-harness/pull/17) merge ([evidence](docs/evidence/p2-2-local-only-run.md), [D026](DECISIONS.md#2026-11-02--d026-isolated-first-slice-acp-execution-and-exact-coding-grants), [card](tasks/02-first-slice.md#p2-2)).
- [x] P2.4 Stream progress, identify attempts and source-attributed usage or unknown, classify outcomes, handle bounded cancellation/cleanup and headless permissions with no cloud-native fallback. Completion effective on task PR merge; [evidence](docs/evidence/p2-4-progress-supervision.md), D027, [card](tasks/02-first-slice.md#p2-4).
- [ ] P2.7 Add basic prerequisite/version diagnostics and read-only resolved-plan/sync preview without model turns or writes; fix exact syntax before release ([card](tasks/02-first-slice.md#p2-7)).
- [ ] P2.8 Report dirty-worktree state and preserve pre-existing edits/untracked files; test failed/cancelled runs without automatic Git mutations ([card](tasks/02-first-slice.md#p2-8)).
- [ ] P2.5 Produce an initial platform binary with installation/setup instructions ([card](tasks/02-first-slice.md#p2-5)).
- [ ] P2.6 Use it for a real edit-and-test task; compare direct OpenCode and record friction before expanding ([card](tasks/02-first-slice.md#p2-6)).
- [ ] P2.9 Phase review: holistically assess all Phase 2 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/02-first-slice.md#p2-9)).

## Phase 3 — Routing and fallback

Detailed scope, dependencies and evidence: [Phase 3 cards](tasks/03-routing.md).

- [ ] P3.1 Define eligible failures, retry limits, and partial-work recovery policy ([card](tasks/03-routing.md#p3-1)).
- [ ] P3.2 Add explicit native OpenCode target/model and cloud-only execution isolated from managed LiteLLM routing ([card](tasks/03-routing.md#p3-2)).
- [ ] P3.3 Add model-group references with explicit proxy-configuration handoff/validation and configured local-first fallback ([card](tasks/03-routing.md#p3-3)).
- [ ] P3.4 Test all mode boundaries, discovery requests, inherited runtime settings, and uncertain outcomes ([card](tasks/03-routing.md#p3-4)).
- [ ] P3.5 Demonstrate each route and eligible fallback in use; record findings ([card](tasks/03-routing.md#p3-5)).
- [ ] P3.6 Phase review: holistically assess all Phase 3 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/03-routing.md#p3-6)).

## Phase 4 — Agents and core MVP

Detailed scope, dependencies and evidence: [Phase 4 cards](tasks/04-core-mvp.md).

- [ ] P4.1 Define/validate canonical YAML schema and actual OpenCode agent destinations ([card](tasks/04-core-mvp.md#p4-1)).
- [ ] P4.2 Add name-based emission, collision handling, and `--agent` selection ([card](tasks/04-core-mvp.md#p4-2)).
- [ ] P4.3 Implement primary/specialized execution and enforce supported model/effort/tool/permission constraints, documenting unsupported effort mappings ([card](tasks/04-core-mvp.md#p4-3)).
- [ ] P4.7 Define/version machine result/event output, preserve stdout/stderr and exit contracts, and document headless/CI use ([card](tasks/04-core-mvp.md#p4-7)).
- [ ] P4.8 Document/test inherited skills, MCP, instructions and context capabilities without bypassing route/agent restrictions ([card](tasks/04-core-mvp.md#p4-8)).
- [ ] P4.4 Verify a coding agent and constrained reviewer; refuse unsupported restrictions ([card](tasks/04-core-mvp.md#p4-4)).
- [ ] P4.5 Declare MVP platform support; build artifacts, setup diagnostics, sample agents/config, and usage documentation ([card](tasks/04-core-mvp.md#p4-5)).
- [ ] P4.6 Record repeated real-use results and prepare core MVP acceptance against G1–G5 and AC01–AC11, including all supporting Phase 2–4 tasks ([card](tasks/04-core-mvp.md#p4-6)).
- [ ] P4.9 Phase review: holistically assess all Phase 4 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/04-core-mvp.md#p4-9)).

## Phase 5 — Sequences

Detailed scope, dependencies and evidence: [Phase 5 cards](tasks/05-sequences.md).

- [ ] P5.1 Decide ordering, context, failure policy, metadata precedence, state schema, and resume interface ([card](tasks/05-sequences.md#p5-1)).
- [ ] P5.5 Define explicit trusted verification commands/gates and record agent success separately from verified success ([card](tasks/05-sequences.md#p5-5)).
- [ ] P5.2 Execute an ordered prompt folder through existing single-run policy ([card](tasks/05-sequences.md#p5-2)).
- [ ] P5.3 Persist step outcomes and handle cancellation/restart without silent replay ([card](tasks/05-sequences.md#p5-3)).
- [ ] P5.4 Validate on a real multi-step task and test recovery cases ([card](tasks/05-sequences.md#p5-4)).
- [ ] P5.6 Phase review: holistically assess all Phase 5 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/05-sequences.md#p5-6)).

## Phase 6 — Ralph

Detailed scope, dependencies and evidence: [Phase 6 cards](tasks/06-ralph.md).

- [ ] P6.1 Evaluate Rust Ralph examples; decide completion verification, limits, and recovery ([card](tasks/06-ralph.md#p6-1)).
- [ ] P6.2 Implement fresh-context iterations and durable filesystem progress ([card](tasks/06-ralph.md#p6-2)).
- [ ] P6.3 Enforce completion verification, iteration/time bounds, and cancellation ([card](tasks/06-ralph.md#p6-3)).
- [ ] P6.4 Demonstrate completion, bounded non-completion, and interrupted-run recovery ([card](tasks/06-ralph.md#p6-4)).
- [ ] P6.5 Phase review: holistically assess all Phase 6 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/06-ralph.md#p6-5)).

## Phase 7 — Native adapter increments

Detailed scope, dependencies and evidence: [Phase 7 cards](tasks/07-native-adapters.md).

Choose order from use; finish one adapter's contract before starting the next.

- [ ] P7.1 Choose first additional native CLI and record its supported integration/authentication ([card](tasks/07-native-adapters.md#p7-1)).
- [ ] P7.2 Claude adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-2)).
- [ ] P7.3 Codex adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-3)).
- [ ] P7.4 Grok adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-4)).
- [ ] P7.5 Gemini adapter: execution, events, constraints, named mapping, tests, and live example ([card](tasks/07-native-adapters.md#p7-5)).
- [ ] P7.6 Audit final capability/version/install coverage after all four committed adapters pass; incremental docs belong to each adapter task ([card](tasks/07-native-adapters.md#p7-6)).
- [ ] P7.7 Phase review: holistically assess all Phase 7 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/07-native-adapters.md#p7-7)).

## Phase 8 — Pi

Detailed scope, dependencies and evidence: [Phase 8 cards](tasks/08-pi.md).

- [ ] P8.1 Decide supported transport, agent/skill mapping, and permission handling ([card](tasks/08-pi.md#p8-1)).
- [ ] P8.2 Implement Pi behind the same route policy and capability checks ([card](tasks/08-pi.md#p8-2)).
- [ ] P8.3 Demonstrate Pi primary/specialized single-run parity and document capability limits; initial Pi milestone may precede sequences/Ralph ([card](tasks/08-pi.md#p8-3)).
- [ ] P8.4 Validate Pi sequence/Ralph parity and recovery after both P8.3 and P6.5; prepare full Phase 8 evidence after this follow-up; P8.5 closes the phase ([card](tasks/08-pi.md#p8-4)).
- [ ] P8.5 Phase review: holistically assess all Phase 8 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/08-pi.md#p8-5)).

## Phase 9 — Optional resource-aware features

Detailed scope, dependencies and evidence: [Phase 9 cards](tasks/09-resource-awareness.md).

Demand-driven, independently scoped additions; not blockers for earlier milestones.

- [ ] P9.1 Reassess ai-queue usage readers and introduce non-spending quota visibility where supported ([card](tasks/09-resource-awareness.md#p9-1)).
- [ ] P9.2 Decide whether optional allocation-aware selection adds value; keep it inside permitted routes ([card](tasks/09-resource-awareness.md#p9-2)).
- [ ] P9.3 Decide scheduling/storage/recovery semantics before adding prompt delays or a durable queue ([card](tasks/09-resource-awareness.md#p9-3)).
- [ ] P9.4 Validate unknown quota, cooldown, scheduling, and restart behavior per selected increment; quota/ranking and scheduling have conditional independent prerequisites, not a requirement to implement all optional scope ([card](tasks/09-resource-awareness.md#p9-4)).
- [ ] P9.5 Phase review: holistically assess all Phase 9 deliverables, resolve/verify findings, and accept the review before phase exit or dependent work ([card](tasks/09-resource-awareness.md#p9-5)).

## Feature candidates

Native session continuation/fork, richer history/export, workflow recipes/templates, hooks/plugins and diff summaries are considered but not committed tasks. Their promotion rules and current exclusions are in [docs/FEATURE_REVIEW.md](docs/FEATURE_REVIEW.md). No exhaustive feature-parity promise is made.

## Deferred decisions

See the owner phase and decision triggers in [DECISIONS.md](DECISIONS.md). Open choices do not block unrelated earlier work.

## Use observations and blockers

2026-11-01 — P1.1: Rust 1.85.0/Cargo 1.85.0 on `aarch64-apple-darwin`; debug/release builds, formatting, Clippy and four CLI integration tests plus one Unix unit test passed. Release binary reports `ah 0.1.0`. No runtime/model call; no direct-tool comparison applies to this scaffold. See [repeatable evidence](docs/evidence/p1-1-rust-scaffold.md). Rust was absent and installed with rustup without modifying shell startup files. Next: P1.6 before live execution. The earlier ai-queue review passed 59 mocked tests; that does not validate this project's live integrations or current CLI compatibility.

When a milestone is used, add date, task, tested versions, route/model, outcome, manual intervention, direct-tool comparison, and resulting task/decision IDs here. Record external blockers with their next validation action.

2026-11-01 — P1.2 partial: OpenCode 1.18.30 on Darwin arm64 completed ACP protocol-1 initialize and session/new with a disposable HOME/project and synthetic, unreachable provider. Effective config and session model were checked; no prompt/model turn or grant was sent. Existing LiteLLM discovery failed with both configured keys (`no_db_connection`) and without authentication (HTTP 500). No proxy reconfiguration/restart or credential changes. Direct structured-output comparison is not yet warranted; no transport is selected. Next action is restore existing alias access and complete permission-enforcement preflight before live prompts. [Repeatable probe and observations](docs/evidence/p1-2-opencode-transport.md). P1.2 remains unchecked; dependent tasks stay gated.

2026-11-01 — P1.2 live continuation: user corrected the API base to `http://litellm:4000/v1`; `.zshrc` supplies the API key. OpenCode 1.18.30 / Python 3.14.7 on Darwin arm64 used existing alias `macmini-qwen3-coder-30b`. Effective-agent inspection exposed an appended tool-output-directory allow; an exact denial removes it before prompting. First instruction-dependent marker assertion failed after streamed text/`end_turn`; the second explicit-marker prompt passed but retained the project marker rule; the final isolated rerun removed `AGENTS.md` and passed with four text chunks and `end_turn`. No tools/grants or coding edits; direct child reaped. No structured-native comparison was warranted. Follow-ups: P1.4 reuse decision, P1.3 project-instruction conformance, effective routing, permission callbacks and lifecycle. [Live evidence](docs/evidence/p1-2-live-acp.md).

2026-11-01 — P1.4: inspected published ACP SDK 3.6.0 and cli-stream 0.5.0 sources/manifests, hashes and licenses on macOS arm64. Retain direct process supervision; reject both convenience launchers for inherited-environment policy gaps. Prefer SDK protocol reuse over caller-owned I/O for P1.3, conditional on Rust 1.88/runtime/compatibility evidence. No candidate compilation or model turn; unchanged OpenCode 1.18.30 no-prompt probe and baseline Rust checks passed. [Evidence](docs/evidence/p1-4-dependency-evaluation.md). Next: P1.3; Phase 1 stays open.

2026-11-02 — P1.7: holistic Phase 1 review ([PR #13](https://github.com/awesomejt/agent-harness/pull/13), [report](docs/reviews/phase-01.md)). Rust/Cargo 1.88.0, OpenCode 1.18.30, Python 3.14.7 on macOS 27.0.1 arm64: root 11 tests/release smoke, locked experiment checks, seventeen adversarial child cases and all five runtime-stub/unavailable scenarios pass. Fresh live text/instruction probes via `http://litellm:4000/v1` / `macmini-qwen3-coder-30b` pass with actual primary/helper alias, instruction loading and cleanup confirmed; merged P1.3 supplies live denial/cancellation evidence. Three holistic findings plus Grok's one concern/two nits resolved and verified. No proxy/config changes or coding grants; no production/direct-tool coding comparison yet (P2.6). Clarified P2.1/P2.2 permissions/cleanup prerequisites, refreshed validation/status records, and preserved platform/shutdown/license limitations. Acceptance takes effect on PR merge; P2.1 is next.

2026-11-02 — P2.1: fixed strict project JSON/precedence, explicit prompt sources, read-only preview semantics, permission profiles, deadlines and distinct exits in D024. Rust 1.88.0/macOS 27.0.1 arm64: all 27 root tests, format/Clippy/release smoke, locked experiment checks, 17 adversarial child cases and five OpenCode 1.18.30 local-stub/unavailable regressions passed. Independent review found four input/trust issues; all resolved and verified. PR #15 Grok review found 0 blockers, 1 concern and 2 nits; safe config-file open, canonical URL validation and exact negative-fixture errors resolve all three, with post-fix verification. Only explicit invocation may authorize trusted host tools. No live model, config writes or production coding run; direct-tool comparison remains P2.6. [Evidence](docs/evidence/p2-1-config-contract.md). Next after PR merge: P2.3.

2026-11-02 — P2.3: project-only routing planner, ownership receipts, byte-preserving strict JSON edits, stale-plan/lock checks and atomic per-file replacement. Rust 1.88.0/macOS arm64: 34 root tests, format and Clippy pass. Seven transaction tests include manual/stale/interrupted conflicts, inactive provider preservation, file modes, outside sentinel preservation and global-path code inspection, no-sync/effective routing, malformed agents, symlink/FIFO refusal and secret absence. Independent review findings corrected and documented. No live model or runtime launch; P2.2 still owns environment/permission enforcement. [Evidence](docs/evidence/p2-3-managed-config.md), [D025](DECISIONS.md#2026-11-02--d025-project-routing-ownership-and-fail-closed-transactions). PR #16 initial Grok review: 0 blockers, 2 concerns and 2 nits, all addressed; follow-up review confirms all fixes with 0 blockers/concerns and 1 diagnostics nit, corrected and verified. Completion effective on merge; next P2.2.

2026-11-02 — P2.2: implemented the local-only single-run adapter with isolated effective-config/agent preflight, exact request-bound coding grants, managed project apply and bounded macOS cleanup. Controlled OpenCode read/edit/bash and external-directory checks passed (six grants); a fresh live LiteLLM trial fixed the arithmetic function and passed runtime/independent tests (four grants, seven matching-alias requests, end_turn/cleanup, exit 0). An earlier separate live trial ended uncertain (exit 4); no replay/fallback or successful-edit claim for that trial. [Evidence](docs/evidence/p2-2-local-only-run.md) records friction and limits. Next after required PR review/merge: P2.4 progress/outcome/supervision hardening.

P2.2 review closeout — PR #17 completed three Grok reviews. Initial concern/three nits and the follow-up omitted-metadata concern were corrected and verified; the final review has 0 blockers/concerns, with metadata/count documentation nits corrected. Final checks: 37 Rust tests, 38 CLI cases plus matching no-sync repeat, format/locked Clippy, locked experiment check and installed OpenCode controlled read/edit/shell/external-access verification pass. Live coding evidence remains as recorded above. Acceptance is effective on PR #17 merge; no further review is required for documentation nits.
