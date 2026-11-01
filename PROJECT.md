# PROJECT.md

Living status and task list for **agent-harness**.

Last updated: 2026-11-01

## Status

**Phase**: 0 — Documentation  
**State**: Design captured; ready for scaffolding  
**MVP target**: OpenCode + LiteLLM dual path with operational modes

## Current focus

Complete documentation and decide on scaffolding next steps (language, config schema, Ralph signal).

## Task list

### Phase 0 — Documentation
- [x] DECISIONS.md
- [x] README.md + AGENTS.md
- [x] docs/SPECIFICATION.md
- [x] docs/DESIGN.md
- [x] docs/ARCHITECTURE.md
- [x] docs/IMPLEMENTATION.md
- [x] docs/FRAMEWORKS.md
- [x] PROJECT.md (this file)

### Phase 1 — Scaffolding
- [ ] Choose implementation language
- [ ] CLI skeleton with `--mode`
- [ ] Config file loader
- [ ] Basic error handling

### Phase 2 — LiteLLM path
- [ ] LiteLLMExecutor
- [ ] Model group resolution
- [ ] Single-shot via LiteLLM
- [ ] Error classification for fallback

### Phase 3 — OpenCode native path
- [ ] NativeCLIExecutor (OpenCode)
- [ ] Per-project OpenCode config sync
- [ ] `--no-sync`
- [ ] Single-shot via OpenCode

### Phase 4 — Agent definitions
- [ ] Canonical agent loader
- [ ] OpenCode emitter
- [ ] `--agent` flag
- [ ] Specialized-agent constraints

### Phase 5 — Execution modes
- [ ] Sequence mode
- [ ] Ralph loop + completion signal
- [ ] local-first fallback path

### Phase 6 — Polish
- [ ] Example config + sample agents
- [ ] Usage examples in README
- [ ] Basic tests

## Open questions

- Ralph completion signal (DONE file, promise tag, exit code, external test)?
- Final config schema and file location?
- Language lock (Python vs other)?
- Exact OpenCode non-interactive flags?

## References

- [DECISIONS.md](DECISIONS.md)
- [docs/SPECIFICATION.md](docs/SPECIFICATION.md)
- [docs/DESIGN.md](docs/DESIGN.md)
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)
- [docs/IMPLEMENTATION.md](docs/IMPLEMENTATION.md)
- [docs/FRAMEWORKS.md](docs/FRAMEWORKS.md)
