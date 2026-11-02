# P1.3 — Lifecycle, permissions and effective routing

Date: 2026-11-01–02 (America/Denver). Baseline: `bc18b18` (PR #10 merged). Task: [P1.3](../../tasks/01-integration.md#p1-3). Platform: Apple Silicon macOS, `aarch64-apple-darwin`. This is disposable integration tooling, not an `ah single` implementation or a phase-exit review.

## Rust protocol experiment

The [standalone experiment crate](../../scripts/experiments/acp_lifecycle/Cargo.toml) compiles and runs the official ACP SDK **3.6.0**, stable protocol 1, with no SDK features. Its committed lockfile resolves schema **1.13.0**, Tokio **1.48.0**, tokio-util **0.7.16**, libc **0.2.177**, and serde_json **1.0.145**. Rust **1.88.0** builds and lints it successfully. The public package/toolchain stays on Rust 1.85.0; no production dependency is adopted. [D022](../../DECISIONS.md#2026-11-02--d022-validate-sdk-wire-reuse-in-an-isolated-lifecycle-experiment) records the consuming-phase decision.

Rust owns launch and cleanup: explicit argument vector, project cwd, `env_clear` plus an allowlist, a new Unix process group, separately discarded stderr, total protocol/text byte bounds, an overall deadline, ACP cancellation, SIGINT handling, bounded TERM→KILL escalation and direct-child wait. SDK `ByteStreams` operates on caller-owned Tokio pipes via compatibility adapters. No SDK launcher, inner tool loop, retry, native route or fallback is added. Error bodies and assistant text are withheld; safe counts, markers and terminal/cleanup summaries are printed. Cleanup escalation applies to the entire group even if its leader exits first.

The [Python driver](../../scripts/experiments/acp_lifecycle.py) prepares a fresh Git-rooted project and HOME/XDG tree, verifies resolved config and the final effective `build` permission rules before each prompt, and launches the Rust probe with only the selected credential reference. No global/persistent config or proxy service changes occur. The live credential comes from the existing environment (`LITELLM_API_KEY`, supplied through interactive Zsh); generated configuration contains only `{env:AH_PROBE_API_KEY}`.

## Effective route and instructions

A loopback request recorder forwards only `/v1/chat/completions` to the explicit existing LiteLLM API base. It checks the serialized model alias before forwarding, holds request bodies only in memory, and prints only model, tool names and sentinel-presence booleans. This observes actual outbound model payloads rather than trusting flags/session metadata alone. Authenticated discovery first confirms the existing alias. The runtime's sole enabled provider and primary/helper model both select `harness-preflight/macmini-qwen3-coder-30b`; ACP session configuration independently confirms this selection. Inherited runtime overrides and other provider keys are excluded.

Live host: user-supplied `http://litellm:4000/v1`; alias: `macmini-qwen3-coder-30b`; OpenCode **1.18.30** (Homebrew **1.18.30_2**); Python **3.14.7**. Remote LiteLLM version remains unreported. Two requests can occur for one prompt: OpenCode's separate title-generation request and its primary request. Both use the selected alias. The helper request has no project instructions; the primary instruction-test request contains the marker from `AGENTS.md`. The instruction-test prompt itself contains no marker. The live assistant returns that exact marker, resolving the earlier P1.2 instruction-loading/conformance uncertainty for this tested setup.

Pinned source supports interpreting these observations: [instruction loading](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/session/instruction.ts), [prompt/title path](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/session/prompt.ts), and [ACP permission mapping](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/acp/permission.ts). These links describe OpenCode 1.18.30, not all releases.

## Permission and lifecycle results

| Check | Evidence / outcome |
|---|---|
| Live text, streaming, terminal | Exact explicit marker; streamed assistant chunks; `end_turn`; no tools or permission requests. |
| Live project instructions | Primary wire request contains the `AGENTS.md` marker absent from the prompt; assistant returns it exactly; `end_turn`; no tools. |
| Live denial callback | Only `read` is exposed, configured `ask`; all other permissions deny and tools disable. Rust maps actual ACP option kinds through the existing default-deny policy and selects advertised rejection. Two callbacks were rejected in the initial live denial run; no grant or allow response exists. The file-content sentinel never appears in observed model requests. |
| Deterministic runtime denial | Local model stub requests one read, OpenCode emits tool progress, Rust rejects one callback, OpenCode terminates with `end_turn`. This separates callback enforcement from model compliance. |
| Live cancellation | Cancel notification sent after the first assistant message chunk while the turn is pending; `stopReason: cancelled` returned within the 15-second cancellation grace. |
| Unavailable service | Real OpenCode uses `http://127.0.0.1:9/v1`; prompt returns an ACP error, never success; cleanup completes. No harness retry or alternate route occurs. Runtime-internal waiting/retries are not claimed absent. |
| Actual process cleanup | After every runtime attempt, the direct child is reaped and `ps` confirms no live member of its process group. This includes text, instructions, denial, cancellation and unavailable-service cases. |
| Adversarial child/descendant | Seventeen cases below verify cleanup even with a descendant ignoring SIGTERM, including when the parent exits before cleanup. `ps` observes both PIDs absent or zombies; zombies are terminated, not running descendants. |

The denial fixture uses canonical paths (`Path.resolve`) because macOS `/var` and `/private/var` spellings otherwise make a project file appear external to OpenCode and trigger an earlier external-directory denial instead of the intended read callback. The initial development variant correctly failed its callback-count assertion; this was fixture friction, not a permission bypass. The effective rules are checked in the backend's actual normalized order (`read: ask` precedes the external-directory denials).

Default SDK client capabilities advertise no filesystem or terminal service. Explicit handlers fail filesystem/terminal requests; no such operation is implemented. Permission identity/session and option validation reject malformed/duplicate requests. No live allow-once grant, write, shell command, interactive approval or response-delivery retry is claimed. Earlier synthetic grant tests remain policy evidence only.

## Repeatable checks

From the repository root, with `~/.cargo/bin` on PATH:

```bash
rustup toolchain install 1.88.0 --profile minimal --component rustfmt,clippy
cargo +1.88.0 build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo +1.88.0 fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo +1.88.0 clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
python3 scripts/experiments/acp_lifecycle.py --runtime --opencode /opt/homebrew/bin/opencode
zsh -ic 'python3 scripts/experiments/acp_lifecycle.py --live --opencode /opt/homebrew/bin/opencode --endpoint http://litellm:4000/v1 --model macmini-qwen3-coder-30b --scenarios text instruction deny cancel'
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
```

Only `--live` forwards to the explicit external service. `--runtime` uses a local model stub (and the deliberate unavailable loopback endpoint); default mode uses the [fake ACP child](../../scripts/experiments/acp_lifecycle_fake.py) without OpenCode/model traffic. Its seventeen cases: text, instruction, denial, cancellation, EOF before completion, malformed JSON, wrong model, wrong session, duplicate option IDs, cancellation when no denial is advertised, permission-response transport closure, oversized output, unexpected filesystem request, overall deadline, SIGINT, early session-setup notification, and oversized assistant text. Wrong-session, malformed-option, filesystem-request and both output-bound cases explicitly require the client's sticky protocol-violation outcome even when the fake peer continues toward `end_turn`; they do not rely on a fixture assertion crash or missing marker. Each checks child/descendant termination. Poisoned provider/runtime environment variables are asserted absent in the child. Fake deadlines use the bounded driver-only `AH_EXPERIMENT_DEADLINE_SECS=8`; it is never forwarded to OpenCode. Normal overall deadline is 180 seconds.

Root Rust formatting, locked Clippy and all 11 tests passed. The standalone crate's locked build, formatting and Clippy passed. The adversarial suite and real OpenCode checks passed; live text/instruction/denial/cancel passed against the supplied alias. No raw model output or credentials are committed.

## Limits and handoff

- No OS/network sandbox is claimed. Process-group cleanup does not contain descendants that deliberately create a new session/group. macOS is the only tested platform; Linux/Windows require their own evidence and supervision design.
- No proxy-internal routing/physical hosting or server version is inferred from the alias. The loopback recorder is an experiment observation point, not the Phase 2 routing architecture.
- Model conformance and number of tool requests vary. No automatic replay occurs after an uncertain prompt. Process termination does not prove downstream model computation stopped or that coding side effects would be absent.
- The disposable probe uses a fixed 300 ms TERM grace followed by unconditional group KILL. This is termination evidence, not proof of graceful state flushing; P1.5 must reassess production shutdown grace.
- SDK malformed-frame/connection behavior is bounded by our deadline even when it does not terminate immediately. A failed permission delivery/EOF is a failed/possibly uncertain attempt, never approval or success. Production outcome/exit conventions remain P2.1/P2.4.
- P1.5 must select final transport/dependencies and production toolchain, reconcile module/contracts and audit the resolved dependency/license graph for distribution. SDK candidate licensing was inspected in P1.4; this PR ships experiment source/lockfile, no prebuilt binary or copied upstream source. P1.7 still gates Phase 2.

## PR review remediation

[Grok review on PR #11](https://github.com/awesomejt/agent-harness/pull/11#pullrequestreview-5733068139): initial review, 0 blockers, 2 concerns and 2 nits. Addressed all four: SDK handler errors now set a sticky attempt violation and wake the owner for immediate cleanup; setup metadata arriving before session identity is stored is tolerated without accepting early text/tool activity, and later wrong-session traffic explicitly fails; fixtures continue toward success after invalid callbacks to test the client itself; zombie status handling uses `startswith('Z')`; fixed 300 ms escalation is explicitly limited above. Added a sixteenth early-notification case. The updated sixteen-case suite and locked experiment build/format/Clippy pass. Post-fix live text/instruction checks passed; the denial scenario then returned an ACP prompt error with successful group cleanup and no client protocol-violation signal. The raw provider/runtime cause was withheld and is not diagnosed. A separate diagnostic denial/cancellation attempt passed (two denials, `end_turn`; then one streamed chunk and `cancelled`). No failed attempt was automatically replayed and no grant or coding side effect was authorized. This is recorded as backend/model variability, not a clean first-attempt success claim. Production adoption and phase acceptance remain open.


[Follow-up Grok review](https://github.com/awesomejt/agent-harness/pull/11#pullrequestreview-5733123454): 0 blockers, 0 concerns, 1 nit. Tightened output-bound fixtures to require explicit client violation: the total wire-byte limit now wakes cleanup immediately, and a separate seventeenth case sends valid oversized assistant text to exercise the 100 KB text cap. Both must fail via the client violation, independent of EOF/deadline. Seventeen cases and experiment formatting/Clippy pass after this fix; no further review is required for the nit. Two reviews completed; two explicit review-trigger comments were sent (the latter standalone after no response to the multiline trigger); no further review requests are permitted in this PR under the conservative three-request accounting.
