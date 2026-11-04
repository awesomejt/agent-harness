# Phase 4 holistic review

## Review scope

- Task: P4.9; consolidating reviewer: Claude Code primary agent (Opus 5.5); date: 2026-11-03 (America/Denver).
- Accepted entry baseline: `2a2a424` (Phase 3 review, [PR #32](https://github.com/awesomejt/agent-harness/pull/32), plus documentation patch [PR #33](https://github.com/awesomejt/agent-harness/pull/33)). Reviewed material head: `b38cc0f` (PR #41 merged). Range `2a2a424..b38cc0f`: 52 files (+5319/−200).
- Included PRs: [#34](https://github.com/awesomejt/agent-harness/pull/34) P4.1 schema; [#35](https://github.com/awesomejt/agent-harness/pull/35) P4.2 selection/emission; [#36](https://github.com/awesomejt/agent-harness/pull/36) P4.3 constrained execution; [#37](https://github.com/awesomejt/agent-harness/pull/37) P4.7 machine output; [#38](https://github.com/awesomejt/agent-harness/pull/38) P4.8 inherited capabilities; [#39](https://github.com/awesomejt/agent-harness/pull/39) P4.4 live roles; [#40](https://github.com/awesomejt/agent-harness/pull/40) P4.5 artifacts (`v0.1.0-alpha.2`); [#41](https://github.com/awesomejt/agent-harness/pull/41) P4.6 acceptance evidence.
- Mandatory scope: P4.1–P4.8 and P4.9; D036–D041; G5 and the core-MVP close of G1–G5 against AC01–AC11, including supporting Phase 2–3 tasks. Excluded: sequences, Ralph, more native CLIs, Pi, resource awareness and live re-inference.
- Inputs: three independent reports on review [PR #42](https://github.com/awesomejt/agent-harness/pull/42). Claude: [report](2026-11-03-claude-phase-4-holistic-review.md), findings C04-01–C04-05. Grok: [report](2026-11-03-grok-phase-4-holistic-review.md), G04-01–G04-05. Codex: [report](2026-11-03-codex-phase-4-holistic-review.md), K04-01–K04-06.

This is revision 1 of the canonical Phase 4 report. **It records an open gate and the agreed remediation plan. It is not a pass.** It is merged by the owner's direction so that the plan is on `main` before the next iteration. P4.9 stays unchecked in PROJECT.md. This report is updated in place by the closeout PR. Accepted-report immutability applies only after a pass is recorded.

## Integrated assessment

All three reviewers independently reach the same conclusion. The Phase 4 implementation, tests and dated live evidence support the core MVP as scoped: one target (`aarch64-apple-darwin`, macOS 27.0.1), OpenCode 2.2.5 exactly, default effort only. None of them found a routing, permission-widening, fallback-replay or project-preservation defect.

- **Requirements/MVP scope:** every mandatory card has evidence. The IMPLEMENTATION Phase 4 exit evidence is present, and the "decide here" items are recorded in D036–D041. The Phase 3 gate inputs were consumed: R03-REC1 was evaluated and declined (D039), and R03-REC2 was satisfied by alpha.2 (D041). See the individual reports for per-card tables.
- **Rust design:** the single crate and its ownership remain proportionate. `agents` is a pure parser and selector. `opencode` owns 2.2.5 mapping. `project_config` extends the D025 transaction. `progress` owns both output modes. `acp` adds kind-bound grants and completion checks. The only new dependency is `serde_yaml_ng` 0.10.0 with `unsafe-libyaml` (MIT); both are attributed in the archive.
- **Routing/permissions/fallback:** effective rules intersect the invocation profile with the role's ceiling, and deny always wins. Three layers enforce them: OpenCode rules, harness grants and completion checks. Specialized capacity never maps to a backend subagent. The recovery guard compares agent name, effective rules and instructions. Codex's separate constraint review found no additional defect.
- **Project/state:** emission is receipt-owned and snapshot-rechecked. A crash between the file and its receipt surfaces as a visible conflict. Native, fallback and `--no-sync` runs write nothing. The runtime never loads the emitted file.
- **Tests/live evidence:** the root suite (82 tests), Clippy, format and every non-live suite pass on Rust 1.88.0 with installed OpenCode 2.2.5. Claude and Codex each ran them independently; Grok relied on those runs. Live evidence is P4.4 plus six P4.6 passes from the published alpha.2, with both failures explained.
- **Operations/platform:** one declared target. Prerequisites and diagnostics are documented, including the missing-key and zero-grant exit-4 cases. No claim exceeds the evidence.
- **Documentation/task consistency:** residual drift is listed below (R04-01 to R04-04).

## Findings and resolution

Consolidated IDs below. The reviewer-local IDs are kept for traceability. All six findings are Low. The first five were found by all three reviewers; R04-06 comes from Codex and was reproduced by Claude.

| Finding ID | Severity | Concrete issue / affected requirement | Reviewer IDs | Correction / task / PR | Verification evidence | Disposition |
|---|---|---|---|---|---|---|
| R04-01 | Low | The DECISIONS.md deferred register row "Canonical agent schema, destination paths, constraints" (owner phase 4) still reads as pending, although D036–D038 and D040 resolve it. | C04-01, G04-01, K04-01 | Patch PR (plan step 1): mark it resolved by D036/D037/D038/D040, with the default-effort-only limit. | Register shows no open Phase 4 row. | Open |
| R04-02 | Low | SPECIFICATION.md "Canonical agents" (line 69) describes the superseded `role: primary/subagent/all` and a single model alias, and defers validation to Phase 4. Line 55 also speaks of Phase 4 machine output in the future tense. | C04-02, G04-02, K04-02 | Plan step 1: describe the D036 fields at goal level, link CONFIGURATION, and change both statements to the past tense. | Compared with `agents/*.md`, `src/agents.rs`, D036 and D038. | Open |
| R04-03 | Low | The DESIGN.md implemented module map omits `agents`, agent emission (`project_config`), named-role mapping (`opencode`) and v1 machine records (`progress`). | C04-03, G04-03, K04-03 | Plan step 1: extend the map through Phase 4, name every `src/*.rs` module and the YAML dependency, and distinguish single-run JSONL from deferred workflow state. | Every `src/*.rs` module is named with its owner. | Open |
| R04-04 | Low | Stale status text: TESTING.md line 3 ("named agents, machine output … remain gated"); ARCHITECTURE.md line 152 ("expanded supported platforms are declared in Phase 4"; D041 declares one); docs/README.md line 5 (P3.6 acceptance phrased as pending). | C04-04, G04-04, K04-04 | Plan step 1: update all three to the post-P4.6 state. Codex did not count the docs/README.md wording as a separate defect, but fixing it costs nothing and is included. | No pending-tense Phase 3/4 status claims remain. | Open |
| R04-05 | Low | Preview's `permissions:` line shows the invocation scope ("trusted: read/write/shell…") for a named role whose effective rules are narrower (for example, the reviewer gets read and search only). Only the `agent:` line shows the narrowing, so AC09 reporting contradicts itself. Enforcement itself is correct. | C04-05, G04-05, K04-05 | Plan step 1 code change in `src/preview.rs`: report invocation authorization and effective role permissions from the shared `opencode::effective`/`grantable` mapping. | Preview assertions for narrowed trusted, deny-invocation and unnamed trusted cases. | Open |
| R04-06 | Low | Preview's fallback line hardcodes provenance `native.model`, even when D037 precedence selects the agent's `models.native`. Reproduced: config `native.model: config-native` with reviewer `models.native: agent-native` prints `opencode/agent-native (native.model; …)`. The runtime selection is correct; only the label is wrong (AC09). | K04-06 | Plan step 1 code change: render the source from the fallback's `sources.model`, as the main model line already does. | Assertions for agent-sourced and config-sourced fallback provenance, and for a primary `--model` override that leaves fallback precedence unchanged. | Open |

### P4.6 residual issues

| Item | Agreed disposition |
|---|---|
| R1 — agent success is not verified success | Accepted scoped limit, not a Phase 4 defect. The harness reports the runtime's terminal state (D024/D039). OPERATIONS already requires independent verification on exit 0. P5.5 verification gates are the remedy and are scheduled first in Phase 5 (plan step 4). |
| R2 — long open-ended runs show counts only | Meets the current progress contract. Covered by recommendation R04-REC1 below. |
| R3 — shared-alias load | Operational note: run live acceptance serially and keep per-row timing. The cause of the recorded cancellation is unconfirmed. Plan step 1 adds a one-line note to TESTING's live-gate paragraph. |
| R4 — environment-dependent prerequisites | Already addressed by the OPERATIONS missing-key diagnostic. No change. |

### Recommendations (not defects)

- **R04-REC1 — tool kind in progress.** Show the ACP tool kind (`read`/`search`/`edit`/`execute`/`other`) on human activity lines, and add per-kind counters as an optional v1-compatible field. Exclude titles and arguments, which can contain paths or commands. All three reviewers support it. Recorded as a candidate to evaluate during Phase 5 planning; it is not authorized Phase 4 scope.
- **R04-REC2 — consumer heuristic guidance.** Add a note to OPERATIONS' CI section that `outcome: succeeded` with `tool_events: 0` on an edit task deserves scrutiny. This is documentation only: the harness must not reinterpret backend success, and must not widen fallback or replay eligibility (D031/D039). Included in plan step 1, because it costs nothing and directly mitigates R1 until P5.5.

## Action plan for the next iteration

Agreed after considering all three reports. Every finding is Low and localized, and no implementation-architecture change is needed.

1. **Patch PR `patch/p4-9-review-fixes`** (one PR, following the P3.6 precedent of `patch/p3-6-review-fixes`):
   - Documentation: R04-01, R04-02, R04-03, R04-04, the R3 live-gate note and R04-REC2.
   - Code: R04-05 and R04-06 in `src/preview.rs`, with fixtures in `tests/cli.rs` and/or `scripts/tests/preview.py`. Cover narrowed trusted, deny-invocation and unnamed trusted permission lines, plus agent-sourced, config-sourced and `--model`-overridden fallback provenance.
   - Checks: `cargo fmt --check`, locked Clippy, `cargo test --locked`, and the `preview.py`, `agents_exec.py`, `local_first.py` and `modes.py` suites. Runtime behavior must stay unchanged: only preview text changes, so the installed-runtime and live records remain current.
   - Post `/grok review` after opening. Address Grok findings under the Git workflow (at most three reviews), then merge.
2. **Closeout PR `review/04-closeout`:** update this report's findings to Resolved with the patch PR link and verification results. Re-run the integrated recheck (root suite, all non-live suites and the installed-runtime suites). Record the gate as pass. Check P4.9 in PROJECT.md, linking this report and both PRs.
3. **No new release is required** for the fixes. Preview wording and documentation do not change the alpha.2 MVP claims. The next artifact will pick them up.
4. **After the gate passes:** Phase 5 begins with P5.5 (trusted verification gates, R1), then P5.1/P5.2. R04-REC1 is evaluated during that planning. Phases 7 and 8 stay selection-gated, and no observed need selects a second native CLI.

Until step 2 merges, no Phase 5, 7 or 8 work may consume the Phase 4 baseline.

## Verification and integrated recheck

Baseline validation on `b38cc0f` (no fixes applied yet), macOS 27.0.1 arm64, Rust 1.88.0, OpenCode 2.2.5:

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings` and `cargo test --locked` (82 tests) pass. Codex also ran debug and release locked builds.
- `single.py`, `preview.py`, `worktree.py`, `native.py` (40 cases), `local_first.py`, `modes.py` (165 cases plus 14 invalid configurations), `agents_exec.py` and `machine.py` pass.
- Installed-runtime checks pass: `single_runtime.py` (default, `--cancel`, `--group=coder` and `--refuse`; Codex also ran the `--jsonl` variants), `native_runtime.py`, `agents_runtime.py` (6 probes), `agent_emission_runtime.py` (8 probes), `agent_exec_runtime.py` (4 runs) and `capabilities_runtime.py` (8 checks).
- After the runs, no `ah-runtime-*` state and no OpenCode `acp`/`serve` process remained.
- The R04-05 and R04-06 reproductions were confirmed by network-free preview.

These commands contact no live provider. P4.4 and the six P4.6 passes from the published alpha.2 remain the live record: changes after `1f7463d` are limited to `roles_live.py` timing and Markdown. Remediation verification and the post-fix integrated recheck are pending (plan steps 1–2).

## Gate outcome

**Changes required** for the reviewed scope `2a2a424..b38cc0f`. Six Low findings are open, and there are no Critical, High or Medium findings. Merging review PR #42 records the reports and this plan only; it does not pass P4.9. The pass will be proposed in the closeout PR (plan step 2), after the patch PR merges and every finding is verified.
