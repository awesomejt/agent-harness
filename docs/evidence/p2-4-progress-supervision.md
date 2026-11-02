# P2.4 — Progress, outcomes and bounded supervision

Date: 2026-11-02 (America/Denver). Entry baseline: `6b15e8a` (P2.2 PR #17 merged). Task: [P2.4](../../tasks/02-first-slice.md#p2-4). Platform: Apple Silicon macOS, `aarch64-apple-darwin`; Rust/Cargo 1.88.0, OpenCode 1.18.30, Python 3.14.7. Acceptance is effective on [PR #18](https://github.com/awesomejt/agent-harness/pull/18) merge after the required review closeout below.

## Delivered behavior

Human stderr now identifies each run, its single attempt, elapsed time, selected route/runtime/model, backend session, sampled assistant/tool activity, headless permission responses, five-second heartbeat, terminal response and cleanup. stdout remains final assistant text after backend `end_turn` and confirmed cleanup. Generic provider/transport failure does not expose raw backend errors or claim a more specific authentication/rate-limit diagnosis. Stable ACP session usage reports, when present, carry provenance, context token units and validated cumulative session currency cost. Missing reports and per-turn tokens remain unknown; reported session context is not billed per-turn usage.

Active SIGINT/SIGTERM/deadline sends `session/cancel` and allows five seconds for a terminal prompt response. ACK/text/EOF without that response remains uncertain (exit 4); confirmed cancellation returns 3, and racing confirmed success can return 0 after cleanup. New permission grants are denied after signal/deadline. Cancellation never rolls back earlier effects. No retry, native/cloud fallback, additional CLI flag or unstable ACP feature is introduced. See [D027](../../DECISIONS.md#2026-11-02--d027-bounded-human-progress-and-cooperative-cancellation) and the [execution contract](../EXECUTION.md#p24-selected-supervision-and-human-output).

Subprocess stderr drains concurrently using 8 KiB and retains only a saturated byte counter; raw text is withheld. Process-group cleanup allows two seconds for TERM, escalates KILL, reaps within five seconds, bounds stderr drain at 500 ms and independently verifies original-group termination. Diagnostic writing uses a 64-entry nonblocking queue and a separate OS thread; final summary is retained outside the queue and final drain gets one second. Final stdout writing has a two-second budget on its own thread. These allowances are additional to the active/preflight deadline. Blocked output consumers cannot prevent process cleanup.

## Verification

Rust formatting, locked Clippy with warnings denied, all 37 Rust tests and the locked standalone lifecycle experiment check pass. The public-CLI suite has 55 cases plus its existing matching-no-sync repetition. It preserves prior routing/permission/input checks and adds:

- Ongoing assistant activity before terminal response; present/absent usage, valid currency cost and invalid-cost redaction.
- Noisy binary stderr exceeding 1 MiB, malformed/truncated JSON, invalid UTF-8, RPC/provider failure, known non-success stop and unexpected EOF.
- Cooperative cancellation, deadline cancellation, ignored cancellation, ACK-only cancellation and racing success. A trusted post-cancel permission request is denied.
- A descendant ignoring TERM and inheriting stdout/stderr after the leader exits; total run remains bounded and original-group members are absent or zombie afterward.
- Blocked final stdout yielding exit 1 after confirmed backend completion/cleanup; an explicitly prefilled stderr pipe overflowing the diagnostic queue, then released to verify a positive omission counter and retained final outcome.
- Trapped native executable names and poisoned inherited provider settings never launch native fallback. A sentinel credential remains absent from output and project config/receipt.

The independent read-only review identified missing stable usage handling and held-pipe coverage; both were corrected and verified. Its remaining diagnostic-overflow evidence concern was addressed by prefilling the actual stderr pipe and asserting a positive omission counter. No raw transcripts or credentials are committed.

## Installed runtime and live observations

The installed OpenCode deterministic SSE test performs outside/project reads, an actual arithmetic fix and a shell test. Six exact allow-once grants, 16 tool events, `end_turn`, confirmed cleanup and exit 0 were observed; an independent arithmetic test passed. Every primary/helper request used the fixture alias. A separate fresh project uses `--cancel` after its actual edit/test: SIGINT produced `session/cancel`, backend `cancelled`, confirmed cleanup and exit 3 in about three seconds total. The edit and success-only test marker remained; independent arithmetic verification passed. This validates cooperative cancellation against the actual runtime without claiming effect-free cancellation or remote containment.

A separate fresh-project live trial used the existing user-supplied LiteLLM endpoint `http://litellm:4000/v1`, alias `macmini-qwen3-coder-30b`, with the existing environment credential (value not recorded). It applied the arithmetic edit and created the success-only verification marker, but lost the terminal response around 85 seconds: exit **4**, `terminal=0`, no protocol violation, four grants, 16 tool events and confirmed local cleanup. Eleven observed primary/helper requests all used the selected alias. The driver correctly failed its success assertion; it did not run the independent post-return arithmetic check. No successful live completion is claimed for this trial. No automatic replay/fallback occurred, and that disposable project was not reused. This records the same uncertain-terminal friction seen in P2.2; diagnosis remains limited because raw provider errors are intentionally withheld. The controlled runtime tests above establish the task's cancellation/output behavior; release/full-use gates remain P2.5/P2.6.

## Commands and limits

```bash
export PATH="$HOME/.cargo/bin:$PATH"
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --locked
python3 scripts/tests/single.py
python3 scripts/tests/single_runtime.py
python3 scripts/tests/single_runtime.py --cancel
cargo check --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
zsh -ic 'python3 scripts/tests/single_runtime.py --live'
```

Only `--live` forwards to the existing external service. All projects, config files and runtime HOME/XDG trees are disposable. This is a development binary, not an installable release. Detached groups, remote inference and arbitrary authorized shell effects remain outside process-group containment; unread/broken stderr may prevent final diagnostic delivery even though cleanup and numeric exits remain bounded. Machine output, preview, dirty-worktree reporting and packaging retain their later task boundaries. Phase 2 remains open.


## PR #18 review closeout

[Grok review](https://github.com/awesomejt/agent-harness/pull/18#pullrequestreview-5742403505): 0 blockers, one minor concern and one nit. The diagnostic writer now holds the global stderr lock only for each write, releasing it while idle; active supervision continues to use the bounded queue. Session diagnostics escape non-ASCII C1 controls and bidi characters before JSON encoding, retaining the bounded identity representation. A new Unicode/control session fixture verifies no raw terminal controls escape into diagnostics. Formatting, Clippy, Rust tests and all 55 public-CLI cases pass after these fixes. No critical/high finding remains; the workflow requires no re-review for these minor changes. One Grok review total.
