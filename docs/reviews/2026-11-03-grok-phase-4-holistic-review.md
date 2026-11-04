# Phase 4 holistic review — Grok

**Reviewer:** Grok (xAI)  
**Date:** 2026-11-03  
**Branch:** `review/04-core-mvp` (PR #42)  
**Reviewed head:** `b38cc0f` (PR #41)  
**Entry baseline:** `2a2a424` (Phase 3 review, PR #32 + doc patch #33)  
**Scope:** P4.1–P4.8 + P4.9; decisions D036–D041; G5 and core-MVP close of G1–G5 against AC01–AC11 (including supporting Phase 2–3 work). Residual issues R1–R4 from P4.6 dispositioned below.  
**Excluded:** live inference re-runs (P4.4/P4.6 records relied on); sequences/Ralph; additional native CLIs/Pi; resource awareness; fixes or merge authorization.

This is an independent holistic assessment of the integrated Phase 4 surface. It examines accumulated behavior across the reviewed range (`2a2a424..b38cc0f`) rather than only the final diff, and is distinct from the primary Claude report already present on this branch.

## Requirements and acceptance coverage

| Task / criterion | Integrated evidence and conclusion |
|---|---|
| P4.1 / AC08 | `src/agents.rs` implements the D036 schema (version 1, capacity primary/specialized/both, permissions ceiling, tools list, route-specific models, effort). Strict typed decoding with `deny_unknown_fields`, custom YAML tags rejected, string visitors prevent coercion, frontmatter capped at 16 KiB, name grammar + OpenCode reserved-name exclusion, tools-vs-ceiling check. `Agent::select` is name-based, refuses symlinks/case variants/non-regular files. |
| P4.2 / AC08, AC04 | Emission in `project_config` is receipt-owned, conflict-aware, snapshot-rechecked, atomic. Native route and `--no-sync` emit nothing. Model precedence and group resolution stay route-correct. |
| P4.3 / AC07, AC08 | Effective permissions are the intersection of invocation profile and agent ceiling; deny always wins. OpenCode rules, harness grant decisions and completion checks form three layers. Specialized capacity does not map to a backend subagent (avoids 2.2.5 silent build substitution); ACP mode check is the backstop. Non-default effort refused before launch. Recovery guard compares effective rules. |
| P4.7 / AC06 | `progress.rs` owns ordered machine records; exactly one terminal result; unknown metrics null; machine mode detected before parse so rejections still produce a result. |
| P4.8 / AC11 | D040 restores AGENTS.md under disabled project config. Resolver is canonical-project-root only; outside symlinks refused; slash-command prompts refused. Skills/MCP/plugins/commands/web tools unloaded or denied. |
| P4.4 / AC05, AC07, AC08, AC11 | Live evidence in `docs/evidence/p4-4-primary-reviewer-acceptance.md` covers coder/reviewer on both routes + fallback, prohibited operations, deny, effort refusal. |
| P4.5 / AC09, AC10 | D041 declares one target (`aarch64-apple-darwin`, macOS 27.0.1). `v0.1.0-alpha.2` archive includes examples and notices; smoke covers upgrade/preservation/rollback. |
| P4.6 / G1–G5, AC01–AC11 | Acceptance record cites evidence; residual issues explained and dispositioned. |

The implementation, tests and dated live evidence support the core MVP claims as scoped (one target, OpenCode 2.2.5 exactly, default effort only). No demonstrated defect in routing, permission enforcement, fallback or project integrity was identified.

## Integrated assessment

**Ownership and module boundaries.** The single crate remains proportionate. The new `agents` module is a pure parser/selector with no side effects. `opencode` owns all 2.2.5-specific mapping (runtime document, ceiling/effective rules, grantable kinds, effort, emitted Markdown). `project_config` extends the existing transaction. `progress` owns both human and machine output. `single` keeps capability refusals ahead of any runtime/network/write. The only new dependency is `serde_yaml_ng` 0.10.0 (MIT); notices are in the published archive. No speculative multi-backend traits or effort mappings were added.

**Routing, permissions and fallback.** Named role changes the default agent and rules, never the provider policy. Permission narrowing is enforced in OpenCode rules, harness grants and completion checks. Local-first fallback cannot widen a role (recovery guard compares effective rules). Trusted shell remains host authority with no OS sandbox; skill tool stays offered while loading is denied; native request contents are unobserved. These limits are documented.

**Project integrity.** Emission follows the existing lock/snapshot/atomic/fsync rules. Crash between agent file and receipt surfaces as ownership conflict. Cloud-only and fallback paths write nothing. Runtime never loads the emitted file, so stale emission cannot affect enforcement.

**Tests and live evidence.** Tests assert observed behavior (wire tools, rule tails, grant outcomes, record order). Live gate is honest about its two residual failures (R1, R3). R1 (agent success without doing the work) is the class of failure AC01 cannot prevent; the harness correctly reports the runtime terminal state.

**Platform and operations.** One declared target. OPERATIONS diagnostics cover the missing-key and zero-grant cases. No platform/effort/capability claim exceeds the cited evidence.

## Findings

No Critical, High or Medium findings. Five Low findings (documentation drift and one preview wording issue) remain open. Severities follow PHASE_REVIEW.md; all must be resolved before pass.

| ID | Severity | Concrete issue / affected requirement | Proposed correction | Verification required |
|---|---|---|---|---|
| G04-01 | Low | DECISIONS.md deferred register still contains the open row “Canonical agent schema, destination paths, constraints” (owner phase 4) with the pre-resolution text, although D036–D038 and D040 resolve it. Traceability defect in the record that owns deferred choices. | Mark the row resolved by D036 (schema/destinations), D037 (selection/emission), D038 (invocation/enforcement/effort) and D040 (inherited capabilities). | Register shows no open Phase 4 row. |
| G04-02 | Low | SPECIFICATION.md “Canonical agents” paragraph still describes the superseded schema (role primary/subagent/all, optional model alias) and uses future tense for Phase 4 validation. Conflicts with D036/CONFIGURATION. | Describe the D036 fields at goal level, link CONFIGURATION for the grammar, and change Phase 4 statements to past tense with links. | Wording matches D036 and the example agents. |
| G04-03 | Low | DESIGN.md “Phase 2 implemented mapping” omits the `agents` module and Phase 4 responsibilities (named-role mapping and emitted Markdown in `opencode`, agent emission in `project_config`, v1 machine records in `progress`). Same class of drift previously fixed for Phase 3. | Extend the section to cover implemented Phases 2–4 and name every `src/*.rs` module with its current owner; note the new dependency. | Module map is complete. |
| G04-04 | Low | Stale status text: TESTING.md still says “named agents, machine output and workflows remain gated”; docs/README.md still says Phase 3 acceptance “is the P3.6 holistic review (PR #32)”; ARCHITECTURE.md still says “Expanded supported platforms are declared in Phase 4 after tests” (D041 declares exactly one target). | Update all three to the post-P4.6 state; cite D041 for the single-target matrix. | No pending-tense Phase 3/4 status claims remain. |
| G04-05 | Low | In `preview::render`, the `permissions:` line reports only the invocation scope. For a named role under a trusted invocation it prints the broader trusted wording even though the effective rules are narrower (visible only on the separate `agent:` line). Overstates authority (conservative direction) but AC09 capability reporting should not contradict itself. | Append the narrowing to the permissions line when a role narrows a trusted invocation (e.g. “narrowed by agent to read, search”) and assert it. Code fix belongs in a linked `patch/` PR with `/grok review`. | Preview fixture asserts the narrowed wording; unnamed trusted line unchanged. |

These match the substance of Claude’s C04-01–C04-05. No additional findings of any severity were identified from independent inspection of the schema parser, emission transaction, permission layers, machine-output ordering, inherited-capability resolver and the cited contract documents.

## Residual issues from P4.6

| P4.6 item | Disposition |
|---|---|
| R1 — agent success is not verified success | **Accepted limit, not a Phase 4 defect.** Harness reports the runtime terminal state. OPERATIONS already requires independent verification on exit 0. P5.5 verification gates remain the correct remedy. |
| R2 — open-ended work can exhaust the bound | **Recommendation, not a defect.** Bound, cancellation and cleanup behaved correctly. |
| R3 — shared-alias load | **Operational note.** Live acceptance runs should not overlap. |
| R4 — environment-dependent prerequisites | **Already addressed** by the OPERATIONS diagnostic row. |

## Recommendations (not findings)

- **R-G04-1 — tool kind in progress.** Add the ACP tool kind (not title/arguments) to human activity lines and as an optional v1-compatible field. Kinds are already harness-validated and carry no paths. Candidate for the backlog.
- **R-G04-2 — documented consumer heuristic.** Until P5.5, OPERATIONS CI notes could flag `outcome: succeeded` with `tool_events: 0` on an edit task. Guidance only; no harness reinterpretation of backend success.

## Verification summary

Independent code and document inspection of the reviewed head (plus the Claude report already on this branch):

- Schema parser (`agents.rs`) rejects unknown fields, tags, coercion, traversal, case variants and tools above the ceiling.
- Emission path is receipt-owned and does not affect enforcement on the native route or under `--no-sync`.
- Permission intersection and three-layer enforcement are present; recovery guard compares effective rules.
- Machine output guarantees exactly one terminal result; rejections still emit a result.
- Inherited-capability resolver is canonical-project-root only.
- Documentation drifts listed above were confirmed by direct reading of DECISIONS.md, SPECIFICATION.md, DESIGN.md, TESTING.md, docs/README.md, ARCHITECTURE.md and `preview.rs`.

Claude’s verification (fmt, Clippy, 82 root tests, all non-live script suites against OpenCode 2.2.5, no leftover state) is relied upon for the executed checks; this review did not re-execute the suite. No live inference was repeated.

## Gate outcome

**Changes required** for the reviewed scope `2a2a424..b38cc0f`. To pass:

1. Correct G04-01 to G04-04 in this review PR (documentation only).
2. Fix G04-05 in a linked `patch/` PR with a fixture, request `/grok review`, and merge it.
3. Re-check the combined state and record the resolved findings in the canonical `docs/reviews/phase-04.md` with links to the independent reports.
4. Then merge the review PR and check P4.9 in PROJECT.md.

All five findings are Low and localized. No Critical/High/Medium issue blocks the core MVP claims. Dependent phases must continue to wait for the accepted P4.9 gate.

---

*This review was performed independently of the primary Claude Phase 4 report. It reaches the same substantive conclusion (changes required, five Low findings, no higher-severity defects) while recording its own traceability.*
