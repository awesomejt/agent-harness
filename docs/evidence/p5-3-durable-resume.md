# P5.3 — Durable resume and inspection

Date: 2026-11-04. Entry baseline: `5e326c7` (merged P5.2 PR #46).
Task branch: `feature/05/p5-3-durable-resume`. Platform: Apple Silicon
macOS 27.0.1 (arm64), Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered scope

D044's record, lock, `show` and `resume` for `ah sequence`. The record fields
and the choices made within D044 are listed in
[WORKFLOWS](../WORKFLOWS.md#durable-records-and-resume).

- **Records.** `run` creates `sequences/RUN_ID.json` under
  `$XDG_STATE_HOME/agent-harness/` (else `$HOME/.local/state/agent-harness/`)
  before step 1. Each attempt is written `active` before its runtime launches,
  and its result is written before the next step. A write is an exclusive
  0600 temporary file, fsync, rename, then a directory fsync. Directories are
  0700. A failed write before a launch exits 1 with nothing launched; after an
  attempt it exits 4 and stops later steps.
- **Content.** Run, project, folder and config identities. For each step:
  name, SHA-256, effective agent and check, and status. For each attempt:
  reason, status, timestamps, input and agent-definition hashes, the pinned
  check identity (program and an argument hash), route, runtime model,
  fallback, permissions, timeout, agent outcome, exit, D043 verification
  fields and the D039 per-backend summary. It never holds prompt text,
  responses, check output, argument text, environment names or key values.
- **Lock.** `run` and `resume` hold a nonblocking `flock` on
  `locks/SHA256(project).lock` for their whole duration and write their run
  ID into it. Contention exits 2 before any launch.
- **`show`.** `show [--project PATH]` lists a project's runs. `show RUN_ID`
  prints each step and attempt and the next action. It is read-only, needs no
  model, and reports a stored `active` run as `interrupted` unless its own
  holder has the lock.
- **`resume`.** Re-reads the folder. Completed steps must lead unchanged; the
  stopping step keeps its name, and later steps may change. Only remaining
  steps resolve, afresh from current config and this invocation. A stopping
  step whose last attempt never submitted a prompt is retried as `resume`.
  Anything that may have had effects (prompt submitted, uncertain,
  interrupted, a failed gate or a failed accept) exits 2 unless `--retry` or
  `--accept` is passed. A gated `--accept` needs `--verify` with the recorded
  check name and reruns that check; an ungated one is recorded `accepted` and
  never labeled verified. Changed identities since the step's previous attempt
  are reported on stderr. The record is re-read under the lock and must be
  unchanged since planning.
- **Compatibility.** A strict reader: a `v` other than 1, unknown fields, an
  invalid status, a mismatched run ID or unparsable JSON exits 2 and leaves
  the file unchanged. The run ID grammar is checked before any path is formed.

## Implementation

- `src/state.rs` (new): location rules, owned-directory checks, run IDs and
  UTC timestamps, the v1 types, strict read, atomic write, listing, lock and
  the holder probe.
- `src/sequence.rs`: `run`/`resume`/`show` dispatch, record creation, a
  `Session` that commits each change only after a durable write, the pure
  `plan` (resume decision) and `rebuild` (re-snapshotted steps), and `show`
  rendering. `drive` takes a start index.
- `src/config.rs`: `Invocation::parse_resume` and `rebase`.
- `src/agents.rs`: definitions keep the SHA-256 of their bytes.
- `src/progress.rs`: `snapshot` exposes the attempt and verification
  summaries that the result record already collects.
- `src/lib.rs`: module and help text. No new dependency.

## Test evidence

Card acceptance: crash-window, competing-writer, changed-input/schema and
cancellation tests prove completed steps are not silently repeated and
uncertain effects are surfaced.

- `tests/state.rs` (6 tests) and a `state` unit test; 103 root tests in
  total:
  - **Plan.** Rejected, failed or cancelled with no prompt submitted resumes
    without a choice. Submitted, uncertain, interrupted, failed-retry or
    failed-accept attempts refuse without one, and either choice proceeds. A
    never-attempted step runs. All complete gives nothing to do, unless steps
    were appended.
  - **Changed inputs.** A completed step that is edited, renamed or missing
    refuses and names it. A moved stopping step refuses, as does one removed by
    truncating the folder to the completed prefix (for any choice, submitted
    or not); an edited one is allowed, and a never-attempted one may be
    dropped. 32 attempts is the bound. Attempts after the first incomplete
    step are inconsistent.
  - **Store.** 0700 directories and 0600 files; round trip; no temporary
    file left behind; `v` 2 or `"1"`, an unknown field, a mismatched run ID
    and bad JSON refuse; an invalid run ID never forms a path; a symlinked
    record is refused. Reused owned directories with any group or other
    bit, and a reused lock file at 0666, 0640 or 0604, exit 2 and keep
    their modes.
  - **Lock.** Exclusive per project; independent across projects; released
    on drop; the holder probe is true only for the named live holder.
  - **Location.** XDG versus HOME fallback; relative or missing values exit
    2; a state root inside the project, directly or through a symlinked
    ancestor, is refused before anything is created; a symlinked
    `agent-harness` directory is refused for writes and reads.
  - **Dates.** Run ID grammar and UTC dates, including 2000-02-29 and 2100.
- `scripts/tests/sequence_state.py`, against fake OpenCode 2.2.5 and fake
  checks (77 invocations):
  - **Record.** Completed two-step run: v1 content, modes, identities, the
    per-backend summary, and no prompt text, key value, key name or argument
    sentinel. `show` lists and details it; `resume` on it exits 0 and
    launches nothing.
  - **Retry.** Step 2 fails after submitting its prompt. `resume` alone exits
    2 naming it; `--retry --accept` exits 2. After the prompt is edited,
    `--retry` reports the changed input hash and runs steps 2 and 3. Step 1
    is not repeated.
  - **Changed inputs.** An edited completed step and a moved stopping step
    both exit 2 and leave the record byte-identical. Truncating the folder to
    step 1 exits 2 with no choice, `--retry` or `--accept`, and leaves the
    record byte-identical. Removing step 3 and adding step 5 is accepted.
  - **Removed gated step.** Step 2's agent succeeds but its `build` gate
    fails; with `2-b.md` deleted, `resume` exits 2 naming it, runs no
    prompt or check, and leaves the record unchanged.
  - **Private state.** After a completed run, `agent-harness/` at 0777 or
    `sequences/` at 0755 makes `run`, `resume` and `show` exit 2;
    `locks/` at 0770 and a lock file at 0666 make `run` exit 2. Nothing
    launches, no record is created and the modes are left as found.
  - **Never submitted.** A preflight rejection at step 1 (no prompt) resumes
    without a choice once the runtime is fixed.
  - **Crash window.** SIGKILL during step 1 leaves an `active` attempt. `show`
    reports it `interrupted` with `prompt submitted unknown`. `resume` alone
    exits 2. `--accept` records an operator acceptance (no agent outcome, no
    verification, no backends) and step 2 runs.
  - **Competing writers and cancellation.** While a run is mid-step, a second
    `run` and a `resume` both exit 2 with no prompt, and `show` reports the
    holder `active`. SIGINT stops it (exit 3, step `cancelled`); `resume`
    then needs a choice. A new `run` starts at step 1 and lists the
    unfinished run.
  - **Accept and gates.** After a failed `test` gate: `--accept` without
    `--verify`, or with `--verify build`, exits 2. A failing accept check
    exits 1 and keeps the run stopped; resume then needs a choice again. Once
    the check passes, `--accept --verify test` records `accepted`, reports
    the changed argument hash, and step 2 runs gated.
  - **Write failures.** A read-only `sequences/` exits 1 with nothing
    launched. A check that makes it read-only during step 1 exits 4, step 2
    does not launch, and `show` then reports step 1 `interrupted`.
  - **Schema.** `v` 2, an unknown field, an invalid status and a mismatched
    run ID make `show RUN_ID` and `resume` exit 2 with the file unchanged;
    the listing marks the file unreadable. Bad JSON exits 2.
  - **Location and arguments.** State inside the project, relative values and
    a missing HOME exit 2 with nothing created in the project; the HOME
    fallback works; a symlinked `agent-harness` exits 2 for `run` and
    `show`. Bad run IDs, `resume --project`, `--output jsonl`, `show RUN_ID
    --project` and a repeated `--retry` exit 2.
- `scripts/tests/sequence.py` (31 runs) and the installed
  `sequence_runtime.py` now use a temporary `XDG_STATE_HOME`. The installed
  run asserts its record: stopped, steps `succeeded, succeeded, failed,
  pending`, step 3's agent succeeded with its gate failed and its prompt
  submitted, and no prompt text.
- Mutation checks, each restored afterwards, all caught: ignoring
  `prompt_submitted` in the resume decision, skipping the exclusive lock,
  ignoring a failed result write, and not marking stale attempts
  `interrupted`.
- Regression: `single`, `preview`, `worktree`, `native`, `local_first`,
  `agents_exec`, `machine`, `verify`, `modes` (165 cases) and installed
  `single_runtime.py --verify` pass unchanged. fmt, locked Clippy with
  `-D warnings` and the locked build pass.

## Review remediation

The stand-in review of `6959883` (in place of Grok) raised two P2 findings,
both fixed with the tests above:

1. **Removed stopping step resumed as complete.** `plan` returned "no
   remaining steps" before checking that an attempted stopping step was
   still present, so deleting it after a failed gate or submitted failure
   made `resume` exit 0. The presence check now precedes that return.
2. **Permissive reused state.** Existing owned directories and the lock file
   were accepted at any mode. They must now belong to the current user with
   no group or other access, or the command exits 2 and leaves them as found.

## Limitations and handoff

- No exactly-once or rollback promise: `--retry` after a submitted prompt can
  repeat effects, and `--accept` trusts the operator (or the check).
- The submission boundary is not persisted, so a crash mid-step is always
  `interrupted` (uncertain), even if the prompt was never sent.
- A concurrent `ah single` in the same project is not detected. Deleting a
  record while a sequence runs is unsupported.
- A record over 4 MiB fails at write time rather than being refused up front.
- No live LiteLLM run was made. P5.4 is the live, interrupted multi-step use
  gate; it also re-evaluates R04-REC1.
