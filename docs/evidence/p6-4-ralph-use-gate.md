# P6.4 — Ralph use gate

Date: 2026-11-05. Entry baseline: `2424b11` (merged P6.3 PR #55).
Task branch: `feature/06/p6-4-ralph-use-gate`. [Card](../../tasks/06-ralph.md#p6-4).
Platform: Apple Silicon macOS 27.0.1 (arm64), installed OpenCode 2.2.5
(Homebrew), Rust 1.88.0. Harness: `target/debug/ah` built from `2424b11`
(SHA-256 `9622b7cc…0036`); no harness source changed in this task. This record
prepares Phase 6 acceptance. It does not close the phase; P6.5 is the holistic
review gate.

## Real task

There was no offline check that the repository's documentation links resolve.
Every holistic review so far has reported documentation drift, and the
cross-references (for example `DECISIONS.md#2026-11-05--d045-…` and
`tasks/06-ralph.md#p6-4`) are checked only by eye. The Ralph task asked for
`scripts/tests/doclinks.py`: a standard-library checker for relative inline
links and images in the Markdown files Git tracks. It checks that target paths
exist and that `#fragment`s match an explicit `<a id>` or a GitHub heading
slug, with duplicate suffixes and case-sensitive matching. It also skips
schemes, fenced code and code spans, prints `PATH:LINE: TARGET` and exits 0, 1
or 2. The task also wires the script into `offline.py` and `docs/TESTING.md`.
The prompt was one file outside the project. Version 1 is 1756 bytes, SHA-256
`254c6a6a…`. Version 2 adds a "Scope and finishing" section: 2510 bytes,
`d083ffc6…`, described under F1.

**Trusted check.** `check.py` is a Python script outside the project, run as
`["/usr/bin/python3", "/abs/check.py"]` with a 300 s timeout. It requires:

- the tool exits 0 on the repository;
- an independent reference scanner, also outside the project, finds no broken
  link, so the tool cannot pass by being lenient;
- on a `git init` fixture with 13 good and 4 broken links, plus an untracked
  file, the tool exits 1 and reports exactly the 4 broken `(file, line)`
  pairs;
- a missing ROOT exits 2;
- `offline.py --list` names the script, and TESTING mentions it.

`links-strict` (`check.py --strict`) adds one case the prompt never states: a
broken reference-style definition `[a]: a.md#not-here`. It exists to produce
a bounded non-completion.

Before use, the check was self-tested against a reference solution: it passes,
it fails when the tool is missing, and `--strict` passes only for a solution
that handles definitions.

**Setup.** Each run used a fresh clone of `2424b11` with its Git remote removed
and an untracked `ah.json` (local-only, LiteLLM `http://litellm:4000/v1`,
alias `flash`, key from `.zshrc`, both checks declared). The clones kept the
committed `agents/coder.md` and the real `AGENTS.md`, and `XDG_STATE_HOME` was
outside them. Every agent invocation used `--agent coder --permissions trusted`.
A small driver, not committed, recorded timestamped merged output and sent the
signal. `ralph run --preview` first resolved the agent, route, pinned check,
bounds and iteration-1 header without launching anything. The runs went one at
a time, never in parallel on the alias.

## Run A: per-iteration deadline, refused bare resume, `--accept`

Run `r20261105T223936Z-24ff4124`, `--verify links --max-iterations 4`, default
`--timeout-secs` 1200 from `ah.json`, prompt v1.

| Event | Result |
|---|---|
| Iteration 1 (`initial`) | 1200 s deadline: `session/cancel`, `cancelled`, cleanup confirmed, exit 3. 130 tool events and 40 grants, of which 16 came in the first 645 s. The run was `stopped` with `claim none` and check `not run` |
| `show` | `stopped; 1/4 iterations`; next action is `--retry or --accept` |
| `resume RUN_ID --verify links` (bare) | Exit 2: "its last iteration may have had effects". Record SHA-256 unchanged (`1ebdd06d…`) |
| `resume --accept --verify links` | No agent turn. Iteration 2 `accept` reran the pinned check, which passed (0.5 s). `completed`; exit 0; 1/4 counted |

The work was finished well before the deadline: the check passes on what the
cancelled iteration left. The turn never ended, though. It kept issuing tool
calls until the deadline, so a correct result arrived only through the
operator's gated accept.

## Run C: SIGINT, refused bare resume, two `--retry`s, verified completion

Run `r20261105T230013Z-b5da0b98`, `--verify links --max-iterations 4
--timeout-secs 1800`.

| Event | Result |
|---|---|
| Iteration 1 (`initial`, v1) | SIGINT at 20.9 s, after 12 tool events and 4 grants (reading only; no tracked file changed). `session/cancel`, `cancelled`, cleanup confirmed, exit 3, `stopped` |
| `resume RUN_ID --verify links` (bare) | Exit 2; record SHA-256 unchanged (`1933f902…`) |
| `resume --retry` (v1) | Iteration 2 (`retry`): "changed since iteration 1: nothing". 1800 s deadline, `cancelled`, cleanup confirmed, exit 3. 231 tool events and 82 grants, with the first assistant text at 1467 s. The script, its wiring and an out-of-scope `PROJECT.md` status entry were left behind. The check would have passed, but there was no claim |
| Prompt steered to v2 | See F1 |
| `resume --retry` (v2) | Iteration 3 (`retry`): "changed since iteration 2: prompt sha256". The agent read the earlier iteration's script and fixed a `SyntaxWarning` in one regex. It reverted the `PROJECT.md` entry as out of scope, verified on the repository and on its own fixtures, and ended with `AH-RALPH-COMPLETE` after 550.9 s (100 tool events, 37 grants). The pinned `links` check passed (0.5 s). `ralph completed at iteration 3: claim verified by a passing check`, exit 0 |

This is the verified completion: a backend-success response ending in the
claim, followed by a passing trusted check from the same iteration.

## Run B: rejected claim, bounded repair, `exhausted`

Run `r20261105T234106Z-70383360`, `--verify links-strict --max-iterations 2
--timeout-secs 1800`, prompt v2. The clone was seeded with run A's three
files, so the loop starts from an existing implementation. That fits the
prompt's "an earlier iteration may already have done the work" rule.

| Event | Result |
|---|---|
| Iteration 1 (`initial`) | 347.6 s, 69 tool events, 26 grants. Backend success ending in the claim. `links-strict` **failed** (exit 1, only the 4 stated cases reported). The iteration was recorded `failed`, exit 1, `agent_outcome: succeeded`, `claim: true`. "claim rejected at iteration 1: check failed; the next iteration is the bounded repair" |
| Iteration 2 (`continue`) | 1272.5 s, 136 tool events, 47 grants. The agent read `ah.json`, then the check program, and found the unstated reference-definition requirement (F2). It implemented the requirement but ended **without** the claim, so no check ran |
| End of invocation | `ralph exhausted: reached 2 iterations without completion`, exit 1, status `exhausted`, `2/2 iterations`. `show` names `--max-iterations N, with N greater than 2` |
| `resume --verify links-strict` (bare) | Refused: "the run reached its iteration bound; pass --max-iterations greater than its counted iterations" |
| `resume --accept --verify links-strict` | Iteration 3 `accept`: no agent turn, the check passed, `completed`. The accept is not counted, so the run shows 2/2 |

The bounded non-completion is the first invocation: a false completion
claim was rejected by the trusted check, the repair iteration counted against
the bound, and the run ended `exhausted` at exit 1. The later accept is the
operator's explicit recovery choice. It does not change that outcome.

## Coverage against the card

- **Verified completion:** run C iteration 3. Neither a clean exit nor a claim
  alone completed a run.
- **Bounded non-completion:** run B, which exhausted at the iteration bound
  after a rejected claim (exit 1).
- **Interrupted and resumed:** run C iteration 1 (SIGINT), then two `--retry`s,
  and run A (deadline), then `--accept`.
- **False completion:** run B iteration 1. The claim plus `failed` check was
  recorded as a rejection and the loop continued.
- **No silent replay:** every re-launch was an explicit `resume` choice. Three
  bare resumes after possible effects or a reached bound were refused, and the
  two measured record hashes did not change. No iteration ran twice under one
  number, and no completed run launched anything.
- **Records:** three records of 3348, 5532 and 5061 bytes, mode 0600 under
  0700 directories. They hold no prompt text (search for the prompt title: 0
  files) and no key value (search of the records, logs and managed configs for
  the live key: 0 files).
- **Cleanup:** all six live agent iterations reported `cleanup=true`; none
  exited 4. Three `ah-runtime-*` directories were created at 16:24–16:25,
  inside run C iteration 2. That iteration's own cleanup was confirmed, so
  they are probably from the agent's own test commands (the repository's fake
  runtime suites), cut short by its tool timeout. They were not proven to be
  from a harness iteration.

## Work product

Run C's result is integrated on this branch unchanged:
`scripts/tests/doclinks.py` (317 lines, executable), the `SUITES` entry in
`scripts/tests/offline.py`, and the command and paragraph in
[TESTING](../TESTING.md). Run B's reference-definition extension is not
integrated, because that requirement was deliberately outside the task.
Independent checks:

- the trusted `links` check passes on this branch;
- `python3 -W error scripts/tests/doclinks.py` exits 0;
- in a scratch clone, renaming the `p6-4` anchor in `tasks/06-ralph.md` and
  rewording the D045 heading in `DECISIONS.md` reported all five inbound
  links (exit 1);
- `offline.py doclinks` passes.

The repository passes with 90 tracked documents and 871 relative targets.

## Findings from use

- **F1, recorded: iterations ran to the deadline after finishing the work.**
  Under prompt v1, three of four live iterations ran to the deadline or were
  signalled. Twice (A1, C2) the work was already done and the check would have
  passed, but the agent kept calling tools and never claimed. C2 also edited
  `PROJECT.md`, which the repository's own `AGENTS.md` asks agents to keep
  current. Prompt v2 named the scope (no record files, no branches or PRs),
  told the agent to read existing work first, ruled out the multi-minute full
  suites, and asked it to stop and claim once two named runs gave the stated
  behavior. Under v2 the iterations took 551, 348 and 1273 s. Ralph prompts
  therefore need an explicit scope and stopping rule. The header's generic
  "update progress files" line does not stop a thorough agent in a
  process-heavy repository. WORKFLOWS now carries this as use guidance. A
  no-progress detector would not have helped: these iterations were making
  tool calls the whole time.
- **F2, recorded for P6.5: in-project `ah.json` exposes and could expose to
  change the check.** In run B iteration 2, the trusted agent read the
  project's `ah.json`, then the check program it names outside the project,
  and inferred the hidden requirement. D043 protects check integrity (pinned
  program outside the project), not secrecy, so this is within the contract,
  and it shows a loop can be taught to the test. The same access lets an agent
  rewrite `ah.json`. A later `resume` re-pins the check from the current
  config, reports `check program`/`check argv sha256` as changed, and still
  proceeds. The file was not changed here (byte-identical after run B). The
  operator mitigation already exists: `--config` outside the project, which
  `resume` then reads from the record. WORKFLOWS now recommends it for trusted
  loops and sequences. Whether resume should refuse a changed check identity,
  rather than report it, is for P6.5 to disposition.
- **F3, recorded: accept iterations report agent and permission changes.** An
  `accept` invocation without `--agent`/`--permissions` reports "changed since
  iteration N: agent definition, permissions" and records `permissions deny`.
  The accept runs no agent turn, so the line is noise. It matches the sequence
  accept behavior that P5.6 chose (K05-02), so it is left unchanged for P6.5
  to consider.
- **P6.3 open question (rejected-claim wording):** run B printed
  `outcome=Failed` for the rejected claim, then "claim rejected … the next
  iteration is the bounded repair". In use, the second line made the
  continuation clear. No change.
- **D045 deferred detectors re-evaluated.** A no-progress detector would not
  have caught F1: every long iteration kept making tool calls. R05-REC1
  tool-kind counters would have answered the operator's question during F1,
  whether the agent was still editing or only running commands, which the
  heartbeat counts cannot answer. It stays a P6.5 recommendation. Nothing is
  added here.

## Checks

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings` and
  `cargo test --locked` pass (no Rust change).
- `python3 scripts/tests/offline.py`: 24/24 suites pass, including the new
  `doclinks.py`.

## Limitations

- One model alias (`flash`), one task and three runs. Run B was seeded from run
  A's output and used a deliberately unstated check requirement, so it
  demonstrates the bound and rejection, not a natural failure to converge.
- The verified completion needed a steered prompt (F1). Prompt v1 never
  produced a claim in two long iterations.
- The live interruptions were a SIGINT and a per-iteration deadline. A SIGKILL
  of `ah` during a Ralph iteration was not repeated live; P6.3's `ralph.py`
  covers it with the fake runtime.
- Usage stays reported only: every iteration reported `session_cost=0 USD`
  from the backend, which is not billing.
- P6.3 limits stand: no detection of a concurrent `ah single`, no persisted
  submission boundary, v1 records without migration, and no pruning command.

## Review

Grok's first review of PR #56 found 0 blockers, 2 concerns and 0 nits. None
is critical or high, so no re-review is needed. Both concern
`scripts/tests/doclinks.py` path resolution and are fixed:

- An absolute target such as `/etc/passwd` was checked against the host
  filesystem rather than ROOT, so it could pass falsely. Absolute paths are
  now reported as broken. The repository has none.
- `os.path.lexists` accepted a dangling symlink. The check now uses
  `exists()`, which follows links, so a dangling link fails like a missing
  file.

A fixture confirmed both fixes (`/etc/passwd`, `/real.md` and a dangling
link are reported; a valid symlink with an anchor passes). The repository
still passes `doclinks.py`, and the trusted `links` check passes. The
docstring and TESTING state both rules.
