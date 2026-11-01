# agent-harness

Agent harness that wraps OpenCode, Pi, and native cloud AI provider CLI tools into one place.

It provides a single entry point for single-shot prompts, sequenced prompts, and Ralph loops, with explicit control over local vs cloud routing while staying on the correct side of provider Terms of Service.

## Status

Early design / MVP planning. Core decisions are recorded in [DECISIONS.md](DECISIONS.md).

## Goals

- Single CLI entry point that dispatches to the right backend.
- Support three operational modes: `local-only`, `cloud-only`, `local-first`.
- Drive both LiteLLM (local models, open-weight subscriptions, OpenRouter) and native cloud CLIs (Claude, Codex, Grok, Gemini, OpenCode, …) without violating ToS.
- Canonical agent/subagent definitions (Markdown + YAML frontmatter) that map to provider-specific formats of the same name.
- Modes: single-shot, sequenced prompts (ordered folder), Ralph loop.
- MVP starts with OpenCode for local + OpenRouter (via LiteLLM) and native OpenCode runs; other native CLIs follow.

## Operational modes

| Mode | Behavior |
|------|----------|
| `local-only` | Use only the LiteLLM path. Never invoke a cloud-subscription CLI. |
| `cloud-only` | Use only native CLIs. Skip LiteLLM. |
| `local-first` | Prefer LiteLLM. On failure or unavailability, fall back to a configured native CLI. |

CLI flag (MVP): `--mode local-only|cloud-only|local-first`

Per-prompt front-matter overrides are planned after the CLI surface is solid.

## Dual-path executor

| Path | Used for | Invocation |
|------|----------|------------|
| LiteLLM | Local models, open-weight subs, OpenRouter | HTTP to existing LiteLLM proxy |
| Native CLI | Cloud subscriptions (Claude, Codex, Grok, Gemini, OpenCode, …) | Spawn official CLI non-interactively |

LiteLLM does **not** proxy cloud subscription traffic that would violate ToS. Those calls go directly to the official CLIs.

Three capacities (all supported):

1. **Primary agent** — main loop for a task.
2. **Specialized agent** — constrained role (reviewer, debater, etc.) using the same canonical definition.
3. **Fallback** — only active in `local-first`; retry against a configured native CLI when LiteLLM fails.

## LiteLLM ownership and OpenCode sync

The harness owns the LiteLLM endpoint, model groups, and routing policy.

When mode is `local-only` or `local-first` and OpenCode is driven:

- Sync writes/merges a provider block into the **project-level** OpenCode config.
- This overrides any global OpenCode settings for that project only.
- Global OpenCode config is left untouched.
- `--no-sync` can skip the write.

Native cloud CLI paths never touch OpenCode’s config.

## Canonical agents

Markdown + YAML frontmatter in a harness-controlled directory (e.g. `./agents/`).

Example:

```markdown
---
name: code-reviewer
description: Reviews changes for correctness, security, and regressions.
mode: subagent
tools:
  - read
  - grep
model: local-capable
---

You are a senior code reviewer.
Focus on security, performance, and maintainability.
```

Sync maps by name into each harness’s expected location (OpenCode `.opencode/agents/`, Claude `.claude/agents/`, Gemini `.gemini/agents/`, Grok `.grok/agents/`, Codex TOML, Pi Skills, …).

## MVP scope

- CLI with `--mode` flag.
- LiteLLM path + OpenCode native path.
- Per-project OpenCode config sync.
- Single / sequence / Ralph modes.
- Agent definition loader + OpenCode emitter.
- Config file for LiteLLM URL, model groups, fallback CLI, etc.

Pi and additional native CLIs come after the OpenCode path is solid. Other open-source subscription fallbacks stay inside LiteLLM.

## Configuration sketch

```yaml
default_mode: local-first
liteLLM:
  base_url: http://litellm.local:4000
  api_key: ${LITELLM_KEY}   # optional

model_groups:
  local-capable:
    - ollama/qwen2.5-coder
    - openrouter/qwen/qwen3-coder

fallback_cli: opencode
sync_to_opencode: true
```

## License

See [LICENSE](LICENSE).
