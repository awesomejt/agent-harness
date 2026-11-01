# Implementation Plan

Sequenced plan for **agent-harness**. Status is tracked in [PROJECT.md](../PROJECT.md).

## Phase 0 — Documentation (current)

- [x] Capture decisions in DECISIONS.md
- [x] README, AGENTS.md
- [x] Specification, design, architecture, frameworks, implementation plan
- [x] Project tracker

## Phase 1 — Scaffolding

- [ ] Choose implementation language (Python acceptable for MVP; revisit with evidence if needed)
- [ ] CLI skeleton (`ah single`, `ah sequence`, `ah ralph`)
- [ ] `--mode` flag with the three operational modes
- [ ] Config file loader (YAML)
- [ ] Basic logging and error handling

## Phase 2 — LiteLLM path

- [ ] LiteLLMExecutor (HTTP client to existing proxy)
- [ ] Model group resolution
- [ ] Simple single-shot call through LiteLLM
- [ ] Error classification (so local-first knows when to fall back)

## Phase 3 — OpenCode native path

- [ ] NativeCLIExecutor for OpenCode (`opencode run` or equivalent non-interactive)
- [ ] Per-project OpenCode config sync (provider block pointing at LiteLLM)
- [ ] `--no-sync` flag
- [ ] Single-shot via OpenCode

## Phase 4 — Agent definitions

- [ ] Canonical agent loader (Markdown + YAML frontmatter)
- [ ] OpenCode emitter (write `.opencode/agents/<name>.md`)
- [ ] `--agent` flag to select definition
- [ ] Specialized-agent constraints (tools / model) passed through

## Phase 5 — Execution modes

- [ ] Sequence mode (ordered folder of prompts)
- [ ] Ralph loop (outer loop + completion signal; decide signal format)
- [ ] Fallback path in local-first (LiteLLM failure → OpenCode)

## Phase 6 — Polish & MVP complete

- [ ] Example config and sample agents
- [ ] README usage examples
- [ ] Basic tests for mode selection and config sync
- [ ] Document remaining open questions

## Post-MVP

- Per-prompt front-matter overrides (`mode`, `model`, `fallback`)
- Additional native CLIs (Claude, Codex, Grok, Gemini)
- Pi support (Skills + invocation)
- Broader agent sync (Claude, Gemini, Grok, Codex TOML)
- Quota / credit awareness where native CLIs expose it
- Prompt delay / scheduling

## Open decisions before coding

- Ralph completion signal
- Final config schema and file name/location
- Exact OpenCode non-interactive invocation flags
- Language lock (if not Python)
