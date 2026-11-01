# Specification

Feature specification for **agent-harness**.

This document describes what the system must do. Design rationale lives in [DESIGN.md](DESIGN.md); structure in [ARCHITECTURE.md](ARCHITECTURE.md); sequencing in [IMPLEMENTATION.md](IMPLEMENTATION.md).

## Purpose

A single-entry-point CLI that orchestrates existing AI agent tools and a LiteLLM proxy while enforcing operational modes that keep cloud subscription usage on the correct side of provider Terms of Service.

## Operational modes

The tool must support three modes, selectable at the CLI (MVP) and later via per-prompt front-matter:

| Mode | Requirement |
|------|-------------|
| `local-only` | Use only the LiteLLM path. Never invoke a cloud-subscription native CLI. |
| `cloud-only` | Use only native CLIs. Do not call LiteLLM. |
| `local-first` | Prefer LiteLLM. On failure or unavailability, fall back to a configured native CLI. |

CLI surface (MVP):

```bash
ah single "prompt" --mode local-first
ah sequence ./prompts/ --mode local-only
ah ralph "task" --mode cloud-only
```

## Dual-path execution

Two backends:

1. **LiteLLM path** — HTTP to an existing LiteLLM proxy. Used for local models, open-weight subscriptions, and OpenRouter.
2. **Native CLI path** — Spawn official CLIs non-interactively (OpenCode, Claude, Codex, Grok, Gemini, …). Used for cloud subscriptions so ToS is not violated by proxying.

LiteLLM must not be used as a proxy for cloud subscription traffic that would violate provider ToS.

## Three capacities

Every mode must support:

1. **Primary agent** — Main loop for a task.
2. **Specialized agent** — Constrained role (reviewer, debater, security, etc.) using the same canonical agent definition with restricted tools, model, or permissions.
3. **Fallback** — Only in `local-first`. Retry the same prompt against a configured native CLI when the LiteLLM path fails.

## Prompt execution modes

- **Single-shot** — One prompt, one result.
- **Sequenced** — Folder of ordered prompt files (alphabetical/numeric). Optional shared context between steps.
- **Ralph loop** — Iterative agent loop with fresh context per iteration, filesystem-persisted state, and a completion signal (DONE file, promise tag, exit code, or external test command — exact signal TBD).

## Agent definitions

Canonical format: Markdown files with YAML frontmatter in a harness-controlled directory (e.g. `./agents/`).

Required / common fields:

- `name`
- `description`
- `mode` (`primary` / `subagent` / `all`)
- `tools` (allowlist or permissions)
- optional `model` (LiteLLM group or native alias)
- body = system prompt

Sync maps by name into each backend’s expected location:

| Backend | Location |
|---------|----------|
| OpenCode | `.opencode/agents/<name>.md` |
| Claude Code | `.claude/agents/<name>.md` |
| Gemini CLI | `.gemini/agents/<name>.md` |
| Grok Build | `.grok/agents/<name>.md` |
| Codex | `.codex/agents/<name>.toml` |
| Pi | Skills (`skills/<name>/SKILL.md`) or prompt injection |

## LiteLLM ownership and OpenCode sync

- Harness owns the LiteLLM base URL, model groups, and routing policy.
- When mode is `local-only` or `local-first` and OpenCode is driven, the harness writes/merges a provider block into the **project-level** OpenCode config, overriding global OpenCode settings for that project only.
- Global OpenCode config is left untouched.
- `--no-sync` skips the write.
- Native cloud CLI paths never modify OpenCode config.

## Configuration

A harness config file (schema to be finalized) must supply at minimum:

- Default mode
- LiteLLM base URL (and optional API key)
- Model groups
- Fallback CLI
- Whether to sync to OpenCode
- Native CLI binary paths / default args

## MVP scope

- CLI with `--mode` flag.
- LiteLLM path + OpenCode native path.
- Per-project OpenCode config sync.
- Single / sequence / Ralph modes.
- Agent definition loader + OpenCode emitter.
- Basic config file.

Pi and additional native CLIs are post-MVP.

## Non-goals (MVP)

- Full multi-harness agent sync (Claude, Gemini, Grok, Codex, Pi).
- Per-prompt front-matter mode overrides (CLI first).
- GUI or web UI.
- Hosted / multi-user service.
