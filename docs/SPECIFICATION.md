# Specification

This is the full intended product scope. A goal listed here is not a claim that it is implemented. Delivery order and milestone boundaries live in [IMPLEMENTATION.md](IMPLEMENTATION.md); tasks live in [PROJECT.md](../PROJECT.md).

## Product and users

A developer uses one CLI to run existing coding agents in a chosen project, select permitted model routes, apply named agent definitions, and repeat work through explicit workflows. `agent-harness` is the primary project; `ai-queue` contributes reusable ideas and test cases.

Prioritize a useful first slice and learn from actual runs before designing every later feature. Keep each phase independently reviewable and usable. There is no fixed calendar commitment.

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

## Operational modes

- `local-only`: the model route is LiteLLM only. Never select a native cloud-subscription route, including on error.
- `cloud-only`: the model route is a configured native CLI route. Do not query LiteLLM, including for health/discovery.
- `local-first`: try LiteLLM first; on eligible failure use the explicitly configured native fallback. No implicit provider ranking.

The CLI mode is authoritative. Per-prompt overrides are later work and cannot silently relax an explicit invocation-level restriction.

`local-only` does not mean physically local or free: LiteLLM can route to OpenRouter and permitted subscriptions. Policy must restrict model routes, including runtime-internal choices; merely launching an allowed executable is insufficient. The same OpenCode executable may serve both routes.

Cloud subscription credentials remain owned by official tools. No credential scraping or proxying subscription traffic contrary to provider terms. Adding a provider requires verifying its supported integration and authentication path at that time.

## Execution and result contract

The working project is explicit or defaults visibly to the current directory. Coding runs retain changes in that project and respect applicable project instructions and backend permissions. Do not inherit ai-queue's temporary-directory, tools-disabled behavior as the coding default.

Show useful progress and a final outcome, including route, runtime, model, exit/failure information, and fallback attempts. Keep credentials out of arguments, logs, and persisted results. Define stable success/failure/cancellation exit behavior in Phase 2; machine-readable output can evolve later.

Primary and specialized execution must enforce supported constraints. Unsupported restrictions must be reported and the run refused rather than silently broadened. Do not promise identical capabilities across providers.

Fallback is a new execution attempt, not an assumption of resumable shared sessions. Before Phase 3 ships, distinguish pre-execution failures from ambiguous failures after tool actions. Do not automatically replay potentially applied work without an explicit recovery policy. Record attempts so users can see what happened.

## Configuration and agents

Configuration must grow to cover default mode, LiteLLM URL and environment-based key reference, model groups, runtime paths, native target/model, fallback target, and project sync. File format, location, and precedence are decided incrementally before their consumers ship.

Synced project configuration must never contain a literal LiteLLM key: retain an environment-variable reference supported by the backend, without resolving it into the generated file.

Project OpenCode sync must preserve unrelated settings, leave global config untouched, avoid partial writes, and detect conflicting generated output. `--no-sync` skips writes; it does not waive routing validation. Native cloud routes must neither write the OpenCode provider block nor accidentally inherit the managed LiteLLM route.

Canonical agents have a name, description, role (`primary`, `subagent`, or `all`), optional model alias, tool/permission constraints, and a Markdown system-prompt body. Validate the exact schema and backend destinations in Phase 4. Provider-specific filenames and permissions are verified when each adapter is implemented.

## Workflow requirements

- Single: one task delegated to an existing runtime, potentially involving many internal tool turns.
- Sequence: deterministic folder ordering; stop/continue behavior, shared versus fresh context, and restart rules specified before Phase 5 implementation.
- Ralph: fresh context each iteration, filesystem-persisted progress, explicit completion verification, iteration limits, cancellation, and restart without silently rerunning uncertain work. Choose the completion protocol in Phase 6.

Every workflow uses the same route policy and agent constraints. A queue is not a substitute for sequence or Ralph semantics. No exactly-once guarantee for external side effects is assumed.

## First slice and core MVP

The first slice is G2 using OpenCode + LiteLLM in `local-only`, with minimal G1/G4 and sufficient progress/errors to use it. It does not wait for named agents, native fallback, sequences, or Ralph.

The core MVP adds all routing modes and named OpenCode agents (G1–G5). Sequences and Ralph remain committed product goals delivered as separate later milestones. This narrows the earlier MVP definition without dropping those features.

## Boundaries

No custom coding-agent tool loop, model gateway replacement, cloud-subscription credential proxy, mandatory daemon, GUI, hosted multi-user service, or distributed scheduler is required. Parallel autonomous teams, automatic Git worktree management, and provider auto-installation are not commitments in this roadmap. Reconsider additions only from observed needs.

## Learning from use

After each usable phase, record representative tasks, runtime/model versions, route, outcome, manual interventions, setup friction, cancellation/recovery behavior, and observed latency. Record cost/usage only when actually reported. Compare with invoking the underlying tool directly. Capture actionable findings in PROJECT.md and resulting decisions in DECISIONS.md before expanding scope.
