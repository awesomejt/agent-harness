# Architecture

High-level architecture of **agent-harness**.

## Components

```
+-------------------------------------------------------------+
|                        agent-harness CLI                     |
|  (single | sequence | ralph)  +  --mode / --agent / …       |
+----------------------------+--------------------------------+
                             |
                             v
+----------------------------+--------------------------------+
|                     Mode & Policy Layer                      |
|  Resolves operational mode, selects backend(s), applies     |
|  fallback rules, loads agent definition                     |
+-------------+------------------------------+---------------+
              |                              |
              v                              v
+-------------+--------------+   +-----------+----------------+
|     LiteLLMExecutor        |   |    NativeCLIExecutor       |
|  - HTTP to LiteLLM proxy   |   |  - Spawn official CLI      |
|  - Model groups            |   |  - OpenCode (MVP)          |
|  - Budgets / fallbacks     |   |  - Claude, Codex, Grok,    |
|    already in LiteLLM      |   |    Gemini (later)          |
+----------------------------+   +----------------------------+
              |                              |
              v                              v
+----------------------------+   +----------------------------+
|   OpenCode config sync     |   |   Agent definition mapper  |
|  (project-level only)      |   |  (canonical → backend)      |
+----------------------------+   +----------------------------+
```

## Data flow (local-first example)

1. CLI parses mode, agent name, prompt (or sequence / Ralph task).
2. Policy layer loads canonical agent definition (if any).
3. If mode allows LiteLLM:
   - Optionally sync OpenCode provider config (when driving OpenCode).
   - Call LiteLLMExecutor.
4. If LiteLLM fails (or mode is cloud-only):
   - Map agent definition to the target native CLI format if needed.
   - Call NativeCLIExecutor with the appropriate binary and args.
5. Return result (or continue Ralph / sequence loop).

## Configuration ownership

| Concern | Owner | Notes |
|---------|-------|-------|
| LiteLLM URL, model groups, fallback policy | Harness | Source of truth |
| Project OpenCode provider block | Harness (sync) | Written only for local-capable OpenCode runs |
| Global OpenCode config | User / OpenCode | Left untouched |
| Native CLI credentials | Native CLI | Never handled by harness or LiteLLM |
| Canonical agent definitions | Harness directory | Synced outward by name |

## Agent definition mapping

Canonical Markdown + frontmatter is loaded once. A mapper emits the backend-specific representation:

- OpenCode / Claude / Gemini / Grok: nearly identical Markdown files into the expected directory.
- Codex: TOML conversion.
- Pi: SKILL.md (Agent Skills standard) or prompt injection for MVP.

## Extensibility

- New native CLIs are additional NativeCLIExecutor targets.
- New harnesses (Pi) are additional sync targets and invocation backends.
- Model groups and fallback order live in config, not code.

## Boundaries

- The harness does not implement its own agent loop for the MVP; it drives existing tools (OpenCode, later others).
- State for Ralph loops is filesystem-based (files, git) so it survives process restarts.
- No long-running daemon is required for MVP; each CLI invocation is self-contained.
