# P5.5 — Trusted verification gates

Date: 2026-11-03. Entry baseline: `53e1707` (merged P4.9 remediation PR #43; Phase 4 pass effective).
Task branch: `feature/05/p5-5-verification-gates`. Platform: Apple Silicon
macOS 27.0.1 (arm64), Rust 1.88.0, installed OpenCode 2.2.5.

## Why first in Phase 5

P4.6 R1 recorded a coder `succeeded`/exit 0 with zero tool calls and no edit. Only
an independent check caught it. The [Phase 4 review](../reviews/phase-04.md)
dispositioned R1 to P5.5 and scheduled it first. Gate semantics need no
sequence ordering, context or state choice, so D043 moves P5.5 ahead of P5.1.
P5.2 consumes both.

## Delivered contract

[D043](../../DECISIONS.md#2026-11-03--d043-trusted-verification-gates-for-single-runs-scheduled-before-sequence-decisions),
[CONFIGURATION](../CONFIGURATION.md#verification-checks-p55--d043) and
[EXECUTION](../EXECUTION.md#p55-verification-gates-d043) define:

- **Trust.** Commands come only from the harness config `checks.NAME = {argv,
  timeout_secs?}`: an argv vector without a shell, 1–64 checks, 1–64 arguments
  of at most 4096 bytes, no NUL, timeout 1–86400 s (default 600). A declared
  check is inert. Only `--verify NAME` authorizes one per run, like explicit
  `--permissions trusted`. Prompts, agents and model output have no command
  surface.
- **Pinning.** The check resolves with the request, before key lookup, stdin,
  runtime discovery, network or writes. A bare name uses absolute PATH entries
  only; a relative program path rejects. The found entry and every symlink hop
  must lie outside the canonical project. It runs by its found absolute path, so
  rustup-style proxies work. A mid-run edit to `ah.json` cannot change it.
- **Execution.** It runs only after backend success and confirmed runtime
  cleanup: in the project directory, in its own process group, with closed
  stdin and both streams on harness stderr. Stdout stays the response or
  machine records. Route key names and the reserved runtime key names are
  removed from its environment. It has its own timeout. SIGTERM, then SIGKILL
  after 2 s, on timeout or cancellation. After every exit, lingering group
  members are terminated and group absence is confirmed.
- **Outcomes.** `not_run`/`passed`/`failed`/`timed_out`/`cancelled`/`error`,
  recorded separately from `agent_outcome`. Exits: unchanged without
  `--verify`; backend non-success keeps its exit; passed 0;
  failed/timed_out/error 1; cancelled 3; unconfirmed check cleanup 4. Machine
  v1 adds the `verification.started`/`verification.finished` records and a
  result `verification` object (`null` without `--verify`). These are additive
  under D039 and carry no argv, paths or output. Human stderr appends
  `verification="NAME" "STATUS"` to the final line.
- **Stop/repair.** No repair, retry or re-prompt; no model-suggested commands. A
  step whose gate is not `passed` stops dependent sequence steps (P5.2); any
  continue-on-failure option is a P5.1 choice. Bounded repair belongs to Ralph
  (P6.1).

## Implementation

- `src/verify.rs` (new): definition validation, pinned resolution with the
  symlink-hop check, the gate (`not_run` unless backend success) and process
  execution.
- `src/config.rs`: optional `checks` block via a generic duplicate-rejecting
  `Named<T>` map (shared with `litellm.groups`), `--verify NAME` and
  `Resolved::verify`. It is never copied to the fallback request; the gate runs
  once on the final outcome.
- `src/process.rs`: `OwnedChild::spawn_output` (null stdin, caller-supplied
  output handles) on a shared `start`; the stderr drain is now optional.
  Cleanup and group confirmation are unchanged.
- `src/progress.rs`: result `verification` object, shared `outcome()` mapping
  and the final-line suffix. `src/single.rs` runs the gate after either
  coordinator path. `src/preview.rs` reports the pinned program and argument
  count, never arguments, and never runs it. The help text lists `--verify`.

## Test evidence

Card acceptance: fake-command tests distinguish agent success, no
verification, passed/failed/timed-out verification and untrusted command
rejection.

- `tests/config.rs` (2 new tests; 85 root tests total):
  - **Schema.** Empty, null, shell-string, unknown-field, duplicate-name,
    bad-name, empty-argv, NUL, relative/empty program, zero timeout and 65-entry
    bounds; an invalid `--verify` name rejects at parse.
  - **Resolution.** The first absolute PATH entry wins and relative entries are
    skipped. Default timeout 600. An undeclared name rejects. Rejected programs:
    an in-project program reached through PATH, an absolute in-project path, an
    outside symlink into the project, an in-project symlink to an outside
    program, and an outside chain through the project. A non-executable or
    missing program rejects. An outside alias is executed by its found name. No
    `--verify` means no check.
- `scripts/tests/verify.py` drives fake OpenCode 2.2.5 plus a fake check
  program outside the project (16 runs):
  - **Passed.** Exit 0. Record order is `attempt.cleanup` <
    `verification.started` < `verification.finished` < `result`. Cwd is the
    project, stdin is empty, own process group. `TEST_KEY`,
    `AH_RUNTIME_API_KEY` and `OPENCODE_API_KEY` are absent. Check output is on
    stderr only.
  - **No `--verify`.** Exit 0, `verification: null`, no check ran.
  - **Failed.** Exit 3 → ah exit 1 with `agent_outcome: succeeded`; the
    response is retained and recovery names no repair. Self-SIGKILL → `failed`
    with `signal: 9`.
  - **Timed out.** 1 s → exit 1; the group and a lingering descendant are
    terminated.
  - **Lingering descendant.** Killed after a passing check, with cleanup
    confirmed.
  - **SIGINT during the check.** Exit 3, `cancelled`, descendant gone.
  - **Agent did not succeed.** Known failure → exit 1 `not_run`, check never
    ran. Preflight rejection → exit 2, `agent_outcome: rejected`.
  - **Untrusted.** Undeclared name, an in-project program (a project-local
    symlink on PATH) and a relative path: exit 2, no runtime launch, no prompt.
  - **Pinning.** A fake runtime case rewrites `ah.json` to `/usr/bin/false`
    mid-turn; the pinned check still passes.
  - **Human mode.** Stdout is exactly `OK`; the final stderr line names the gate.
  - **Preview.** Shows the check without arguments and does not run it.
- The first suite run found a real gap. An in-project symlink to an outside
  program passed the canonical-target check, although the harness would run
  that agent-retargetable link. The hop-by-hop check closes it; Rust tests cover
  both directions.
- Mutation checks, each restored afterwards, all caught:
  - running the check after a backend failure fails `verify.py`;
  - removing the outside-project check fails `verify.py` and `tests/config.rs`;
  - removing the key scrub fails `verify.py`.

Full non-live suite on the branch: `cargo fmt --check`, locked Clippy
`-D warnings`, 85 root tests and a release build (`ah 0.1.0-alpha.2`) pass. So
do `single`, `preview`, `worktree`, `single_runtime` (plain, `--cancel`,
`--group=coder`, `--refuse`, new `--verify`, and `--verify --cancel`), `native`,
`native_runtime`, `agents_runtime`, `agent_emission_runtime`, `local_first`,
`modes` (165 cases), `agents_exec`, `machine` and `verify`.

## Installed-runtime and live evidence

- `single_runtime.py --verify` (installed OpenCode 2.2.5, local deterministic
  model stub, trusted): the real runtime edits `calc.py`, then the configured
  check `[python3, test_calc.py]` passes, exit 0 in 25 ms, cleanup confirmed.
  With `--cancel`, the run exits 3 with verification `not_run` and
  `agent_outcome: cancelled`.
- `single_runtime.py --live --verify` (live LiteLLM at the corrected
  `http://litellm:4000/v1`, alias `macmini-qwen3-coder-30b`, trusted, 2026-11-03):
  4 grants and 14 tool events. The model fixed `add`, and the pinned harness
  check ran after confirmed runtime cleanup: `passed`, exit 0, 29 ms, cleanup
  confirmed. Final line: `outcome=Success; verification="test" "passed"`. The
  model's own `touch verified` step and the independent rerun also passed. One
  run; no retry. Context 3172/200000 tokens, reported cost 0 USD.

## Boundaries

- Single runs only. Sequence reference syntax, continue-on-failure and durable
  outcome/output references are P5.1–P5.3. Ralph completion gating is P6.1.
- One check per run (`--verify` is not repeatable); combine commands in one
  operator-owned script outside the project, or an interpreter argv.
- Not containment: a check executes current project content with host
  privileges. Pinning prevents project-content substitution of the program, not
  host-level changes by a trusted agent.
- Check output is passed through to stderr, not captured, bounded or persisted.
- No new dependency; config schema stays version 1 (additive optional field).
  Older binaries reject a config containing `checks` as an unknown field.
