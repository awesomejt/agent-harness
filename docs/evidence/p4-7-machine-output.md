# P4.7 — Versioned machine and CI contract

Date: 2026-11-03. Entry baseline: `78e4af1` (merged P4.3 PR #36).
Task branch: `feature/04/p4-7-machine-output`. Platform: Apple Silicon
macOS, Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered contract

[D039](../../DECISIONS.md#2026-11-03--d039-opt-in-version-1-machine-records-with-unchanged-exits)
and [EXECUTION](../EXECUTION.md#p47-machine-output-d039) define:

- Selection: `--output human|jsonl`; `human` is the default and unchanged. The
  adjacent pair `--output jsonl` is detected before validation, so rejected
  machine invocations still end in a result record. `--output jsonl --preview`
  rejects; preview stays human-only.
- Stream: stdout carries only `\n`-terminated JSON Lines; human diagnostics stay
  on stderr. Envelope `v`/`seq`/`run`/`type`/`ts_ms`/`elapsed_ms` plus `attempt`
  on attempt-scoped records. Ten record types, ending in exactly one `result`.
- Result: an explicit `outcome` mapping of exits 0–4, `exit`, static `reason`,
  final `response` (moved off raw stdout), per-attempt summaries with
  submission/backend stop/cleanup/counters/runtime-state removal/usage, `fallback`,
  `recovery`, `diagnostics_omitted` and `records_dropped`. Unknown metrics are
  `null`, never zero.
- Delivery: one ordered writer thread, 256-record queue, `seq` assigned under the
  queue lock. Non-terminal drops leave counted gaps; cumulative counters are
  repeated in the result. The result is written last within two seconds. An
  undelivered success becomes exit 1; other exits are unchanged.
- Compatibility: refuse `v` ≠ 1; additive types/fields/values within v1; removal,
  renaming, retyping, meaning changes or a new `outcome` require v2.
- Redaction: no prompt, partial text, reasoning, tool arguments, raw stderr,
  provider errors, paths, endpoints, environment names or key values.
- Headless: no change to the noninteractive input/permission behavior; CI usage
  is documented in [OPERATIONS](../OPERATIONS.md#headless-and-ci-use-p47).

## R03-REC1 evaluation (declined)

Phase 3 recommended exit 1 for a post-submission provider failure with zero
grants and zero completed tool calls. It is declined. The ACP adapter still
cannot classify provider rejections, and D031/EXECUTION state that absent tool
events do not prove no tool ran. Turning that observation into a known outcome
would weaken the uncertainty precedence that consumers rely on. Exit 4 stands.
The result record exposes the evidence instead (`prompt_submitted: true`,
`backend_stop: null`, `grants: 0`, `tool_events: 0`), so a consumer can apply its
own policy. Fixture `rpc-error` asserts exactly this.

## Test evidence

`cargo test --locked` (Rust 1.88.0): 78 root tests pass (76 before this task).
New:

- `tests/cli.rs::machine_output_rejections_end_in_one_result_record`: missing
  config, `--preview`, duplicate option and missing prompt each produce exactly
  `run.started` + `result` (`rejected`, exit 2, static reason, empty attempts),
  human stderr only; `--output xml` and a missing value stay human-only with
  empty stdout.
- `tests/config.rs::output_format_parses_and_machine_mode_is_detected_before_validation`.

`cargo fmt --check` and `cargo clippy --locked --all-targets -- -D warnings`
pass.

`scripts/tests/machine.py` (new; fake OpenCode 2.2.5, no model traffic) uses an
independent consumer validator. On every run it checks that each stdout line
parses, `v` is 1, `run` is constant, `seq` is strictly increasing and gap-free
when nothing was dropped, `elapsed_ms` is nondecreasing, `run.started` comes
first and exactly one `result` comes last, `outcome` matches the exit, every
attempt has the full key set and a null `turn_tokens`, stderr lines are all
`ah: ` diagnostics, and the key, prompt and project path never appear. Cases:

| Case | Exit | Specific assertion |
|---|---|---|
| `text` with open, unread stdin | 0 | No hidden wait; `response` "OK"; record order; usage all `null` |
| `usage` / `usage-invalid-cost` | 0 | Reported context/cost with source; invalid cost `null` |
| `read` trusted | 0 | 1 request, 1 grant |
| `known-failure` | 1 | `backend_stop` `other`, no response |
| `backend-cancelled` | 3 | `backend_stop` `cancelled` |
| `deny-completed` | 4 | `protocol_violation`, no response |
| `rpc-error` | 4 | R03-REC1 shape: submitted, no stop, 0 grants/tools |
| SIGINT after prompt | 4 | Submitted, result still delivered |
| `--preview`, duplicate `--output` | 2 | Two records; reason |
| Preflight version mismatch | 2 | Attempt not launched |
| Blocked stdout (900 KB response never read) | 1 | Exits within bound; undelivered success becomes 1 |
| Local-first, closed endpoint | 0 | Two attempts, `fallback` record, attempt 1 not launched, later records attempt 2 |
| Human mode (default and explicit), `--output xml` | 0/2 | stdout exactly `OK`; invalid value human-only |

| Missing key reference | 2 | `reason` names the missing key reference |

Result: `PASS machine output fixtures` (16 runs).

Existing fake-runtime suites rerun unchanged against this build: `single.py`,
`preview.py`, `modes.py` (165 cases), `native.py` (40 cases), `local_first.py`,
`agents_exec.py` and `worktree.py` all pass. Human stdout/stderr behavior is
unchanged.

## Installed-runtime evidence (OpenCode 2.2.5, local deterministic model stub)

`single_runtime.py` gains `--jsonl`, which adds `--output jsonl` and validates the
records:

- `--jsonl`: exit 0, actual `calc.py` edit and independent arithmetic test pass.
  26 records: `run.started`, `attempt.started`, `attempt.session`,
  `attempt.prompt_submitted`, 19 `attempt.activity`, `attempt.backend_stop`
  (`end_turn`), `attempt.cleanup`, `result` (`succeeded`, string response,
  5 requests/5 grants/13 tool events, usage all `null`; the stub sends no usage).
- `--jsonl --cancel`: exit 3 after the edit/test; result `cancelled`, records
  ordered, cleanup and runtime-state removal confirmed.

No live provider inference was needed: the contract covers harness output, and
the installed runtime and real tool calls are exercised through the stub.

## Review closeout

Grok PR #37: 0 blockers, 1 concern, 1 nit. The concern was that runtime-phase
exit 2 paths (missing runtime/key, preflight mismatch) left `reason` null. Fixed:
each now sets a static reason, and fixtures assert it for preflight and a missing
key. The nit was that `launched`/`prompt_submitted` default to `false` while the
contract said unobserved fields are `null`. The contract now states that these
harness-owned boundaries are `false` until crossed; the code is unchanged.
Neither finding is critical/high, so no re-review is required.

## Boundaries

- Machine output covers `single` only. Sequence/workflow records and durable
  state remain Phase 5.
- Human stderr is still not a schema. Abrupt termination (SIGKILL) produces no
  result; the exit code then governs.
- `reason` is human text, not a stable code. Stable rejection codes were not
  added; a later version may add them as an optional field.
