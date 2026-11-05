# Phase 5 holistic review

## Review scope

- Task: P5.6; reviewer: Antigravity / Gemini 3.8 Flash; date: 2026-11-04 (America/Denver).
- Accepted entry baseline: `53e1707` (Phase 4 review pass, [PR #43](https://github.com/awesomejt/agent-harness/pull/43)). Reviewed material head: `f886208` (P5.4 sequence use gate, [PR #48](https://github.com/awesomejt/agent-harness/pull/48)). Range `53e1707..f886208`: 39 files (+5921/−140).
- Included PRs:
  - [#44](https://github.com/awesomejt/agent-harness/pull/44) P5.5 trusted verification gates (`88db9e9`, `b583aed`, `1fa9df0`, `8642561`)
  - [#45](https://github.com/awesomejt/agent-harness/pull/45) P5.1 sequence decisions (`5473bb3`, `f1140f4`, `5591319`, `5b442ae`, `2add7ac`)
  - [#46](https://github.com/awesomejt/agent-harness/pull/46) P5.2 ordered prompt execution (`d546334`, `b54b613`, `602ec5f`, `5e326c7`)
  - [#47](https://github.com/awesomejt/agent-harness/pull/47) P5.3 durable resume and inspection (`94ec535`, `6959883`, `f16aee5`, `c77c406`)
  - [#48](https://github.com/awesomejt/agent-harness/pull/48) P5.4 sequence use gate (`a044171`, `1bd5b7d`, `ba0758b`, `f886208`)
- Mandatory scope: P5.5, P5.1, P5.2, P5.3, P5.4, P5.6; D043 (trusted verification gates), D044 (sequence inputs, state and resume); G6 (ordered sequences), G7 (trusted verification gates).
- Excluded scope: Phase 6 Ralph (P6.1–P6.5), Phase 7 native adapters (P7.1–P7.7), Phase 8 Pi (P8.1–P8.5), Phase 9 resource awareness (P9.1–P9.5), per-prompt operational modes (deferred from D003), continue-on-failure, sequence machine records (`--output jsonl` for sequence commands).

This is revision 1 of the canonical Phase 5 report under [PHASE_REVIEW.md](../PHASE_REVIEW.md) and [D042](../../DECISIONS.md#2026-11-03--d042-review-prs-merge-once-findings-are-recorded-fixes-go-through-grok-reviewed-patch-prs). The review PR records the holistic assessment, findings and remediation plan with gate outcome **changes required**. Remediation patch PR `patch/p5-6-review-fixes` will resolve every finding, record verification and propose the pass.

## Integrated assessment

The Phase 5 deliverables, architecture, automated suites and dated live evidence successfully deliver ordered prompt sequences and trusted verification gates without compromising routing isolation, permissions or project preservation.

- **Requirements/MVP scope:** All mandatory cards (P5.5, P5.1, P5.2, P5.3, P5.4) have complete evidence. Verification gates (P5.5, D043) execute declared checks after backend success and verified cleanup, without shell interpretation, using program pinning outside the canonical project. Sequence inputs (P5.1/P5.2, D044) snapshot ordered prompt files (`N-slug.md`) in memory before execution. Durable records (P5.3, D044) persist schema v1 records atomically under `$XDG_STATE_HOME/agent-harness/sequences/` with nonblocking project-level locking (`locks/PROJECT_KEY.lock`). `ah sequence show` inspects state without models or locks, and `ah sequence resume` enforces explicit operator choice (`--retry` or `--accept`) when an interrupted step may have had effects.
- **Rust design and dependencies:** Responsibilities map cleanly to modular components: `src/verify.rs` (330 lines) manages check validation, program path pinning, process-group execution, and SIGTERM/SIGKILL escalation; `src/state.rs` (615 lines) handles filesystem hierarchy, permissions, atomic file replacement, and schema v1 serialization; `src/sequence.rs` (1462 lines) manages CLI options, folder snapshots, strict YAML frontmatter metadata, sequential launch orchestration, and resume planning. Pinned dependency `sha2` (v0.10.8 / 0.10.9) with `default-features = false` (RustCrypto, MIT/Apache-2.0) was evaluated and integrated cleanly.
- **Routing/permissions/fallback:** Every step in a sequence runs as an isolated single run through `single::launch`, maintaining exact route policy, per-step preflight checks, isolated HOME/XDG environments, exact allow-once grants, and local-first fallback guards. Step metadata cannot set mode, model, permissions, or timeout, and cannot disable verification gates. No grants, sessions, or backend context leak across steps.
- **Project/state integrity:** The prompt folder snapshot is immutable during execution: edits by agent steps to prompt files cannot alter later steps in the running sequence. State directories and records are mode 0700/0600; existing permissive stores reject rather than repair. Advisory locking prevents concurrent sequence runs on the same project. Unchanged Git baseline files and untracked files are preserved; no automatic Git stash/reset/clean/commit occurs.
- **Tests/live evidence:** 105 Rust tests pass; locked Clippy and formatting pass with zero warnings. All 22 offline test suites pass under `python3 scripts/tests/offline.py` (22/22, ~214 s). P5.4 documents real multi-step sequence execution on a live LiteLLM coding task across two runs with intentional interruptions (SIGINT, SIGKILL), failed gate acceptance, and recovery via `--retry` and `--accept`.
- **Platform/operations:** Tested on `aarch64-apple-darwin` (macOS 27.0.1) with installed OpenCode 2.2.5. Key values are scrubbed from stderr, sequence records, logs, and managed configs (0 instances found). Residual friction and documentation drift are listed below.

## Findings and resolution

Consolidated findings across Phase 5 deliverables. All five findings are Low.

| Finding ID | Severity | Concrete issue / affected requirement | Correction / task / PR | Verification evidence | Disposition |
|---|---|---|---|---|---|
| R05-01 | Low | `--accept` without `--verify` names a later step (P5.4 F3): When resuming a stopped sequence where the stopping step was gated, running `ah sequence resume RUN_ID --accept` without `--verify` emits `step <later-step>: step metadata verify requires --verify` if a subsequent step in the remaining snapshot has frontmatter `verify: CHECK`. Because `resolve_all` validates all remaining steps upfront before checking the stopping step's gated-accept requirement, the error message cites the later step instead of explaining that the stopping step requires `--verify` and the recorded check name. The exit code (2, invalid) and safety (nothing launched) are correct, but the message points to the wrong step. | Update `src/sequence.rs` in `resume()` to validate the stopping step's gated-accept constraint before resolving later remaining steps, or validate the stopping step's check requirement first. Add a test in `tests/sequence.rs` and `scripts/tests/sequence_state.py`. | Reproduction test asserts that resuming with `--accept` without `--verify` on a gated stopping step names the stopping step, even if a later step has `verify:` metadata. | Open (`patch/p5-6-review-fixes`) |
| R05-02 | Low | Documentation drift in `docs/README.md`: line 16 states `Durable schema/resume 5; completion/limits 6` under "What remains phase-gated" for Workflow state, and line 5 describes Phase 5 as current work rather than accepted. | Update `docs/README.md` to reflect that Phase 5 workflow state and resume are implemented and verified; only Phase 6 completion/limits remain gated. Link this report. | Document re-read against `WORKFLOWS.md` and `PROJECT.md`. | Open (`patch/p5-6-review-fixes`) |
| R05-03 | Low | Documentation drift in `docs/DESIGN.md`: line 82 states "Workflow schemas and completion protocols stay deferred to Phases 5–6", although workflow schemas and durable state were finalized in Phase 5 (D044). Also update the DECISIONS.md deferred register row for Phase 5 if any pending phrasing remains. | Update `docs/DESIGN.md` line 82 to cite D044 for workflow schemas/state, leaving only Phase 6 completion protocols deferred. | Document re-read against `DECISIONS.md` and `DESIGN.md`. | Open (`patch/p5-6-review-fixes`) |
| R05-04 | Low | Documentation consistency in `docs/SPECIFICATION.md`: line 33 refers to persisting workflow records in the future tense ("persist workflow records when resume arrives"). | Update `docs/SPECIFICATION.md` line 33 to reference Phase 5 durable records in the past tense, citing D044. | Re-read against `SPECIFICATION.md` and `WORKFLOWS.md`. | Open (`patch/p5-6-review-fixes`) |
| R05-05 | Low | Operations runbook coverage in `docs/OPERATIONS.md`: line 3 still states "Workflow and additional native-adapter guidance remains prospective." While `0.1.0-alpha.2` was the Phase 4 MVP artifact, Phase 5 commands (`ah sequence run`, `ah sequence show`, `ah sequence resume`, `ah single ... --verify`) are implemented and lack operational runbook guidance (state location, locking, troubleshooting `interrupted` runs, inspect/resume commands). | Update `docs/OPERATIONS.md` status line and add a section documenting sequence workflow operations, lock troubleshooting, and verification checks. | Re-read against `WORKFLOWS.md` and `OPERATIONS.md`. | Open (`patch/p5-6-review-fixes`) |

### P5.4 residual issues

| Item | Agreed disposition |
|---|---|
| F1 — unterminated step responses joined and stayed buffered | Resolved in P5.4 (`f886208`): each sequence step response ends on its own line and human output is flushed within the 2-second budget. Verified by `sequence.py` and `verify.py`. |
| F2 — stored `interrupted` attempt displayed as never submitted | Resolved in P5.4 (`f886208`): `show` displays `unknown` for `interrupted` attempts. Verified by `sequence_state.py`. |
| F3 — `--accept` without `--verify` names a later step | Tracked as finding R05-01 above; to be resolved in remediation patch PR `patch/p5-6-review-fixes`. |

### Recommendations (not defects)

- **R05-REC1 (carried from R04-REC1): ACP tool kinds in progress and attempt records.** Live sequence use in P5.4 Run B confirmed that after an interrupted or crashed attempt, the operator cannot tell from the record whether edits occurred (`git status` was required to confirm no files were touched). Adding tool kind counters (`edit=0`, `read=3`, etc.) to progress and attempt summaries would enable informed `--accept` vs `--retry` decisions. This remains a recommendation for Phase 6 planning or candidate backlog; it is not authorized Phase 5 scope.

## Action plan for the next iteration

1. **Review PR `review/05-sequences`:** Merges under D042 with this report, findings R05-01–R05-05, and gate outcome **changes required**.
2. **Patch PR `patch/p5-6-review-fixes`:**
   - Code: Fix R05-01 in `src/sequence.rs` so that gated-accept validation for the stopping step takes precedence or is checked before resolving subsequent steps, with regression fixtures in `tests/sequence.rs` and `scripts/tests/sequence_state.py`.
   - Documentation: Fix R05-02 (`docs/README.md`), R05-03 (`docs/DESIGN.md`), R05-04 (`docs/SPECIFICATION.md`), and R05-05 (`docs/OPERATIONS.md`).
   - Checks: Run `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo test --locked`, and `python3 scripts/tests/offline.py` (22/22 suites).
   - Verify all five findings, update this report with verification evidence, propose the pass, and update `PROJECT.md`.
   - Following user instruction that Grok is currently unavailable, review will be conducted by another AI agent stand-in before merge.
3. **Phase progression:** Dependent phases (Phase 6 Ralph, Phase 7 native adapters, Phase 8 Pi, Phase 9 resource awareness) remain gated until `patch/p5-6-review-fixes` merges.

## Verification and integrated recheck

Baseline validation on `f886208` (macOS 27.0.1 arm64, Rust 1.88.0, OpenCode 2.2.5):

- `cargo fmt --check`: passes.
- `cargo clippy --all-targets --locked -- -D warnings`: passes with 0 warnings.
- `cargo test --locked`: passes (105 tests across unit and integration suites).
- `cargo build --release --locked`: passes (`ah 0.1.0-alpha.2`).
- `python3 scripts/tests/offline.py`: passes all 22 offline suites (22/22 passed, ~214 s), including `sequence.py`, `sequence_state.py`, `sequence_runtime.py`, `verify.py`, `single_runtime.py --verify`, `modes.py` (165 cases), and `capabilities_runtime.py`.
- Network-free preview: verified on sequence runs (`ah sequence run prompts/ --preview`).
- Reproduction of R05-01 confirmed: running `resume --accept` on a sequence where step 1 was gated and step 2 has `verify: check` metadata emits an error naming step 2 instead of step 1.

## Gate outcome

**Changes required** for reviewed scope `53e1707..f886208`. All five Low findings (R05-01–R05-05) are recorded with concrete remediation plans. No Critical, High, or Medium findings exist. In accordance with D042, this review PR may merge to establish the canonical review baseline. Dependent phases remain gated until the closing remediation PR `patch/p5-6-review-fixes` merges.
