# Implementation plan

[PROJECT.md](../PROJECT.md) owns task status. [SPECIFICATION.md](SPECIFICATION.md) owns goals. Phases below define order and acceptance evidence; later decisions are made at their phase boundary.

Recommended execution/PR order and cross-phase dependencies are in [PROJECT_PLAN.md](PROJECT_PLAN.md). Detailed task cards are in [tasks/README.md](../tasks/README.md); task status remains only in PROJECT.md. These cards refine the existing phases without fixing later implementation choices.

## Working method

Use small feature branches/PRs following [GIT_WORKFLOW.md](GIT_WORKFLOW.md). Split each phase into focused changes; a phase is not one large PR. Every implementation change carries appropriate tests and updates its task/decision records. Ship and use each usable milestone before broadening it. Review findings can reorder later work without redefining completed evidence.

## Phase 0 — Scope and roadmap

**Outcome:** a shared product charter, first slice, core MVP, and deferred-decision register.

**Exit evidence:** consistent repository docs; explicit goals, non-goals, phase dependencies, acceptance criteria, and actionable next tasks. Documentation authorship does not imply implementation exists.

Feature coverage is captured in [FEATURE_REVIEW.md](FEATURE_REVIEW.md). [The documentation map](README.md) identifies technical contracts and when concrete interfaces/schemas must replace deferred choices. The feature pass adds supporting tasks inside these phases without moving the first-slice or core-MVP boundaries. AC01–AC11 in SPECIFICATION.md are the core-MVP acceptance checklist; DESIGN.md and ARCHITECTURE.md provide the Rust blueprint and diagrams.

## Phase 1 — OpenCode integration experiment

**Depends on:** Phase 0. **Goals:** reduce uncertainty for G2/G3.

Build the smallest Rust experiment that connects to OpenCode in a disposable project. Evaluate ACP first against the native structured-output alternative. Compare direct SDK use with a small existing adapter/process library only where it saves work. Verify model selection, project rules, permission callbacks, streamed events, cancellation, child cleanup, and observable failures using LiteLLM when available.

**Exit evidence:** repeatable experiment/test output, exact tested versions, and a decision selecting the transport and minimum dependencies. If the configured LiteLLM endpoint is unavailable, report that limitation and resolve live validation before declaring the local integration proven. Do not build a general framework or a library benchmark suite.

**Decide here:** Cargo package name, initial development target, OpenCode transport, minimum config needs, Rust edition/MSRV, proposed module/type boundaries, permission handling (P1.6 fixes the non-interactive default before P1.2 live work; P1.3 validates behavior without implicit widening). Stable ACP versus native output is an experiment, not a preselected dependency.

## Phase 2 — First usable local coding slice

**Depends on:** Phase 1. **Goals:** G1/G2, initial G3/G4.

Implement `ah single` in a project through OpenCode configured to LiteLLM. Support explicit `--mode local-only`, a model alias, minimal config, safe project-level provider sync using an environment-variable reference rather than a literal key, and `--no-sync` with route validation. Reject unimplemented modes clearly. Include inline/file/stdin prompt input, basic prerequisite diagnostics and read-only plan/sync preview, streamed progress, attempt identity, understandable errors, deadlines/cancellation, and meaningful exit codes. Preserve dirty-worktree user changes. See EXECUTION.md and CONFIGURATION.md.

**Exit evidence:** from a prebuilt binary on the initial supported platform, complete a real small project change and its verification; preserve project/global configuration and verify a sentinel key value never appears in generated config; demonstrate LiteLLM-unavailable and cancellation behavior; prove forbidden native fallback is not invoked. Include setup and direct-OpenCode comparison notes. A text-only completion is insufficient.

**Decide here:** config format/location/precedence, exit conventions, managed-config ownership and conflict behavior, initial binary release mechanism. Ship a binary and instructions; expand the platform matrix later.

## Phase 3 — Dual-route single execution

**Depends on:** Phase 2. **Goals:** complete G3, extend G4.

Add native OpenCode execution for `cloud-only`, model-group references for LiteLLM, and a configured native fallback for `local-first`. Preserve LiteLLM's ownership of routing inside its route; the harness selects between permitted routes. Keep runtime selection separate from route selection.

**Exit evidence:** tests cover allowed and forbidden traffic for all modes, successful local execution, eligible fallback, no fallback on local-only, no LiteLLM discovery in cloud-only, and native selection unaffected by managed LiteLLM settings. Demonstrate deterministic pre-execution fallback and a refused/explicitly handled ambiguous failure after a possible tool action. Try both routes in actual use.

**Decide here:** eligible failures, retry bounds, partial-work recovery, fallback authentication/config isolation, model-group configuration. Do not replay coding side effects based solely on a timeout.

## Phase 4 — Named agents; core MVP

