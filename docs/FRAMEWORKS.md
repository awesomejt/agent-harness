# Frameworks and Tools

Tools and frameworks under consideration or already in use for **agent-harness**.

## In use / planned for MVP

| Tool | Role | Notes |
|------|------|-------|
| **LiteLLM** | Model gateway for local models, open-weight subscriptions, OpenRouter | Already running on user’s Docker/Proxmox. Harness owns config and syncs to OpenCode. Not used for cloud subscription proxying. |
| **OpenCode** | Primary agent harness for MVP | Local models + OpenRouter via LiteLLM; also direct native runs. Agent definitions as Markdown + frontmatter in `.opencode/agents/`. |

## Planned post-MVP

| Tool | Role | Notes |
|------|------|-------|
| **Pi** | Alternative minimal harness | Skills (SKILL.md / Agent Skills standard), TypeScript extensions. Multiple Ralph loop packages exist. Good candidate for wider interest. |
| **Claude Code** | Native cloud CLI | Subagents as Markdown + frontmatter in `.claude/agents/`. Direct invocation only. |
| **OpenAI Codex** | Native cloud CLI | Custom agents as TOML in `.codex/agents/`. Direct invocation only. |
| **Grok Build** | Native cloud CLI | Agents as Markdown in `.grok/agents/`. Direct invocation only. |
| **Gemini CLI** | Native cloud CLI | Subagents as Markdown + frontmatter in `.gemini/agents/`. Direct invocation only. |

## Patterns and standards

| Item | Role | Notes |
|------|------|-------|
| **Agent Skills standard** | Portable skill format | Used by Pi and increasingly by other tools. SKILL.md with name + description frontmatter. |
| **Ralph loop** | Iterative agent pattern | Filesystem-persisted state, fresh context per iteration, completion signal. Outer loop around existing harness for MVP. |
| **Markdown + YAML frontmatter** | Canonical agent definition | De facto standard across OpenCode, Claude Code, Gemini CLI, Grok Build. |

## Explicitly out of scope for routing

Cloud subscription traffic for Anthropic, OpenAI, xAI, Google, etc. is **not** routed through LiteLLM. The harness invokes the official CLIs directly so Terms of Service are respected.

## Language / implementation (open)

Python is acceptable for initial scaffolding. A stronger evidence-based language decision can still be made before locking the implementation. The architecture (dual-path executor, config ownership, agent mapping) is language-agnostic.
