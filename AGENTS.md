# AGENTS.md

Instructions for AI coding agents working on the `agent-harness` repository.

## Project purpose

`agent-harness` is a single-entry-point CLI that orchestrates existing AI agent tools (OpenCode, Pi, Claude, Codex, Grok, Gemini, …) and a LiteLLM proxy.

It enforces operational modes (`local-only`, `cloud-only`, `local-first`) so cloud subscription CLIs are only invoked when ToS permits, while LiteLLM handles local models, open-weight subscriptions, and OpenRouter.

## Key constraints

- Never route cloud subscription traffic through LiteLLM if doing so would violate the provider’s Terms of Service. Those calls must go to the official native CLIs.
- The harness owns LiteLLM routing configuration. When driving OpenCode in a local-capable mode, sync the relevant provider settings into the **project-level** OpenCode config only.
- Canonical agent definitions live as Markdown + YAML frontmatter. Mapping to provider-specific formats is name-based.
- OpenCode is the first runtime. The first usable slice is one local-only project coding run through LiteLLM. The core MVP adds all routing modes and named agents; sequences, Ralph, other native CLIs, and Pi follow in focused phases (see docs/IMPLEMENTATION.md).

## Git workflow

All agents must follow the multi-agent Git workflow documented in [docs/GIT_WORKFLOW.md](docs/GIT_WORKFLOW.md):

- No direct commits to `main`. Use a feature branch per task.
- Open a PR to `main` when the task is complete (this triggers an automatic Grok review).
- Address critical/high findings and request re-review with `/grok review` if needed.
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

- Rust is the implementation direction; prebuilt binaries are the intended user installation path. Evaluate dependencies and the OpenCode transport in a narrow Phase 1 experiment.
- PROJECT.md owns task status; docs/SPECIFICATION.md owns full goals; docs/IMPLEMENTATION.md owns phase acceptance; DECISIONS.md owns decisions and deferred choices.
- docs/README.md indexes technical contracts; docs/FEATURE_REVIEW.md owns feature dispositions. Candidate features are not implementation authorization. Finalize each phase's interfaces and schemas before shipping it.
- Work in small focused phases. Ship/use the first slice before broadening it; record live evidence and friction. Mocked tests alone do not close milestones that require live integration.
- Resolve deferred choices at their consuming phase. Do not block single-run delivery on Ralph, all provider mappings, or scheduling.

## When implementing

- Preserve the dual-path routing policy (LiteLLMExecutor + NativeCLIExecutor conceptually). Separate model route from runtime/transport: an OpenCode subprocess can serve either route. OpenCode owns the inner coding-agent loop; raw HTTP completion is not a coding run.
- Keep the CLI surface small: Phase 2 introduces `--mode`, optional `--model`, and `--no-sync`; Phase 4 introduces `--agent`. Decide fallback overrides in Phase 3 and runtime-selection syntax in Phases 7–8 before adding corresponding flags. Reject unsupported modes explicitly; no speculative command skeletons are needed for later workflows.
- Document any deviation from the decisions in `DECISIONS.md`.
- Follow the Git workflow above for all code changes.

## Memory

Important design decisions are recorded in [DECISIONS.md](DECISIONS.md). Read it before making architectural changes.
