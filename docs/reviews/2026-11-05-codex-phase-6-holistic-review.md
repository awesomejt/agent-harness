# Codex holistic review — Phase 6

## Review scope

- **Reviewer/date:** Codex, 2026-11-05 (America/Denver).
- **Task/branch:** [P6.5](../../tasks/06-ralph.md#p6-5), using the existing `review/06-claude-ralph` branch. This is a separate reviewer report, alongside [Claude's review](2026-11-05-claude-opus-phase-6-holistic-review.md). Consolidation into `phase-06.md` and phase acceptance remain pending.
- **Accepted entry baseline:** `f146d0d`, Phase 5 acceptance/remediation [PR #52](https://github.com/awesomejt/agent-harness/pull/52).
- **Implementation reviewed:** `f146d0d..45cd62c`, 26 files, +4593/−162. Included PRs: [#53](https://github.com/awesomejt/agent-harness/pull/53) (P6.1), [#54](https://github.com/awesomejt/agent-harness/pull/54) (P6.2), [#55](https://github.com/awesomejt/agent-harness/pull/55) (P6.3), [#56](https://github.com/awesomejt/agent-harness/pull/56) (P6.4). Review-branch starting head `1db2768` adds only Claude's report to that implementation.
- **Coverage:** mandatory P6.1–P6.4 deliverables and the P6.5 gate; G7; F08 and Phase 6 portions of F14–F17; D045 and the Phase 6 exit criteria in [IMPLEMENTATION](../IMPLEMENTATION.md#phase-6--bounded-ralph-loops). D024, D031, D034, D038, D043/D044 and AC01–AC11 remain integration/regression constraints.
- **Method:** inspected the full Ralph coordinator, Phase 6 changes to configuration, progress, state and sequence integration, Rust/Python tests, `doclinks.py`, decisions, task cards, operational contracts and P6.1–P6.4 evidence. Independently exercised public-CLI edge cases through the existing fake-runtime fixture. Read Claude's report and explicitly dispositioned its findings below.
- **Boundary:** review and report only. No implementation, test, contract or status fixes; no phase pass, merge or release. No live inference was launched. Pi parity, further native adapters, scheduling, token/cost enforcement and no-progress detection remain deferred.

## Outcome

**Changes required: three Medium and four Low findings.** No Critical or High impact was demonstrated. Existing tests pass but do not cover the reproduced record overflow, completed-run no-op failure or link-check false negative. Findings remain open; the proposed corrections below are plans, not implemented fixes.

## Requirements and integrated assessment

| Area | Assessment and evidence |
|---|---|
| P6.1 / completion decisions | [Study](../evidence/p6-1-ralph-study.md) compares existing Rust loops, and D045 settles claim plus trusted check, fresh context, stop rules, bounds, explicit recovery and usage limitations before implementation. No model assertion, DONE file or clean exit is sufficient. |
| P6.2 / fresh context and durable state | Each agent iteration reuses `single::launch` with fresh progress/runtime/session/grants. The fixed header carries enumerated facts, and the prompt is snapshotted per invocation. Records preserve prompt/input/agent/check and route identities without transcripts, arguments or credentials. The shared store retains outside-project state, private owned directories, atomic publication/replacement and sequence/Ralph mutual exclusion. **Exception: X06-01 breaks the record limit and subsequent inspection/recovery.** |
| P6.3 / completion and recovery | `after()` centralizes the live/resume decision: successful claim plus passed check completes; failed/timed-out claims repair within bounds; other agent/check failures stop. Bare resume refuses uncertain/submitted non-success; retry/accept are explicit. Active records without their lock holder are interrupted. **Exceptions: X06-02 and X06-05.** |
| Bounds and cancellation | `next()` checks cancellation, counted agent iterations and remaining wall time before launch; the iteration deadline is capped. The single-run coordinator shares that deadline with native fallback. A started checker retains its own timeout, an explicit D045 allowance; this is not a strict process-wide wall cutoff. Accept runs no agent turn and bypasses the agent bound. Between-iteration signal coverage exists in the scripted drive tests; Python tests cover in-turn/check cancellation and SIGKILL recovery. |
| Routing / permissions / regression | Ralph delegates execution to the established single-run path; fallback receives the rewritten header/prompt and capped timeout. No new subscription-through-proxy path or provider bypass was found. Resolved role constraints remain enforced by single-run preflight and grants; a new invocation can resolve current options as D044/D045 specify. Scratch cloud-only, local-first fallback and named-coder claim/check runs completed successfully. **X06-03 records the missing durable regression coverage.** |
| Rust architecture | Coordinator, state writer, gate and runtime retain distinct responsibilities; no dependency was added. The `Stored`/`Kind` refactor shares storage and locking with sequences, whose regression suites remain applicable. `progress::deliver` calls `ralph::claims`, creating a small dependency inversion, but that pure predicate does not choose routes or alter single-run outcomes. Treat its relocation as maintenance, rather than a demonstrated acceptance failure. |
| P6.4 / actual use | [Live evidence](../evidence/p6-4-ralph-use-gate.md) records local-only LiteLLM `flash`, named coder/trusted permissions, verified completion (run C), rejected claim plus bounded non-completion (run B), deadline/SIGINT and explicit recovery. This meets the three required scenario categories. Run B was deliberately seeded and used an unstated failing check; the completion required prompt steering. These are stated limitations, not evidence of broad model/route reliability. I did not repeat live inference. |
| F14–F17 / operational limits | Usage totals require every submitted backend to report one currency and are labeled backend reports, not billing. No cost cap is claimed. Concurrent `single`, persisted submission-boundary updates, pruning and schema migration remain expressly unsupported. The former live accept-identity observation is consistent with the existing sequence contract; see dispositions below. |
| P6.4 work product | `doclinks.py` is a useful standalone standard-library check wired into the offline suite. Its absolute-path and dangling-symlink PR fixes are present. **X06-06 demonstrates a remaining false negative in anchor recognition.** The live checker scripts are described in evidence but are not committed repeatable regression fixtures. |
| Platforms / installation | Validation here is Apple Silicon macOS 27.0.1, Rust 1.88.0 and installed OpenCode 2.2.5. D041's existing release/support boundary is unchanged. Ralph evidence applies to current source, not proof that the previously published alpha.2 archive contains Ralph. No new archive installation, other OS, provider version or power-loss test is claimed. |
| Documentation / progression | WORKFLOWS and D045 cover the implemented CLI and limits; P8.4 explicitly waits for P6.5. P6.5 remains unchecked. **X06-07 covers stale operations/status summaries.** Canonical consolidation must preserve all reviewers' dispositions and verify remediation before a pass. |

## Findings and remediation plan

All source locations refer to implementation head `45cd62c`. All findings are **open**; no corrective PR or verification of a fix exists yet. Severity follows [PHASE_REVIEW](../PHASE_REVIEW.md).

### X06-01 — Medium: accept rows allow the loop to write an unreadable record

**Affected:** F14/F15/F16, D045 record limit; `src/ralph.rs:204–208, 944–953`, `src/state.rs:435–442, 775–793`.

The resume planner checks the 100-recorded-iteration limit only once, while the running loop checks the agent count. Accept rows consume record capacity but do not count as agent iterations. The writer only checks serialization size. A run with an accept can therefore append iteration 101; the strict reader subsequently rejects the entire record.

**Independent reproduction:** fake-runtime `run --max-iterations 1` without a claim; `resume --accept` with a failing check; `resume --retry --max-iterations 100`. The last invocation exits 1 with 101 rows on disk. `show RUN_ID` then exits 2: `Ralph record is invalid for schema v1; not rewritten`. This confirms Claude C06-01.

**Proposed correction:** a focused record-integrity patch must check total record capacity before every append and keep the terminal record readable. Enforce reader-consistent records on publication/write as defense in depth, with the appropriate pre-/post-launch failure classification. Clarify the relationship between agent count and record capacity in D045.

**Required verification:** repeat this sequence and assert at most 100 rows, no launch beyond capacity, successful `show`, and safe/refused recovery with a useful explanation. Add a meaningful write/read consistency test.

### X06-02 — Medium: a changed definition of done can complete an existing run on resume

**Affected:** F17, D043 verification trust and P6.4 F2; `src/ralph.rs:544–568, 644–690`.

Resume retains only the check name, re-pins current config and reports a changed program/argument hash without requiring acknowledgment. With default in-project `ah.json` and trusted execution, the coding agent can change the check used by a later invocation. The stderr change report happens after resume has already elected to proceed. This behavior is documented in D045; the finding is a verification-trust design gap requiring a contract decision, rather than an accidental mismatch with that paragraph.

**Independent reproduction:** create an exhausted one-iteration run whose configured checker would fail; replace `checks.test.argv` in `ah.json` with `["/usr/bin/true"]`; `resume --accept --verify test` exits 0 and records `completed`. No new agent prompt is sent, the original checker is never called, and stderr reports `check program, check argv sha256`. This confirms Claude C06-02 without claiming that pinning can protect arbitrary agent-editable test inputs.

**Proposed correction:** a resume-contract patch should refuse changed recorded program/argv identity by default, or require a separate explicit authorization of the changed check. An ordinary retry/accept choice should not silently authorize changing the definition of done. Resolve the equivalent sequence behavior and update D044/D045/WORKFLOWS together. Keeping configuration outside the project remains useful guidance.

**Required verification:** changed program and changed arguments independently refuse without a record change or launch/check for bare/retry/accept; unchanged identities continue; any selected explicit override is separately tested. Include the corresponding sequence case. Reassess the live F2 disposition against the chosen contract.

### X06-03 — Medium: Ralph-specific fallback and role wiring lack committed integration coverage

**Affected:** routing/permission regression constraints; `scripts/tests/ralph.py`, `src/ralph.rs:1010–1013`.

All committed Ralph CLI fixtures use local-only and omit `--agent`. Earlier single-run mode/role suites cannot detect a regression in Ralph's own fallback prompt/timeout rewrite. Live P6.4 covers a named role only on local-only. The changed-check path also has no committed regression assertion.

**Independent check:** scratch cloud-only and unreachable-local-first fixtures each completed a claimed task with a passing check. Both sent the Ralph header; records held one and two backend summaries respectively. A separate local-only named-coder run also completed and recorded its agent hash and trusted policy. These checks support current behavior but do not close the repository coverage gap or establish live native inference.

**Proposed correction:** add bounded fake-runtime Ralph cases for cloud-only, local-first native fallback, and named-role execution, alongside the resume-check cases in X06-02. Assert the header/task, effective deadline, selected role/constraints, recorded identity and check outcome at the runtime boundary.

**Required verification:** these cases and the offline suite pass; removing the fallback rewrite or role propagation must fail the relevant case. This agrees with Claude C06-03.

### X06-04 — Low: a rejected claim says there is no automatic repair immediately before repairing

**Affected:** operator diagnostics; `src/verify.rs:323–325`, `src/ralph.rs:1081–1088`.

The shared verification gate sets recovery text to `no automatic retry, repair or fallback after verification` on a failed/timed-out check. Ralph prints that summary and then launches its bounded repair iteration. The continuation note helps, but the two statements conflict. The `outcome=Failed` label itself accurately describes the rejected iteration and need not be removed.

**Evidence:** inspected the shared gate and coordinator; the existing `REPAIR` fixture exercises that path. Claude C06-04 independently records its stderr reproduction.

**Proposed correction:** make recovery wording reflect the caller's policy while preserving single/sequence semantics.

**Required verification:** rejected-claim Ralph output describes bounded repair without the contradictory clause; single and sequence verification diagnostics remain accurate.

### X06-05 — Low: completed-run resume still requires the old task file

**Affected:** D045 completed-run no-op contract, P6.3 recovery; `src/ralph.rs:515–535`.

Resume reads the recorded prompt before asking `plan()` whether the run is completed. Removing or making the task file invalid after completion changes an advertised no-op success into exit 2. The completed record and project remain valid, and `show` still says nothing needs resuming. A unit test of `plan()` cannot catch this ordering defect.

**Independent reproduction:** run `CLAIM the task.` with a passing checker, then delete `TASK.md` and invoke `resume RUN_ID --verify test`. Exit 2: `recorded prompt file: cannot open input file`; the record is unchanged and no new prompt is submitted.

**Proposed correction:** recognize a validated completed record before reading inputs needed only for another iteration, retaining the requirement to re-read FILE before launching unfinished work.

**Required verification:** completed-run resume exits 0 without task/config/credential dependencies or writes; unfinished runs with missing/invalid FILE still refuse before launch. Include a public-CLI regression case.

### X06-06 — Low: inline-code examples can manufacture nonexistent Markdown anchors

**Affected:** P6.4 link-check work product; `scripts/tests/doclinks.py:244–255, 284–287`.

Outgoing-link scanning masks inline code, but target-anchor collection scans the original lines and only excludes fenced blocks. An HTML anchor written inside a code span is therefore treated as a real target. The tool can exit successfully for a broken fragment link.

**Independent reproduction:** in a temporary Git repository, track a README containing an example code span with the literal text `<a id="ghost"></a>`, then a link `[Broken link](#ghost)`. The checker exits 0 with no diagnostic. Replace the example with ordinary text and leave the same link: exit 1, `README.md:3: #ghost`. The first document has no rendered HTML anchor either.

**Proposed correction:** exclude inline-code HTML examples from explicit-anchor extraction while preserving actual heading text/slug semantics and real HTML anchors. Add a durable fixture for the work product; do not rely solely on the uncommitted live checker.

**Required verification:** the example-only anchor fails, a real HTML anchor passes, and heading anchors containing inline code retain their intended slugs. Run the repository link check and offline suite.

### X06-07 — Low: operational and current-work summaries still describe the pre-review state

**Affected:** operations and task/document consistency; `docs/OPERATIONS.md:3, 299`, `PROJECT.md:8`, `docs/README.md`, `docs/DESIGN.md:62`.

OPERATIONS still calls Ralph guidance prospective and has no Ralph runbook; its sequence-lock sentence omits Ralph. PROJECT's current-state summary still calls P6.4 active although its task is checked and P6.5 is the work underway. The docs index omits P6.4/study evidence in its narrative, and DESIGN's concrete implementation paragraph omits the new coordinator (its proposed-module table does include it).

**Proposed correction:** a documentation patch should add concise current-source Ralph operations/recovery guidance, distinguish those commands from the released artifact, correct the shared-lock wording and refresh current-work/index/module summaries. Do not check P6.5 or mark acceptance while findings remain unresolved.

**Required verification:** read the updated runbook against CLI/WORKFLOWS; verify links and that PROJECT remains the sole mutable status board. Confirms Claude C06-07. These documents were deliberately left unchanged in this review-only task.

## Disposition of Claude findings and live observations

| Incoming item | Codex disposition |
|---|---|
| C06-01 | Confirmed independently; X06-01. |
| C06-02 / live F2 | Confirmed independently; X06-02. Current name-only behavior is intentional/documented, but a stronger authorization boundary is warranted before acceptance. This does not promise secrecy or tamper-proof project test content. |
| C06-03 | Agree; X06-03. Scratch mode checks pass, but committed Ralph integration coverage is still missing. |
| C06-04 | Agree; X06-04. Preserve truthful iteration-failure attribution and fix the contradictory recovery clause. |
| C06-05 / live F3 | **Maintenance recommendation, not an additional defect in this review.** D044 explicitly says accept route fields describe resolution at accept time; D045 inherits those attempt fields, and Ralph labels the row `accept`, with no agent outcome or backends. Misleading change-report noise is worth improving, but current data does not assert an agent turn ran. Consolidation must record this difference from Claude's Low classification and choose a disposition. |
| C06-06 | **Maintenance recommendation, not an additional defect in this review.** Moving the pure marker predicate out of the workflow module would improve dependency direction. No policy or acceptance break was demonstrated by that dependency alone. Consolidation must retain Claude's Low classification and this rationale before deciding. |
| C06-07 | Agree; X06-07. |
| Live F1 / deferred detectors | Prompt scope/stopping guidance addresses observed continued tool use. Tool-kind counters and stronger stopping instructions remain candidates, not authorization for more Phase 6 features. A no-progress detector is not demonstrated necessary when the observed turns kept using tools. |
| Claude R06-REC2–REC4 | Minimum useful launch budget, header refinement and resume-wall-bound presentation are optional design/usability recommendations. They do not establish failures of the chosen D045 behavior. |

## Verification and limitations

Executed against the reviewed source on Apple Silicon macOS 27.0.1, Rust 1.88.0, installed OpenCode 2.2.5:

- `cargo test --locked`: **120 tests pass**, 24 library and 96 integration tests; no failures.
- `cargo fmt --check`: pass.
- `cargo clippy --locked --all-targets -- -D warnings`: pass.
- `cargo build --locked`: pass; scratch reproductions use this executable.
- `python3 scripts/tests/offline.py`: **24/24 suites pass**, including Ralph, sequence/state regressions and installed-runtime suites against local stubs.
- `python3 scripts/tests/doclinks.py` and `git diff --cached --check`: pass with this report staged.
- Scratch public-CLI reproductions: X06-01, X06-02 and X06-05 reproduced with temporary projects/state and the existing fake OpenCode fixture; cloud-only, local-first native fallback and named-coder claim/check paths pass. A separate temporary tracked-Markdown fixture reproduces X06-06. Scratch scripts/logs are local verification aids, not committed production tests.

No provider traffic was needed for these reproductions. The full offline runner includes installed OpenCode against local stubs, which is distinct from live provider inference. P6.4's dated evidence supplies the required live scenarios; no new published-archive, alternate-platform, destructive crash-durability or live routing claim is made here. Passing baseline tests do not verify the proposed corrections.

## Gate outcome and handoff

**Changes required for `f146d0d..45cd62c`; P6.5 remains open.** This report is added to existing [review PR #57](https://github.com/awesomejt/agent-harness/pull/57) for other reviewers, with no fixes or merge. Preserve Claude's report unchanged and consolidate all reviewer findings/disagreements into `docs/reviews/phase-06.md` before acceptance.

Suggested follow-up: a record-integrity patch for X06-01; a resume-contract/coverage patch for X06-02/X06-03/X06-05; and focused diagnostics/documentation/link-check corrections for X06-04/X06-06/X06-07. These are proposed groupings, subject to consolidation. Use linked `patch/` PRs and `/grok review`, one open PR at a time, after this review stage. Verify each correction and repeat affected integrated checks; the final remediation PR records the recheck and proposes a pass. P8.4 stays gated until the accepted P6.5 review and required merges.
