# AGENTS.md

Instructions for AI coding agents working on the `agent-harness` repository.

## Project purpose

`agent-harness` is a single-entry-point CLI that orchestrates existing AI agent tools (OpenCode, Pi, Claude, Codex, Grok, Gemini, …) and a LiteLLM proxy.

It enforces operational modes (`local-only`, `cloud-only`, `local-first`) so cloud subscription CLIs are only invoked when ToS permits, while LiteLLM handles local models, open-weight subscriptions, and OpenRouter.

## Key constraints

- Never route cloud subscription traffic through LiteLLM if doing so would violate the provider’s Terms of Service. Those calls must go to the official native CLIs.
- The harness owns LiteLLM routing configuration. When driving OpenCode in a local-capable mode, sync the relevant provider settings into the **project-level** OpenCode config only.
- Canonical agent definitions live as Markdown + YAML frontmatter. Mapping to provider-specific formats is name-based.
- MVP focuses on OpenCode (local + OpenRouter via LiteLLM, plus direct OpenCode runs). Other native CLIs and Pi support come later.

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

## Three capacities

Support primary agent, specialized agent (reviewer/debater/etc.), and fallback (local-first only).

## File layout expectations (evolving)

- Design decisions: `DECISIONS.md`
- Git workflow: `docs/GIT_WORKFLOW.md`
- Agent definitions (once implemented): `agents/*.md`
- Configuration: harness config file (schema still to be finalized)

## When implementing

- Prefer the dual-path executor design already agreed (LiteLLMExecutor + NativeCLIExecutor).
- Keep the CLI surface small for MVP: `--mode`, optional `--model`, `--agent`, `--fallback`, `--harness`, `--no-sync`.
- Document any deviation from the decisions in `DECISIONS.md`.
- Follow the Git workflow above for all code changes.

## Memory

Important design decisions are recorded in [DECISIONS.md](DECISIONS.md). Read it before making architectural changes.
