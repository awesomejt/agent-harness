# Codex holistic review — Phase 4

## Review scope

- **Reviewer/date:** Codex, 2026-11-03 (America/Denver), with an independent read-only review of permission enforcement and runtime isolation.
- **Task/branch:** P4.9; existing `review/04-core-mvp`, [PR #42](https://github.com/awesomejt/agent-harness/pull/42). This is an individual review report, not the canonical acceptance report or a status-board update.
- **Accepted entry:** `2a2a424` (Phase 3 review, PR #32; documentation patch #33 included). **Implementation head:** `b38cc0f582cabe6022aa349b4b17d497a61b4bef` (PR #41). Review range `2a2a424..b38cc0f`: 52 files, 5,319 additions and 200 deletions. Review-branch head before this report: `3d22e7e47998163e92d4840bc6b71ad8e41965a7`; its two additional commits contain Claude's and Grok's reports, with no implementation changes.
- **Phase PRs:** [#34](https://github.com/awesomejt/agent-harness/pull/34) schema; [#35](https://github.com/awesomejt/agent-harness/pull/35) selection/emission; [#36](https://github.com/awesomejt/agent-harness/pull/36) constrained execution; [#37](https://github.com/awesomejt/agent-harness/pull/37) machine output; [#38](https://github.com/awesomejt/agent-harness/pull/38) inherited capabilities; [#39](https://github.com/awesomejt/agent-harness/pull/39) live roles; [#40](https://github.com/awesomejt/agent-harness/pull/40) artifacts; [#41](https://github.com/awesomejt/agent-harness/pull/41) repeated use/acceptance preparation.
- **Mandatory coverage:** P4.1–P4.8 and P4.9; D036–D041; G1–G5 and AC01–AC11. Earlier routing, permissions, supervision, project transactions and release machinery were examined where Phase 4 extends or depends on them. Applicable contracts: CONFIGURATION, EXECUTION, OPERATIONS, IMPLEMENTATION, SPECIFICATION, FEATURE_REVIEW and PHASE_REVIEW.
- **Exclusions:** fixes, phase acceptance, merge, new release, live provider inference and later-phase features. Historical live evidence and artifact evidence are assessed as records, not represented as freshly repeated checks.

## Result

**Changes required: six open Low findings; no Critical, High or Medium finding identified.** Five findings overlap the earlier reports; K04-06 adds a reproduced fallback-model provenance error in preview. No routing, permission-widening, fallback-replay or project-preservation defect was demonstrated. All severities must be resolved and verified before P4.9 can pass.

## Integrated assessment and coverage

| Scope / criteria | Assessment and evidence |
|---|---|
| P4.1; G5, AC08; F05/F06 | Canonical definitions use strict typed YAML, bounded UTF-8/frontmatter, actual string scalars, explicit ceilings/tools and filename-bound names. Unknown/duplicate fields, custom tags, coercions and invalid tool/ceiling combinations refuse. `tests/agents.rs` and the installed destination probe cover the parser and OpenCode format separately. `Catalog` is bounded; CLI selection reads only the chosen project definition. |
| P4.2; G4/G5, AC04/AC05/AC08; F03/F04 | Emission extends the existing project-only transaction. Exact-content receipts protect ownership; unrecorded files, manual edits, case variants and alternate OpenCode sources refuse. Snapshot rechecks, locking, per-file atomic replacement and directory fsync are retained. The isolated runtime does not load emitted files. Native and no-sync routes do not emit agents. Golden/ownership/stale-plan tests pass. |
| P4.3; G3/G5, AC02/AC03/AC07/AC08; F02/F05/F06/F24 | Invocation denial wins; trusted invocation narrows to the canonical ceiling and listed tools. Global rules also constrain helpers. Preflight validates every agent's rule tail/model/request overrides and the selected role's exact system text, description and visible primary status. ACP checks selected session mode before submission, listed kinds and exact arguments before a one-shot grant, and prohibited/unknown completed kinds. Non-default effort refuses before runtime/network/writes. Fallback preserves the role, effective rules and instruction path and never replays submitted work. Focused independent review found no additional defect. |
| P4.7; G2, AC06; F13/F14/F24 | Machine output has explicit v1 envelopes, ordered sequence numbers, nullable unknown usage, a separately retained terminal result and bounded output delivery. Rejected invocations still produce machine records. Human diagnostics remain separate. Consumer fixtures cover every exit, cancellation, uncertainty, blocked stdout, headless stdin, redaction and linked fallback attempts. D039 explicitly evaluates and declines R03-REC1; conservative post-submission uncertainty remains justified. |
| P4.8; AC11; F18/F19 | D040 explicitly restores only project-root `AGENTS.md` under disabled project discovery. Resolution requires a regular in-project target; both attempts carry the same path. Runtime commands are refused. The installed capability suite checks planted config/agent/skill/plugin/MCP/command sources against a recording local model stub. Context/compaction remain runtime-owned and unverified, rather than being presented as implemented harness behavior. |
| P4.4; G2/G5, AC05/AC07/AC08/AC11 | [Live role evidence](../evidence/p4-4-primary-reviewer-acceptance.md) records coder/reviewer inference on both routes and fallback, prohibited-operation/deny trials, effort refusals and dirty-work preservation. LiteLLM traces show role/instruction delivery and offered tools. Native instruction delivery is behavioral evidence, not a provider request trace or a driver assertion; the record states that limitation. |
| P4.5; G1, AC09/AC10; F11/F25 | [Artifact evidence](../evidence/p4-5-mvp-artifacts.md), D041 and OPERATIONS declare exactly one target: Apple Silicon macOS 27.0.1 with OpenCode 2.2.5. Packaging includes reviewed examples and dependency attribution; smoke checks install/upgrade/rollback and configuration/login preservation. P4.6 verifies the published alpha.2 checksum/provenance and repeats use with that binary, satisfying R03-REC2. No new platform, signing or notarization claim is inferred. Preview reporting gaps are listed below. |
| P4.6; G1–G5, AC01–AC11; F01/F12/F16/F20 | [Acceptance preparation](../evidence/p4-6-core-mvp-acceptance.md) maps every goal and criterion to Phase 2–4 evidence, including real maintenance edits, independent tests and review, cancellation and artifact use. It records unsuccessful trials as well as successes. All mandatory cards have evidence; P4.9 remains unchecked. Backend success is not independent task verification. |

**Rust ownership and dependencies.** The single crate remains proportionate. `agents` owns parsing/selection; `opencode` owns version-specific generation and validation; `project_config` owns emission/ownership; `acp` owns protocol and grant checks; `progress` owns output; `single` owns coordination. OpenCode retains the inner coding loop. The new pinned YAML dependency is covered by the dependency evaluation and packaging notice collector; locked builds remain on Rust 1.88. No architecture change is required by this review. DESIGN's implementation map needs updating (K04-03).

**State, cleanup and operational limits.** The receipt is an ownership aid, not authentication against a hostile project author. File/receipt updates are individually atomic, not one atomic transaction; an interrupted agent-file update becomes a visible ownership conflict. External editors can race checks. Trusted execute remains host shell authority without an OS sandbox; detached descendants are outside process-group containment. Project instructions are runtime-read and unsnapshotted. Those limits are documented and are not newly discovered defects. No durable workflow state, scheduler, additional adapter or autonomous delegation is part of Phase 4.

## Findings and required verification

All entries are **open**. Corrective work below is proposed, not performed or authorized as part of this report. IDs are local to this report; overlaps identify the same defect for later consolidation.

| ID | Severity | Concrete issue / affected requirement | Correction/task/PR | Verification evidence / required recheck |
|---|---|---|---|---|
| K04-01 | Low | `DECISIONS.md:183` still leaves canonical schema/destinations/constraints pending, despite D036–D038 resolving them. Deferred-choice traceability is inconsistent. Same defect as C04-01/G04-01. | Update the register in PR #42 to cite the adopted decisions and explicit effort limits. | Directly confirmed the stale row. Recheck it against D036–D038 and CONFIGURATION after correction. |
| K04-02 | Low | `docs/SPECIFICATION.md:69` describes canonical `role: primary/subagent/all` and a single model alias. The implemented schema requires `capacity: primary/specialized/both` and optional route-specific `models`; the paragraph still defers validation to Phase 4. The goal-owning document contradicts the parser. Same defect as C04-02/G04-02. | Correct the goal-level description and link the implemented grammar in CONFIGURATION; retain backend modes as mapping details. Documentation change in PR #42. | Direct comparison with `agents/*.md`, `src/agents.rs` and D036/D038. Recheck schema terms and remove obsolete pending wording. |
| K04-03 | Low | `docs/DESIGN.md:90–94` omits `agents`, machine-output ownership and agent-emission responsibilities from the implemented module map, and still says canonical agents/machine output remain gated. Same defect as C04-03/G04-03. | Update the implemented mapping through Phase 4 in PR #42. | Compare all `src/*.rs` responsibilities with the revised map; distinguish implemented single-run JSONL from deferred workflow state. |
| K04-04 | Low | `docs/TESTING.md:3` still calls named agents/machine output gated; `docs/ARCHITECTURE.md:152` still promises expanded platforms in Phase 4, whereas D041 declares one target. Current capability/platform status is inconsistent. Overlaps C04-04/G04-04; I do not treat the docs index's reference to the accepted P3.6 review as a separate defect. | Correct current-status text in PR #42; use D041's tested matrix and keep future expansion deferred. | Directly confirmed both passages. Re-read against P4.6, OPERATIONS and D041. |
| K04-05 | Low | `src/preview.rs:53–55` renders the invocation's broad trusted scope as `permissions: trusted: read/write/shell...` even for a read-only named reviewer. The separate `agent:` line lists the narrower kinds, leaving contradictory authority descriptions (AC09). Same defect as C04-05/G04-05. Enforcement itself narrows correctly. | Linked `patch/` PR: distinguish invocation authorization from effective role permissions using the shared effective-policy mapping. | Reproduced with read-only reviewer plus `--permissions trusted --preview`: agent line reports read/search, permissions line reports write/shell. Add preview assertions for narrowed trusted, deny and unnamed trusted cases; run relevant permission/preview suites. |
| K04-06 | Low | `src/preview.rs:108–111` hardcodes fallback provenance as `native.model`, even when D037 precedence selects the agent's `models.native`. AC09 diagnostics misidentify the source of the displayed fallback model. No incorrect runtime model selection was observed. | Linked `patch/` PR (can accompany K04-05): render fallback provenance from `native.sources.model`, as the main model line already does. | Reproduced with config `native.model: config-native` and reviewer `models.native: agent-native`: preview prints `opencode/agent-native (native.model; key reference present)`. Assert agent and config fallback provenance separately, including a primary `--model` override that must not alter fallback precedence. |

### Preview reproduction for K04-05/K04-06

In a disposable project, use this `ah.json` (dummy environment reference; no network required):

```json
{"version":1,"mode":"local-first","model":"local-config","litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"TEST_KEY"},"native":{"target":"opencode","model":"config-native","api_key_env":"TEST_KEY"}}
```

Create `agents/reviewer.md`:

```markdown
---
version: 1
name: reviewer
description: Read only reviewer
capacity: specialized
permissions: read-only
tools: [read, search]
models:
  native: agent-native
---
Review only.
```

Run `TEST_KEY=fixture ah single review --project PROJECT --agent reviewer --permissions trusted --preview`. Exit is 0. The `agent:` line correctly reports effective `["read", "search"]`; the `permissions:` line still advertises read/write/shell. The fallback line correctly selects `opencode/agent-native` but labels its source `native.model`.

## Residual issues and recommendations

- **P4.6 R1:** accepted scoped limitation. An `end_turn`/exit 0 can occur without the requested edit; the independent check caught it. P5.5 verification gates address this, and remain dependent on Phase 4 acceptance. Zero tool events are useful evidence, not proof that replay is safe or a universal failure rule.
- **P4.6 R2:** bounded long-running reviews with only counters meet the current progress contract. Support the other reports' candidate recommendation for tool-kind visibility, excluding raw titles/arguments that may contain sensitive data. This is not additional Phase 4 implementation scope.
- **P4.6 R3:** shared-alias contention is an operational observation; the recorded cancellation cause is unconfirmed. Run live acceptance serially and retain timing.
- **P4.6 R4:** exported prerequisites and actionable missing-key diagnostics are already documented/tested.
- Preserve D039's conservative uncertainty and no-replay policy. A consumer heuristic or future verification gate must not silently expand fallback eligibility.

## Verification and integrated recheck

Environment: macOS 27.0.1 (26A434), arm64; Rust 1.88.0; installed OpenCode 2.2.5. Toolchain/Homebrew directories were added to this shell's PATH; no project configuration was changed.

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo test --locked`, `cargo build --locked` and `cargo build --release --locked`: pass; **82 root tests**.
- Fake-runtime suites: `agents_exec.py`, `machine.py`, `preview.py`, `local_first.py`, `modes.py` (**165 cases**), `native.py` (**40 cases**), `single.py` and `worktree.py`: pass.
- Installed-runtime suites: `agents_runtime.py` (six destination probes), `agent_emission_runtime.py` (eight emission/collision probes), `agent_exec_runtime.py` (four named-role preflight/session runs), `capabilities_runtime.py` (eight capability checks) and `native_runtime.py`: pass. These use local stubs or intercept prompts; no provider inference is established by them.
- Installed-runtime checks: `single_runtime.py`, `single_runtime.py --jsonl --cancel`, `single_runtime.py --jsonl --refuse`: pass with a deterministic local model stub; edit/test succeeds, cancellation preserves applied effects and refusal grants no prohibited operation.
- Independent constraint reviewer also ran `cargo test --locked`, `agents_exec.py`, `local_first.py`, `agent_exec_runtime.py` and `capabilities_runtime.py`: pass, with no additional findings.
- Ad hoc preview reproduction above: both reporting errors confirmed. No fixes were applied, so these checks are baseline validation, not remediation verification.
- Live inference, a fresh published-archive download/install smoke and new packaging were not repeated. Dated P4.4–P4.6 evidence supports those claims; native provider request contents and model reliability retain their stated limitations. No account probing or provider model turn was used in this review.

## Gate outcome

**Changes required for `2a2a424..b38cc0f`.** Keep P4.9 and dependent phases open. Consolidate the three independent reports into `docs/reviews/phase-04.md` after agreeing the remediation plan. Correct documentation in this review PR; put code corrections in linked `patch/` PRs with the required Grok review. Verify every correction and recheck the combined integrated state before proposing pass. PROJECT.md and canonical acceptance should be updated only through that subsequent closeout; this report does not accept or merge Phase 4.
