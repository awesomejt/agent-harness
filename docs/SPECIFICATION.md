# Specification

This is the full intended product scope. A goal listed here is not a claim that it is implemented. Delivery order and milestone boundaries live in [IMPLEMENTATION.md](IMPLEMENTATION.md); tasks live in [PROJECT.md](../PROJECT.md).

## Product and users

A developer uses one CLI to run existing coding agents in a chosen project, select permitted model routes, apply named agent definitions, and repeat work through explicit workflows. `agent-harness` is the primary project; `ai-queue` contributes reusable ideas and test cases.

Prioritize a useful first slice and learn from actual runs before designing every later feature. Keep each phase independently reviewable and usable. There is no fixed calendar commitment.

## Implementation constraints

Rust is the accepted harness language. Deliver `ah` as prebuilt platform binaries; no Python interpreter, Python bridge, or ai-queue package is a harness runtime dependency. External coding CLIs and LiteLLM retain their own prerequisites. Start with a single Cargo package and modular boundaries; the Phase 1 experiment validates concrete APIs, toolchain baseline, transport and dependencies. [DESIGN.md](DESIGN.md) is the proposed Rust blueprint, not existing code.

## Full goals

| ID | Goal | Success criterion | Delivery |
|---|---|---|---|
| G1 | Easy installation | Prebuilt binaries for declared OS/architecture targets; no Rust/Python toolchain required by binary users. Missing agent CLIs are explained separately. | Phase 2 onward |
| G2 | Real project execution | A single prompt can inspect/edit project files and run project tools through an existing runtime; progress, failure, and cancellation are visible. | Phase 2 |
| G3 | Explicit routing | All three modes enforce their permitted routes; selected model/route and fallback reason are observable. | Phases 2–3 |
| G4 | Harness-owned configuration | LiteLLM endpoint/model groups and managed OpenCode settings have one source of truth; project-only updates preserve user settings. | Phases 2–3 |
| G5 | Portable named agents | Markdown + YAML definitions map by name; primary and specialized roles carry supported model/tool/permission constraints. | Phase 4, expanded in 7–8 |
| G6 | Ordered execution | A folder of prompts runs in deterministic order with defined failure, context, and restart behavior. | Phase 5 |
| G7 | Bounded iterative execution | Ralph uses fresh agent context per iteration, durable filesystem state, an explicit completion signal, and limits. | Phase 6 |
| G8 | Multiple runtimes | OpenCode first; native Claude, Codex, Grok, Gemini and Pi added with documented capability differences. | Phases 7–8 |
| G9 | Optional resource-aware operation | Where supported, expose quota/cooldown information and optional scheduling without overriding mode policy. | Phase 9; demand-driven |

## Feature coverage and supporting contracts

The [feature landscape review](FEATURE_REVIEW.md) compares eight upstream projects and assigns F01–F26 to committed, backend-owned, candidate, or excluded scope. It supplements G1–G9 rather than claiming parity with every tool. [The documentation map](README.md) links the technical contracts and the phase responsible for finalizing each one.

Within existing goals, include inline/file/stdin prompt input; basic prerequisite diagnostics and a read-only resolved-plan/sync preview in Phase 2; versioned machine output and headless/CI guidance by Phase 4; and explicit verification gates in Phases 5–6. Show transient attempt outcomes initially and persist workflow records when resume arrives. Model-effort mapping is added only for supported adapters with documented handling of approximations.

Preserve dirty/untracked user changes and expose effective permissions. Do not automatically stash/reset/commit/roll back the project. Backend-owned skills, MCP, instructions, context management and compaction remain available only when their behavior is supported and consistent with harness routing/constraints. The harness does not implement replacement subsystems for them.

Native session continuation/fork, richer history/export, workflow recipes, hooks and plugins remain candidates for later decisions. Provider auto-installation, silent self-update, a workflow marketplace, automatic worktrees, parallel teams and a general DAG scheduler are not added to the roadmap by this review.

## Operational modes

- `local-only`: the model route is LiteLLM only. Never select a native cloud-subscription route, including on error.
- `cloud-only`: the model route is a configured native CLI route. Do not query LiteLLM, including for health/discovery.
- `local-first`: try LiteLLM first; on eligible failure use the explicitly configured native fallback. No implicit provider ranking.

The CLI mode is authoritative. Per-prompt overrides are later work and cannot silently relax an explicit invocation-level restriction.

