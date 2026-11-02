# P1.5 — Integration experiment acceptance preparation

Date: 2026-11-02 (America/Denver). Baseline: `2fe0e5f` (P1.3 / PR #11 merged). Task: [P1.5](../../tasks/01-integration.md#p1-5). Decision: [D023](../../DECISIONS.md#2026-11-02--d023-select-acp-and-the-tested-rust-integration-boundaries). This record prepares the Phase 1 review; it does not pass P1.7 or implement coding runs.

## Selection and exact tested baseline

Select OpenCode **1.18.30** (Homebrew **1.18.30_2**) ACP stdio, stable protocol **1**, with the official Rust SDK **3.6.0**, default features disabled. OpenCode supplies the coding loop. Harness-owned launch/environment/group cleanup and policy remain separate from SDK wire dispatch. The convenience launcher and `cli-stream` were rejected in [P1.4](p1-4-dependency-evaluation.md); implementing a custom dispatcher or comparing native structured output adds no needed evidence after ACP met this experiment's requirements.

| Component | Selected/tested version or boundary |
|---|---|
| Package/binary | `awesomejt-agent-harness` 0.1.0 / `ah`; one package, no workspace framework |
| Rust | edition 2024, MSRV/pin **1.88.0**, rustc `6b00bc388` (2025-06-23), rustfmt/Clippy |
| Initial target | `aarch64-apple-darwin`, macOS **27.0.1**, build **26A434** |
| ACP schema | **1.13.0**, resolved by the committed experiment lockfile; stable protocol 1 only |
| Async/I/O | Tokio **1.48.0** (`macros`, `rt`, `process`, `io-util`, `time`, `sync`, `signal`); tokio-util **0.7.16** (`compat`) |
| Supporting direct crates | serde_json **1.0.145**; Unix libc **0.2.177** |
| Experiment driver | Python **3.14.7**, development tooling only; no Python runtime dependency for `ah` |
| Live API/alias | `http://litellm:4000/v1` / `macmini-qwen3-coder-30b`; server version unreported |

The selected stack is the minimum proven integration stack, not the full future config/CLI/distribution dependency set. Raise the root Rust floor/pin now because the SDK/schema require it and the locked experiment already builds at that floor. Keep dependency declarations in the isolated experiment until Phase 2 code consumes them. The scaffold still has no external dependencies; adding unused SDK packages would not implement or validate the production adapter. [Dependency inventory](p1-5-dependencies.md) records the entire resolved graph, target reachability, inspected license files and distribution follow-ups.

## Evidence coverage

| Required Phase 1 behavior | Merged evidence and interpretation |
|---|---|
| Package/toolchain boundary | [P1.1](p1-1-rust-scaffold.md): minimal library/binary, informational CLI. P1.5 verifies this unchanged behavior at Rust 1.88. |
| Permission policy before live work | [P1.6](p1-6-permission-policy.md): D020, default deny, malformed request refusal, exact one-use synthetic grants, no TUI. |
| Real ACP session and streaming | [P1.2](p1-2-live-acp.md): authenticated alias discovery, effective deny-all preflight, protocol/session/model selection, text chunks and `end_turn`. |
| Dependency/runtime compatibility | [P1.4](p1-4-dependency-evaluation.md) pinned source comparison; [P1.3](p1-3-lifecycle.md) Rust SDK compile and real OpenCode interoperability. |
| Effective model and instructions | P1.3 recorder observes outbound primary/helper model aliases; primary request includes AGENTS.md sentinel absent from prompt; assistant follows it. No proxy-internal route/location claim. |
| Permission callback enforcement | P1.3 real OpenCode/local stub deterministic read request denied; live read denial with sentinel absent from outgoing model payload. No live allow/write/shell grant proven. |
| Cancellation, unavailable service, cleanup | P1.3 live `cancelled`, real unavailable loopback endpoint fails, direct child reaped and no live process-group members; TERM-resistant descendant fixtures, even after leader exit. |
| Failure does not become success | P1.3 seventeen adversarial cases include EOF, malformed JSON, wrong session/model, send closure, deadline, SIGINT, unsolicited filesystem callback and both byte limits. Sticky callback failure overrides later peer success. |

P1.3 also records an intermittent live denial prompt error after review fixes; cleanup passed and a separate diagnostic denial/cancellation attempt passed. Its raw cause is unknown. Preserve that observation rather than claiming universal model/backend reliability. Existing live records are acceptance evidence; no coding turn, successful edit/test or production shutdown flush is inferred from them.

## Rust boundaries confirmed by the experiment

| Boundary | Evidence and production responsibility |
|---|---|
| Pure permission policy | `src/permission.rs` accepts normalized data without SDK dependencies. Keep route/permission policy independent of transport. |
| OpenCode adapter | Explicit protocol negotiation, session/model check, project config preflight, actual option-kind mapping, session validation and sticky callback failure. Translate SDK values to internal events/outcomes here. |
| Process/transport supervisor | One owner launches with cwd/argument vector and cleared allowlisted environment, drives SDK over caller-owned pipes, bounds work, cancels and cleans up. `OwnedChild` is a probe prototype, not a finished production abstraction. |
| Application/outcome | Backend terminal status, client violation, cancellation and cleanup must all feed the attempt result. Keep possible side effects/uncertainty separate from a text marker or child exit. No retry/fallback loop is added. |
| Project/output services | Python disposable config/recorder and summary counts are evidence fixtures. Phase 2 must implement project-only sync/validation and useful bounded progress/diagnostics in Rust; the loopback recorder is not the production route. |

These observations validate responsibility separation in DESIGN, not every proposed type name or a public API. Keep one package and introduce concrete modules with consumers. Raw JSON callback inspection and marker assertions are experiment scaffolding, not production event normalization.

## Shutdown reassessment and remaining work

The probe's **180 s** overall bound, **15 s** cancellation-response bound, **300 ms** TERM grace and **5 s** direct-child reap bound are test settings. Its group-wide KILL even after leader exit is necessary for the resistant-descendant fixture. The 300 ms delay establishes forced termination, with no evidence of graceful application state flushing. Select the supervision sequence, not that grace interval, for production. P2.4 must choose/test production budgets, cancellation races, pipe draining, group verification and uncertain cleanup using coding tools; do not claim a production flush guarantee or release with probe settings assumed adequate.

| Follow-up owner | Required before its consuming milestone |
|---|---|
| P1.7 | Review all integrated Phase 1 deliverables and this evidence; record/remediate findings before phase exit. |
| P2.1 / P2.4 | Finalize request/config/exits and enforce useful headless coding permissions. Live grants, writes, shell/tests and their scope are unverified; default-deny feasibility alone does not enable coding. |
| P2.3 | Rust project-only transactional config sync and effective-route checks including `--no-sync`, inherited helpers/tools and sentinel credential protection. Isolated probe configuration is not proof for arbitrary projects. |
| P2.4 | Implement supervisor, bounded stdout/stderr/events, shutdown budgets and side-effect-aware failure/cleanup outcomes. Probe stderr is discarded, SDK malformed-frame failures can await outer deadline, and production backpressure is unverified. |
| P2.5 | Produce initial binary and complete license/notice bundle for the actual release graph/target; inventory identifies missing schema archive text and inactive r-efi attribution follow-up. |
| P2.6 | Real project edit/test with the binary and comparison to direct OpenCode; text-only probes do not satisfy this gate. |
| Phase 4 / future target work | Capability/version policy and declared target matrix. Linux/Windows, detached process-group containment, usage/effort/skills/MCP mappings and remote-inference cancellation remain unverified. |

No OS/network sandbox, proxy service management, native subscription route, automatic retry or broad platform support is claimed. Existing live evidence resolves the earlier unavailable-host blocker; endpoint/alias availability is still an external prerequisite for future runs. No credential values or private transcripts are recorded.

## P1.5 validation

From the repository root with `~/.cargo/bin` on PATH:

```bash
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo run --locked -- --version
cargo +1.88.0 build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo +1.88.0 fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo +1.88.0 clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
python3 scripts/experiments/acp_lifecycle.py --runtime --opencode /opt/homebrew/bin/opencode
zsh -ic 'python3 scripts/experiments/acp_lifecycle.py --live --opencode /opt/homebrew/bin/opencode --endpoint http://litellm:4000/v1 --model macmini-qwen3-coder-30b --scenarios text instruction'
git diff --check
```

Root formatting/Clippy and all 11 tests pass at the new floor; `ah --version` prints `ah 0.1.0`. Locked experiment build/format/Clippy pass. All seventeen adversarial cases passed with child/descendant absence. Real OpenCode local-stub text/instruction/deny/cancel and the unavailable endpoint passed. Fresh authenticated live text (four chunks) and instruction (two chunks) probes passed: both `end_turn`, expected marker, correct primary/helper alias, zero tool/permission events, direct-child reap and no live group members. The instruction sentinel occurred in the primary wire request only. Markdown file links and whitespace checks passed. PR review is recorded below. Live probes use disposable projects and the existing environment key; the selected credential value and raw assistant/provider output are withheld. No denial/cancellation live replay is needed to replace the already merged P1.3 evidence.


## PR review

[Grok review on PR #12](https://github.com/awesomejt/agent-harness/pull/12#pullrequestreview-5739712973): one completed review, 0 blockers, 0 concerns, 1 nit. Added this explicit review section to resolve the dangling review-record reference, updated PROJECT.md with the PR/review outcome, and verified local Markdown file targets and `git diff --check`. No re-review is required for the nit under the Git workflow. P1.5 completion takes effect on PR #12 merge; P1.7 remains the required holistic phase review.
