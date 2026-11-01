# DECISIONS.md

Living record of important design decisions for agent-harness.

Dates are approximate based on the design discussion (late October / early November 2026).

## 2026-11-01 — Name

- **Decision**: Repository and project name is `agent-harness`. CLI command is `ah` (or `agent-harness`).
- **Rationale**: Explicit about the role; easy to search; leaves room for modes, agent sync, fallback, and Ralph loops.

## 2026-11-01 — LiteLLM scope

- **Decision**: LiteLLM is used only for local models, open-weight subscriptions, and OpenRouter. It is **not** used as a proxy for cloud subscription traffic that would violate provider ToS.
- **Rationale**: Avoid account suspension or request refusal. Native CLIs are driven directly for those providers.

## 2026-11-01 — Operational modes

- **Decision**: Support three modes via CLI flag (MVP) and later via per-prompt front-matter:
  - `local-only` — LiteLLM only.
  - `cloud-only` — native CLIs only.
  - `local-first` — LiteLLM first, native CLI fallback on failure.
- **Rationale**: Explicit control at the entry point; matches user preference for CLI first, front-matter later.

## 2026-11-01 — Dual-path executor and three capacities

- **Decision**: Two backends — `LiteLLMExecutor` and `NativeCLIExecutor`. Support primary agent, specialized agent, and fallback (fallback only in local-first).
- **Rationale**: Clean separation of ToS-safe routing from direct CLI use; covers the three requested capacities.

## 2026-11-01 — LiteLLM ownership and OpenCode sync

- **Decision**: Harness owns LiteLLM endpoint, model groups, and routing policy. When driving OpenCode in a local-capable mode, sync the provider block into the **project-level** OpenCode config (overrides global OpenCode settings for that project only). Global OpenCode config is left alone. `--no-sync` available.
- **Rationale**: Single source of truth; avoids maintaining two routing configs; keeps other tools/manual sessions unaffected.

## 2026-11-01 — Canonical agent format

- **Decision**: Markdown + YAML frontmatter is the canonical format. Sync maps by name into each provider’s expected location (OpenCode, Claude, Gemini, Grok, Codex TOML, Pi Skills, etc.).
- **Rationale**: Matches the de facto standard already used by OpenCode, Claude Code, Gemini CLI, and Grok Build.

## 2026-11-01 — MVP scope

- **Decision**: Start with OpenCode for local models + OpenRouter (via LiteLLM) and direct OpenCode runs. CLI `--mode` flag first. Agent sync for OpenCode. Single / sequence / Ralph modes. Pi and other native CLIs later. Other open-source subscription fallbacks stay inside LiteLLM.
- **Rationale**: Smallest useful surface that exercises the dual-path design and the user’s existing LiteLLM instance.

## Open questions / later

- Exact completion signal for Ralph loops (promise tag, DONE file, exit code, external test command).
- Final config schema and file location.
- Language/tooling for the CLI implementation (Python was acceptable for scaffolding; strong evidence still preferred before locking the language).
- How specialized-agent constraints (tools, model, permissions) are expressed and enforced across backends.
