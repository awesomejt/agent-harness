# agent-harness

`agent-harness` is the primary project for a CLI (`ah`) that orchestrates existing coding agents and an existing LiteLLM proxy. `ai-queue` is an earlier, narrower attempt and a source of reusable behavior and tests.

The goal is to run real project work with explicit routing, portable agent definitions, and repeatable single, sequence, and Ralph execution. The harness drives existing agent runtimes rather than building a new coding-agent tool loop.

## Status

Phase 1 integration experiment: a minimal Rust scaffold provides `ah --help` and `ah --version`. Coding runs are not implemented yet. Rust is the accepted implementation language, with prebuilt platform binaries as the intended installation path. ACP protocol 1 and the minimal Rust stack are selected in [P1.5](docs/evidence/p1-5-integration-acceptance.md); the [holistic Phase 1 review](docs/reviews/phase-01.md) proposes acceptance on its PR merge, after which P2.1 is next.

## Development scaffold

Install [Rust with rustup](https://rust-lang.org/tools/install/) and the platform's native linker tools (Xcode Command Line Tools on macOS). The repository pins Rust 1.88.0 with rustfmt and Clippy; rustup selects it in this directory. Ensure `~/.cargo/bin` is on PATH, or run `source "$HOME/.cargo/env"` for the current shell.

```bash
cargo build --locked
cargo run --locked -- --version
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
```

The Cargo package is `awesomejt-agent-harness`; the binary is `ah`. The initial verified development target is Apple Silicon macOS (`aarch64-apple-darwin`). Other platforms and release installation remain unverified. See [P1.1 evidence](docs/evidence/p1-1-rust-scaffold.md) for the tested baseline. Prebuilt distribution starts in Phase 2.

The separate [P1.3 ACP lifecycle experiment](docs/evidence/p1-3-lifecycle.md) uses Rust 1.88.0 via explicit `cargo +1.88.0` commands and its own manifest/lockfile under `scripts/experiments/acp_lifecycle/`. It verifies SDK wire compatibility and macOS lifecycle behavior with the same toolchain now selected for the public scaffold. The SDK remains in the isolated experiment until Phase 2 implements the adapter; no coding-run commands are added here.

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
# Replace <configured-alias> with an alias already configured in LiteLLM.
ah single "Fix the parser and run its tests" --mode local-only --model "<configured-alias>"
```

The run should show the selected route/model, stream agent activity, preserve project changes, and provide a meaningful exit status. Cancellation and missing/unreachable dependencies must be understandable. Setup instructions must distinguish installing `ah` from installing OpenCode and configuring LiteLLM.

## Project records

[Documentation map](docs/README.md) indexes technical contracts and their finalization phases. [Feature landscape review](docs/FEATURE_REVIEW.md) records upstream comparisons, scope gaps, optional candidates and exclusions.

- [Specification](docs/SPECIFICATION.md): complete goals, boundaries, and success criteria.
- [Implementation plan](docs/IMPLEMENTATION.md): focused phases and exit evidence.
- [Project tracker](PROJECT.md): canonical task status and immediate ready work.
- [Phase review gates](docs/PHASE_REVIEW.md): holistic review and verified remediation before dependent phases.
- [Execution plan](docs/PROJECT_PLAN.md) and [task cards](tasks/README.md): dependencies, small work packages and acceptance evidence for remaining phases.
- [Decisions](DECISIONS.md): accepted direction, rationale, and deferred choices.
- [Architecture](docs/ARCHITECTURE.md): system, component, execution, fallback, lifecycle, and deployment diagrams.
- [Rust software design](docs/DESIGN.md): module blueprint, domain types, ownership and I/O boundaries.
- [Documentation consistency review](docs/CONSISTENCY_REVIEW.md): agreement checks, resolved ambiguities and deferred choices.
- [Frameworks](docs/FRAMEWORKS.md): reuse candidates and evaluation criteria.
- [Git workflow](docs/GIT_WORKFLOW.md): branch, PR, and review requirements.

## License

See [LICENSE](LICENSE).
