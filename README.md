# agent-harness

`agent-harness` is the primary project for a CLI (`ah`) that orchestrates existing coding agents and an existing LiteLLM proxy. `ai-queue` is an earlier, narrower attempt and a source of reusable behavior and tests.

The goal is to run real project work with explicit routing, portable agent definitions, and repeatable single, sequence, and Ralph execution. The harness drives existing agent runtimes rather than building a new coding-agent tool loop.

## Status

Planning; no executable implementation yet. Rust is the implementation direction, with prebuilt platform binaries as the intended installation path. Specific libraries and transport choices remain subject to a small integration experiment.

## Delivery milestones

| Milestone | Usable outcome |
|---|---|
| First slice (Phase 2) | One prompt runs OpenCode against LiteLLM in a project, streams progress, and reports an outcome. |
| Core MVP (Phase 4) | Single runs support all three routing modes, a configured native fallback, and named primary/specialized agents in OpenCode. |
| Workflow milestones (Phases 5–6) | Ordered prompt sequences, then bounded, restartable Ralph loops. |
| Broader support (Phases 7–9) | More native CLIs, Pi, and optional quota/scheduling features in independent increments. |

The first slice ships before the core MVP. It must be useful enough to expose real integration problems through daily use.

## Routing contract

| Mode | Allowed model route |
|---|---|
| `local-only` | LiteLLM only; no native cloud-subscription fallback. |
| `cloud-only` | Configured native route only; no LiteLLM requests. |
| `local-first` | LiteLLM first, then a configured native route after an eligible failure. |

These are route names, not guarantees about physical locality or cost: the LiteLLM route may include OpenRouter or permitted subscriptions. OpenCode may run as a subprocess on either route. Native subscription credentials stay with the official CLI; the harness must not proxy subscription traffic where provider terms prohibit it.

For local coding runs, OpenCode supplies tools and the agent loop while using LiteLLM as its model endpoint. A raw HTTP chat completion alone does not satisfy the coding-run milestone.

The harness owns its LiteLLM routing configuration and managed project-level OpenCode settings. It preserves unrelated project settings and global configuration. Canonical agent definitions use Markdown with YAML frontmatter, mapped by name to supported backends.

## Planned first-slice experience

```bash
# Proposed interface; not implemented yet. Run from the target project.
ah single "Fix the parser and run its tests" --mode local-only --model <configured-alias>
```

The run should show the selected route/model, stream agent activity, preserve project changes, and provide a meaningful exit status. Cancellation and missing/unreachable dependencies must be understandable. Setup instructions must distinguish installing `ah` from installing OpenCode and configuring LiteLLM.

## Project records

[Documentation map](docs/README.md) indexes technical contracts and their finalization phases. [Feature landscape review](docs/FEATURE_REVIEW.md) records upstream comparisons, scope gaps, optional candidates and exclusions.

- [Specification](docs/SPECIFICATION.md): complete goals, boundaries, and success criteria.
- [Implementation plan](docs/IMPLEMENTATION.md): focused phases and exit evidence.
- [Project tracker](PROJECT.md): actionable tasks and current status.
- [Decisions](DECISIONS.md): accepted direction, rationale, and deferred choices.
- [Architecture](docs/ARCHITECTURE.md): policy, runtime, and transport boundaries.
- [Frameworks](docs/FRAMEWORKS.md): reuse candidates and evaluation criteria.
- [Git workflow](docs/GIT_WORKFLOW.md): branch, PR, and review requirements.

## License

See [LICENSE](LICENSE).
