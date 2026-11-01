# Design

Design decisions and rationale for **agent-harness**.

See [DECISIONS.md](../DECISIONS.md) for the living record and [SPECIFICATION.md](SPECIFICATION.md) for requirements.

## Core problem

Many AI coding agent tools cannot safely share a single routing layer when cloud subscriptions are involved. Proxying Anthropic, OpenAI, or similar subscription traffic through a third-party harness risks ToS violations, account suspension, or refused requests. At the same time, users want:

- A single entry point.
- Local models and OpenRouter via an existing LiteLLM instance.
- Explicit control over local vs cloud.
- Agent/subagent definitions that work across tools.
- Single-shot, sequenced, and Ralph-loop execution.

## Dual-path design

Two independent backends:

```
                    +------------------+
                    |   agent-harness  |
                    |   (CLI / modes)  |
                    +--------+---------+
                             |
              +--------------+--------------+
              |                             |
     +--------v--------+           +--------v--------+
     | LiteLLMExecutor |           | NativeCLIExecutor|
     | (local, OR,     |           | (Claude, Codex,  |
     |  open-weight)   |           |  Grok, Gemini,   |
     +-----------------+           |  OpenCode, …)    |
                                   +-----------------+
```

- **LiteLLM path**: Safe for local models, open-weight subscriptions, and OpenRouter. The harness talks HTTP to the user’s existing LiteLLM proxy.
- **Native CLI path**: Official binaries only. No proxying of cloud subscription credentials or traffic.

The operational mode selects which path(s) are allowed and in what order.

## Operational modes as first-class policy

Modes are not an afterthought; they are the policy that selects backends:

- `local-only` — LiteLLMExecutor only.
- `cloud-only` — NativeCLIExecutor only.
- `local-first` — LiteLLMExecutor, then NativeCLIExecutor on failure.

CLI flag is the MVP control surface. Per-prompt front-matter overrides come later so the entry point stays simple and explicit.

## Ownership of routing

The harness is the source of truth for LiteLLM endpoint, model groups, and fallback policy. When it drives OpenCode in a local-capable mode it syncs the relevant provider block into the project-level OpenCode config. This:

- Avoids two divergent routing configs.
- Leaves global OpenCode settings alone.
- Keeps native cloud CLI sessions unaffected.

## Canonical agents

Markdown + YAML frontmatter was chosen because it is already the de facto format across OpenCode, Claude Code, Gemini CLI, and Grok Build. Codex (TOML) and Pi (Skills) are mapped rather than forced into a different primary format. Name-based mapping keeps definitions portable.

## Three capacities

Primary, specialized, and fallback are orthogonal to the mode:

- Primary and specialized differ mainly in constraints (tools, model, permissions, or subagent invocation).
- Fallback is only meaningful in `local-first` and reuses the same prompt against a native CLI.

## Ralph loop

The Ralph pattern (filesystem-persisted iterative loop, fresh context per iteration, completion signal) is implemented as an outer loop around an existing harness (OpenCode for MVP) rather than a new agent runtime. Existing OpenCode Ralph plugins or a thin wrapper around `opencode run` are acceptable.

## Frameworks considered

See [FRAMEWORKS.md](FRAMEWORKS.md) for the list of tools and libraries under consideration and the current recommendation.
