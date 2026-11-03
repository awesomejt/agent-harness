# Phase 3 holistic review

## Review scope

- Task: P3.6; reviewer: Claude Code primary agent (Opus 5.5); date: 2026-11-03 (America/Denver).
- Accepted entry baseline: `4c33b22` (Phase 2 review, [PR #24](https://github.com/awesomejt/agent-harness/pull/24)). Reviewed material head: `dd4397a` (PR #31 merged); range `4c33b22..dd4397a`, 41 changed files (+3267/−630). Phase 2 input, transaction, supervision, preview, preservation and release behavior remain integration context. Report/status-only commits need not identify their own SHA.
- Included PRs: [#25](https://github.com/awesomejt/agent-harness/pull/25) P3.1 recovery policy; [#26](https://github.com/awesomejt/agent-harness/pull/26) P3.2 native isolation; [#27](https://github.com/awesomejt/agent-harness/pull/27) P3.3 part 1 model groups; [#28](https://github.com/awesomejt/agent-harness/pull/28) P3.3 part 2 local-first fallback; [#29](https://github.com/awesomejt/agent-harness/pull/29) P3.4 mode matrix; [#30](https://github.com/awesomejt/agent-harness/pull/30) P3.7 OpenCode 2.2.5 baseline; [#31](https://github.com/awesomejt/agent-harness/pull/31) P3.5 dual-route use. Each received an automatic Grok review; all reported findings were corrected and verified on their branches, as recorded in PROJECT.md. This review assesses their accumulated behavior.
- Mandatory scope: P3.1–P3.5, P3.7 and P3.6; G3 completion and the Phase 3 part of G4; D031–D035; the core-MVP columns of AC02, AC03 and AC04, plus the native-route part of AC05/AC07. Excluded: named agents, machine output, additional platforms and artifacts, native CLIs other than OpenCode, sequences/Ralph and optional resource features. No feature candidate is promoted.

## Requirements and acceptance coverage

| Task / criterion | Integrated evidence and conclusion |
|---|---|
| P3.1 / AC03 | [Recovery evidence](../evidence/p3-1-recovery-policy.md), D031, `src/recovery.rs` and `tests/recovery.rs`. Only pre-submission unavailable/rate-limit/transport failures may qualify, under every guard; cancellation, deadline, unknown and post-submission outcomes stop. No same-route retry. |
| P3.2 / AC02, AC04 | [Native evidence](../evidence/p3-2-native-isolation.md), D032. cloud-only uses only the built-in `opencode` API-key provider, bypasses managed planning, and its trap sees zero LiteLLM discovery or model requests. |
| P3.3 / AC03, AC04 | [Group evidence](../evidence/p3-3-model-groups.md), D033: explicit `group:NAME` references resolve to one proxy group, never reach the runtime as harness names, and reject on the native route. [Fallback evidence](../evidence/p3-3-local-first-fallback.md), D034: one linked `attempt=2` native run only after a byte-free TCP reachability failure before any runtime, state or project write. |
| P3.4 / AC02, AC03 | [Matrix evidence](../evidence/p3-4-mode-matrix.md). One combined config runs every scenario in all three modes against reachable and closed endpoints and checks effective behavior: launched route and count, exact environment, endpoint contact, inherited-choice rejection, attempt lines, uncertainty without replay and managed writes. |
| P3.7 / AC02, AC07 | [Baseline evidence](../evidence/p3-7-opencode-2-baseline.md), D035. User-directed move to an exact OpenCode 2.2.5 pin on both routes: `--standalone` inspection, sources check, agent rule tails, `opencode/`-only native catalog and exact `rawInput` grant binding. A validator mutation is caught. |
| P3.5 / AC01–AC03 live | [Use evidence](../evidence/p3-5-dual-route-use.md). Live local-only, cloud-only, reachable local-first and closed-port fallback each edited a disposable project and passed an independent test (exit 0). Managed project files were byte-identical across native runs, user OpenCode directories showed 0 changes, and no private state or `serve` process remained. Rejected-key and unknown-alias limits stop without fallback. |
| IMPLEMENTATION Phase 3 exit evidence | Allowed/forbidden traffic for all modes, successful local execution, eligible fallback, no fallback on local-only, no cloud-only discovery and native selection unaffected by managed settings are covered by P3.2/P3.4 fixtures and P3.5 live runs. Deterministic pre-execution fallback is live-demonstrated. Ambiguous failure after a possible tool action is covered by the `deny-completed`, `unexpected-write`, `eof` and `rpc-error` scenarios (exit 4, no replay or fallback in every mode). Confirmed cancellation after an actual installed-runtime edit is also covered (`single_runtime.py --cancel`). Both routes were used for real. |
| G3 / G4 | G3 complete: all three modes enforce their routes, and route, model, attempt and fallback reason appear in preview and progress. G4 extended: model groups are harness-owned, the proxy stays operator-owned, and native isolation leaves managed config untouched. |
| P3.6 / phase exit | This report, its documentation corrections and the merged review PR supply the gate, beyond individual PR approval. |

F02 is complete for this phase. F04's group part and F11's route/fallback preview lines are assessed above. F01, F03, F12, F16, F20 and F24 keep their Phase 2 evidence, now exercised on both routes. G5–G9 and remaining feature families are outside this acceptance.

## Integrated assessment

**Rust ownership and integration.** The package stays a single crate with a thin executable. Phase 3 adds three focused modules: `recovery` (a pure decision), `probe` (the bounded reachability worker) and `opencode` (the pinned runtime document and pure validators). Config resolution builds an immutable `Resolved` request with at most one non-nested `fallback`; `single::coordinate` is the only place that links attempts. OpenCode owns the coding loop on both routes, and LiteLLM owns routing inside its route. No common adapter framework, provider pool, new dependency or public flag was added; `--mode`, `--model` and `--no-sync` remain the CLI surface, as AGENTS.md requires before Phase 4.

**Routing and permissions.** Local-only and cloud-only never contact the other route. Local-first sends no bytes or credentials to establish eligibility, and everything after the reachability check is final. Both route keys and both static targets are validated before input acquisition. The fallback receives the identical project, permissions, timeout, deadline and prompt, plus a fresh private runtime and grants and a full native preflight. The probe worker and private-home cleanup are plain OS threads, so an unbounded resolver call or recursive deletion cannot block runtime shutdown. Under 2.2.5, deny removes tools from the model, trusted binds each grant to exact `rawInput`, and `other`-kind tools are always refused. The documented limits stand: reachability is not model availability, DNS failure counts as transport (so a mistyped host falls back), and trusted grants host privileges without an OS sandbox.

**Project integrity and lifetime.** cloud-only bypasses the D025 transaction entirely. A local-first fallback writes nothing to the project, because the plan is prepared but never applied before the check. The shared signal watcher covers the gap between attempts, and cancellation or deadline wins over a concurrent classification. D030 cleanup runs after every attempt and its failure overrides the outcome with exit 4. Phase 2 preservation fixtures pass unchanged.

**Tests and real use.** P3.4's matrix asserts effective behavior rather than enum values, and its two mutation checks were caught. P3.7 added a validator mutation check. The P3.5 live gate uses one representative edit/test task per route on free or unpriced models; paid native models, rate limiting and proxy-group outages were not exercised, and that limit is recorded. The reported `session_cost=0 USD` is OpenCode's own figure, not a bill.

**Platform and operations.** Verified here: Apple Silicon macOS 27.0.1, Rust/Cargo 1.88.0 and OpenCode 2.2.5 (Homebrew). The published `v0.1.0-alpha.1` remains unchanged. It predates Phase 3 and D030, supports local-only only and requires OpenCode 1.18.30; native and local-first routes are source-only until a new artifact (R03-REC2). Managed project `opencode.json` keeps legacy keys that 2.x translates; migration stays deferred by D035.

## Findings and resolution

| Finding | Severity | Concrete issue | Correction / verification | Disposition |
|---|---|---|---|---|
| R03-01 | Low | README Status still names P3.1 as next and describes only the LiteLLM route. The Install line names OpenCode 1.18.30 without saying it applies only to the published binary, while source requires 2.2.5. | This PR rewrites Status for the three implemented modes, P3.5 evidence and the alpha.1 limits, and qualifies the Install prerequisite by artifact versus source. Checked against `opencode::VERSION`, D032–D035 and OPERATIONS. | Resolved |
| R03-02 | Low | OPERATIONS stale claims: its status line calls native guidance prospective; the preview description says it reports "expected OpenCode 1.18.30" (source prints 2.2.5); and the native section says live native use "remains P3.5" after P3.5 merged. | This PR updates the status line, the preview description (2.2.5 for source, 1.18.30 for alpha.1, plus route/fallback lines) and links the P3.5 evidence. Checked against `preview::render` and a fresh preview run. | Resolved |
| R03-03 | Medium | The OPERATIONS diagnostic table tells a rejected native login to "use the official CLI login flow". D032 consumes no login store, so following it cannot fix the implemented API-key route. The table also has no guidance for the commonest P3.5 setup failures (exit 4 with 0 grants after a bad key or missing alias) or for an unexpected local-first fallback. | This PR replaces the row with `native.api_key_env`/model-access guidance and adds rows for post-submission provider failure and unexpected `attempt=2` fallback (including the D034 mistyped-host case). Each row was checked against D032/D034, `single.rs` progress text and the P3.5 observations. | Resolved |
| R03-04 | Low | TESTING still says "P3.5 owns live native use" and its live-evidence list omits P3.5. EXECUTION still calls the policy's consumer "the future coordinator". | This PR updates both sentences and adds the P3.5 link. Historical evidence (for example, P3.4's original `deny-progress` scenario name, renamed in P3.7) is left unchanged. | Resolved |
| R03-05 | Low | PROJECT.md current-state still lists P3.5 / PR #31 as the active task after its merge, and the backlog count predates this review. | This PR updates the active-task line, the backlog count, the P3.6 row and the journal for the post-review state. | Resolved |

No Critical or High defect was found and no code change is required, so no patch PR is needed. Every severity remains a pass prerequisite.

### Recommendations (not defects)

- **R03-REC1 — exit classification for zero-activity provider failures.** P3.5 found that a rejected key or missing alias after prompt submission exits 4 (uncertain) with 0 grants and no completed tool call, although the 2.2.5 profile gates or removes every tool. This matches D031 and EXECUTION ("a missing trustworthy terminal response remains uncertain"), so it is not a defect. Reporting exit 1 in that case would reduce noise but changes a public exit contract. Recorded as a P4.7 gate input; adopt only with a decision entry and fixtures, and never with fallback.
- **R03-REC2 — refresh the published artifact.** Binary users cannot use native or local-first routes, the 2.2.5 pin or D030 cleanup until a new artifact is packaged. Recorded as a P4.5 gate input; a separate earlier pre-release would need its own task and user approval.

## Verification and integrated recheck

Run on `dd4397a` plus this PR's documentation-only changes, macOS 27.0.1 arm64, Rust 1.88.0, OpenCode 2.2.5:

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo test --locked` (57 tests) and `cargo build --release --locked` pass. `./target/release/ah --version` reports `ah 0.1.0-alpha.1`.
- `scripts/tests/single.py` (69 local cases), `preview.py`, `worktree.py`, `native.py` (40 native cases, zero LiteLLM requests), `local_first.py` and `modes.py` (165 matrix cases: 21 scenarios per endpoint, `--mode` overrides, `--no-sync`, 14 invalid configs) pass.
- Installed-runtime `single_runtime.py` (edit/test), `--cancel` (confirmed cancellation after an actual edit), `--group=coder` and `--refuse` (`other` kind refused, no effect) pass, as does `native_runtime.py` (deny/trusted and local-first fallback setup, 0 native prompts forwarded).
- The standalone lifecycle experiment's locked build/format/Clippy and fixture driver pass.
- Afterwards, no `ah-runtime-*` directory remains under the temporary directory and no `opencode serve` process is running. `git diff --check` passes.

These commands contact no live provider. Live dual-route use is the merged P3.5 record from source `ea9a5f4`; the only later source changes are P3.5's documentation-only PR, so that record is current for the reviewed head. No uncertain project is replayed. The corrected documents were rechecked against each other and against the source: the route/fallback wording in README, OPERATIONS, CONFIGURATION, EXECUTION and D034 agrees, and the P4.5/P4.7 cards cite this report.

## Gate outcome

Pass proposed for this exact Phase 3 scope, effective only on this report PR's merge. Every mandatory task and Phase 3 acceptance column has evidence, all five findings are resolved and verified, no code remediation PR is required, and no finding remains open. On acceptance P3.6 passes and P4.1 becomes ready. Named agents, machine output, additional platforms and artifacts remain gated; no core-MVP completion or updated published artifact is implied.
