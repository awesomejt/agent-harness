# P1.4 — Narrow ACP/process dependency evaluation

Date: 2026-11-01 (America/Denver). Baseline: `edd253f` (PR #9 merged). Platform: `aarch64-apple-darwin`. This is a pinned-source evaluation, not a Rust SDK integration or platform certification. Task: [P1.4](../../tasks/01-integration.md#p1-4); decision: [D021](../../DECISIONS.md#2026-11-01--d021-keep-process-policy-owned-evaluate-sdk-wire-reuse).

## Decision and required features

Keep subprocess ownership in the harness using direct Rust process APIs. Reject `cli-stream` 0.5.0 and the official SDK's `AcpAgent` convenience launcher for this integration. Prefer evaluating the official SDK's protocol engine over caller-owned I/O in P1.3, rather than writing a complete JSON-RPC dispatcher. That protocol reuse is conditional: P1.3 must prove compatibility and justify a toolchain change before adoption; P1.5 finalizes dependencies/transport. No dependency, toolchain pin or public CLI changes in P1.4.

The required boundary is an explicit executable/argument vector, project cwd, cleared and allowlisted environment, piped input, separately drained stdout/stderr, bounded requests and shutdown, streamed notifications, D020 permission handling, and observable cancellation/reaping. A dependency must not choose routes, approve tools, inherit unvalidated runtime overrides, or implement another coding loop.

The [working P1.2 experiment](p1-2-live-acp.md) proves installed OpenCode 1.18.30 can use ACP protocol 1 with explicit project/model selection, streamed text and `end_turn` through the existing LiteLLM alias. Its [standard-library probe](../../scripts/experiments/acp_preflight.py) uses a minimal child environment and explicit process-group shutdown. This supports retaining direct process ownership; it does **not** establish Rust SDK compatibility, project-instruction conformance, live permission callbacks or descendant cleanup.

## Pinned releases and provenance

Published archives were downloaded from crates.io and inspected, including normalized manifests, source and VCS metadata. Versions were not inferred from repository HEAD.

| Candidate | Published release / VCS commit | MSRV / edition | .crate archive SHA-256 |
|---|---|---|---|
| [Official ACP SDK 3.6.0](https://docs.rs/crate/agent-client-protocol/3.6.0/source/) | 2026-10-28; `a978f01e8cde58a7976666a713531d8c9342fb51`, `src/agent-client-protocol` | Rust 1.88.0 / 2024 | `89b41f18aeb4a6d1a463b994cb880cc562cdea7d616ea3e22f9c6f2a438fc4f6` |
| [cli-stream 0.5.0](https://docs.rs/crate/cli-stream/0.5.0/source/) | 2026-09-05; `cd42566aab9e21903e96b4d59ab7e674f7fb415d`, `crates/cli-stream` | Rust 1.88 / 2024 | `26b460d6a2696c255a2802418ebf0fb2b1a31e440e9658fe4a9bae0389b0b257` |

Both exceed the current Rust 1.85.0 baseline. Neither was compiled here; no compatibility claim follows from source inspection. An older release was not selected simply to retain the current pin. A justified MSRV change is allowed by D019 but belongs with the actual dependency experiment and its locked build evidence.

## Comparison

| Option | Useful behavior / defaults inspected | Decision |
|---|---|---|
| Direct Rust `std::process::Command` and Unix process APIs | Explicit `env_clear`, cwd, argument vector, pipes and process-group setup; no protocol dispatcher, async executor, automatic deadlines, pipe limits or cleanup guard | Retain process-policy ownership. P1.3 must implement/verify supervision; selecting APIs is not proof of cleanup. Async I/O/runtime selection remains open. |
| Official SDK 3.6.0 protocol engine with caller-owned transport | Empty default feature set; `ByteStreams` accepts `futures::io::AsyncRead`/`AsyncWrite`, `Lines` accepts newline JSON. Typed requests, notifications and permission responders save dispatcher work. Caller must drive the connection future. | Preferred protocol-reuse experiment for P1.3, without `process`, `stdio` or unstable features. Verify exact protocol-1 schemas and runtime/I/O compatibility before adoption. |
| Official SDK 3.6.0 `process` feature / `AcpAgent` | `AcpAgentConfig` exposes command/args/env additions, but no cwd or environment-clear control. `spawn_process` starts with inherited environment and applies `envs`. Unix group guard kills on drop; Windows path sets no-window creation flags, without the Unix group guarantee. | Reject convenience launcher: it cannot express our child-environment policy. Do not copy the `yolo_one_shot_client` example's allow-once/allow-always approval logic. |
| `cli-stream` 0.5.0 | Piped stdin is opt-in (default null); stdout/stderr lines, 1024-event bounded channel, optional timeout (default none), Unix SIGTERM/group escalation and Windows Job Objects with best-effort fallback. `Command.env` adds to inherited environment; no environment-clear option. Handle drop does not cancel. | Reject leaf wrapper: patching its spawn policy and adding our own ownership guard erodes the implementation saved, and ACP still needs its own dispatcher. |

SDK source references: [manifest](https://docs.rs/crate/agent-client-protocol/3.6.0/source/Cargo.toml), [transport abstractions](https://docs.rs/crate/agent-client-protocol/3.6.0/source/src/lib.rs), [launcher](https://docs.rs/crate/agent-client-protocol/3.6.0/source/src/acp_agent.rs), [example](https://docs.rs/crate/agent-client-protocol/3.6.0/source/examples/yolo_one_shot_client.rs), [cancellation](https://docs.rs/crate/agent-client-protocol/3.6.0/source/src/concepts/cancellation.rs). Leaf wrapper: [process source](https://docs.rs/crate/cli-stream/0.5.0/source/src/process.rs).

## Lifecycle and compatibility limits

- SDK request cancellation (`$/cancel_request`) is cooperative; successful enqueue is not peer acknowledgement. Test OpenCode's protocol-1 `session/cancel` and terminal behavior explicitly, with bounded process shutdown if cooperation fails. Do not substitute request cancellation for session cancellation.
- The SDK supports protocol 1 and opt-in unstable protocol 2; OpenCode's observed session model is in `configOptions`. P1.3 must prove typed parsing, effective route selection and permission option mapping against this installed version. Wire type availability is not live compatibility.
- `cli-stream`'s wait thread joins pipe readers before emitting `Exited`. A descendant retaining a pipe can delay that event; a bounded channel can block readers when the receiver stops draining. Its Unix escalation is best effort and its comments do not prove descendants are gone. These are inspection risks, not reproduced failures.
- Harness-owned supervision must bound drains, preserve the original failure, reap the direct child, and verify descendants after leader exit, cancellation and unavailable service. EOF and group-signal success alone are insufficient. Escaped process groups remain a platform limitation to assess.
- Only macOS arm64 was exercised by the existing probe. Windows Job Objects, SDK Windows behavior, Linux and cross-compilation were inspected only; no platform support expansion is claimed.

## License and attribution inspection

SDK 3.6.0 declares Apache-2.0 and ships the Apache license in its archive. `cli-stream` 0.5.0 declares `MIT OR Apache-2.0`, but its published archive contains no LICENSE files. The matching [source commit](https://github.com/getlatentic/agent-harness/tree/cd42566aab9e21903e96b4d59ab7e674f7fb415d) contains [LICENSE-APACHE](https://github.com/getlatentic/agent-harness/blob/cd42566aab9e21903e96b4d59ab7e674f7fb415d/LICENSE-APACHE) and [LICENSE-MIT](https://github.com/getlatentic/agent-harness/blob/cd42566aab9e21903e96b4d59ab7e674f7fb415d/LICENSE-MIT) (copyright 2026 Tosin Amuda); both were retrieved and inspected. No candidate source was copied or shipped. If adopted, preserve the chosen license text, applicable copyright/NOTICE material, and audit the resolved transitive graph for binary distribution. Manifest labels alone are not a distribution attribution bundle.

## Repeatable inspection and validation

Download `https://crates.io/api/v1/crates/agent-client-protocol/3.6.0/download` and `https://crates.io/api/v1/crates/cli-stream/0.5.0/download`; verify the SHA-256 of each downloaded crates.io `.crate` archive against the table above and its sparse-index `cksum` (both matched in this evaluation), extract, and inspect `Cargo.toml`, `.cargo_vcs_info.json` and the linked source files. This requires no credentials, installation or model turn.

The unchanged no-prompt preflight was rerun on OpenCode 1.18.30: deny-all/tool-disable resolved configuration, protocol-1 initialize, disposable session with sole synthetic model and no MCP, then direct-child shutdown. No prompt or model traffic. Rust 1.85.0 formatting, locked Clippy and all 11 tests passed. These checks protect the baseline; they do not validate either candidate crate. Phase 1 remains open; P1.3 is next.

## PR review

[Grok review on PR #10](https://github.com/awesomejt/agent-harness/pull/10#pullrequestreview-5732900873): one review, 0 blockers, 0 concerns, 1 nit. Addressed by splitting MSRV/edition from archive SHA-256, explicitly identifying the hashed download, and checking both hashes against the crates.io sparse-index `cksum`. Documentation links and whitespace checks passed. No re-review required under the Git workflow.
