# P6.3: Ralph completion, bounds and cancellation

Date: 2026-11-05. Entry baseline: `005a3ae` (merged P6.2 PR #54).
Task branch: `feature/06/p6-3-ralph-completion`. Platform: Apple Silicon
macOS 27.0.1 (arm64), Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered scope

D045 completion verification, the check-status stop rules, explicit
`ah ralph resume`, and the remaining bound and cancellation tests. The bounds
and the between-iteration signal check were already in P6.2.

- **Completion.** After an iteration that ends in backend success with a
  claim, the loop runs the pinned check through the D043 gate in the project,
  with the check's own timeout and the loop's signal token. `passed` completes
  the run: status `completed`, exit 0. The check never runs without a claim,
  so a check that would already pass, a DONE file or a clean exit does not
  complete the loop.
- **Rejected claims.** A claim whose check ends `failed` or `timed_out` is
  rejected. The iteration is recorded `failed` with exit 1, `claim: true`,
  the verification object and `agent_outcome: succeeded`, and the loop
  continues. The next header reports `completion claimed: yes; check status:
  failed` (or `timed_out`). That iteration is the bounded repair, and it still
  counts against `--max-iterations`.
- **Stops.** A check ending `error` or `cancelled`, or with unconfirmed cleanup
  (exit 4), stops the run (`stopped`) with its D043 exit. So does any agent
  outcome other than success, as in P6.2. `ralph::after` makes this decision
  from the recorded iteration alone, so the loop, `resume` and `show` all read
  the same rule.
- **Resume.** `ah ralph resume RUN_ID [--retry|--accept] --verify NAME
  [--max-iterations N] [--max-runtime-secs S] [single options]`. The
  project, config and prompt path come from the record, so `--project`,
  `--config` and `--preview` reject, as do prompt sources and `--output
  jsonl`. Without `--verify` it exits 2, and passing both choices exits 2.
  The prompt file is re-read from its recorded path before config, key
  lookup, lock or write. A changed prompt is allowed and reported. `ralph::plan`
  applies the D045 rules:
  - a `completed` run exits 0 and launches nothing;
  - bare resume launches the next iteration (reason `resume`) when the last
    iteration never submitted a prompt, when the loop would have continued
    after it (a success with no claim, or a rejected claim), or when the run
    has no iteration;
  - otherwise (a submitted non-success, uncertain, interrupted, a check that
    stopped the run, or an accept that failed) it exits 2 unless `--retry` or
    `--accept` is given;
  - `--retry` launches a new agent iteration (reason `retry`);
  - `--accept` needs a last iteration that may have had effects. It runs no
    agent turn and appends an `accept` iteration that only runs the check. A
    pass completes the run with that iteration `accepted`, with no agent
    outcome, no claim and no backends. A failure keeps the run `stopped` with
    the D043 exit;
  - a run whose counted agent iterations reached its bound needs
    `--max-iterations` greater than that count before any launch. Any
    `--max-iterations` must be greater than the count, and the new bound is
    recorded. A run exhausted only by wall time resumes under its recorded
    bound, since each invocation has its own wall bound. An `accept` is not
    counted and needs no larger bound;
  - 100 recorded iterations, the record limit, refuses every choice.

  Later iterations of a resumed invocation have reason `continue`. A stale
  `active` iteration is recorded `interrupted`, and the next header reports it
  as `agent outcome interrupted`. Each resume appends an invocation whose
  reason is `resume`, `retry` or `accept`, with its own wall bound. As with
  sequences, the record is re-read under the lock and must be unchanged.
- **Check identity.** `--verify` must name the check recorded on the run's
  iterations, or resume exits 2. A run with no iteration has none recorded,
  and any declared check is then accepted. The check is re-pinned from the
  current config. The first iteration of a resumed invocation reports on
  stderr what changed since the previous iteration: prompt SHA-256, agent
  definition, check name, program or argv hash, route, model, fallback or
  permissions. The timeout is left out, because the wall bound caps it on
  every iteration.
- **Accept input.** An `accept` iteration sends no input. Its `input_sha256`
  is the SHA-256 of the empty string, and `prompt_sha256` is the re-read file.
- **Inspection.** `show RUN_ID` now prints the resume command that applies:
  bare, with `--max-iterations N` greater than the count, with `--retry` or
  `--accept` after possible effects, or "start a new run" at 100 iterations.
  `run` names `ah ralph resume RUN_ID` beside each unfinished run it lists.

## Implementation

- `src/ralph.rs`: `After`/`after` (completion and stop decision), `settled`
  and `plan` (resume decision), `resume`, `pin` (request and check pinning
  shared by `run` and `resume`), identity `changes`, and `drive`. `drive` is
  the loop body behind an injectable iteration launcher. `execute` supplies the
  production launcher, which runs an agent turn and the gate after a claim, or
  the gate alone for `accept`. In-crate tests drive the real record store with
  scripted launches.
- `src/state.rs`: `Iteration::may_have_effects`, the same rule as for sequence
  attempts.
- `src/config.rs`: `Invocation::parse_ralph_resume`, with bound parsing shared
  with `parse_ralph`.
- `src/lib.rs`: help text.

## Validation

- `cargo fmt --check`, `cargo clippy --all-targets` (no warnings) and
  `cargo test` pass, 120 tests in all.
  - `tests/ralph.rs` adds the completion and stop table, with clean exits and
    unclaimed passes never completing, accepts, and unfinished iterations
    stopping. It adds every resume choice against completed, empty, settled,
    effect-bearing, bound-reached, wall-exhausted and 100-iteration records,
    and the resume argument rules.
  - `src/ralph.rs` in-crate tests drive the loop with scripted iterations. A
    **signal between iterations** stops before the next launch (exit 3,
    `stopped`, resumable without a choice), which closes the P6.2 test gap.
    Rejected claims (`failed`, then `timed_out`) repair until a verified
    claim completes. `error`, `cancelled`, unconfirmed check cleanup and
    failed or uncertain agents stop the run. Rejected claims still exhaust the
    bound. An accept runs only the check and is not counted, and a failed
    accept stops.
- `scripts/tests/ralph.py` (fake OpenCode 2.2.5, a real check program outside
  the project) adds these cases:
  - a claim plus a passing check completes at iteration 1 (exit 0), running the
    check exactly once, and resuming a completed run launches nothing;
  - a rejected claim continues to a repair iteration whose header reports
    `claimed: yes; check status: failed`, and the repaired claim completes;
  - rejected claims, failing or timing out, end `exhausted` at the bound;
  - the marker mentioned mid-response is no claim and runs no check;
  - a claim in iteration 1 does not carry over: later iterations write a DONE
    file and make the check pass without claiming, the check runs only once,
    and the run ends `exhausted`;
  - removing the pinned check program yields check `error`, which stops the
    run (exit 1). `show` then suggests `--retry or --accept`, bare resume
    refuses, and both choices together reject;
  - SIGINT while the check runs gives check `cancelled`, exit 3, `stopped`;
  - an exhausted bound needs a larger `--max-iterations`, a smaller or equal
    one refuses, a different `--verify` refuses, and a resumed iteration reports
    the steered prompt's changed SHA-256;
  - after a submitted failure, a failing `--accept` stays stopped, a passing
    `--accept` completes with an `accepted` iteration and `show` counts 1/10,
    and `--retry` launches a `retry` iteration;
  - a run exhausted by wall time resumes bare under its recorded bound with
    the new invocation's wall bound;
  - an interrupted (SIGKILL) iteration needs a choice, and `--retry` records
    it `interrupted` with that outcome in the next header;
  - resume argument refusals.

  All P6.2 cases still pass.
- `scripts/tests/offline.py`: 23/23 suites pass.

## Limitations and handoff

- No live model run was made. P6.4 is the use gate: one verified completion,
  one bounded non-completion and one interrupted and resumed run, with real
  iterations.
- A rejected-claim iteration prints its own terminal line as `outcome=Failed`
  (exit 1) before the loop note says it continues. The record keeps the agent
  outcome `succeeded` separately. P6.4 use can show whether this wording
  confuses.
- As in P6.2, a concurrent `ah single` in the same project is not detected,
  and the submission boundary is not persisted, so a crash mid-iteration is
  always `interrupted`.
- Usage stays reported, not enforced (D045). There are still no no-progress
  or consecutive-failure detectors; both are re-evaluated from P6.4 use.
