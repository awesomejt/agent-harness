# P2.8 — Dirty-project preservation

Date: 2026-11-02 (America/Denver). Entry baseline: `902613c` (P2.7 PR #19 merged). Task: [P2.8](../../tasks/02-first-slice.md#p2-8). Tested platform: Apple Silicon macOS; Rust/Cargo 1.88.0, Python 3.14.7. Completion takes effect on the task PR merge after required review.

## Behavior

The production CLI reports repository-wide staged, unstaged and untracked counts before preflight, managed config apply or prompting. NUL-delimited parsing handles renames, non-UTF-8 paths and control characters without printing filenames. A file may count as both staged and unstaged. Submodule contents and ignored files are excluded. The baseline is advisory; no rollback or attribution is promised. Authorized runtime tools can change existing files, including their prior edits.

Use fixed system Git with cleared environment, no global/system config, optional locks disabled and fsmonitor disabled. Inspect effective Git config, including includes and worktree config, before status; any filter setting or incomplete config inspection skips status to prevent clean/process filter execution. Both commands share a two-second observation bound, each with a 1 MiB output cap, retaining no raw Git stderr; incomplete/failed observations report unavailable. Reuse owned process-group cleanup; unconfirmed cleanup refuses launch with exit 4. Existing active deadline includes observation; cleanup retains its finite supervisor allowances. Invalid inputs/plans and runtime preparation errors can return before observation. Preview still launches no child. No new dependency, CLI flag, automatic Git mutation, snapshot persistence, ignore edit or recovery operation is introduced. See the [execution contract](../EXECUTION.md#process-and-project-integrity).

## Evidence

`scripts/tests/worktree.py` creates disposable real Git repositories with committed files, staged plus unstaged changes in one file, separate unstaged changes, a staged rename containing a newline and untracked binary data under a control-character filename. A repository fsmonitor trap and poisoned inherited GIT_DIR verify that observation disables fsmonitor and ignores inherited Git routing. The diagnostic reports `staged=2 unstaged=2 untracked=1`, with no filename/key sentinel leakage.

Five public CLI cases use the controlled runtime: preflight version rejection (exit 2), pre-prompt cancellation (3), confirmed active cancellation (3), interruption without terminal evidence (4), and success (0). Each verifies baseline file bytes/mtimes, every Git metadata file's bytes/mtime (including index and refs), no hook execution and no locks left in `.git`. Launch rejection creates no managed config; post-preflight cases retain the managed config/receipt as designed. Additional fixtures verify clean and unborn repositories, linked worktrees and non-Git directories without writes. Filter-trap fixtures exercise local clean configuration, include.path clean configuration and worktree process configuration; all report unavailable and leave the entire tree unchanged, with no filter execution. No test resets or cleans the user repository; all setup commits are explicit fixture operations in temporary repositories. These checks exercise real Git and the real harness supervisor, with no model traffic. Existing runtime/edit evidence remains P2.2/P2.4; this task does not claim to undo authorized tool effects.

Validation commands:

```sh
cargo fmt --all -- --check
cargo test --locked
cargo clippy --locked --all-targets -- -D warnings
cargo build --locked
python3 scripts/tests/worktree.py
python3 scripts/tests/preview.py
python3 scripts/tests/single.py
```

The NUL parser unit check covers clean status, staged/unstaged overlap, rename source records, non-UTF-8/control paths and truncated records. Public preview checks retain no-child/no-write guarantees; broad single-run fixtures cover non-Git projects, exits, cancellation, permissions, route isolation and bounded output. No new live service prerequisite or release/platform claim is introduced. Observation can race concurrent user/runtime edits and does not provide perfect change attribution.

## PR review follow-up

PR #20 initial Grok review: 0 blockers, one concern (repository clean/process filters can execute during status), one nit (macOS system Git requires Command Line Tools). The concern is fixed by effective-config inspection and status refusal for any configured filter; three trap fixtures verify local/included/worktree definitions. The execution contract records the remaining concurrent-config race, global-only filter count differences, and Command Line Tools shim behavior. Rust checks and preservation fixtures passed after the fix; re-review requested for the filter change.
