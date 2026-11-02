# DECISIONS.md

Living record of important design decisions for agent-harness.

Entries record design intent, not implementation completion. New decisions identify superseded scope and the phase that must supply validation.

## 2026-11-01 — D001: Name

- **Decision**: Repository and project name is `agent-harness`. CLI command is `ah` (or `agent-harness`).
- **Rationale**: Explicit about the role; easy to search; leaves room for modes, agent sync, fallback, and Ralph loops.

## 2026-11-01 — D002: LiteLLM scope

- **Decision**: LiteLLM is used only for local models, open-weight subscriptions, and OpenRouter. It is **not** used as a proxy for cloud subscription traffic that would violate provider ToS.
- **Rationale**: Avoid account suspension or request refusal. Native CLIs are driven directly for those providers.

## 2026-11-01 — D003: Operational modes

- **Decision**: Support three modes via CLI flag (MVP) and later via per-prompt front-matter:
  - `local-only` — LiteLLM only.
  - `cloud-only` — native CLIs only.
  - `local-first` — LiteLLM first, native CLI fallback on failure.
- **Rationale**: Explicit control at the entry point; matches user preference for CLI first, front-matter later.

## 2026-11-01 — D004: Dual-path executor and three capacities

- **Decision**: Two backends — `LiteLLMExecutor` and `NativeCLIExecutor`. Support primary agent, specialized agent, and fallback (fallback only in local-first).
- **Rationale**: Clean separation of ToS-safe routing from direct CLI use; covers the three requested capacities.

## 2026-11-01 — D005: LiteLLM ownership and OpenCode sync

- **Decision**: Harness owns LiteLLM endpoint, model groups, and routing policy. When driving OpenCode in a local-capable mode, sync the provider block into the **project-level** OpenCode config (overrides global OpenCode settings for that project only). Global OpenCode config is left alone. `--no-sync` available.
- **Rationale**: Single source of truth; avoids maintaining two routing configs; keeps other tools/manual sessions unaffected.

## 2026-11-01 — D006: Canonical agent format

- **Decision**: Markdown + YAML frontmatter is the canonical format. Sync maps by name into each provider’s expected location (OpenCode, Claude, Gemini, Grok, Codex TOML, Pi Skills, etc.).
- **Rationale**: Matches the de facto standard already used by OpenCode, Claude Code, Gemini CLI, and Grok Build.

## 2026-11-01 — D007: Original MVP scope (superseded below)

- **Decision**: Start with OpenCode for local models + OpenRouter (via LiteLLM) and direct OpenCode runs. CLI `--mode` flag first. Agent sync for OpenCode. Single / sequence / Ralph modes. Pi and other native CLIs later. Other open-source subscription fallbacks stay inside LiteLLM.
- **Rationale**: Smallest useful surface that exercises the dual-path design and the user’s existing LiteLLM instance.

## 2026-11-01 — D008: Rust and binary installation direction

- **Status**: Accepted implementation direction for planning; concrete dependencies remain open.
- **Decision**: Use Rust for the CLI and target prebuilt platform binaries as the primary installation experience. Keep `agent-harness` as the project/repository name and `ah` as the command. Choose a distinct Cargo package name in Phase 1 because the public package name is occupied.
- **Rationale**: The user prioritizes easy installation, prefers compiled distribution, and is willing to learn Rust with AI assistance. Python runtime management and direct ai-queue code reuse are secondary concerns.
- **Validation**: Phase 1 proves the OpenCode integration; Phase 2 produces the first installable binary. Initial and expanded platform support are declared only with build/run evidence.

## 2026-11-01 — D009: First slice before core MVP

- **Decision**: Phase 2 delivers one real project coding run through OpenCode + LiteLLM in local-only mode. Phase 4 closes the core MVP with all operational modes, configured fallback, and named OpenCode agents. Sequences and Ralph are separate later milestones, followed by additional runtimes and optional resource awareness.
- **Supersedes**: D007, the original requirement to include single/sequence/Ralph in the first MVP; no full-product workflow goal is dropped.
- **Rationale**: Start learning through useful execution quickly. Do not wait for every workflow or provider.
- **Validation**: Each usable phase records representative tasks and direct-tool comparisons in PROJECT.md. Goals and exit evidence are in docs/SPECIFICATION.md and docs/IMPLEMENTATION.md.

