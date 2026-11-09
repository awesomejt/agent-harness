# AGENTS.md

Instructions for AI coding agents working on the `agent-harness` repository.

## Project purpose

`agent-harness` is a single-entry-point CLI that orchestrates existing AI agent tools (OpenCode, Pi, Claude, Codex, Grok, Antigravity, …) and a LiteLLM proxy.

It enforces operational modes (`local-only`, `cloud-only`, `local-first`) so cloud subscription CLIs are only invoked when ToS permits, while LiteLLM handles local models, open-weight subscriptions, and OpenRouter.

## Key constraints

- Never route cloud subscription traffic through LiteLLM if doing so would violate the provider’s Terms of Service. Those calls must go to the official native CLIs.
- The harness owns LiteLLM routing configuration. When driving OpenCode in a local-capable mode, sync the relevant provider settings into the **project-level** OpenCode config only.
- Canonical agent definitions live as Markdown + YAML frontmatter. Mapping to provider-specific formats is name-based.
- Phase 7 follows D068: existing OpenCode/LiteLLM and accepted Claude, plus separately gated ChatGPT-plan and dedicated Go routes through OpenCode. Paused Codex/Grok and blocked Antigravity retain their gates outside mandatory portfolio closure; Pi stays independent. F27/F28 remain candidates and D034 fallback is unchanged.
- OpenCode is the first runtime. The first usable slice is one local-only project coding run through LiteLLM. The core MVP adds all routing modes and named agents; sequences, Ralph, other native CLIs, and Pi follow in focused phases (see docs/IMPLEMENTATION.md).

## Git workflow

All agents must follow the multi-agent Git workflow documented in [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md):

- No direct commits to `main`. Use `feature/<phase>/<task>-description` for normal tasks, `review/<phase>-description` for holistic phase reviews, and `patch/<task>` for standalone fixes outside the feature/task process.
- Open a PR to `main` when the task is complete. Feature PRs trigger automatic Grok review; patch PRs require an explicit `/grok review` comment; `review/` branches bypass that process while retaining the holistic phase-review gate.
- On feature/patch PRs, address critical/high Grok findings and request re-review with `/grok review` if needed. A phase-review PR may merge once every finding is recorded with a remediation plan; fix findings in `patch/` PRs with `/grok review`, keep one PR open at a time, and resolve/verify all findings before phase acceptance (D042).
- Minor/nitpick findings do not require re-review.
- Maximum 3 Grok reviews per PR; after that, hand off to a human.
- On clean approval: merge, delete remote branch, then locally `git checkout main && git pull --prune && git branch -d <branch>`.

## Operational modes

Always respect the mode passed via CLI (and, later, per-prompt front-matter):

- `local-only` — LiteLLM only.
- `cloud-only` — native CLIs only.
- `local-first` — LiteLLM first, native CLI fallback on failure.

Route labels do not imply physical locality or price: local-only may use OpenRouter through LiteLLM. Validate effective routing even with `--no-sync`; never silently widen agent constraints or replay uncertain coding side effects.

## Three capacities

Support primary agent, specialized agent (reviewer/debater/etc.), and fallback (local-first only).

## File layout expectations (evolving)

- Design decisions: `DECISIONS.md`
- Git workflow: `docs/GIT_WORKFLOW.md`
- Agent definitions (once implemented): `agents/*.md`
- Configuration: harness config file (schema still to be finalized)

## Delivery and project records

- Rust is the accepted implementation language; prebuilt binaries are the intended user installation path. Evaluate dependencies and the OpenCode transport in a narrow Phase 1 experiment.
- PROJECT.md owns task status; docs/SPECIFICATION.md owns full goals; docs/IMPLEMENTATION.md owns phase acceptance; DECISIONS.md owns decisions and deferred choices.
- docs/README.md indexes technical contracts; docs/FEATURE_REVIEW.md owns feature dispositions. Candidate features are not implementation authorization. Finalize each phase's interfaces and schemas before shipping it.
- docs/DESIGN.md defines the proposed Rust module/domain blueprint and docs/ARCHITECTURE.md owns the diagrams. AC01–AC11 in docs/SPECIFICATION.md are the explicit MVP acceptance checklist; proposed internal names are not frozen public APIs.
- docs/PROJECT_PLAN.md defines execution order and readiness; tasks/ phase cards define dependency/scope/evidence. PROJECT.md remains the only mutable status board. Default to one active implementation task/PR; selection/demand gates are required before native-adapter or optional-resource work.
- Every phase ends with an explicit holistic phase-review task. Follow docs/PHASE_REVIEW.md, record findings and verified fixes in docs/reviews/, and do not start dependent phases until the review passes and required PRs merge. Individual PR approvals do not replace this review.
- Work in small focused phases. Ship/use the first slice before broadening it; record live evidence and friction. Mocked tests alone do not close milestones that require live integration.
- Resolve deferred choices at their consuming phase. Do not block single-run delivery on Ralph, all provider mappings, or scheduling.

## When implementing

- Preserve the dual-path routing policy (LiteLLMExecutor + NativeCLIExecutor conceptually). Separate model route from runtime/transport: an OpenCode subprocess can serve either route. OpenCode owns the inner coding-agent loop; raw HTTP completion is not a coding run.
- Keep the CLI surface small: Phase 2 introduces `--mode`, optional `--model`, and `--no-sync`; Phase 4 introduces `--agent`. Decide fallback overrides in Phase 3 and runtime-selection syntax in Phases 7–8 before adding corresponding flags. Reject unsupported modes explicitly; no speculative command skeletons are needed for later workflows.
- Document any deviation from the decisions in `DECISIONS.md`.
- Follow the Git workflow above for all code changes.

## Memory

Important design decisions are recorded in [DECISIONS.md](DECISIONS.md). Read it before making architectural changes.
