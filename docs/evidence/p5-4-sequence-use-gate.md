# P5.4 — Sequence use gate

Date: 2026-11-04. Entry baseline: `c77c406` (merged P5.3 PR #47).
Task branch: `feature/05/p5-4-sequence-use-gate`. [Card](../../tasks/05-sequences.md#p5-4).
Platform: Apple Silicon macOS 27.0.1 (26A434), installed OpenCode 2.2.5
(Homebrew), Rust 1.88.0. This record prepares Phase 5 acceptance. It does not
close the phase; P5.6 is the holistic review gate.

## Real task

Live use found real friction. The "Rust and release checks" block in
[TESTING](../TESTING.md) omitted five current suites (`sequence.py`,
`sequence_state.py`, `sequence_runtime.py`, `agent_exec_runtime.py`,
`capabilities_runtime.py`). There was also no single command for the 22
offline Python suites, which every evidence record runs one by one. The
sequence had three dependent steps, each gated:

| Step | Prompt | Gate (trusted check) |
|---|---|---|
| `1-suite-list.md` | Create `scripts/tests/offline.py` with the ordered `SUITES` list and `--list` | `list`: `--list` names exactly the 22 expected entries |
| `2-run-suites.md` (`verify: run`) | Add running: name selection, `PASS`/`FAIL` lines, exit 1 on failure, exit 2 on an unknown name or a missing binary | `run`: compiles; `no_such_suite` exits 2; `preview` passes; `--list` still works |
| `3-testing-docs.md` (`verify: docs`) | Add the omitted suites and a runner paragraph to TESTING | `docs`: TESTING names the runner and the five suites |

Each step depends on the previous step's file. The checks are Python scripts
outside the project, run as `["/usr/bin/python3", "/abs/path/check.py"]` from
an untracked `ah.json`. The prompts folder and the `XDG_STATE_HOME` root were
also outside the project. Each run used a fresh clone of `c77c406` with its Git
remote removed, the committed `agents/coder.md` and the real `AGENTS.md`.
`target/debug/ah` was copied in so the `run` gate could execute `preview.py`.

Invocation: `ah sequence run PROMPTS --agent coder --permissions trusted
--verify list`, local-only through the user's LiteLLM proxy
(`http://litellm:4000/v1`, alias `flash`; credentials from `.zshrc`). A small
driver (not committed) recorded timestamped merged output and sent the signal.
`--preview` first resolved all three steps, agents and pinned checks without
launching anything.

## Run A: SIGINT after submission, then `--retry`

Run `s20261104T214113Z-150b151e`, harness built from `c77c406` (pre-fix).

| Event | Result |
|---|---|
| Step 1 | `succeeded`, `list` passed; 166.0 s, 16 grants, 53 tool events |
| Step 2, attempt 1 | SIGINT 10.8 s after the step started, prompt already submitted. `session/cancel`, backend `cancelled`, cleanup confirmed, check `not_run`. Exit 3; step 3 `pending`, not launched |
| `show` / `show RUN_ID` | `stopped; 1/3 steps complete`; step 2 `cancelled`, `prompt submitted yes`; next action names `--retry` or `--accept` |
| `resume RUN_ID` (no choice) | Exit 2 "may have had effects"; record byte-identical (SHA-256 compared) |
| `resume RUN_ID --retry` | Step 1 not repeated. Step 2 attempt 2 (`retry`, "changed since attempt 1: nothing"), `run` passed; 136.0 s, 13 grants, 46 tool events. Step 3 (`resume`), `docs` passed; 74.6 s, 8 grants, 29 tool events. `completed all 3 steps`, exit 0 |
| `resume` again | Exit 0, "no remaining steps; nothing launched" |

The driver's trigger counted heartbeat lines (`tools=0`), so the signal landed
before step 2's first tool call (0 grants, 0 tool events). That still
exercises the post-submission rule, because the prompt had been sent. Run B
waited for nonzero tool events.

## Run B: SIGKILL mid-step, failed accept, then `--retry`

Run `s20261104T214908Z-efa2e0f3`, harness with the stdout fix below
(`8aaee6b3…`); the final retry used the build that also has the `show` fix
(`b08d4df4…`).

| Event | Result |
|---|---|
| Step 1, attempt 1 | SIGKILL to `ah` at 25.9 s, after 9 tool events and 3 grants (the model was still reading). No `opencode` process remained. One private `ah-runtime-*` directory was retained, as EXECUTION documents |
| `show --project` | `interrupted; 0/3 steps complete`; attempt `interrupted`, `prompt submitted unknown`, exit and outcome `none` |
| `resume RUN_ID` (no choice) | Exit 2 |
| `resume --accept` without `--verify` | Exit 2 (see F3) |
| `resume --accept --verify list` | No agent turn; reran the trusted `list` check. `offline.py` did not exist, so the check failed. Exit 1, the run stays stopped, attempt 2 `accept` `failed` |
| `resume --retry --verify list` | Attempt 3 `retry`: 154.7 s, 16 grants, 55 tool events, `list` passed. Step 2: 237.8 s, 22 grants, 84 tool events, `run` passed. Step 3: 71.1 s, 8 grants, 26 tool events, `docs` passed. Exit 0 |

The operator's accept was refused by the check, not by trust: an accept is
only as good as the gate behind it. Run B's attempt history keeps
`interrupted`, the failed `accept` and the successful `retry`.

## Order, verification, failure and recovery covered

- **Order:** steps ran 1→2→3 in both runs. Each later step used files from
  the previous step, and no step launched before its predecessor's gate passed.
- **Verification:** 7 live gate runs: 6 passed after agent success, and 1
  accept check failed. A cancelled step reported `not_run`. Agent outcome and
  verification are recorded separately in every attempt.
- **Failure:** a cancellation (exit 3) and a failed accept check (exit 1) each
  stopped the sequence with later steps `pending`.
- **Recovery:** completed steps never reran. Run A's step 1 kept its single
  attempt through the resume, and no step in either record has more than one
  successful attempt. Uncertain attempts required an explicit choice, and a
  completed run resumes as a no-op.
- **Records:** two records, mode 0600 under 0700 directories, 6972 and 7519
  bytes. They hold no prompt text and no key value (searched for the live key
  value across records, logs and managed configs: 0 files); the only route
  string is the runtime model `ah-litellm/flash`.

## Independent review of the work product

Run A's `offline.py` was reviewed by hand. `SUITES` matched the expected 22
entries and was unchanged by step 2. The repository-root logic is correct, an
unknown name exits 2 before anything runs, and the TESTING paragraph is
accurate. Paths the gates did not cover were checked separately: a failing
suite prints `FAIL`, the run continues and exits 1, and a missing binary exits
2 while `--list` still works. Run A's output is integrated on this branch with
two edits: `flush=True` on the `PASS`/`FAIL` lines (otherwise they can land
out of order with inherited suite output when piped), and a docstring that
covers running. Run B's independent implementation passed the same gates; it
is not integrated.

`python3 scripts/tests/offline.py` then ran every offline suite on this
branch: see Checks.

## Findings from use

- **F1, fixed: unterminated step responses joined and stayed buffered.** The
  human response was written with `write_all` and never flushed. Rust's
  stdout flushes only at a newline, so a response without a final newline sat
  in the buffer. In run A, step 1's reply appeared only at process exit,
  after step 2 had been cancelled. In a sequence, the next step's reply would
  have joined it on one line. The fake fixtures had codified this
  (`'OKOKOK'`). Now each sequence step's response ends on its own line, and
  every human response, single or sequence, is flushed inside the existing
  two-second stdout budget. Single-run stdout bytes are unchanged. Run B shows
  step 1's reply in full before its gate. Tests: `sequence.py` expects
  `OK\nOK\nOK\n`, and a new case SIGKILLs during step 2 and still finds step
  1's `OK\n`; `verify.py` SIGKILLs a single run during its check and still
  finds `OK`. Mutations: dropping the newline fails `sequence.py`, and
  dropping the flush fails `verify.py`.
- **F2, fixed: a stored `interrupted` attempt was shown as never submitted.**
  `show` printed `unknown` only for a stale `active` attempt. Once `resume`
  persisted the `interrupted` marking, the same crashed attempt read `prompt
  submitted no`, although run B's log shows 9 tool events. Resume planning was
  unaffected, because `may_have_effects` treats `interrupted` as uncertain.
  But `show` is what an operator reads to choose `--retry` or `--accept`. It
  now prints `unknown` for `interrupted` too. The `sequence_state.py` crash
  window asserts this after `--accept`; the mutation is caught.
- **F3, recorded: `--accept` without `--verify` names a later step.** Run B's
  refusal read "step 2-run-suites.md: step metadata verify requires
  --verify". Resolving the remaining steps rejects step 2's `verify:` metadata
  before the gated-accept rule for step 1 is reached. The exit (2, nothing
  launched) is correct and the remedy is the same, but the message points away
  from the stopping step. Left for P5.6 to disposition.
- **R04-REC1 re-evaluated.** Sequence semantics did not need tool kinds. They
  would have helped the recovery decision, though. After run B's crash, the
  record said only "unknown", and `git status` was the only way to learn that
  nothing had been written yet. Per-kind counts (for example `edit=0`) in
  progress and in the attempt record would make `--accept` versus `--retry`
  an informed choice. This strengthens the recommendation for P5.6
  and later planning. No kind field is added here.

## Checks

- 102 root tests, fmt and locked Clippy with `-D warnings` pass.
- `python3 scripts/tests/offline.py` (all 22 offline suites, through the
  integrated runner): 22/22 passed (about 214 s of suite time; `modes.py` 165 cases, `single.py` 59.8 s), including the updated `sequence.py`, `sequence_state.py` and `verify.py`
- Three mutation checks, each caught and then restored: dropping the
  newline and dropping the flush (F1), and the `interrupted` display (F2).

## Limitations

- One model alias (`flash`) and one task, two runs. Model behavior varied (run
  B wrote a different `offline.py`); gates, not model prose, decided
  completion.
- Live interruptions were a SIGINT and a SIGKILL of `ah`. A power loss or a
  kill of the whole session group was not tried; crash windows below
  that are covered by `sequence_state.py`.
- SIGKILL cannot run cleanup, so a private `ah-runtime-*` directory remains
  for deliberate inspection, as documented.
- The P5.3 limits stand. There is no exactly-once or rollback promise, and the
  submission boundary is not persisted. A concurrent `ah single` is not
  detected. Records are v1 with no migration path yet; a schema change
  bumps `v`. There is no pruning command.