## 2026-11-01 — D010: Separate model route from runtime transport

- **Decision**: Preserve LiteLLM and native routes as policy boundaries. OpenCode supplies the coding-agent loop on either route; ACP or another supported interface is its transport. `LiteLLMExecutor` / `NativeCLIExecutor` are conceptual paths, not mandatory concrete type names. Raw HTTP completions alone do not satisfy a coding milestone.
- **Clarifies**: The earlier architecture sketch that equated the LiteLLM path with a raw chat request and native execution with any subprocess.
- **Rationale**: The same OpenCode process can use LiteLLM or a native model target. Mode policy must control effective model routing, including inherited settings and subagent choices.
- **Validation**: Phase 1 tests transport/model control; Phases 2–3 test routing isolation. No custom inner tool loop is planned for MVP.

## 2026-11-01 — D011: Decide at the consuming phase

- **Decision**: Plan the complete product but resolve detailed choices just before the phase that needs them. Give each open question an owner phase and evidence trigger. Record rationale, constraints, alternatives, and superseded decisions as choices are made.
- **Rationale**: Avoid blocking first use on Ralph signals, all provider formats, or scheduling storage.
- **Validation**: PROJECT.md owns task status; the implementation plan owns phase acceptance; this log owns decisions. None is a substitute for the others.

## 2026-11-01 — D012: Selective reuse with a narrow integration experiment

- **Decision**: Treat ai-queue as prior work, not the primary architecture or a required dependency. Evaluate Rust ACP and small adapter/process libraries in Phase 1; adopt only after compatibility and license inspection. ACP is the first candidate, not a locked transport.
- **Rationale**: Useful code exists, but framework defaults must not dictate routing, permissions, or a new inner agent loop.
- **Validation**: Record tested releases, model/permission control, streamed events, cancellation, process cleanup, and live limitations before promoting a candidate.

## Deferred decision register

| Choice | Owner phase | Decide when / required evidence |
|---|---|---|
| Cargo package name, initial development target | 1 | Before scaffolding/publishing; verify naming and toolchain availability. |
| OpenCode transport and adapter/process dependencies | 1 | After a narrow experiment proves model selection, project instructions, callbacks, streaming, and cancellation. |
| ACP permission-request handling (allow/deny/prompt) | 1 | Before the first live run; document the non-interactive default and prove no implicit permission widening. |
| Config format, filename/location, precedence, exit codes | 2 | Before first-slice configuration/CLI is implemented; use the smallest schema that supports that slice. YAML is an earlier sketch, not a locked harness-config format. |
| Project sync ownership/conflicts and no-sync validation | 2 | Before any managed project writes; prove preservation and effective routing. |
| Release tooling and initial binary target | 2 | Before first usable distribution; validate installation and external prerequisites. |
| Failure eligibility, retries, uncertain tool side effects | 3 | Before automatic native fallback; define refusal/recovery behavior and test it. No blind replay of potentially applied work. |
| Model groups and native-route config isolation | 3 | Before dual routing ships; prove cloud-only cannot inherit the managed LiteLLM route. |
| Canonical agent schema, destination paths, constraints | 4 | Before mapping ships; verify installed backend semantics and reject unsupported restrictions. Markdown + YAML remains canonical. |
| MVP platform matrix and packaging polish | 4 | After tested builds/runs; do not imply all targets from Rust portability alone. |
| Sequence ordering/context, metadata, state and resume | 5 | Before sequence execution; define interrupted/uncertain step behavior. |
| Ralph completion, verification, limits and recovery | 6 | Before loop implementation; test false completion and bounded failure. |
| Additional native CLI order/interface/version support | 7 | One adapter at a time, chosen from actual use; verify supported auth and provider integration. |
| Pi transport and agent/skill mapping | 8 | Before Pi adapter; validate capability and route parity. |
| Quota freshness/ranking, scheduling, storage | 9 | Only as usage justifies each addition; evaluate ai-queue behavior without importing its defaults. |