**Depends on:** Phase 3. **Goals:** G5; close G1–G5 MVP against AC01–AC11, including all supporting tasks in Phases 2–4.

Load canonical Markdown + YAML agents, map by name to OpenCode, add `--agent`, and support primary/specialized invocation with enforced supported constraints. Preserve user-owned agent files and show mapping conflicts. Complete setup diagnostics and release documentation for the declared MVP platforms, versioned machine result/events and headless/CI behavior. Document inherited skills/MCP/context capabilities and supported effort mapping without taking ownership of those backend subsystems.

**Exit evidence:** a primary coding task and a constrained review task use named definitions; prohibited writes/tools are denied; unsupported restrictions fail visibly. Adapter fixtures cover emitted config/definitions. Repeated real use demonstrates the dual-route workflow and identifies remaining friction. Publish installable artifacts for each declared supported target.

**Decide here:** exact agent schema and destinations, invocation semantics for specialized roles, compatibility reporting, MVP platform matrix. Broader adapter support is not a prerequisite for MVP.

## Phase 5 — Ordered prompt sequences

**Depends on:** Phase 4. **Goal:** G6.

Add ordered-folder execution using existing single-run policy and agent resolution. Add minimal durable step outcomes needed for restart and inspection, and explicit trusted verification gates with outcomes separate from agent execution. Finalize WORKFLOWS.md storage/recovery choices before implementation.

**Exit evidence:** a real multi-step task executes in documented order; failed/cancelled steps stop or continue according to explicit policy; restart does not silently repeat completed or uncertain side effects. Test ordering and state recovery.

**Decide here:** ordering, context sharing, failure policy, persisted schema, resume interface, and optional per-prompt metadata/precedence. Do not introduce scheduling to implement a sequence.

## Phase 6 — Bounded Ralph loops

**Depends on:** Phase 5, reusing durable execution records. **Goal:** G7.

Add a thin outer loop with fresh context per iteration, filesystem progress, a verified completion signal, and iteration/time limits. Study existing Rust Ralph implementations before writing loop mechanics.

**Exit evidence:** a real task reaches verified completion; a non-completing task stops at its bound; cancellation/restart and false completion are covered. Persist enough evidence to explain each iteration and recovery choice.

**Decide here:** completion protocol, verification command rules, limits, budget handling where measurable, and recovery semantics. Neither a clean child exit nor model prose alone automatically proves task completion.

## Phase 7 — Additional native CLIs

**Depends on:** Phase 4; may run independently of Phases 5–6. **Goal:** extend G8/G5.

Choose the first target from observed needs, then deliver Claude, Codex, Grok, and Gemini one adapter at a time. Each adapter must cover official authentication, runtime launch, events, model selection, cancellation, constraints, and name-based agent mapping. Verify provider integration rules at implementation time.

**Exit evidence per adapter:** capability matrix, fixtures, lifecycle/policy tests, one live project task, and docs. Unsupported features are explicit. No single milestone must wait for all four providers.

**Decide per adapter:** ACP/native interface, version range, permission mapping, provider-specific setup. Do not bake a speculative common API around every provider.

## Phase 8 — Pi and portability

**Depends on:** Phase 4; sequence/Ralph parity depends on Phases 5–6. **Goal:** extend G8/G5.

Add Pi as an alternative runtime using the same policy boundary. Evaluate its supported integration and agent/skill mapping at that time.

**Exit evidence:** P8.3 delivers primary/specialized single-run tasks, permitted route enforcement and documented capability limits. P8.4 verifies sequence/Ralph parity after P6.4; initial Pi use does not wait for those workflows, but full Phase 8 closeout includes this follow-up.

**Decide here:** Pi transport, definition mapping, context and permission differences. Do not silently convert restrictions into advisory prompt text.

## Phase 9 — Optional quota and scheduling increments

**Depends on:** a relevant completed native adapter from Phase 7 for native quota work; Phase 5 for queued execution state. Quota/ranking and scheduling are independent demand-gated increments; full Phase 7 completion is not required. **Goal:** G9.

Revisit ai-queue's usage readers, cooldown logic, prompt delays, and queue behavior as demand appears. Deliver read-only usage visibility before allocation-aware selection; deliver scheduling separately. These are not MVP or full workflow blockers.

**Exit evidence per increment:** limits are measured rather than guessed, unavailable usage stays unknown, scheduling/recovery behavior is explicit, and mode restrictions remain authoritative. No credential scraping or spending prompts for quota discovery by default.

**Decide here:** provider support, freshness policy, optional ranking, storage, scheduling syntax, and recovery guarantees. A daemon is not assumed.

## Phase closeout

For each phase: run appropriate checks, record the usable example and limitations, complete PR review, update PROJECT.md, and append decisions with evidence. An unchecked task or unavailable external dependency remains visible; do not mark a milestone complete from mocked tests alone when live evidence is required.
