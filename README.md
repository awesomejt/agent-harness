# agent-harness

`agent-harness` is the primary project for a CLI (`ah`) that orchestrates existing coding agents and an existing LiteLLM proxy. `ai-queue` is an earlier, narrower attempt and a source of reusable behavior and tests.

The goal is to run real project work with explicit routing, portable agent definitions, and repeatable single, sequence, and Ralph execution. The harness drives existing agent runtimes rather than building a new coding-agent tool loop.

## Status

The [Phase 3 holistic review](docs/reviews/phase-03.md) records dual-route acceptance, effective on its report PR merge; Phase 4 named agents are in progress: canonical agents parse (P4.1), and `--agent` selects, previews and plans conflict-aware OpenCode emission (P4.2), while named execution refuses until constraint enforcement (P4.3). From source, `ah single` runs OpenCode **2.2.5** over ACP on macOS (D035) in all three modes: `local-only` through the configured LiteLLM alias or `group:` reference, `cloud-only` through OpenCode's built-in `opencode` API-key provider, and `local-first` with one native fallback only when the LiteLLM endpoint is unreachable before launch. Managed project routing, explicit inline/file/stdin inputs, bounded progress/cancellation, read-only preview and dirty-project reporting are implemented. [Dual-route use evidence](docs/evidence/p3-5-dual-route-use.md) records live runs on each route. The first Apple Silicon macOS pre-release ([real-use evidence](docs/evidence/p2-6-first-use.md)) predates Phase 3: it supports local-only only, requires OpenCode 1.18.30 and retains best-effort private-state deletion, as documented in the [runbook](docs/OPERATIONS.md).

## Install

The Apple Silicon macOS prebuilt binary is published as [v0.1.0-alpha.1](https://github.com/awesomejt/agent-harness/releases/tag/v0.1.0-alpha.1). Follow the [checksum, installation and prerequisite instructions](docs/OPERATIONS.md). Binary users need no Rust or Python; its coding runs separately require OpenCode 1.18.30 and an existing LiteLLM service. Current source requires OpenCode 2.2.5 instead, and native/local-first routes are available only from source until a new release. Only macOS 27.0.1 on Apple Silicon has been release-tested.

## Development scaffold

Install [Rust with rustup](https://rust-lang.org/tools/install/) and the platform's native linker tools (Xcode Command Line Tools on macOS). The repository pins Rust 1.88.0 with rustfmt and Clippy; rustup selects it in this directory. Ensure `~/.cargo/bin` is on PATH, or run `source "$HOME/.cargo/env"` for the current shell.

```bash
cargo build --locked
cargo run --locked -- --version
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
```

The Cargo package is `awesomejt-agent-harness`; the binary is `ah`. The initial verified development target is Apple Silicon macOS (`aarch64-apple-darwin`). Other platforms remain unverified. See [P1.1 evidence](docs/evidence/p1-1-rust-scaffold.md) for the tested baseline. P2.5 supplies the initial prebuilt distribution.

The separate [P1.3 ACP lifecycle experiment](docs/evidence/p1-3-lifecycle.md) uses Rust 1.88.0 via explicit `cargo +1.88.0` commands and its own manifest/lockfile under `scripts/experiments/acp_lifecycle/`. It verifies SDK wire compatibility and macOS lifecycle behavior with the same toolchain now selected for the public scaffold. The production adapter now consumes the same pinned SDK 3.6.0/Tokio 1.48.0 transport stack; the standalone experiment remains separate regression tooling.

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

## Development coding run

```bash
# Build with cargo build --locked, then put target/debug/ah on PATH.
# Create ah.json in the target project using docs/CONFIGURATION.md.
# Replace <configured-alias> with an alias already configured in LiteLLM.
ah single "Fix the parser and run its tests" --mode local-only --model "<configured-alias>" --permissions trusted
```

The local-only command requires an existing LiteLLM alias and nonempty environment key reference. Current source also supports isolated native OpenCode `cloud-only` with an explicit native model and API-key reference; see [native setup](docs/OPERATIONS.md#native-cloud-only-from-source-p32). `local-first` runs one configured native attempt only when the LiteLLM endpoint is unreachable before launch; see [local-first setup](docs/OPERATIONS.md#local-first-from-source-p33). The published alpha.1 binary predates these additions. It reports the selected route/model, buffers bounded assistant text until successful completion, and writes human diagnostics to stderr. `--prompt-file task.txt` and `--prompt-file -` select file/stdin input. Default permissions deny tools; only explicit `--permissions trusted` authorizes host-level file and shell access. This is not a sandbox.

The first adapter isolates HOME/XDG and ignores unmanaged OpenCode settings during execution, preserving them on disk. It requires effective primary/helper routing and exact permission-rule verification before prompting. Active interruption or transport loss without a terminal response returns **4 (uncertain)**; inspect effects before trying again. There is no fallback or automatic retry. Use `--preview` for a read-only local plan. See [configuration](docs/CONFIGURATION.md), [execution](docs/EXECUTION.md) and [P2.2 evidence](docs/evidence/p2-2-local-only-run.md).

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

Inspect a resolved plan without starting OpenCode, contacting LiteLLM or writing configuration:

```bash
ah single "Review this project" --preview
```

Preview validates the same inputs and managed routing as execution. It reports required changes, choice sources and local OpenCode discovery, with secrets and prompt contents omitted. Version/capability, service and alias availability remain unverified; exit 0 confirms only a valid local plan. Use `--no-sync` to require an already matching project route.
