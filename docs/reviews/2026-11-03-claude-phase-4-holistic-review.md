# Claude holistic project review — Phase 4

## Review scope

- **Reviewer/date:** Claude Code (Opus 5.5), 2026-11-03 (America/Denver).
- **Review task:** P4.9 ([card](../../tasks/04-core-mvp.md#p4-9)); branch `review/04-core-mvp`. This is one reviewer's independent assessment. It is not the canonical `phase-04.md` revision, and it does not record acceptance.
- **Accepted entry:** `2a2a424` (Phase 3 review, [PR #32](https://github.com/awesomejt/agent-harness/pull/32), with documentation patch [PR #33](https://github.com/awesomejt/agent-harness/pull/33)). **Reviewed head:** `b38cc0f` (PR #41 merged). Range `2a2a424..b38cc0f`: 52 files, +5319/−200.
- **Included PRs:** [#34](https://github.com/awesomejt/agent-harness/pull/34) P4.1 schema; [#35](https://github.com/awesomejt/agent-harness/pull/35) P4.2 emission/selection; [#36](https://github.com/awesomejt/agent-harness/pull/36) P4.3 constrained execution; [#37](https://github.com/awesomejt/agent-harness/pull/37) P4.7 machine output; [#38](https://github.com/awesomejt/agent-harness/pull/38) P4.8 inherited capabilities; [#39](https://github.com/awesomejt/agent-harness/pull/39) P4.4 role acceptance; [#40](https://github.com/awesomejt/agent-harness/pull/40) P4.5 artifacts (`v0.1.0-alpha.2`); [#41](https://github.com/awesomejt/agent-harness/pull/41) P4.6 MVP acceptance evidence.
- **Mandatory scope:** P4.1–P4.8 and the P4.9 gate; decisions D036–D041; G5 and the core-MVP close of G1–G5 against AC01–AC11, including the supporting Phase 2–3 tasks. The residual issues R1–R4 from [P4.6](../evidence/p4-6-core-mvp-acceptance.md#residual-issues-and-friction) are dispositioned below.
- **Method:** read every changed Rust module in the range (`agents`, `config`, `opencode`, `acp`, `progress`, `project_config`, `preview`, `single`, `runtime`), the decisions, task cards, evidence and contract documents. Re-ran the root suite, Clippy, format and every non-live script suite against installed OpenCode 2.2.5. Added ad hoc preview/rejection probes against the debug build.
- **Exclusions:** no live model inference was repeated. P4.4/P4.6 live records are relied on as dated evidence. No fixes, merge, release or new feature authorization is part of this report. Sequences, Ralph, more native CLIs, Pi and resource awareness remain later-phase work.

## Conclusion

**Changes required before Phase 4 acceptance: five open Low findings.** No Critical, High or Medium finding was identified, and no demonstrated defect in routing, permission enforcement, fallback or project integrity. The implementation, tests and live evidence support the core MVP claims as scoped: one target (`aarch64-apple-darwin`, macOS 27.0.1), OpenCode 2.2.5 exactly, default effort only.

Four findings are documentation drift: a decision register row and three contract/status documents still describe pre-Phase-4 or superseded state. One is a preview wording issue in code. Under [PHASE_REVIEW.md](../PHASE_REVIEW.md), every severity must be resolved before a pass. Dependent phases must continue to wait for the accepted P4.9 gate.

## Requirements and acceptance coverage

| Task / criterion | Assessment and evidence |
|---|---|
| P4.1 / AC08 | `src/agents.rs` implements the D036 schema strictly. Unknown or duplicate fields are rejected by direct typed decoding. Custom YAML tags are rejected after a bounded pre-parse. String visitors stop YAML null/number/bool coercion. Frontmatter is capped at 16 KiB under the shared input bound. Names are flat, lowercase, filename-bound and exclude OpenCode built-ins. The ceiling check rejects tools above the permission ceiling (for example, read-only with `execute`). `tests/agents.rs` covers malformed, ambiguous and traversal inputs. `agents_runtime.py` re-verified both 2.2.5 destinations. |
| P4.2 / AC08, AC04 | `Agent::select` reads only `PROJECT/agents/NAME.md`. It refuses a symlinked directory, a case-variant filename and a symlinked or non-regular file, and it never parses unrelated definitions. Model precedence per route is `--model`, then the agent's route model, then config; the fallback uses the agent's native model, else `native.model`. `project_config::Emission` is receipt-owned. It refuses edited, unrecorded, case-variant, legacy-directory and config-key collisions, re-checks snapshots before apply, and writes nothing for preview, `--no-sync` or the native route. `tests/agent_emission.rs` and `agent_emission_runtime.py` pass. |
| P4.3 / AC07, AC08 | `opencode::effective` intersects the invocation profile with the ceiling; deny always wins and no rule allows. The same rules are the global permissions, so built-in helpers cannot exceed the role. `validate_agents` requires every agent's rule tail to match, and the named entry to be a visible primary with exact model, description and system text. ACP enforcement adds two checks: a grant needs a listed kind, and a completed call of any unlisted or unknown kind is a violation. The session `mode` must equal the role. A non-default effort exits 2 before discovery, network or writes. The recovery guard compares agent name, effective rules and instructions. `agents_exec.py` and `agent_exec_runtime.py` pass. |
| P4.7 / AC06 | `progress.rs` keeps a separate ordered writer. `seq` is assigned under the queue lock, non-terminal records are best-effort with counted drops, and exactly one `result` is written last within a 2 s budget. An undelivered success becomes exit 1. Outcomes are an explicit mapping, not enum serialization. Unknown metrics are `null`. Machine mode is detected before parsing, so rejected invocations still end in a result (re-probed here). R03-REC1 is evaluated and declined in D039, with the evidence fields exposed. `machine.py` and `tests/cli.rs` pass. |
| P4.8 / AC11 | D040 fixes the 2.2.5 regression in which disabling project config also disabled `AGENTS.md`. The resolver names only the canonical project-root file. It must resolve to a regular file inside the canonicalized project (an outside symlink is refused, re-probed here). Slash-command prompts are refused before launch. Skills, MCP, plugins, commands and web tools are unloaded or denied. `capabilities_runtime.py` passes. |
| P4.4 / AC05, AC07, AC08, AC11 | [Live evidence](../evidence/p4-4-primary-reviewer-acceptance.md): coder and reviewer on both routes and through the fallback; prohibited operations, deny-invocation and effort refusals. The LiteLLM wire shows the reviewer offered exactly `glob, grep, read, skill`, and the role text plus `AGENTS.md` on every primary request. Native instruction delivery is behavioral only, which is documented. |
| P4.5 / AC09, AC10 | D041 declares one target. The published `v0.1.0-alpha.2` archive contains `examples/` (three configs, two agents) and third-party notices. Archive smoke covers upgrade, sample previews, preservation and rollback. Intel, other macOS releases, Linux and Windows are explicitly unsupported. |
| P4.6 / G1–G5, AC01–AC11 | [Acceptance record](../evidence/p4-6-core-mvp-acceptance.md): every row cites evidence; 23 of 25 repeated live runs met their assertions, and both failures are explained (R1, R3). Real maintenance on this repository was integrated. |
| IMPLEMENTATION Phase 4 exit | Named coding and constrained review tasks, denied prohibited writes/tools, visible refusal of unsupported restrictions, emission fixtures, repeated dual-route use and an artifact for the declared target are all present. The "decide here" items are recorded: schema/destinations (D036/D037), specialized invocation semantics (D038), compatibility reporting (D040 matrix) and the platform matrix (D041). |

The Phase 3 gate inputs were consumed as directed. R03-REC1 was evaluated and declined with a decision entry and fixtures (D039). R03-REC2 was satisfied by packaging current source as alpha.2 (D041).

## Integrated assessment

### Architecture and ownership

The single crate stays proportionate. The new `agents` module is a pure parser and selector with no runtime side effects. `opencode` owns every 2.2.5-specific mapping: runtime document, ceiling/effective rules, grantable kinds, effort support, prompt support and emitted Markdown. `project_config` extends the existing transaction rather than adding a second writer. `progress` owns both output modes. `single` keeps capability refusals ahead of any runtime, network or write. Dependency direction is unchanged: policy stays pure, and I/O stays in `runtime`, `acp`, `process` and `project_config`. The only new dependency is `serde_yaml_ng` 0.10.0 with `unsafe-libyaml`, both MIT; their notices are present in the published archive. No speculative adapter traits, multi-backend emitters or effort mappings were added.

### Routing, permissions and fallback

The model route and the runtime stay separate. A named role changes the default agent and the rules, never the provider policy. Agent `group:NAME` references resolve only on the active LiteLLM route, and an undefined group is rejected (re-probed here). Permission narrowing is enforced in three layers: OpenCode's rules (deny removes tools from the model), harness grant decisions (exact one-shot, listed kind) and completion checks (an unlisted kind is a violation, so it is uncertain after submission). Specialized capacity never maps to a backend subagent, which avoids the 2.2.5 silent `build` substitution; the ACP `mode` check is the backstop. The local-first fallback cannot widen a role, because the recovery guard compares effective rules, not only names.

Residual limits are documented rather than hidden: trusted shell access is host authority, with no OS sandbox; the `skill` tool stays offered while its loading is denied; native request contents are unobserved.

### Project integrity and state

Emission follows D025's lock, snapshot re-check, atomic replace and fsync rules, plus directory fsync on creation. A crash between the agent file and its receipt surfaces as an ownership conflict rather than a silent overwrite. Receipts never delete other owned entries. Cloud-only and the fallback path still write nothing. `--no-sync` emits nothing, and the runtime never loads the emitted file, so stale emission cannot affect enforcement.

### Tests and live evidence

The tests assert observed behavior: wire-offered tools, rule tails, grant outcomes, file bytes and record order. They do not assert internal enum choices. Mutation checks are recorded for the capability suite and the archive smoke. The live gate is honest about its two failures. R1 (an agent reported success without doing the work) is exactly the class of failure that AC01's "runtime owns the tool loop" cannot prevent, and the harness correctly reports the runtime's terminal state without fabricating verification.

### Operations and platform claims

OPERATIONS states one target, separate prerequisites, a setup check, upgrade from alpha.1 and rollback. Its diagnostics table covers the missing-key case (R4) and the zero-grant exit-4 case. Exit 0 guidance already tells users to verify tests independently (R1). No platform, effort or capability claim exceeds the cited evidence.

### Documentation and records

PROJECT.md, the task cards, D036–D041, CONFIGURATION, EXECUTION and OPERATIONS agree with the implementation. Residual drift remains in the decision register, SPECIFICATION, DESIGN and three status paragraphs (findings C04-01 to C04-04).

## Findings

Severities follow [PHASE_REVIEW.md](../PHASE_REVIEW.md). All findings are open at the time of writing.

| ID | Severity | Concrete issue / affected requirement | Proposed correction | Verification required |
|---|---|---|---|---|
| C04-01 | Low | [DECISIONS.md](../../DECISIONS.md) deferred register, row "Canonical agent schema, destination paths, constraints" (owner phase 4), still reads "Before mapping ships…", although D036–D038 resolve it and D040 covers inherited capabilities. The two sibling Phase 4 rows were updated. This is a traceability defect in the record that owns deferred choices. | Mark the row resolved by D036 (schema/destinations), D037 (selection/emission), D038 (invocation/enforcement/effort) and D040 (inherited capabilities). | Register shows no open Phase 4 row. |
| C04-02 | Low | [SPECIFICATION.md](../SPECIFICATION.md) "Canonical agents" paragraph (line 69) describes a superseded schema: "role (`primary`, `subagent`, or `all`), optional model alias". D036 instead uses `capacity: primary/specialized/both`, a `permissions` ceiling, a `tools` list, route-specific `models.local`/`models.native` and `effort`. It also still says "Validate the exact schema … in Phase 4" in the future tense. Line 55 similarly says machine output "arrive[s] in Phase 4". The specification owns goals, and its schema description now conflicts with D036/CONFIGURATION. | Describe the D036 fields at goal level, link CONFIGURATION for the grammar, and change Phase 4 statements to the past tense with links to D036/D039. | Wording matches D036 and the example agents. |
| C04-03 | Low | [DESIGN.md](../DESIGN.md) "Phase 2 implemented mapping" (line 92) is the concrete module map, and it omits the `agents` module and the Phase 4 responsibilities: named-role mapping and emitted Markdown in `opencode`, agent emission in `project_config`, and v1 machine records in `progress` ("bounded human diagnostics" only). The Phase 3 review fixed the same class of drift (C03-02). | Retitle or extend the section to cover implemented Phases 2–4, and add the responsibilities above and the `serde_yaml_ng` dependency. | Every `src/*.rs` module is named with its current owner. |
| C04-04 | Low | Stale status text. [TESTING.md](../TESTING.md) line 3 says "named agents, machine output and workflows remain gated", while the same file documents their suites. [docs/README.md](../README.md) line 5 says Phase 3 "acceptance is the P3.6 holistic review (PR #32)", although it passed and merged. [ARCHITECTURE.md](../ARCHITECTURE.md) line 152 says "Expanded supported platforms are declared in Phase 4 after tests", but D041 declares exactly one target. | Update all three to the post-P4.6 state; cite D041 for the single-target matrix. | grep finds no pending-tense Phase 3/4 status claims. |
| C04-05 | Low | Preview's `permissions:` line reports only the invocation scope. For `--agent reviewer --permissions trusted` it prints "trusted: read/write/shell with host privileges", although the effective rules are `["read", "search"]`. The narrowing appears only on the separate `agent:` line (reproduced against the debug build). The error is in the conservative direction (it overstates authority), but AC09 capability reporting should not contradict itself in one plan. | In `preview::render`, append the narrowing to the permissions line when a role narrows a trusted invocation (for example "narrowed by agent to read, search"), and assert it in `tests/cli.rs` or `preview.py`. Code fix goes in a linked `patch/` PR with `/grok review`. | Preview fixture asserts the narrowed wording; the unnamed trusted line is unchanged. |

## Residual issues from P4.6

| P4.6 item | Disposition |
|---|---|
| R1 — agent success is not verified success | **Accepted limit, not a Phase 4 defect.** The harness reports the runtime's terminal state as D024/D039 specify. OPERATIONS already requires independent verification on exit 0, and the JSONL result exposes `tool_events`/`grants` for consumer policy. P5.5 verification gates remain the correct remedy; schedule it early in Phase 5, as P4.6 proposes. See R04-REC2. |
| R2 — open-ended work can exhaust the bound with uninformative progress | **Recommendation (R04-REC1), not a defect.** The bound, cancellation and cleanup behaved correctly. Progress shows counts only by design. |
| R3 — shared-alias load | **Operational note.** One cancellation coincided with a concurrent session on the same alias. Per-row timing now makes it diagnosable. Live acceptance runs should not overlap; this belongs in TESTING's live-gate notes if repeated. |
| R4 — environment-dependent prerequisites | **Already addressed.** The OPERATIONS diagnostic row for the missing-key error says to export the variable "in the shell that runs `ah`". No change required. |

## Recommendations (not findings)

- **R04-REC1 — tool kind in progress.** Add the ACP tool *kind* (`read`/`search`/`edit`/`execute`/`other`), not title or arguments, to human tool-activity lines, and add per-kind counters to `attempt.activity`/`result` as a v1-compatible optional field. Kinds are already harness-validated and carry no paths or arguments, so redaction holds. Titles can contain paths and commands and should stay excluded. This is a candidate for the backlog, not authorized scope.
- **R04-REC2 — documented consumer heuristic.** Until P5.5, OPERATIONS' CI section could note that `outcome: succeeded` with `tool_events: 0` on an edit task deserves scrutiny. This is guidance only; no harness heuristic should reinterpret backend success.

Observations reviewed and judged not to be defects:

- The slash-command refusal is broader than the advertised command list (for example, "/tmp is full" is refused). D040 records this as deliberate, and preview reports it.
- The `--output jsonl` pre-scan uses adjacent raw arguments. Odd placements, such as a `--prompt-file --output jsonl` value, still end in a well-formed `rejected` result.
- `AGENTS.md` content is read by the runtime, not snapshotted. D040 documents this, and the path handed over is the canonical resolved target.

## Verification performed

Environment: Apple Silicon macOS 27.0.1, Rust/Cargo 1.88.0, OpenCode 2.2.5 (Homebrew), source at `b38cc0f` (branch `review/04-core-mvp`, no source changes).

| Check | Result |
|---|---|
| `cargo fmt --check` | pass |
| `cargo clippy --locked --all-targets -- -D warnings` | pass |
| `cargo test --locked` | 82 passed, 0 failed |
| `single.py`, `preview.py`, `worktree.py` | pass |
| `single_runtime.py` (default, `--cancel`, `--group=coder`, `--refuse`) on installed 2.2.5 | pass |
| `native.py` (40 cases), `native_runtime.py` | pass |
| `agents_runtime.py` (6 probes), `agent_emission_runtime.py` (8 probes) | pass |
| `local_first.py` | pass |
| `modes.py` (165 matrix cases, 14 invalid configurations) | pass |
| `agents_exec.py`, `machine.py` | pass |
| `agent_exec_runtime.py` (4 runs), `capabilities_runtime.py` (8 checks) on installed 2.2.5 | pass |
| Leftover state after all suites | no `ah-runtime-*` directory and no OpenCode `acp`/`serve` process |
| Ad hoc probes (debug build, preview/rejection only) | Reviewer preview shows effective `["read","search"]` and planned emission; an undefined agent `group:` is rejected; an outside-symlinked `AGENTS.md` is rejected; slash prompts are refused in preview and with exit 2 in JSONL; a rejected `--output jsonl` invocation ends in one `result` record with `outcome: rejected` |

Live inference was not repeated. P4.4 and P4.6 (six `roles_live.py` passes from the published `v0.1.0-alpha.2`) remain the live record for the reviewed head: changes after `1f7463d` are limited to `roles_live.py` timing and Markdown.

## Gate outcome

**Changes required** for the reviewed scope `2a2a424..b38cc0f`. To pass:

1. Correct C04-01 to C04-04 in the review PR (documentation only).
2. Fix C04-05 in a linked `patch/` PR with a fixture, request `/grok review`, and merge it.
3. Re-check the combined state, and record the resolved findings in the canonical `docs/reviews/phase-04.md` with links to this report.
4. Then merge the review PR, and check P4.9 in PROJECT.md.

Until then, Phase 5, Phase 7 and Phase 8 work must not consume the Phase 4 baseline.
