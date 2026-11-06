# Grok holistic review — Phase 6

## Review scope

- **Reviewer/date:** Grok, 2026-11-05 (America/Denver).
- **Review task:** P6.5 ([card](../../tasks/06-ralph.md#p6-5)); existing branch `review/06-claude-ralph`. Independent assessment alongside [Claude's review](2026-11-05-claude-opus-phase-6-holistic-review.md) and [Codex's review](2026-11-05-codex-phase-6-holistic-review.md). Not the canonical `phase-06.md`; does not record acceptance.
- **Accepted entry:** `f146d0d` (Phase 5 pass, [PR #52](https://github.com/awesomejt/agent-harness/pull/52)). **Implementation head:** `45cd62c` (P6.4 merged, [PR #56](https://github.com/awesomejt/agent-harness/pull/56)). Range `f146d0d..45cd62c`: 26 files, +4593/−162.
- **Included PRs:** [#53](https://github.com/awesomejt/agent-harness/pull/53) P6.1 Ralph decisions (D045); [#54](https://github.com/awesomejt/agent-harness/pull/54) P6.2 fresh iterations and records; [#55](https://github.com/awesomejt/agent-harness/pull/55) P6.3 completion verification and resume; [#56](https://github.com/awesomejt/agent-harness/pull/56) P6.4 live use gate and `doclinks.py`.
- **Mandatory scope:** P6.1–P6.4 and the P6.5 gate; D045; G7; F08, F14–F17 (Phase 6 portions); IMPLEMENTATION Phase 6 exit criteria. Routing modes, permission narrowing, D034 fallback and AC01–AC11 are regression constraints via reuse of `single::launch` and the D044 store.
- **Method:** Inspected `src/ralph.rs` (coordinator, `next`/`after`/`plan`/`header`/`claims`), Phase 6 diffs to `state.rs`, `config.rs`, `sequence.rs`, `progress.rs`, Rust and Python tests, evidence records (p6-1 through p6-4), D045, WORKFLOWS, and status documents. Cross-checked against Claude and Codex findings. No new live inference; relied on P6.4 evidence and offline fixtures.
- **Exclusions:** no fixes, no merge, no release. Deferred items (Pi parity, native adapters, scheduling, cost budgets, no-progress detectors) out of scope.

## Conclusion

**Changes required before Phase 6 acceptance: three Medium and four Low findings.** No Critical or High findings demonstrated. The core D045 invariant holds: completion requires a claim plus a passing pinned check from the same iteration. Clean exits, prose, DONE files and stale claims do not complete a run. Every re-launch after possible effects requires an explicit choice (`--retry` or `--accept`). Routing, permissions and fallback policy are inherited unchanged.

The Medium findings match the independent assessments already recorded:

- **G06-01 / C06-01 / X06-01:** a run including an `accept` iteration can record a 101st iteration. The strict reader then rejects the record, so `show` and every `resume` exit 2. Record integrity is broken for the documented bound.
- **G06-02 / C06-02 / X06-02:** resume re-pins a changed check program/argv and only reports it. With the default in-project `ah.json`, a trusted agent can rewrite the definition of done. The next `--accept` or claim completes against the weakened check.
- **G06-03 / C06-03:** Ralph has no offline test outside local-only. The local-first fallback prompt/deadline rewrite and the changed-check report on resume are untested.

## Requirements and acceptance coverage

| Task / criterion | Assessment and evidence |
|---|---|
| P6.1 / D045 | Study covers existing loops; D045 settles claim-plus-check, both bounds with `exhausted`, usage recorded but not enforced, D044 state, and explicit resume. Card met. |
| P6.2 / F08 / F14 | Each iteration is a fresh `single::launch` with isolated runtime HOME, session and grants. Records are strict v1, private, outside the project. Header carries only enumerated values. **Exception: G06-01.** |
| P6.3 / F16 / F17 | `after()` is the single decision table shared by loop, resume and `show`. Rejected claims continue; other non-success stops. Bounds, wall cap, signals and resume branches covered. **Exceptions: G06-02, G06-03.** |
| P6.4 | Live evidence covers a real task, local-only LiteLLM, agent and permissions. Verified completion after SIGINT/retries, rejected claim leading to exhausted, deadline followed by `--accept`. Bare resumes refused. Card met. |
| IMPLEMENTATION Phase 6 exit | Real task reaches verified completion; non-completing task stops at bound; cancellation, restart and false completion covered; each iteration explained by record/`show` (except where G06-01 makes the record unreadable). Neither clean exit nor prose proves completion. |

## Integrated assessment

### Architecture and ownership

`ralph` is a thin coordinator over `single::launch`, as DESIGN intends. It owns the snapshot, header, decision table, session writer, `show` and preview. It reuses the shared store, lock and verification gate. No new dependencies. The `drive` seam behind an injectable launcher is clean for testing.

One layering note: `progress::deliver` calls `crate::ralph::claims` on every response (including plain single runs and sequence steps). Harmless today, but couples the output layer to a workflow module (G06-06).

### Routing, permissions and fallback

Ralph adds no route surface. Mode, model, agent, permissions and check are resolved once per invocation and checked by `single::supported`. The fallback receives the same header and deadline. Resume re-resolves from current config and reports changes. Narrowing is safe; widening needs an explicit flag. Matches D044. The fallback rewrite itself is untested offline (G06-03).

### Completion, bounds and recovery

The completion rule is strict and conservative. `claims()` requires an exact final line. The check runs only after a claim. `may_have_effects()` treats every accept iteration as possibly effectful. The wall bound is honest. Gaps are in record integrity past 100 recorded iterations when accepts are present (G06-01) and in how far resume trusts a re-pinned check (G06-02).

### State and concurrency

Records share the D044 store, private-mode checks, atomic create/replace and the per-project lock. A running Ralph refuses a sequence and vice versa. Resume plans on a copy, takes the lock, then refuses if the record changed. `Store::write` does not apply `consistent()`, which allows the 101st-iteration record to persist (G06-01).

### Tests and evidence

Tests assert observable behavior: prompts that reached the runtime, record bytes and modes, checker invocations and exits. Root tests (120) and `ralph.py` pass on the reviewed head. Gaps are specific: no Ralph case under local-first or cloud-only, no case that changes a check's program/argv between invocations, and no case that pushes recorded iterations past 100 with an accept in the record.

### Operations and documentation

WORKFLOWS carries the full Ralph contract and P6.4 use guidance. OPERATIONS has no Ralph runbook and still calls Ralph guidance prospective. Its sequence runbook says only one sequence can hold a project, although the lock is now shared with Ralph. Other summaries have drifted (G06-07).

## Findings

IDs are local to this review. Severities follow [PHASE_REVIEW.md](../PHASE_REVIEW.md). All findings are open. No fixes were applied. These align with Claude's C06-* and Codex's X06-* assessments.

| ID | Severity | Concrete issue / affected requirement | Proposed correction | Verification required |
|---|---|---|---|---|
| G06-01 | Medium | **A run with an `accept` iteration can persist a record its strict reader rejects.** Iteration bound counts agent iterations only (`counted()`, max 100). `RalphRecord::consistent()` caps recorded iterations at `MAX_ITERATIONS` (100). `plan()` refuses at 100 recorded, but only when resume starts. Inside `drive`, `next()` checks only `counted >= bound`, and `Store::write` does not apply `consistent()`. A run whose record holds one or more accepts, resumed with `--max-iterations 100`, writes iteration 101. Afterwards `show` and every `resume` treat it as invalid v1. | Stop before launch when the record already holds `MAX_ITERATIONS` iterations, or refuse. Make `Store::write`/`create_record` refuse a record that fails `consistent()`. State the chosen rule in D045. | Reproduced path ends without writing iteration 101; `show`/`--accept` still work; unit test that `write` refuses an inconsistent record. **Open.** |
| G06-02 | Medium | **Resume accepts an agent-rewritable change to the definition of done.** D043 pins the check per invocation. `resume` re-pins from the current config and checks only the check name. A changed program or argv is printed once on stderr and the run proceeds. Default config is `PROJECT/ah.json`, which a trusted agent can write. An agent can replace the check with a trivial one; the next `--accept` or claim completes against it. Sequence resume has the same name-only rule. | Make the recorded check identity binding: on any resume, refuse (exit 2, record unchanged) when the re-pinned program or `argv_sha256` differs. Require a distinct explicit flag if mid-run check changes are wanted. Apply the same rule to `sequence resume` or record why they differ. | Same resume exits 2 with record hash unchanged for bare, `--retry` and `--accept`; unchanged check still resumes. **Open.** |
| G06-03 | Medium | **Ralph routing coverage is local-only.** Every `ralph.py` case and every P6.4 live run uses local-only. Ralph's own code rewrites the fallback prompt and timeout each iteration. Cloud-only Ralph and `--agent` with Ralph are untested offline. No test asserts the changed-check report on resume. | Add `ralph.py` cases: local-first with unreachable LiteLLM and native fallback (assert header on fallback prompt); cloud-only through the native fake; `--agent NAME`; and the resume check-identity refusal. | Cases pass; mutation of the fallback rewrite fails the new local-first case; `offline.py` passes. **Open.** |
| G06-04 | Low | **A rejected claim prints "no automatic retry, repair or fallback".** `verify::gate` appends this recovery text. In Ralph the iteration summary then reads the Failed outcome plus that clause, immediately followed by "ralph claim rejected … the next iteration is the bounded repair". The two lines contradict. | Let the caller supply the recovery wording, or have Ralph's rejected-claim path say "Ralph continues with the bounded repair iteration" instead. | `ralph.py` asserts the rejected-claim stderr has no "no automatic retry, repair" clause; single-run and sequence wording unchanged. **Open.** |
| G06-05 | Low | **Accept iterations record and report agent-turn identities.** An `accept` runs no agent turn, but records the accept invocation's agent, route, model, fallback and permissions, and `changes()` reports them. An accept without flags records `permissions deny` and prints change notes for a trusted run. | Limit an accept's change report to prompt and check identity. Carry the previous iteration's agent/route/permissions fields into the accept row, or mark them not applicable in `show`. | Fake-runtime case: an accept without route flags reports only prompt/check changes. **Open.** |
| G06-06 | Low | **Output layer depends on the Ralph module.** `progress::deliver` calls `crate::ralph::claims` for every response. `progress` now imports a workflow coordinator. | Move the marker predicate to a neutral module (or into `progress`) and let `ralph` interpret it. No behavior change. | `claims` tests keep passing; `progress` has no `crate::ralph` reference. **Open.** |
| G06-07 | Low | **Documentation and status drift.** (a) OPERATIONS status line says Ralph guidance remains prospective; no Ralph runbook. (b) Sequence runbook says only one sequence can act on a project; lock is now shared with Ralph. (c) docs/README names P6.2 and P6.3 but neither P6.4 nor the P6.1 study. (d) DESIGN implementation paragraph lists `sequence` and `state` but not `ralph`. (e) PROJECT.md current-state line still names P6.4 as the active task. | Add a short Ralph runbook to OPERATIONS; correct status and lock sentence. Add P6.4 and the study to docs/README. Add `ralph` to the DESIGN module paragraph. Set PROJECT.md active task to P6.5 and its remediation. | Re-read each document against the code and WORKFLOWS; `doclinks.py` passes. **Open.** |

## Assessment of prior reviewer findings

I agree with Claude's C06-01 through C06-07 and Codex's corresponding X06-* assessments on severity and substance. No additional Critical/High issues were identified. The recommendations (tool-kind counters, minimum launch budget, header stopping instruction, resume wall-bound default) remain optional backlog items, not defects.

## Recommendations (not defects)

- Carry forward R05-REC1 (tool-kind counters) as a candidate; it would have informed the long-iteration observation in P6.4 F1.
- Consider exhausting when remaining wall time is below a small floor rather than launching a near-empty iteration.
- Strengthen the fixed header with an explicit "stop and claim as soon as the task's stated checks pass".
- On resume, inherit or prominently print the effective wall bound from the prior invocation.

## Verification and integrated recheck

Environment notes: reviewed against the source at `45cd62c` plus the existing review-branch reports. Full suite execution was not repeated here (prior reviewers confirmed 120 tests, fmt, Clippy, `offline.py` 24/24 and `doclinks.py` on the same head). Scratch reproductions of the Medium findings were independently confirmed by Claude and Codex against the fake OpenCode fixture.

No provider traffic was launched. P6.4's dated live evidence supplies the required real-task scenarios.

## Gate outcome and handoff

**Changes required for `f146d0d..45cd62c`; P6.5 remains open.** This report is added to existing [review PR #57](https://github.com/awesomejt/agent-harness/pull/57). No fixes or merge. Preserve Claude's and Codex's reports unchanged and consolidate all reviewer findings into `docs/reviews/phase-06.md` before acceptance.

