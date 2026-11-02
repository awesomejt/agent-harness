# P2.2 — Local-only single coding run

Date: 2026-11-02 (America/Denver). Entry baseline: `2e0a6ea` (P2.3 PR #16 merged). Task: [P2.2](../../tasks/02-first-slice.md#p2-2). Platform: Apple Silicon macOS, `aarch64-apple-darwin`; Rust/Cargo 1.88.0, OpenCode 1.18.30, Python 3.14.7. Acceptance is effective only after this task PR completes required review and merges.

## Delivered boundary

`ah single` resolves the strict P2.1 configuration/input contract, prepares the P2.3 transaction, verifies the isolated OpenCode effective route/permissions, applies the project-only plan and runs one ACP coding turn. Inline, file and explicit stdin inputs work. Unsupported modes/versions/capabilities and preview refuse; no native route, fallback, retry or separate tool loop is introduced. OpenCode owns reads/edits/shell execution. See [D026](../../DECISIONS.md#2026-11-02--d026-isolated-first-slice-acp-execution-and-exact-coding-grants).

Production dependencies now consume SDK 3.6.0, schema 1.13.0, Tokio 1.48.0 and tokio-util 0.7.16 (compat plus cancellation token support). This activates the Phase 1 selected stack; no process-launch framework or custom agent loop is added. Root/experiment lockfiles are updated for their shared local package. The Phase 1 [dependency inventory](p1-5-dependencies.md) covers the selected stack, but is not a claim that the new root resolution has identical transitive versions. Distribution/notice refresh remains a P2.5 gate; no binary is published here.

## Checks before live coding authorization

Final local validation: formatting, locked Clippy with warnings denied, all 37 Rust tests, locked standalone experiment check, and the 38-case public CLI suite pass. The suite also includes a matching no-sync repetition.

The public-CLI [fake OpenCode suite](../../scripts/tests/single.py) invokes the actual `ah` binary against disposable config/version/ACP children. It checks invalid inputs before launch/writes, inline/file/stdin, effective helper-route mismatch, version refusal, widened permission rules, reversed agent-rule order, default denial, each trusted action kind, exact external-directory shape, unknown kinds, missing allow-once, wrong-kind/unbound grants, malformed IDs/options, wrong-session traffic, unexpected filesystem write, EOF/oversized output, before-prompt cancellation, active interruption/deadline, backend cancellation and session-model refusal. Child fixtures include a descendant ignoring TERM; direct/descendant process status must be absent or zombie after every attempt. A matching no-sync repeat preserves config/receipt/lock bytes and mtimes. Sentinel credentials must be absent from stdout/stderr and generated project files. These are controlled tests, not evidence of proxy availability.

The installed-OpenCode [runtime test](../../scripts/tests/single_runtime.py), without `--live`, runs a deterministic local SSE model stub. It requests an outside-project file read, project file read, actual edit and a shell command accessing the outside file then running the test. Result: six separate permission requests/grants, 16 tool events, `end_turn`, CLI exit 0 and confirmed cleanup. `calc.py` changes `return a - b` to `return a + b`; `python3 test_calc.py` passes in the runtime and independently afterward; a success-only `verified` marker exists. All six observed model requests, including the helper request, use the fixture alias. Only read/search/edit/write/bash built-ins are exposed; task/subagents, MCP, skills and web tools are absent. This enforcement check preceded the live coding prompt.

Integration friction resolved before acceptance:

- Legacy `tools` settings can introduce permission auto-allows. Explicit `apply_patch: ask` and exact effective rule checks prevent that widening.
- OpenCode appends an external tool-output auto-allow unless specifically overridden. The generated policy names that private path explicitly, and validates the ordered rule suffix.
- Read permission callbacks contain empty raw metadata. The adapter joins full arguments from the matching same-session tool event. OpenCode reports `in_progress` while still waiting for permission; terminal updates retire descriptors. The initial implementation denied these requests and the controlled test failed, rather than falsely claiming coding success.
- The pinned runtime attempts optional editor-side write synchronization despite absent client filesystem capability. Only the exact already-granted edit/path receives an unsupported non-mutating response; OpenCode performs its own authorized edit. Other client filesystem callbacks fail the attempt.
- File and shell external-directory callbacks have distinct metadata shapes. Both require a supported underlying tool, exact allow-once grants and the explicit trusted profile.

## Live LiteLLM coding result

Endpoint: user-supplied existing `http://litellm:4000/v1`; alias `macmini-qwen3-coder-30b`; key source: existing environment loaded by interactive Zsh. No key values, raw prompts/responses, transcripts or temporary paths are committed. Remote LiteLLM version remains unreported.

The test creates a fresh Git-rooted project with a faulty arithmetic function and an assertion test, then asks `ah single --permissions trusted` to read/fix the function and run its test. A loopback observation point forwards only `/v1/chat/completions` to the explicitly selected existing endpoint and checks every outbound model field. This is test observation, not a new harness proxy service.

- First live trial: exit **4 (uncertain)** without a trustworthy terminal response; eleven wire requests all used the selected alias. No automatic replay/fallback occurred. The driver discarded that disposable test project; file effects were not captured before disposal, so no successful-edit claim is made for that trial. It remains a recorded unsuccessful attempt, not a clean first-attempt claim.
- Separate trial in a **new disposable project**, with a 300-second explicit bound: four permission requests, four allow-once grants, 16 tool events, backend `end_turn`, confirmed cleanup, exit **0**. Seven wire requests (including helper) all used the selected alias. The function was fixed, runtime verification created the success-only marker, and an independent `python3 test_calc.py` passed. The two trials share no project/session state and the harness performs no retry.

No direct-OpenCode coding comparison or installed-release use is claimed; those remain P2.6. Live coding demonstrates a real project/tool loop, not text-only completion.

## Repeatable commands

```bash
export PATH="$HOME/.cargo/bin:$PATH"
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --locked
python3 scripts/tests/single.py
python3 scripts/tests/single_runtime.py
zsh -ic 'python3 scripts/tests/single_runtime.py --live'
cargo check --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
```

Only `--live` forwards to the existing external service. Controlled checks and root tests do not contact a model service. Runtime tests use temporary projects and HOME/XDG trees; they do not edit the user repository or global OpenCode configuration. The development binary is not an installable release artifact.

## Remaining scope and limits

P2.4 owns ongoing progress/IDs/usage, richer bounded stderr diagnostics, graceful ACP cancellation and adversarial hardening. Current assistant output is buffered up to 1 MB; total ACP input is 8 MB; child stderr is discarded. Active interruption without a terminal response remains uncertain even with successful local cleanup. No inference is made that local cleanup stops remote inference.

The macOS supervisor sends group TERM, waits up to 500 ms while the leader remains active, sends KILL, allows five seconds to reap and uses bounded process-status checks to verify no live original-group members. Detached groups and arbitrary shell effects are outside containment. Synchronous filesystem operations depend on OS completion; timeout/signal checks run again before a subsequent launch. P2.7/P2.8 still own preview/prerequisite and dirty-baseline reporting; P2.5/P2.6 own release installation and full first-use evidence. Phase 2 remains open until its holistic review passes.

## PR #17 review remediation

Initial [Grok review](https://github.com/awesomejt/agent-harness/pull/17#pullrequestreview-5741673810): 0 blockers, 1 concern and 3 nits. Added callback/shared-argument and normalized-path consistency checks with negative tests; generated edit diffs remain backend metadata rather than independent verification. Executable discovery now skips relative/empty PATH entries and non-executable files, with rogue-project-executable fixtures. Already-exited preflight leaders skip the unnecessary grace sleep, while descendants still receive group KILL and verification. After one cleanup escalation, Drop no longer sends another delayed group signal following leader reap; numeric process-group identity still has ordinary Unix reuse limits. Also moved the absolute deadline immediately after prompt resolution so planning/runtime setup consume the same bound, and made confirmed terminal outcome authoritative over a concurrent cancellation signal. Post-fix local checks cover these changes; the live result above predates this review tightening.

[Second Grok review](https://github.com/awesomejt/agent-harness/pull/17#pullrequestreview-5741739817): all four initial findings confirmed addressed; 0 blockers, 1 compatibility concern, 0 nits. Added empty-object and omitted/null read-metadata fixtures and accepts absent metadata only while retaining the complete matching tool descriptor requirement. Non-object metadata and conflicting shared arguments still refuse grants. Installed-OpenCode controlled read/edit/shell/external-access verification is rerun after the change.
