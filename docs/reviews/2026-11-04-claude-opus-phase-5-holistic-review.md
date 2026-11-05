# Claude Opus holistic review — Phase 5

## Review scope

- **Reviewer/date:** Claude Code (Claude Opus 5.5), 2026-11-04 (America/Denver).
- **Review task:** P5.6 ([card](../../tasks/05-sequences.md#p5-6)). This is one reviewer's independent assessment, alongside [Gemini's](2026-11-04-gemini-phase-5-holistic-review.md) and [Codex's](2026-11-04-codex-phase-5-holistic-review.md). It is not the canonical `phase-05.md` revision, and it does not record acceptance or authorize recommendations.
- **Accepted entry:** `53e1707` (Phase 4 pass, [PR #43](https://github.com/awesomejt/agent-harness/pull/43)). **Implementation head:** `f886208` (P5.4 merged, [PR #48](https://github.com/awesomejt/agent-harness/pull/48)). Range `53e1707..f886208`: 39 files, +5921/−140. Working head `286dd6c` adds only review documents; `src/`, `tests/`, `scripts/` and `Cargo.toml` are unchanged from `f886208`.
- **Included PRs:** [#44](https://github.com/awesomejt/agent-harness/pull/44) P5.5 verification gates; [#45](https://github.com/awesomejt/agent-harness/pull/45) P5.1 decisions; [#46](https://github.com/awesomejt/agent-harness/pull/46) P5.2 ordered execution; [#47](https://github.com/awesomejt/agent-harness/pull/47) P5.3 durable resume; [#48](https://github.com/awesomejt/agent-harness/pull/48) P5.4 use gate; [#49](https://github.com/awesomejt/agent-harness/pull/49) Gemini review.
- **Mandatory scope:** P5.5, P5.1–P5.4 and the P5.6 gate; D043, D044; G6; F07, F14, F15, F17 (Phase 5 portions). G1–G5 and AC01–AC11 are regression constraints wherever a sequence step reuses single-run policy. G7/F08 are Phase 6 Ralph scope.
- **Method:** I read `verify.rs`, `sequence.rs` and `state.rs` in full, and the Phase 5 diffs to `config`, `single`, `progress`, `process`, `preview`, `agents`, `lib` and `main`. I also read D043/D044, WORKFLOWS, the four evidence records, the task cards, PROJECT.md and the drift-prone contract summaries. I re-ran the root suite, fmt, Clippy and the offline runner. I reproduced candidate issues with a scratch copy of the `sequence_state.py` fixture and fake OpenCode, with no provider traffic.
- **Exclusions:** no fixes, no new live inference (P5.4's dated live runs are relied on), no merge, no release. Ralph, native adapters, Pi, scheduling, parallel steps, per-step modes and sequence machine output are out of scope.

## Conclusion

**Changes required before Phase 5 acceptance: two new Medium findings and two new Low findings, in addition to the confirmed Codex findings.** No Critical or High finding was demonstrated. Routing isolation, permission narrowing, local-first fallback eligibility and project preservation are intact for sequence steps.

Both new Medium findings are in resume recovery, and both let a step complete without the evidence D044 intends:

- **C05-01:** a resume without `--verify` (bare or `--retry`) silently ungates a step whose last attempt was gated. The run can then complete with that step `succeeded` although its check never passed.
- **C05-02:** `--accept` is honored when the stopping step never submitted a prompt. A step that was rejected before launch can be recorded `accepted` although no agent ever ran it. This shares a root cause with Codex K05-05 (an `--accept` on a never-attempted step) and broadens it.

Both pass the existing suites, because no test asserts these branches.

I independently confirm Codex K05-01 (Medium, the verification-path trust bypass), K05-02, K05-03 (= Gemini R05-01 / P5.4 F3), K05-04 and K05-06. Gemini's documentation items are dispositioned below. Under [PHASE_REVIEW.md](../PHASE_REVIEW.md), every finding must be resolved before a pass. Phase 6, and any consumer of Phase 5 workflow state, waits for the accepted P5.6 gate.

## Requirements and acceptance coverage

| Task / criterion | Assessment and evidence |
|---|---|
| P5.5 / D043 / F17 | Checks are defined only in config (`checks.NAME = {argv, timeout_secs?}`), validated strictly (name grammar, 1–64 argv, no NUL, no relative program, timeout 1–86400). A check is authorized only by `--verify NAME`. It is pinned with the request before key lookup, runtime or writes, and runs after the final backend success without a shell, in its own process group, with stdin closed and route keys scrubbed. Outcomes are distinct (`not_run`, `passed`, `failed`, `timed_out`, `cancelled`, `error`). The biased `select!` keeps a real exit at the bound. Unconfirmed cleanup exits 4 and takes precedence. `verify.py` and `single_runtime.py --verify` cover the outcome matrix. **Exception: K05-01.** `outside()` canonicalizes each hop's parent, which hides a project-controlled directory symlink inside the path. |
| P5.1 / D044 | Every card item is decided before its consumer: ordering, filtering, context, failure, metadata, state, retention, locking, resume syntax, changed inputs, uncertain attempts and schema compatibility. Deferred features are listed explicitly. No scheduler or database exists. |
| P5.2 / G6 / F07 | `snapshot` reads the folder once, non-recursively. It ignores dot entries and rejects every other non-`N-slug.md` entry, symlinks (`file_type` plus `O_NOFOLLOW`, with a post-open `is_file`), FIFOs (`O_NONBLOCK`), duplicate numbers and empty folders. It enforces the step-count, per-file and aggregate bounds. Metadata is strict YAML (no tags, unknown or duplicate keys exit 2) with only `agent`/`verify`. `Invocation::step` refuses an agent conflict and `verify` without `--verify`. Every step resolves against one cloned `Config` and passes `single::supported` before any lock or write. Each step is one `single::launch` with a fresh runtime, session, grants and preflight. Prompts come from memory, so agent edits to later files do not affect the running sequence (`EDIT-LATER` fixture). |
| P5.3 / F14 / F15 | Records are strict v1 JSON (version-first parse, `deny_unknown_fields`, run-ID match), private (0700/0600, uid and mode checks, never repaired) and outside the project (deepest-existing-ancestor check). Writes are exclusive temp + fsync + rename + directory fsync. Attempts are written `active` before launch and their results before the next step, with write failures mapped to exit 1 or 4. The project lock is a nonblocking `flock` that names its holder; `show` probes it with a momentary shared lock. Resume plans on a copy, takes the lock, then refuses if the record changed. The record holds no prompt text, argv text, output or keys (asserted by `sequence_state.py`). **Exceptions: C05-01, C05-02/K05-05, K05-02, K05-06.** |
| P5.4 | [Live evidence](../evidence/p5-4-sequence-use-gate.md) records a real three-step dependent task (local-only LiteLLM `flash`, trusted coder, every step gated). SIGINT after submission was followed by a refused bare resume and a successful `--retry`. SIGKILL mid-step was followed by a failed gated `--accept` and a successful `--retry`. Completed steps never reran, and the run output was independently reviewed and integrated. F1/F2 were fixed with mutation-checked tests, and F3 was recorded. The evidence meets the card. Run B's retry passed `--verify list` and steps 2–3 carried `verify:` metadata, so the live run could not have exposed C05-01. |
| IMPLEMENTATION Phase 5 exit | Documented order: yes. Failed or cancelled steps stop under the explicit policy: yes. Restart does not silently repeat completed or uncertain side effects: yes for completed steps and for the refusal of bare resume after submission. C05-01 and C05-02 are cases where restart silently completes a step without its gate or without agent work. That is the inverse of a replay. The exit text names only repetition, but D044's recovery rules, which the exit relies on, exclude both. Ordering and state recovery are tested. |

## Integrated assessment

### Architecture and ownership

The single crate stays proportionate. `verify` owns check definition, pinning and execution. `state` owns the record schema, store, atomic writes and lock. `sequence` owns snapshots, the linear loop, resume planning and inspection. `single::launch` was extracted so a sequence step and a single run are literally one call, which is the strongest guarantee that route policy, fallback and preflight cannot diverge. `process::OwnedChild` gained `spawn_output` without changing ACP supervision. Dependency direction is unchanged: `plan`/`rebuild`/`changes` are pure, and I/O stays in `state`, `verify`, `process` and the command functions. The one new dependency, `sha2` 0.10.9 with `default-features = false`, is evaluated in [P5.2 evidence](../evidence/p5-2-ordered-execution.md#dependency).

`sequence.rs` (1462 lines) combines CLI parsing, snapshotting, the session writer, resume planning and `show` rendering. That is a reasonable future extraction point (for example, `show`/`detail` rendering), but its size is not a defect.

### Routing, permissions and fallback

Step metadata cannot set mode, model, permissions, timeout, sync or commands, and the `--agent` conflict rule prevents a prompt file from overriding the invocation's role. Each step is re-resolved and re-preflighted, so a step cannot inherit a previous step's grants or session. The fallback request never carries a check (`verify: None`), and the gate runs once on the coordinator's final outcome. A gated `--accept` runs the check with `Exit::Success` and no agent turn, and its record nulls `agent_outcome`, so an accept is never labeled agent success. No path adds automatic native fallback, replay or repair.

### Recovery semantics

D044's recovery model is sound: completed prefixes are identity-checked, attempted stopping steps cannot be removed, stale `active` attempts become `interrupted`, and an explicit choice is required whenever effects are possible. Two gaps remain where recovery can mark a step done without the evidence the original run required:

1. The gate is part of a step's identity (`StepRecord.check` and the attempt's `check`), but only the `--accept` path holds the step to its recorded gate. `rebuild` overwrites pending steps' recorded `check` with the new resolution, again without a diagnostic (C05-01).
2. `plan` maps `Choice::Accept` to `Reason::Accept` on every branch, including the two where D044 says resume retries without a choice (C05-02/K05-05).

Both are narrow fixes in `resume`/`plan` and do not need a schema change.

### Project integrity and state

No Phase 5 path stashes, resets, cleans, commits or rolls back. Managed project sync is re-planned per step through the existing transaction (`prepare_plan` inside `launch`), so later steps see earlier steps' edits correctly. State never lives in the project. The documented limits are honest: a concurrent `ah single` is undetected, SIGKILL leaves a private runtime directory, nothing is exactly-once, and the submission boundary is not persisted. Durability uses `fsync`, as D025 does. On macOS that does not force a drive cache flush (`F_FULLFSYNC`), but no document claims power-loss durability, and P5.4 records that power loss was not tried.

### Tests and evidence

The tests assert observable behavior: record bytes and modes, prompts that actually reached the fake runtime, check invocations and exits. Mutation checks are recorded for P5.2–P5.4. The gaps are specific. `tests/state.rs::resume_plan_requires_a_choice_whenever_effects_are_possible` asserts `Choice::None`/`Retry` on the never-submitted and never-attempted branches but never `Choice::Accept`. No fixture resumes a gated run without `--verify`. Codex notes the K05-01 path shape is absent from `verify.py`.

### Operations and documentation

OPERATIONS documents sequences, records, inspection, locking and recovery. It already tells users to "pass the same route options" on resume, which is the only current mitigation for C05-01, and nothing enforces it. Summary-status drift (DESIGN line 82, the OPERATIONS status line, WORKFLOWS' lock-privacy claim for `show`) is covered by K05-04. PROJECT.md's P5.6 entries carry figures from the first review that are now superseded (C05-04).

## Findings

IDs are local to this review. Severities follow [PHASE_REVIEW.md](../PHASE_REVIEW.md). All findings are open, and no fixes were applied.

| ID | Severity | Concrete issue / affected requirement | Proposed correction | Verification required |
|---|---|---|---|---|
| C05-01 | Medium | **Resume drops or substitutes a recorded gate except on `--accept`.** `resume` resolves remaining steps afresh from the invocation (`sequence.rs:1063`); the "stays gated from the record" check (`:1070–1081`) runs only for `Reason::Accept`. Omitting `--verify` on `resume --retry`, or on a bare resume of a never-submitted gated attempt, runs the stopping step ungated, records it `succeeded` and completes the run. `rebuild` also silently replaces pending steps' recorded `check`. A different `--verify NAME` substitutes the gate the same way. D044 says a step whose last attempt had a check "stays gated from the record", and D043/P5.5 exist because agent success is not verified success (P4.6 R1). The only signal is one `changed since attempt N: check name, check program, check argv sha256` line on stderr; the final summary and `show` read `completed`. Steps with `verify:` metadata are protected only incidentally, by the "requires --verify" error. | Apply the record's gate on every resume path. If the stopping step's last attempt had a check, any resume (none, `--retry`, `--accept`) requires `--verify` and the same effective check name (exit 2 otherwise, naming the step and check). Decide in D044 whether a pending step's recorded `check` also binds, or whether a gate change after the stopping step is refused or reported. If deliberately dropping a gate on retry is wanted, make it an explicit, documented choice with a distinct diagnostic, not the default for an omitted flag. Update WORKFLOWS/OPERATIONS to match. Linked recovery-policy patch, together with C05-02/K05-05. | Reproduced: one-step run with `--verify test` (check fails), exit 1. Then reconfigure and run `resume RUN --retry` with no `--verify`: exit 0, run `completed`, step `succeeded`, attempt 2 `check` null, checks log `['test']` only (the failed run). Also reproduced: gated step rejected before submission, then bare `resume RUN` exits 0 with the step `succeeded` and no check ever run. Regression cases: `--retry` and bare resume without `--verify` exit 2 with nothing launched and the record unchanged; with the same `--verify`, both proceed; a different check name exits 2. **Open.** |
| C05-02 | Medium | **`--accept` is honored where D044 offers no choice.** `plan` maps `Choice::Accept` to `Reason::Accept` both when the stopping step's last attempt never crossed the submission boundary (`sequence.rs:945–948`) and when the step has no attempts (`:927–936`, Codex K05-05). D044 says such a step is *retried*; `--retry`/`--accept` exist for "a step that may have had effects". As a result, a step whose only attempt was rejected before launch can be recorded `accepted` with no agent ever having seen its prompt. A gated `--accept` on an unattempted or never-submitted step marks it `accepted` when the pre-existing project already passes the check, which is the R1 false-success pattern the gate was meant to stop. | Same patch as K05-05: accept only when the stopping step's last attempt `may_have_effects()`. Otherwise exit 2 with a diagnostic that the step never ran and resume will run it (or follow the normal path with an explicit note, per K05-05's alternative). Add `Choice::Accept` assertions to `tests/state.rs` for the never-submitted and never-attempted branches, plus CLI fixtures. | Reproduced: `version` case rejects step 1 before submission (exit 2, `prompt_submitted` false). `resume RUN --accept` then exits 0, step 1 `[initial rejected, accept accepted]`, and only step 2's prompt reached the runtime. Also reproduced: completed one-step gated run, append `2-b.md`, `resume RUN --accept --verify test`: exit 0, step 2 `accepted`, zero prompts. **Open.** |
| C05-03 | Low | **Resume parse errors name `sequence run`.** `parse_resume` reuses `options(…, sequence=true)`, so `ah sequence resume RUN extra` reports `sequence run takes one prompt folder; prompt sources reject` (exit 2). The exit is correct, but the message names the wrong command and suggests a prompt folder. | Give `options` the command context (or check positional count in `parse_resume`) and report `sequence resume takes one run ID`. Add a CLI case to `tests/sequence.rs` or the `sequence_state.py` rejection table. | Reproduced against the debug build. Fixture asserts the resume-specific wording; `run` wording is unchanged. **Open.** |
| C05-04 | Low | **PROJECT.md P5.6 status carries superseded or incorrect review figures.** The current-work line and the 2026-11-04 P5.6 entry record "105 Rust tests" (102 at this head; see verification), "five Low findings R05-01–R05-05" as the review outcome, and state that Phases 7 and 8 "stay gated". PHASE_REVIEW/PROJECT_PLAN allow independently selected native-adapter and initial Pi work after Phase 4; only Phase 6, P8.4 parity and other Phase 5 state consumers wait for P5.6. PROJECT.md is the single mutable status board. | During consolidation into `phase-05.md`, correct the test count, list the consolidated findings across all three reports and narrow the gating statement to the dependencies PROJECT_PLAN actually defines. | Re-read PROJECT.md against `phase-05.md`, PROJECT_PLAN and the `cargo test` count. **Open.** |

## Assessment of the other reviews

### Codex

| Codex item | Independent disposition |
|---|---|
| K05-01 (Medium) | **Confirmed by code inspection.** `verify.rs:131` canonicalizes `hop.parent()`, which resolves every directory symlink in the parent chain at once. The membership test then sees only the canonical result, so an in-project directory-symlink hop between two outside paths is invisible. The loop follows only final-component symlinks. I did not repeat the runtime retarget, but the preview acceptance follows directly from this code. Medium is right: it defeats an explicit D043 trust rule and can yield a false `passed`, although a trusted agent already has host privileges. A fix should walk components (lexically joining and `read_link`ing each component, rejecting any intermediate inside the project) and keep rustup-style alias dispatch. |
| K05-05 (Medium) | **Confirmed and broadened** by C05-02. The defect is the unconditional `Choice::Accept` mapping, which also covers the never-submitted branch. Fix both together. |
| K05-02 (Low) | **Confirmed by code.** `accept_ungated` builds its attempt without `changes()`, so an edited prompt or changed identity accepted without a check prints no `changed since` line. Folding the report into a shared helper used by `begin` and `accept_ungated` fixes it. |
| K05-03 (Low) | **Confirmed by code order:** `resolve_all` (`:1063`) runs before the gated-accept check (`:1070`). The same as Gemini R05-01 and P5.4 F3. If C05-01 adds a gate check for every resume path, perform it before `resolve_all` to fix both. |
| K05-04 (Low) | **Confirmed.** DESIGN line 82 still defers workflow schemas to Phases 5–6. The OPERATIONS status line calls workflow guidance prospective although its "Ordered sequences" section exists. `Store::existing` validates only the root and `sequences/`, so WORKFLOWS' statement that `show` refuses a permissive lock path overstates the code. Fix the documentation, or make `show` validate `locks/` where it probes. |
| K05-06 (Low) | **Confirmed by code.** `record_path().exists()` (`sequence.rs:372`) followed by a rename-based `write` is not atomic no-clobber. Two projects take different locks but share the run-ID namespace. The probability is about 2⁻³² per same-second pair, but the retention invariant ("never delete or rewrite failure evidence") should be enforced, for example with `link`/`renameatx_np(RENAME_EXCL)` for the first write, or by retrying ID allocation. |
| 102 vs 105 tests; G7 mapping; Phase 7–8 gating | **Agreed.** Reflected in C05-04. |

### Gemini

| Gemini item | Independent disposition |
|---|---|
| R05-01 | Same as K05-03; confirmed. |
| R05-02 | Partially confirmed. The docs/README "What remains phase-gated" column records phase ownership, not unimplemented status. The narrative must not call Phase 5 accepted while P5.6 is open. Fold into K05-04 as a clarity edit; not a separate behavioral defect. |
| R05-03 | Confirmed (DESIGN line 82); part of K05-04. |
| R05-04 | Not a defect. SPECIFICATION's "persist workflow records when resume arrives" is a normative requirement, not a status claim; adding a D044 cross-reference is optional. Agree with Codex. |
| R05-05 | Partially confirmed. Only the OPERATIONS status line is stale; the sequence runbook exists. If C05-01 is resolved by documentation rather than enforcement, OPERATIONS must state the gate-dropping behavior prominently. |
| R05-REC1 | Keep as a candidate. Per-kind counts would help the `--retry`/`--accept` decision, but they cannot prove the absence of effects after a crash before a durable write. |

## Recommendations (not defects)

- **R05-REC2 — report changes to the remaining step list on resume.** Resume prints only the new step count. Steps added, removed or renamed after the stopping step run without a diff against the record. D044 permits this, and per-attempt changes are already reported. When the prompt folder lies inside the project, a trusted step's agent can also add a step that a later resume will run with the operator's permissions. A one-line added/removed summary, plus a preview or `run` notice when the folder is inside the project, would make this visible. Candidate for the consolidation's backlog; not Phase 5 scope.
- **R05-REC3 — bound record listing cost.** `run` (unfinished-run notice) and `show` read every record file in the store, up to 4 MiB each, across all projects, and nothing prunes records. This is fine at current scale. Note it for when a pruning command or an index is considered.

## Verification and integrated recheck

Environment: Apple Silicon macOS 27.0.1, Rust 1.88.0, installed OpenCode 2.2.5. Source matches `f886208`.

- `cargo fmt --check`, `cargo clippy --locked --all-targets -- -D warnings`: pass.
- `cargo test --locked`: **102 tests pass**, zero failures (19 library tests plus 83 integration tests; no doc tests).
- `python3 scripts/tests/offline.py`: **22/22 suites pass**, including `verify.py`, `sequence.py`, `sequence_state.py`, installed-runtime `sequence_runtime.py` (failed step-3 gate stops step 4 before launch), the 165-case mode matrix, `machine.py`, `agent_exec_runtime.py` and `capabilities_runtime.py`.

- Ad hoc reproductions (scratch fixture copied from `sequence_state.py`, fake OpenCode 2.2.5, unreachable LiteLLM base, no provider traffic): C05-01 (`--retry` and bare resume without `--verify`), C05-02 (`--accept` after a rejected never-submitted attempt; gated `--accept` on an appended step) and C05-03 confirmed as described. K05-01–K05-06 were assessed by code inspection against Codex's reproductions.
- No live model call, published-archive install or power-loss experiment was performed. Baseline passes do not verify remediation. After fixes, re-run the affected suites and `offline.py`. Because C05-01 and C05-02 change the recovery contract, update D044/WORKFLOWS, and decide in the consolidation whether a short live resume repeat is required.

## Gate outcome and handoff

**Changes required for `53e1707..f886208`.** Keep P5.6 open. Consolidate this report with Gemini's and Codex's into `docs/reviews/phase-05.md`, recording each incoming finding's disposition.

Suggested remediation grouping, one open PR at a time:

1. **K05-01:** a verification path-trust patch.
2. **C05-01, C05-02/K05-05, K05-02, K05-03:** one recovery-policy patch, since they share `resume`/`plan` and the D044 text. Update D044 first if the policy changes.
3. **K05-06:** a state-integrity patch.
4. **K05-04, C05-03, C05-04:** documentation and diagnostics, which can ride with item 2 or close the set.

Each patch needs `/grok review` (or the authorized stand-in while Grok is unavailable). The patch that resolves the last finding updates `phase-05.md` and PROJECT.md with verification and the integrated recheck, and proposes the pass, effective on merge.
