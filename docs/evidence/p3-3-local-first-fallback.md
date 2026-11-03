# P3.3 (part 2 of 2) — Configured local-first fallback

Date: 2026-11-02. Entry: `7204784` (merged P3.3 part 1 / PR #27). Task branch: `feature/03/p3-3-local-first-fallback`. This is the second PR the [P3.3 card](../../tasks/03-routing.md#p3-3) allows. It adds the configured local-first coordinator and completes P3.3. [D034](../../DECISIONS.md#2026-11-02--d034-local-first-fallback-only-on-pre-submission-litellm-reachability-failure) records the decision. The [configuration contract](../CONFIGURATION.md#local-first-route-p33--d034) and [execution contract](../EXECUTION.md#failure-and-fallback) define the behavior.

## Delivered behavior

- `local-first` is accepted in config and `--mode`. It requires `litellm`, a local model default (or `--model`) and `native`. Both key references are checked before stdin or prompt-file input. A missing route or key exits 2 with no launch or network contact.
- Resolution produces the LiteLLM primary plus one boxed native fallback request. The fallback uses `native.model`, and `--model`/`group:` apply only to the primary. The fallback carries identical project, permissions, timeout and prompt, and it cannot nest.
- Pre-submission evidence (new `probe` module): one TCP connect per resolved address on a plain worker thread, within a five-second budget inside the overall deadline. No bytes, credential or HTTP request is sent. Resolution failure, or a refused, unreachable or timed-out connection on every address, gives `Transport`. Other errors give `Unknown`. Cancellation or deadline overrides any concurrent result.
- The check runs after static validation and read-only plan preparation, and before local runtime construction, private HOME, preflight and project apply. `recovery::decide` receives `NotAttempted`, confirmed cleanup (nothing was created) and checked constraints. When it permits fallback, one linked native attempt runs. That attempt has the same `run=`, the `attempt=2` prefix, a new private runtime, fresh grants, the full native preflight, and the shared deadline and signal watcher. Its outcome is final.
- When the endpoint is reachable, the unchanged local attempt runs and every later failure stops without fallback. An inconclusive check exits 1, and a cancelled or expired check exits 3.
- Attempt identity: `Progress::attempt(n)` prefixes all adapter diagnostics, replacing the hard-coded `attempt=1` literals. Local-only and cloud-only output is unchanged. The final line reports the recovery outcome, for example `fallback=attempt 2 (native) after pre-submission LiteLLM transport failure`.
- Signals: one invocation-wide SIGINT/SIGTERM watcher now feeds every attempt, so a signal between attempts is not lost.
- Preview reports `mode: local-first`, the route and the configured fallback target, and stays network-free. Help lists the mode.
- No new dependency, Tokio feature, flag or command. `Cargo.lock` is unchanged.

## Validation

Tested on macOS 27.0.1 arm64, Rust/Cargo 1.88.0 and OpenCode 1.18.30. All commands are non-spending, and fixture keys are synthetic.

| Command | Observed result |
|---|---|
| `cargo test --locked` | 54 tests pass: the prior 49, plus 3 probe tests and 2 local-first config tests. The probe tests cover a listening endpoint receiving zero bytes; refused IPv4/IPv6 and unresolvable `.invalid` endpoints; and cancellation or expired deadline overriding a concurrent result. The config tests cover primary/fallback resolution with `--model` affecting only the primary; group primaries; missing route blocks/model; and each missing key rejecting before stdin. The two prior "local-first unavailable" expectations now cover an unknown mode. |
| `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo build --release --locked` | Pass. |
| `python3 scripts/tests/local_first.py` | 17 cases pass. **Reachable:** local only for success (0), session-model (1), rpc-error (4) and preflight version (2); `--no-sync` on a fresh project rejects statically (2). The listener records ≥4 connections and zero received bytes. **Unreachable (closed port or unresolvable host):** exactly one native attempt for success (0), trusted read (0), rpc-error (4), session-model (1) and deadline cancellation (3). A native preflight failure exits 2 with no further attempt. Fallback runs write no `opencode.json` or receipt, and each private runtime home is removed. **Static:** a missing native or local key, or preview, makes zero listener connections. **Blackholed 10.255.255.1:** SIGINT and deadline during the check exit 3 with no launch. Prompt or key sentinels never leak. |
| `python3 scripts/tests/native_runtime.py` | Installed OpenCode 1.18.30 runs the native setup for deny/trusted, then a local-first project with a closed LiteLLM port. The fallback passes real native preflight and the ACP session, the prompt is intercepted (none forwarded), and no managed files are created. |
| `python3 scripts/tests/single.py`, `native.py`, `preview.py`, `worktree.py` | 59, 32 (zero LiteLLM requests), all preview and all worktree fixtures pass. Local-only progress still reports `attempt=1`. |
| `python3 scripts/tests/single_runtime.py [--cancel] [--group coder]` | All four variants pass: actual edit/test, group wire routing and confirmed cancellation. |

## Limits and next step

- Reachability is the only eligible evidence. It does not establish proxy-group or deployment availability. A reachable proxy that rejects, rate-limits or lacks the group fails locally without fallback. That is conservative under D031, but it means fallback covers only an off, unreachable or unresolvable proxy.
- A mistyped LiteLLM host in local-first looks unresolvable and falls back to native. Progress says so, and preview shows the target.
- No live LiteLLM or native inference ran for this PR. P3.4 owns the full mode-boundary matrix. P3.5 owns live local-only, native cloud-only and eligible-fallback use.
