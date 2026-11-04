# P5.2 — Ordered prompt execution

Date: 2026-11-04. Entry baseline: `2add7ac` (merged P5.1 PR #45, D044).
Task branch: `feature/05/p5-2-ordered-execution`. Platform: Apple Silicon
macOS 27.0.1 (arm64), Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered scope

`ah sequence run DIR [options]` implements the D044 input, context and failure
rules. Durable records, the project lock, `show` and `resume` are P5.3. Until
then a stopped sequence must be restarted with `run`, which starts at step 1.

- **Options.** The `single` coding options plus `--preview`. `--prompt-file`,
  a second positional argument and `--output jsonl` exit 2. `sequence show` and
  `sequence resume` exit 2 as unsupported commands until P5.3 adds them.
- **Snapshot.** DIR is read once, non-recursively, before the config, key
  lookup, runtime, network or any write. Names starting with `.` are ignored.
  Every other entry must be a regular file named `N-slug.md` (1–6 digits, slug
  `[A-Za-z0-9][A-Za-z0-9._-]*`, at most 128 bytes). Directories, symlinks
  (checked by entry type and again with `O_NOFOLLOW` on open), other names,
  non-UTF-8 names, an empty folder, a duplicate numeric value (`1-a.md` with
  `01-b.md`), more than 256 steps or more than 16 MiB in all exit 2. Each file
  is read under the existing 1 MiB/UTF-8 prompt rules. Steps run from memory,
  so an agent's edit to a later prompt file does not change the run.
- **Identity.** File name plus the lowercase-hex SHA-256 of the raw bytes,
  metadata included. Each step's diagnostics and the preview print both.
- **Metadata.** An optional block opened by a first line of exactly `---`,
  at most 16 KiB, parsed with the D036 rules: tags rejected, then a strict
  struct decode, so unknown or duplicate keys exit 2, and only string scalars
  are accepted (`agent: 7`, `true` or `null` exit 2). Only `agent` and `verify`
  exist. The prompt is the body after the block and must not be blank.
- **Resolution before launch.** Every step goes through the existing
  `Invocation::resolve`, using one loaded config snapshot, before step 1. Step
  metadata replaces only the prompt, agent and check. A metadata agent that
  differs from `--agent`, or `verify` without `--verify`, exits 2. An undefined
  agent or check exits 2. Every agent and check is pinned at this point, so
  later edits to `agents/` or `ah.json` do not affect the run. Then the D038
  effort refusal and D040 slash-command refusal apply to every step. Errors
  name the step file, which has a strict grammar.
- **Execution.** Each step is one call to the same `single::launch` as
  `ah single`: its own deadline (`--timeout-secs` per step), managed sync plan,
  private runtime and grants, full preflight, D034 fallback and D043 gate. Each
  step gets its own run ID and final summary line. One signal watcher spans
  all steps.
- **Failure.** Strictly linear. A step that is not a success (agent failure,
  rejection, cancellation, uncertainty, or a gate that did not pass) stops the
  run. Its exit becomes the sequence exit, and the stderr summary names the
  step and how many later steps were not launched. A signal seen before the
  next launch exits 3 without launching it. All steps complete: exit 0.
- **Preview.** `run --preview` resolves the snapshot, metadata, agents and
  pinned checks. For each step it prints a line with its name, SHA-256, size,
  agent, route, model, check (program path, never arguments), planned managed
  changes and any execution refusal. It omits prompt text, reads no state,
  takes no lock, launches nothing and writes nothing. It exits 0 when every
  step resolves.

## Implementation

- `src/sequence.rs` (new): `snapshot`, `Step::parse` (name grammar, metadata,
  SHA-256), `resolve` (all steps before launch), `run`, the strictly linear
  `drive` loop with an injectable launcher, and `preview`.
- `src/single.rs`: the post-resolution path is now `supported` (D038/D040
  refusals) and `launch` (deadline, plan, coordinator or attempt, then gate).
  `ah single` calls them with no change in behavior. All existing suites pass
  unchanged.
- `src/config.rs`: `Invocation::parse_sequence`, `Invocation::step` and a
  shared option parser. `Config` and `Invocation` derive `Clone`, so each step
  resolves from one snapshot. `src/verify.rs`: `Definition` derives `Clone`.
- `src/agents.rs`: the existing strict YAML helpers become crate-visible.
- `src/lib.rs`, `src/main.rs`: module, help text and `sequence` dispatch.

## Dependency

D044 required SHA-256. `sha2 = "=0.10.9"` is used with default features off.
The lockfile adds `sha2` 0.10.9, `digest` 0.10.7, `block-buffer` 0.10.4,
`crypto-common` 0.1.7, `generic-array` 0.14.7, `typenum` 1.20.1,
`cpufeatures` 0.2.17 and the build-only `version_check` 0.9.5. `cfg-if` and
`libc` were already locked. Licenses: `generic-array` is MIT; the rest are
`MIT OR Apache-2.0` (`version_check` writes it `MIT/Apache-2.0`). The extracted
registry sources include their license files. All three expressions are
already in the release collector's reviewed map, so no new exception is
needed. `typenum` declares Rust 1.41; the others declare no MSRV. The locked
build, Clippy and tests pass on the pinned Rust 1.88.0. The 0.11 line was not
evaluated: 0.10.9 is the established release and covers the need. This is
compatibility and attribution evidence, not a vulnerability audit. A locked
`scripts/release/package.py` run on the task commit bundled each new crate's
license files and source archive; the packaged binary rejects a missing
folder with exit 2. No release is published by this task.

## Test evidence

Card acceptance: ordering, input and constraint tests covering empty folders,
changed files, metadata conflicts and stopping dependent steps after failure.

- `tests/sequence.rs` (8 tests) and 2 `sequence` unit tests; 95 root tests in
  total:
  - **Order.** Numeric value, not text (`000001`, `2`, `10`); dot entries
    ignored; the known SHA-256 of a fixture's bytes.
  - **Changed files.** Identical bytes give the same hash. A changed body or
    changed metadata gives a new hash, even when the prompt body is unchanged.
  - **Folder errors.** Empty (only hidden entries), missing, not a directory,
    duplicate numeric value, 11 bad names (including 129 bytes; 128 accepted),
    a directory entry, a symlink entry, non-UTF-8 content, over 1 MiB, 257
    steps (256 accepted) and over 16 MiB in all.
  - **Metadata.** `mode`, `model` and `permissions` keys, a duplicate key,
    non-string scalars, a sequence, a tag, bad agent/check names, an unclosed
    block, a blank body and over 16 KiB all reject. CRLF delimiters work, and
    a later `---` line in a plain prompt is body text.
  - **Options.** Prompt sources, a second folder, jsonl, `show`/`resume` and
    an invalid mode reject; `--preview`, `--no-sync` and `--output human` parse.
  - **Resolution.** Per-step agent and check substitution, with the default
    check on the other steps. `--agent` applies to every step. No `--verify`
    means no gate. Invocation model and timeout are unchanged by metadata.
    Conflicts, undefined references and a missing key report the failing
    step's index.
  - **Loop.** Each non-success exit (1–4) at step 2 stops step 3. A
    cancellation after step 1 completes stops before step 2 launches; a signal
    already seen launches nothing.
- `scripts/tests/sequence.py`, using fake OpenCode 2.2.5 and a fake check (31
  runs):
  - **Order and context.** `1`, `2`, `10` arrive in that order, each in its
    own private runtime home. Responses go to stdout; each step has its own
    final line.
  - **Metadata.** It is stripped from the prompt. The agent applies only to
    its step (`build`, `reviewer`, `build`). `--agent` with agreeing metadata
    applies to every step.
  - **In-memory snapshot.** Step 2's runtime rewrites `3-*.md`; step 3 still
    receives the original text.
  - **Stop on failure.** A known agent failure at step 2 exits 1, and step 3
    is never prompted.
  - **Gates.** `--verify test` with step 2 `verify: build` runs
    `test, build, test`. A failing gate at step 1 exits 1 and stops step 2.
    Without `--verify`, nothing runs and no step is labeled verified.
  - **Signals.** SIGINT during step 1 exits 3 and step 2 never launches. A
    check that signals the harness as it passes also exits 3 without
    launching step 2. In practice that signal lands on the gate as
    `cancelled`, so the between-steps branch is covered by the unit test.
  - **Validation before launch.** 17 refusals exit 2 with no runtime launch
    and no prompt, including when only step 2 is bad: empty folder, duplicate
    number, bad names, blank body, unknown/duplicate metadata, unclosed block,
    agent conflict, verify without `--verify`, undefined check, undefined
    agent, unsupported effort, slash command, `--prompt-file` and jsonl.
  - **Entries.** A directory or symlink step rejects.
  - **Unread stderr.** With stderr pre-filled and never read, a failing step 1
    still exits 1 within the bound without launching step 2, and a passing
    sequence exits 0 (PR #46 review fix; hangs on the unfixed build).
  - **Preview.** Per-step identity, agent, check and refusal are shown. Prompt
    text is omitted, nothing launches and no project file is written.
- `scripts/tests/sequence_runtime.py` uses installed OpenCode 2.2.5 with a
  local deterministic model stub, trusted permissions and per-step `test -f`
  checks:
  - Steps 1 and 2 create files through the real shell tool, and step 2 only
    if step 1's file exists, so the filesystem is the only state carried over.
  - Step 3's agent succeeds without creating its file, so its `three` gate
    fails and the sequence exits 1.
  - The stub received model turns for steps 1–3 only; step 4 never launched.
- Mutation checks, each restored afterwards, all caught: removing the
  between-steps signal check, continuing after a non-rejection failure,
  removing the numeric sort, and allowing `verify` metadata without `--verify`.
- Regression: `single` (69 runs), `preview`, `worktree` (12), `native`,
  `local_first` (19), `agents_exec`, `machine` (16), `verify` (18), `modes`
  (165 cases) and installed `single_runtime.py --verify` pass unchanged.
  fmt, locked Clippy with `-D warnings` and the locked build pass.

## Limitations and handoff

- There are no durable records, project lock, `show` or `resume`. An
  interrupted or failed sequence restarts only with `run`, from step 1. P5.3
  adds D044's record, lock and explicit resume choices.
- A concurrent `ah single` or second `ah sequence run` in the same project is
  unsupported and is not yet detected; the P5.3 lock covers sequences.
- Sequence-level lines go to stderr only between steps, through a dedicated
  writer thread with a one-second bounded wait, so an unread stderr cannot
  stall the signal watcher or exit; step diagnostics keep the bounded
  `Progress` writer. Under that backpressure, sequence lines may be lost.
- No live LiteLLM run was made. P5.4 is the live, interrupted multi-step use
  gate.
