# P4.6 — Core MVP acceptance evidence

Date: 2026-11-03. Entry baseline: `1f7463d` (merged P4.5 PR #40; `v0.1.0-alpha.2`
packaged from it). Task branch: `feature/04/p4-6-mvp-acceptance`, [PR #41](https://github.com/awesomejt/agent-harness/pull/41).
[Card](../../tasks/04-core-mvp.md#p4-6). Platform: Apple Silicon macOS 27.0.1 (26A434),
installed OpenCode 2.2.5 (Homebrew), Rust/Cargo 1.88.0 (fixtures only).
This record prepares acceptance; the P4.9 holistic review remains the Phase 4 exit
gate. It does not claim core MVP acceptance.

## Published artifact under test

Downloaded the [v0.1.0-alpha.2](https://github.com/awesomejt/agent-harness/releases/tag/v0.1.0-alpha.2)
archive and `SHA256SUMS` and verified the checksum (archive SHA-256
`54313171…49432c`). `BUILD-INFO.json` names source `1f7463de642d35498d9e597a4540095c718c80fd`,
the merged `main` head. The extracted executable's SHA-256 (`fbdc345e…85803`) matches
`binary_sha256`, and it reports `ah 0.1.0-alpha.2`. `scripts/release/smoke.sh` passed on
the downloaded assets (upgrade/rollback, sample previews, redaction, HOME/project
preservation, no toolchains on PATH). Every live run below uses this executable.

Routes: the user's LiteLLM proxy `http://litellm:4000/v1`, alias `flash` (direct or
through harness group `coder`/`review`), and OpenCode's built-in `opencode` provider,
`opencode/deepseek-v4.1-flash-free`. Credentials come from `.zshrc`; the drivers assert
that no key value appears in output, and none was recorded.

## Repeated real use

### Real maintenance task in this repository

Each run used a fresh local clone of the entry baseline with its Git remote removed,
so trusted shell access could not reach GitHub. The clone carried an untracked
`ah.json` (local-first, groups `coder`/`review` → `flash`, the native fallback). The
committed `agents/coder.md` and `agents/reviewer.md` and the repository's real
`AGENTS.md` were used unchanged.

The task came from friction found while running this evidence: `roles_live.py` rows
had no wall-clock time, so a cancelled case could not be diagnosed afterwards (see
pass 2 below). The coder prompt asked for `time.monotonic()` around `run()` in
`live()`, an `elapsed` keyword on `summary()` and an `elapsed_secs` row field, with no
assertion changes, then `py_compile` and `--help`.

| Run | Route / model | Exit | Elapsed | Grants | Tool events | Result |
|---|---|---|---|---|---|---|
| Reviewer, open-ended review of `scripts/release/package.py` | local-first → LiteLLM `flash` (group `review`) | 3 | 900.0 s (bound) | 17 / 17 | 54 | Cancelled at the deadline with no reply text; cleanup confirmed; only managed files added |
| Coder, timing change (clone A) | cloud-only, native | 0 | 18.3 s | 6 / 6 | 20 | Correct change; independent compile and `--help` pass; no managed LiteLLM files written |
| Coder, same task (clone B) | local-only, `flash` | 0 | 143.1 s | 14 / 14 | 47 | Same change, using `t0` as the timer name; independent compile and `--help` pass |
| Reviewer, scoped review of clone A's change | local-first → LiteLLM `flash` (reachable; fallback not eligible) | 0 | 82.9 s | 4 / 4 | 12 | Four findings; reviewed file byte-identical afterwards |

The scoped review's first finding was real. Clone A's local `started = time.monotonic()`
shadows the name of the `started()` helper defined later in `main()`. It is harmless
today because the variable is local to `live()`, but it is a trap for later edits. The
reviewer recommended `t0`, which is what clone B already used. Finding 3 is also valid:
a driver-side `subprocess.TimeoutExpired` aborts before a row prints. That path covers
only a harness that overruns its own deadline by the driver's margin, so it is recorded
here rather than fixed. Findings 2 and 4 are style and labeling points. Clone B's diff
was integrated unchanged on this branch after inspection. Then pass 5 below ran it live.

All four runs used `--output jsonl` except the first, which used human output. Every
JSONL stream ended in exactly one `result` record whose exit matched the process exit.
After the runs, no `opencode acp`/`serve` process or `ah-runtime-*` state remained.

### Live role suite, repeated

`python3 scripts/tests/roles_live.py --binary <published ah>` ran five times. The suite
covers coder and reviewer on LiteLLM, coder deny-invocation, coder and prohibited-edit
reviewer on native, local-first fallback through a closed port, `effort: high`
refusals on all three modes, preview refusal and dirty/untracked preservation.

| Pass | Result | Notes |
|---|---|---|
| 1 | PASS: 7 live runs, 3 refusals | All `end_turn`; coder edited and independently verified on both routes |
| 2 | FAIL at case 3 | Ran concurrently with the 900 s review above on the same alias. The prohibited-operation reviewer ended `cancelled`, exit 3, with 4 grants, 12 tool events and an unchanged project; the driver requires `end_turn`. Elapsed time was not recorded, so a deadline cancellation is likely but unconfirmed. |
| 3 | PASS: 7 live runs, 3 refusals | Run alone; 2 min 12 s total |
| 4 | FAIL at case 1 (with timing) | The local coder returned `succeeded`, exit 0, `end_turn` in 10.3 s with zero tool events and no edit. The driver's independent edit check rejected it. |
| 5 | PASS: 7 live runs, 3 refusals | Live cases took 6.9–31.4 s each |

Of 25 driver live runs, 23 met their assertions, and all 9 refusals reached in the
passing passes behaved as specified (exit 2, zero attempts, unchanged tree).
`single_runtime.py --live --jsonl --model flash --group coder` also passed from the
published executable: a real edit and an independent arithmetic test through the
harness group.

On every LiteLLM primary request, the forwarder saw the `AGENTS.md` marker and the
role's text. Reviewer requests offered exactly `glob, grep, read, skill`. The coder
never exceeded its trusted set, and the deny-invocation coder was offered only
`skill`. The final-reply marker stays recorded rather than asserted (P4.4): in pass 5
the local reviewer's reply omitted it although its requests carried it.

### Deterministic checks on the same artifact and source

The published executable passed `single_runtime.py` edit/test, cancellation (human and
JSONL) and unsupported-tool refusal (human and JSONL) against the local model stub.
The source debug build of the same commit passed `agent_exec_runtime.py`,
`capabilities_runtime.py`, `native_runtime.py`, `agent_emission_runtime.py` and
`agents_runtime.py` on installed OpenCode 2.2.5. It also passed `cargo fmt --check`,
locked Clippy with warnings denied, 82 root tests and the `single`, `preview`,
`worktree`, `modes` (165 cases), `native` (40 cases), `local_first`, `machine` and
`agents_exec` fake-runtime suites.

## Goal assessment (G1–G5)

| Goal | Assessment | Evidence |
|---|---|---|
| G1 Easy installation | Met for the one declared target. The checksummed archive installs and runs with no toolchain; prerequisites are documented separately. | [P2.5](p2-5-installable-binary.md), [P4.5](p4-5-mvp-artifacts.md), artifact section above |
| G2 Real project execution | Met. Real edits and project tests on both routes, visible 5 s progress, bounded cancellation with cleanup. | [P2.2](p2-2-local-only-run.md), [P2.4](p2-4-progress-supervision.md), [P2.6](p2-6-first-use.md), [P3.5](p3-5-dual-route-use.md), real use above |
| G3 Explicit routing | Met. All three modes ran live from the artifact; route, model and fallback eligibility are reported in human and JSONL output. | [P3.2](p3-2-native-isolation.md), [P3.3](p3-3-local-first-fallback.md), [P3.4](p3-4-mode-matrix.md), [P3.5](p3-5-dual-route-use.md) |
| G4 Harness-owned configuration | Met. Project-only managed files on LiteLLM routes, none on cloud-only, groups resolved from `ah.json`, alpha.1-managed projects upgrade with no planned changes. | [P2.3](p2-3-managed-config.md), [P3.3 groups](p3-3-model-groups.md), [P4.5](p4-5-mvp-artifacts.md) |
| G5 Portable named agents | Met for OpenCode 2.2.5 with default effort only. Canonical coder/reviewer map by name and are enforced at the offered-tool and grant level; `effort` is refused. | [P4.1](p4-1-agent-schema.md)–[P4.4](p4-4-primary-reviewer-acceptance.md), D036–D038 |

## Acceptance matrix (AC01–AC11, core MVP column)

| Row | Core MVP requirement | Status | Evidence and boundary |
|---|---|---|---|
| AC01 | Repeated primary tasks on supported routes; runtime owns the tool loop | Evidence present | 11 live coding runs here (excluding deny-invocation) across local-only, cloud-only and a group reference; 10 produced independently verified edits, plus P2.2/P2.6/P3.5/P4.4/P4.5. The other reported success without doing the work (pass 4); see residual R1. |
| AC02 | All three modes; no LiteLLM discovery in cloud-only; validated helper choices | Evidence present | P2.4, P3.2, P3.4 (165 matrix cases re-run); cloud-only rows here show zero forwarder requests; real runs used all three modes. |
| AC03 | Deterministic eligible failure tries configured native target; uncertain work never replayed | Evidence present | P3.1, P3.3, P3.5; closed-port fallback passed in passes 1, 3 and 5; the reachable-proxy runs report `fallback not eligible after the reachability check`, including the 900 s cancellation, with no retry. |
| AC04 | Model groups, native isolation, project-only provider block, no literal secrets | Evidence present | P2.1, P2.3, P3.2, P3.3; groups `coder`/`review` used live here; cloud-only run wrote no managed LiteLLM files; key absence asserted by drivers. |
| AC05 | Inputs and integrity with named agents and native routes; no automatic Git mutation | Evidence present | P2.2, P2.8, P4.4; inline and `--prompt-file` inputs in real use; dirty/untracked preservation in every passing pass; untracked `ah.json` preserved in all clones. |
| AC06 | Versioned machine records, stdout/stderr separation, headless/CI | Evidence present | P2.4, P4.7; every JSONL stream here validated (contiguous `seq`, one `result`, matching exit); `machine.py` passes. |
| AC07 | Lifetime and permission guarantees on both routes and constrained roles; unsupported restrictions refused | Evidence present | P1.6, P1.3, P2.4, P4.3, P4.4; 900 s deadline cancel with confirmed cleanup; the reviewer's file was unchanged; JSONL cancel/refuse on the artifact; effort refused. |
| AC08 | Canonical agents, name-based mapping, enforced primary/specialized roles | Evidence present | P4.1–P4.4; committed agents used unchanged on all three modes from the artifact. Effort mapping unsupported (D038). |
| AC09 | Capability reporting, actionable setup and conflict diagnostics | Evidence present | P2.7, P4.5; preview of the real clone reported routes, agent ceiling, groups and planned files; the missing-key diagnostic (exit 2) was hit outside an interactive shell and named the fix. |
| AC10 | Artifacts and smoke for every declared target; no harness toolchain | Evidence present | P2.5, P4.5; published alpha.2 checksum, provenance and smoke verified here. One target is declared (D041). |
| AC11 | Inherited capabilities, version support and limits; live-use/contract tests | Evidence present | P1.3, P4.8, P4.4; `capabilities_runtime.py` passes; `AGENTS.md` delivery asserted on the LiteLLM wire in every pass, and observed only through the reply on native. |

Supporting Phase 2–4 tasks are all complete in [PROJECT.md](../../PROJECT.md):
P2.1–P2.8, P2.9 review, P3.1–P3.5, P3.7, P3.6 review, P4.1–P4.5, P4.7 and P4.8. No
restriction or platform beyond what the cited evidence tested is advertised: one
target, OpenCode 2.2.5 exactly, default effort only.

## Residual issues and friction

- **R1 — agent success is not verified success.** In pass 4 the coder ended
  `succeeded`/`end_turn`/exit 0 without calling a tool. The harness reports what the
  runtime reports, as specified. Only an independent check, here the driver's, caught
  it. Users must verify results. This is the strongest argument for P5.5 verification
  gates.
- **R2 — open-ended work on a large project can exhaust the bound with no output.**
  The real review read for 15 minutes with turns about 150 s apart and produced no
  text before the deadline. The bound, cancellation and cleanup worked. The scoped
  prompt finished in 83 s. Human progress shows only counts (`tools=48`), so a user
  cannot tell what a long run is doing. P4.9 should assess whether tool kind or title
  belongs in progress output; no change is made here.
- **R3 — shared-alias load.** The only cancellation in the suite happened while
  another long session used the same alias. Per-row timing, added here, makes the
  next occurrence diagnosable. Live acceptance runs should not overlap.
- **R4 — environment-dependent prerequisites.** Preview and runs need the key
  variables exported. A non-interactive shell without `.zshrc` exits 2 with the
  documented diagnostic.
- Unchanged limits: native request contents are unobserved; free native models may
  have different data-use terms (P3.5); no Developer ID signing or notarization
  (D029); one model per route; results are not a quality benchmark. The direct
  OpenCode comparison was not repeated; P2.6 remains the comparison record.

## Next priorities

1. P4.9 holistic Phase 4 review, including R1–R4 above.
2. After phase acceptance, Phase 5 with P5.5 verification gates early (R1), then
   P5.1/P5.2 sequences.
3. Phases 7–8 remain selection-gated; no observed need here selects a second native CLI.

## Change in this task

`scripts/tests/roles_live.py` prints `elapsed_secs` for each live row, produced by the
published binary's `coder` on the LiteLLM route and reviewed by its `reviewer`
(above). No harness source, CLI, configuration or release artifact changed.

## Repeatable verification

```sh
gh release download v0.1.0-alpha.2 -R awesomejt/agent-harness -D <empty dir>
shasum -a 256 -c SHA256SUMS
sh scripts/release/smoke.sh <dir> 0.1.0-alpha.2
B=/absolute/path/to/extracted/ah
zsh -ic "python3 scripts/tests/roles_live.py --binary $B"         # live; both keys
zsh -ic "python3 scripts/tests/single_runtime.py --binary $B --live --jsonl --model flash --group coder"
python3 scripts/tests/single_runtime.py --binary "$B" --jsonl --cancel
python3 scripts/tests/single_runtime.py --binary "$B" --jsonl --refuse
```

The real-repository runs were manual trials with the prompts and configuration
described above. Repeat them only in a fresh clone with no Git remote.
