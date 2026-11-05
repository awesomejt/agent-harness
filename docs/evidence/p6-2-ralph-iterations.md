# P6.2: Fresh-context durable Ralph iterations

Date: 2026-11-05. Entry baseline: `9782d91` (merged P6.1 PR #53).
Task branch: `feature/06/p6-2-ralph-iterations`. Platform: Apple Silicon
macOS 27.0.1 (arm64), Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered scope

The D045 outer loop, its records and read-only inspection for `ah ralph`.
Completion verification (a claim followed by the check), resume and the
P6.3 test matrix are not part of this task.

- **Commands.** `ah ralph run FILE --verify NAME [--max-iterations N]
  [--max-runtime-secs S] [single options] [--preview]` and
  `ah ralph show [RUN_ID | --project PATH]`. `--verify` is required, and FILE
  is the only prompt source: inline text, `--prompt-file` and stdin reject.
  `--output jsonl` rejects. `ah ralph resume` is refused with exit 2 until
  P6.3 implements it.
- **Snapshot and pinning.** FILE is read once, before config, key lookup,
  lock or state, under the single-run prompt rules: a regular UTF-8 file of
  at most 1 MiB that is not blank, with D040 slash-command refusal. The
  invocation resolves agent, model, route, permissions and the check once,
  then sends that snapshot on every iteration. An agent edit to FILE does not
  reach later iterations.
- **Fresh context.** Each iteration is one `single::launch` call with a new
  `Progress`, private runtime HOME, session, grants and full preflight, under
  the same route policy, managed sync and D034 fallback. The check is taken
  out of the launched request, so no iteration runs it as a single-run gate.
- **Header.** The prompt sent is a fixed header, then the snapshot. The
  header holds the iteration number and bound, the previous iteration's
  outcome, claim and check status, the check name and the completion
  instruction. Recorded values that are not known enumerated names print as
  `unknown`. It never holds response text, check output, file content or
  paths.
- **Claim.** `Progress::deliver` records only whether the delivered final
  response's last non-empty line, with trailing ASCII whitespace removed, is
  `AH-RALPH-COMPLETE`. The iteration's `claim` is `null` unless the iteration
  ended in backend success. This build records and reports a claim but does
  not act on it, and says so on stderr.
- **Loop.** Before each launch: a signal stops first (exit 3, run
  `stopped`). Next, the counted iterations against `--max-iterations`, then
  the invocation's remaining wall time against `--max-runtime-secs`. Either
  bound ends the run `exhausted` (exit 1). The remaining wall time also caps
  that iteration's agent deadline, and less than a whole second left counts
  as exhausted. The first iteration that does not succeed stops the run with
  its exit. Nothing is replayed.
- **Records.** `ralph/RUN_ID.json` (`RUN_ID` = `r` plus the D044 grammar)
  sits in the same store and uses the same atomic writes and privacy rules as
  sequence records. The fields are listed under
  [WORKFLOWS](../WORKFLOWS.md#ralph-loop): run identity, canonical project,
  prompt and config paths, status, the iteration bound, invocations (start,
  reason, wall bound) and ordered iterations. Each iteration keeps the D044
  attempt fields plus `prompt_sha256`, `input_sha256`, `claim` and the
  per-backend D039 usage object. An iteration is written `active` before
  launch and its result is written before the next launch. A failed write
  exits 1 before a launch and 4 after one. Records hold no prompt, header,
  response, check output, argv text, environment names or keys. The reader
  is strict: `v` must be 1, unknown fields are refused, the bound must be
  1–100, at least one invocation must exist, there are at most 100
  iterations numbered consecutively, and no iteration may be `pending`.
- **Lock.** Ralph and sequence runs take the same per-project lock. While
  either holds it, the other refuses before launch with exit 2 ("another
  sequence or Ralph run holds this project's lock").
- **Inspection.** `show` lists a project's Ralph runs or details one: its
  invocations, each iteration, a backend-reported cost total, and the next
  action. The cost total is given only when every submitted backend attempt
  reported a cost in one currency; otherwise it is `unknown`. A stored
  `active` run or iteration is reported `interrupted`, with prompt submission
  `unknown`, unless its own holder has the lock. `run` lists the project's
  unfinished Ralph runs and starts a new one at iteration 1. `run --preview`
  prints the file size and hash, agent, route, pinned check, both bounds,
  planned changes and the iteration-1 header, with no state, lock, launch or
  write.

## Implementation

- `src/ralph.rs` (new): `claims`, `header`, the pure `next` launch decision,
  `read_prompt`, `run`/`show`/preview, a `Session` that commits only after a
  durable write, and the macOS loop.
- `src/state.rs`: `Kind` (sequence or Ralph directory, ID prefix and message
  wording) and the `Stored` trait. Read, publish, write, list and parse are
  now generic over the record type. Adds the Ralph v1 types and
  `RalphRecord::counted`. Store and lock messages that both kinds share now
  say "workflow".
- `src/config.rs`: `Invocation::parse_ralph`, `Bounds`, Ralph-specific
  prompt-source messages. `Invalid` is now `Copy`.
- `src/progress.rs`: the claim bit and `claimed()`.
- `src/sequence.rs`: `utf8`, `route`, `identity` and `permissions` are shared
  with Ralph. Sequence behaviour is unchanged.
- `src/lib.rs`, `src/main.rs`: dispatch and help.

## Validation

- `cargo fmt --check`, `cargo clippy --all-targets` (no warnings) and
  `cargo test`: all suites pass, including 8 new `tests/ralph.rs` cases. These
  cover claim parsing (the marker elsewhere or followed by text is no claim),
  header content and refusal of unknown recorded values, the launch decision
  order and wall-time cap, argument rules, prompt file rules, cost totals,
  strict records, and the lock shared with sequence stores.
- `scripts/tests/ralph.py` (fake OpenCode 2.2.5, temporary `XDG_STATE_HOME`
  outside the project) covers these cases:
  - three iterations, each with a distinct and removed runtime HOME;
  - header numbering and previous-iteration lines, with the snapshot
    unchanged after an agent edit to FILE;
  - record content, modes and privacy, ending `exhausted` (exit 1);
  - claims recorded `true` with no check run;
  - a failed iteration stopping the run with `claim` `null`;
  - the wall-time bound capping deadlines and ending `exhausted`;
  - SIGKILL leaving an `active` iteration that `show` reports interrupted
    with submission unknown, and a later `run` that lists it;
  - SIGINT during an iteration (exit 3, `cancelled`);
  - the lock refusing Ralph against Ralph, sequence against Ralph and Ralph
    against sequence;
  - a preview that writes nothing;
  - ten argument refusals.
- `scripts/tests/offline.py`: 23/23 suites pass, `ralph.py` included. The
  updated lock message is asserted in `tests/state.rs` and
  `sequence_state.py`.

## Limitations and handoff

- The loop cannot complete yet. Without completion verification every run
  ends `exhausted` or `stopped`. P6.3 adds claim → check → `completed`,
  rejected-claim continuation and the check-status stop rules. It also adds
  resume with `--retry`/`--accept` and the D045 P6.3 tests: false, stale and
  DONE-file signals, cancellation between iterations, check `error`, and the
  resume choices.
- Until P6.3, `show` reports any unfinished run as not resumable.
- No live model run was made; P6.4 is the live use gate.
- As for sequences, a concurrent `ah single` in the same project is not
  detected, and the submission boundary is not persisted, so a crash
  mid-iteration is always `interrupted`.