`local-only` does not mean physically local or free: LiteLLM can route to OpenRouter and permitted subscriptions. Policy must restrict model routes, including runtime-internal choices; merely launching an allowed executable is insufficient. The same OpenCode executable may serve both routes.

Cloud subscription credentials remain owned by official tools. No credential scraping or proxying subscription traffic contrary to provider terms. Adding a provider requires verifying its supported integration and authentication path at that time.

## Execution and result contract

The working project is explicit or defaults visibly to the current directory. Coding runs retain changes in that project and respect applicable project instructions and backend permissions. Do not inherit ai-queue's temporary-directory, tools-disabled behavior as the coding default.

Show useful progress and a final outcome, including route, runtime, model, exit/failure information, and fallback attempts. Keep credentials out of arguments, logs, and persisted results. Define stable, distinct success, failed/rejected, known-cancelled, and uncertain exit statuses in Phase 2. Report uncertainty on stderr immediately. Phase 4 added opt-in versioned machine-readable results/events (`--output jsonl`, [D039](../DECISIONS.md#2026-11-03--d039-opt-in-version-1-machine-records-with-unchanged-exits)).

Primary and specialized execution must enforce supported constraints. Unsupported restrictions must be reported and the run refused rather than silently broadened. Do not promise identical capabilities across providers.

Fallback is a new execution attempt, not an assumption of resumable shared sessions. Before Phase 3 ships, distinguish pre-execution failures from ambiguous failures after tool actions. Do not automatically replay potentially applied work without an explicit recovery policy. Record attempts so users can see what happened.

## Configuration and agents

Configuration must grow to cover default mode, LiteLLM URL and environment-based key reference, model groups, runtime paths, native target/model, fallback target, and project sync. File format, location, and precedence are decided incrementally before their consumers ship.

Synced project configuration must never contain a literal LiteLLM key: retain an environment-variable reference supported by the backend, without resolving it into the generated file.

Project OpenCode sync must preserve unrelated settings, leave global config untouched, avoid partial writes, and detect conflicting generated output. `--no-sync` skips writes; it does not waive routing validation. Native cloud routes must neither write the OpenCode provider block nor accidentally inherit the managed LiteLLM route.

Canonical agents have a name, a description, a capacity (`primary`, `specialized` or `both`), a permission ceiling (`deny`, `read-only` or `trusted`), a tool list, optional route-specific models (`models.local`, `models.native`), an optional effort requirement, and a Markdown system-prompt body. Phase 4 fixed the schema and the OpenCode destinations ([D036](../DECISIONS.md#2026-11-03--d036-canonical-agent-schema-and-opencode-destinations)–[D038](../DECISIONS.md#2026-11-03--d038-directly-invoked-named-roles-with-intersected-runtime-rules)). [CONFIGURATION](CONFIGURATION.md#canonical-agents) owns the grammar. Backend modes such as OpenCode's `primary`/`subagent`/`all` are mapping details. Only default effort runs on OpenCode 2.2.5. Provider-specific filenames and permissions are verified when each later adapter is implemented.

## Workflow requirements

- Single: one task delegated to an existing runtime, potentially involving many internal tool turns.
- Sequence: deterministic folder ordering; stop/continue behavior, shared versus fresh context, and restart rules specified before Phase 5 implementation.
- Ralph: fresh context each iteration, filesystem-persisted progress, explicit completion verification, iteration limits, cancellation, and restart without silently rerunning uncertain work. Choose the completion protocol in Phase 6.

Every workflow uses the same route policy and agent constraints. A queue is not a substitute for sequence or Ralph semantics. No exactly-once guarantee for external side effects is assumed.

## First slice and core MVP

The first slice is G2 using OpenCode + LiteLLM in `local-only`, with minimal G1/G4 and sufficient progress/errors to use it. It does not wait for named agents, native fallback, sequences, or Ralph.

The core MVP adds all routing modes and named OpenCode agents (G1–G5). Sequences and Ralph remain committed product goals delivered as separate later milestones. This narrows the earlier MVP definition without dropping those features.

## Milestone acceptance matrix

Every row is required for core MVP; the first-slice column shows what must already work at Phase 2. These are acceptance checks for G1–G5 and supporting features, not additional product phases. The core MVP closes only after all rows and all Phase 2–4 tasks have evidence in PROJECT.md and holistic Phase 4 review P4.9 passes with no unresolved findings. Every phase similarly requires its explicit review before dependent work, as defined in PHASE_REVIEW.md.

| ID | Requirement | First usable slice (Phase 2) | Core MVP (Phase 4) / acceptance evidence | Tasks |
|---|---|---|---|---|
| AC01 | Real coding execution | One project task through OpenCode + LiteLLM; edits and project verification observed | Repeated primary tasks on supported routes; underlying runtime owns tool loop | P2.2, P2.6, P4.6 |
| AC02 | Route policy | Explicit local-only; reject unimplemented modes; never launch native fallback | All three modes, no LiteLLM discovery in cloud-only, validated inherited/helper choices | P2.4, P3.2, P3.4 |
| AC03 | Configured fallback | No fallback required | Deterministic eligible failure tries configured native OpenCode target; uncertain work never blindly replayed | P3.1, P3.3, P3.5 |
| AC04 | Configuration ownership | Minimal config, project sync/no-sync validation, environment key reference, conflict/global-preservation tests | Add model groups and native isolation; provider block remains project-only and secrets never serialized literally | P2.1, P2.3, P3.2, P3.3 |
| AC05 | Prompt input and project integrity | Inline/file/stdin inputs; reject ambiguity/empty prompt; dirty/untracked work preserved by harness setup/recovery | Same behavior with named agents and native routes; no automatic Git cleanup/commit/rollback | P2.2, P2.8, P4.4 |
| AC06 | Progress, outcomes and usage | Visible route/model/attempt, streamed activity, reported-or-unknown usage, meaningful exits including uncertainty | Versioned machine result/events, stdout/stderr separation and headless/CI tests | P2.1, P2.4, P4.7 |
| AC07 | Lifetime and permissions | Bounded cancellation/deadlines/cleanup; defined noninteractive permission behavior | Same guarantees for both routes and constrained roles; unsupported restrictions refused | P1.6, P1.3, P2.4, P4.3, P4.4 |
| AC08 | Named agents | Not required | Canonical Markdown + YAML, name-based OpenCode mapping, primary and specialized role with enforced supported restrictions/effort | P4.1, P4.2, P4.3, P4.4 |
| AC09 | Diagnostics and preview | Prerequisite/version diagnosis and read-only plan/sync preview; no writes or model turn | Supported capability reporting, actionable setup and conflict diagnostics | P2.7, P4.5 |
| AC10 | Distribution | Installable binary for one tested target and separate prerequisite instructions | Artifacts and smoke tests for every declared MVP target; no harness language toolchain for binary users | P2.5, P4.5 |
| AC11 | Backend capabilities and evidence | Validate project instructions and route-relevant behavior required for the run | Document inherited skills/MCP/context capabilities, version support and limits; complete live-use/contract tests | P1.3, P4.8, P4.6 |

Not required for core MVP: sequences, durable workflow resume, general harness verification gates, Ralph, additional native CLIs, Pi, quota/scheduling, native session continuation, plugins, recipes or worktree automation. Sequences/Ralph and additional runtimes retain their later committed phases; optional candidates retain their disposition in FEATURE_REVIEW.md. First-slice backend/manual verification is evidence, not a claim that general harness verification gates already exist.

## Nonfunctional requirements

- Keep policy testable independently of I/O; backend types must not decide allowed routes.
- Bound stream buffering, record sizes, execution/cancellation/cleanup waiting, and retries where supported. Choose numeric bounds at the consuming phase and test them rather than inventing unmeasured performance promises now.
- Validate project configuration before work; failed setup must not silently destroy unrelated settings or global content. Never store a literal key in generated config.
- Preserve run/attempt provenance and unknown metrics; separate backend execution, cleanup certainty and verification results. Provider text is not a structured success signal.
- Version external machine/state contracts when they ship. Record supported runtime/platform versions with evidence, not assumptions of universal portability.

## Boundaries

No custom coding-agent tool loop, model gateway replacement, cloud-subscription credential proxy, mandatory daemon, GUI, hosted multi-user service, or distributed scheduler is required. Parallel autonomous teams, automatic Git worktree management, and provider auto-installation are not commitments in this roadmap. Reconsider additions only from observed needs.

## Learning from use

After each usable phase, record representative tasks, runtime/model versions, route, outcome, manual interventions, setup friction, cancellation/recovery behavior, and observed latency. Record cost/usage only when actually reported. Compare with invoking the underlying tool directly. Capture actionable findings in PROJECT.md and resulting decisions in DECISIONS.md before expanding scope.
