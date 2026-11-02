# Architecture

The harness separates model-route policy from agent runtimes and their transports. This clarifies the earlier dual-executor sketch; see [DECISIONS.md](../DECISIONS.md).

```text
CLI: single / sequence / ralph
              |
              v
Resolve configuration + canonical agent + capabilities
              |
              v
Mode policy: select permitted route and eligible fallback
              |
       +------+-------+
       |              |
       v              v
LiteLLM route      Native subscription route
       |              |
Project provider   Official CLI authentication
sync/validation    and explicit native target
       |              |
       +------+-------+
              v
Runtime adapter: OpenCode first; other CLIs and Pi later
              |
Transport: ACP / structured CLI output (selected by experiment)
              |
Progress events + result + cancellation + attempt record
```

## Route and runtime are separate

`LiteLLMExecutor` and `NativeCLIExecutor` remain conceptual execution paths, not a requirement for exactly two concrete Rust types. The policy layer chooses the allowed model route. The runtime adapter executes the coding task. The transport communicates with that runtime.

OpenCode can run as a subprocess over ACP or another supported interface while its model calls go through LiteLLM. A subprocess therefore does not imply cloud-only. A native OpenCode run must select its native target without inheriting a LiteLLM model from harness-managed settings.

Direct HTTP to LiteLLM is suitable for discovery/diagnostics and optional text-only work. It supplies no coding tools by itself. The MVP does not add a custom tool loop to make raw completions act as coding runs.

## Single-run flow

1. Resolve project, explicit mode, model alias, and optional agent definition.
2. Validate configuration, capabilities, and route restrictions before launching work.
3. For a LiteLLM route, merge/validate only project-managed provider settings. `--no-sync` skips mutation, not validation.
4. Drive OpenCode in the project, enforcing supported agent constraints and collecting progress/outcome.
5. For local-first eligible failure, record the failed attempt and apply the Phase 3 recovery policy before launching the configured native target. Unknown tool side effects are not automatically replayed.
6. Return an outcome or pass it to the sequence/Ralph outer loop.

## Ownership

| Concern | Owner |
|---|---|
| Mode, allowed routes, model groups, native fallback selection | Harness |
| Model routing within the configured LiteLLM route | Harness-owned LiteLLM configuration / proxy |
| Project OpenCode managed provider settings | Harness sync, preserving unrelated content |
| Global OpenCode config | User; never modified |
| Native credentials and authentication | Official native CLI |
| Tool execution and inner agent loop | Existing runtime |
| Canonical definitions and name-based mapping | Harness |
| Sequence/Ralph orchestration and durable progress | Harness, added in Phases 5–6 |

## Internal boundaries

Use a small set of modules for CLI/configuration, policy, runtime adapters, project sync, agent loading, and outcomes. Add workflow state only when implementing sequences. Concrete traits and crate layout are selected from the integration experiment; do not build a plugin framework before a second adapter needs it.

A common event/outcome vocabulary should preserve meaningful backend details and distinguish configuration/authentication, availability, rate limits, runtime failure, cancellation, and uncertain completion. Normalize only what the harness needs to make correct decisions.

Each adapter reports supported features. Missing permission or tool restrictions cause refusal rather than implicit widening. Fresh sessions, resumed sessions, specialized roles, and streamed events must be validated per backend rather than assumed portable.

## Persistence and process lifetime

Early single runs need observable attempts and final outcomes, not a mandatory database. Sequence and Ralph durable state is filesystem-based; schema and interrupted-run semantics are decided before those phases ship. Child processes and descendants must terminate correctly on cancellation/deadline. Pipe draining, event backpressure, and partial output are part of the adapter acceptance criteria.

No long-running daemon is required. Prebuilt binaries remove the harness language runtime requirement, but selected agent CLIs and the LiteLLM service remain external prerequisites.
