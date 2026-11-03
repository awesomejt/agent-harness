# Phase 2 holistic review

## Review scope

- Task: P2.9; reviewer: Codex primary agent with an independent runtime/permission/lifecycle reviewer; date: 2026-11-02 (America/Denver).
- Accepted entry baseline: `e791a7d81ba44e6a8d20dac6f925c9d0a3326c4a` (Phase 1 review, PR #13). Initial reviewed head: `3be52777cdde6f8d7ad5006d6901d94691fad975` (PR #22 merged); range `e791a7d..3be5277`, 46 changed files. Earlier permission policy and lifecycle experiment remain integration context. Remediation behavior head: `4c7e851434a71dbf5e09f643b11da067d01a385a`; source-comment clarification head: `7edf6c0`, merged at `45deed3a190df8a09adc1e253a07aae2c21c411c` in [PR #23](https://github.com/awesomejt/agent-harness/pull/23); report/status-only commits need not identify their own SHA.
- Included PRs: [#14](https://github.com/awesomejt/agent-harness/pull/14) Git conventions; [#15](https://github.com/awesomejt/agent-harness/pull/15) P2.1 inputs; [#16](https://github.com/awesomejt/agent-harness/pull/16) P2.3 transactions; [#17](https://github.com/awesomejt/agent-harness/pull/17) P2.2 coding adapter; [#18](https://github.com/awesomejt/agent-harness/pull/18) P2.4 supervision; [#19](https://github.com/awesomejt/agent-harness/pull/19) P2.7 preview; [#20](https://github.com/awesomejt/agent-harness/pull/20) P2.8 preservation; [#21](https://github.com/awesomejt/agent-harness/pull/21) P2.5 release; [#22](https://github.com/awesomejt/agent-harness/pull/22) P2.6 installed real use. Earlier individual review findings/fixes remain in their dated evidence; this review assesses their accumulated behavior.
- Mandatory scope: P2.1–P2.8, P2.9, G1/G2 and the first-slice portions of G3/G4, D024–D030, and all first-slice AC01–AC11 columns. Excluded: native/cloud/local-first routes and fallback, model groups, named agents, machine output, additional platforms, sequences/Ralph and optional resource features. No feature candidate is promoted.

## Requirements and acceptance coverage

| Task / criterion | Integrated evidence and conclusion |
|---|---|
| P2.1 / AC04–AC07 | [Input evidence](../evidence/p2-1-config-contract.md), strict config/CLI fixtures and D024 establish project-only JSON, source precedence, explicit input acquisition, environment key references, invocation-only host authorization and exits 0–4. Invalid/unsupported inputs reject before launch. |
| P2.3 / AC04 | [Transaction evidence](../evidence/p2-3-managed-config.md), project-config tests and D025 cover managed field ownership, byte-preserved unrelated values, inactive providers, manual/stale/interrupted conflicts, regular-file checks, exact no-sync routes and global preservation. Advisory locks cannot stop racing noncooperating editors. |
| P2.2 / AC01, AC02, AC05, AC07 | [Coding evidence](../evidence/p2-2-local-only-run.md), public CLI fixtures and actual installed OpenCode/stub read/edit/shell tests establish an inner coding loop owned by OpenCode, matching primary/helper aliases, effective preflight and exact callback-bound grants. Live coding success and an earlier uncertain attempt are both retained. |
| P2.4 / AC02, AC06, AC07 | [Supervision evidence](../evidence/p2-4-progress-supervision.md) and adversarial public CLI cases cover streamed activity, source-attributed/unknown usage, terminal precedence, output/backpressure limits, cooperative/forced cancellation and original-group cleanup. Uncertain effects never trigger replay/fallback. |
| P2.7 / AC09 | [Preview evidence](../evidence/p2-7-diagnostics-preview.md) and current trap fixtures confirm shared resolution/planning, local prerequisite guidance and no child/network/write. Exit 0 means a valid plan; runtime version/service/alias readiness remains unverified. |
| P2.8 / AC05 | [Preservation evidence](../evidence/p2-8-dirty-project-preservation.md) and real-Git fixtures cover baseline reporting, dirty/untracked bytes/mtime and Git metadata preservation across success/rejection/cancellation/uncertainty, including filter/fsmonitor traps. Authorized runtime edits remain distinct from harness setup. |
| P2.5 / AC10 | [Release evidence](../evidence/p2-5-installable-binary.md), D029, published checksums/provenance and fresh archive install smoke establish a prebuilt Apple Silicon macOS executable with notices and separate runtime/service prerequisites. Browser/Gatekeeper and other platforms remain unverified. |
| P2.6 / AC01–AC11 | [First-use evidence](../evidence/p2-6-first-use.md) records the published-binary maintenance edit/test, independent verification, direct OpenCode comparison, unavailable endpoint, post-edit cancellation, interventions and friction. It explicitly distinguishes manual trials and repeatable commands. |
| AC03, AC08 and later AC11 capabilities | Fallback and named agents are N/A in this slice. Phase 1 instruction-loading plus current installed-runtime instruction tests cover the initial AC11 boundary; MCP/skills/context expansion remains P4.8. No core-MVP acceptance is inferred. |
| P2.9 / phase exit | This integrated report, verified remediation and merged review PR supply the progression gate, beyond individual PR approval. |

F01/F12/F20 are delivered for the first slice; F02/F03/F04/F11/F13/F14/F16/F24/F25 have their Phase 2 portions assessed above. F18/F19 retain the narrow backend instruction/coding-loop boundary, with unmanaged customizations disabled pending verified later mappings. G1/G2 are evidenced on the declared initial target; G3/G4 retain Phase 3 obligations. G5–G9 and remaining feature families are outside this acceptance.

## Integrated assessment

**Rust ownership and integration.** The implementation remains one Cargo package, a thin executable and focused modules. Input/policy/project transformations are separate from runtime/process I/O; SDK records stay in the adapter. `single` coordinates one attempt, OpenCode owns coding turns and LiteLLM owns its internal model route. The concrete module mapping is now documented in DESIGN; no speculative common adapter framework or second agent loop is introduced. Exact direct dependency pins/MSRV remain Rust 1.88.0, SDK 3.6.0/schema 1.13.0, Tokio 1.48.0 and tokio-util 0.7.16. Packaging refreshes the actual target graph and notices rather than relying on Phase 1's historical inventory.

**Routing and permissions.** Only local-only is accepted. Private HOME/XDG, a cleared child environment, reserved key variable, disabled project config/plugins/MCP/subagents/network tools and exact effective primary/helper/permission checks prevent inherited runtime settings from widening the route. No-sync still performs preflight. Native trap executables remain untouched. Trusted explicitly authorizes host file/shell operations, including outside-project/network effects through shell; it provides no containment. Default deny, unknown tool rejection, full event/callback argument binding, allow-once selection and denial after cancellation are covered. The tests observe aliases and tool sets sent to the configured endpoint; they do not audit the remote proxy's internal configuration or infer physical locality/price. No new subscription-provider path is introduced.

**Project integrity and lifetime.** Project config and receipt use conflict-aware per-file atomic updates; interrupted pairs require manual reconciliation. Harness setup never stashes/resets/cleans/commits/restores user work. Git observation disables hooks/filters as documented, remains advisory and cannot prevent concurrent config edits. Successful runtime turns, task verification, confirmed cancellation and process cleanup are separate facts. ACK/text/EOF cannot establish completion. Original-group TERM/KILL/reap verification is bounded; detached descendants and downstream inference remain outside that guarantee. D030 adds private-directory removal/absence verification with a two-second worker wait; failure is explicit uncertainty. Constructor cleanup remains best effort, and abrupt termination/detached writers are outside the guarantee. Final stdout may already be delivered before removal failure changes the exit. Immutable alpha.1 artifacts retain their earlier best-effort removal; the corrected source must ship in a future version. This localized retention correction does not invalidate the published coding/routing/installation evidence.

**Tests and real use.** Pure tests alone do not close the milestone. Current installed-runtime/stub tests perform actual edits and independent arithmetic verification, plus cancellation after those effects. Merged live evidence records both successful and uncertain real-provider runs. P2.6's installed maintenance trial succeeded with three exact grants/six matching-alias requests; direct OpenCode completed the same change independently with seven matching-alias requests. The primary removed one unrelated bare return from the candidate before integration. Overlapping service trials are not a performance benchmark. The unavailable endpoint remained active until its deadline and then returned confirmed cancellation; this observation does not establish an immediate network-specific failure or automatic fallback eligibility. Those limits feed P3.1.

**Platform and operations.** Verified here: Apple Silicon macOS 27.0.1 (26A434), Rust/Cargo 1.88.0, Python 3.14.7 and OpenCode 1.18.30. Python/Rust are validation/maintainer tools, not prebuilt-binary requirements. Remote LiteLLM version is unreported. The release build setting 14.0 is not older-macOS compatibility evidence. Release provenance, system-only linkage, unstripped build workaround, notices and ad hoc signature limitations remain explicit. No browser quarantine/notarization, Linux/Windows/Intel support or universal secret scrubber is claimed. New source fixes do not change already-published versioned assets.

## Findings and resolution

| Finding | Severity | Concrete issue | Correction / verification | Disposition |
|---|---|---|---|---|
| R02-01 | Medium | The standalone experiment lockfile still names root version 0.1.0 after P2.5 changed it to 0.1.0-alpha.1; the documented locked build fails. | [PR #23](https://github.com/awesomejt/agent-harness/pull/23) updates only the path-package version, with no registry dependency changes. Locked build/format/Clippy, seventeen child cases and all five installed-runtime scenarios pass. | Resolved |
| R02-02 | Low | TESTING still calls production coding/sync/release planned and omits production suites; DESIGN retains obsolete scaffold-only claims. Current tracker also treats merged PR #22 as pending. | This report PR updates implemented boundaries, runnable production/release checks, concrete Rust module mapping, deployment wording and post-review status. Historical evidence/reviews remain unchanged. | Resolved |
| R02-03 | Medium | Private runtime HOME deletion occurs only in Drop and ignores errors, despite documentation promising removal. A successful process outcome can hide retained private state. | PR #23 / D030 makes deletion explicit with verified absence and a two-second worker wait, returning 4 on failure. Normal/preflight removal and chmod-induced retained-state fixtures pass; the failure fixture restores permissions/removes its residue in finally. Existing alpha.1 assets are documented as predating this source fix. | Resolved |
| R02-04 | Low | SIGTERM uses a separate Unix listener, while documented signal guarantees have only direct SIGINT/deadline fixture evidence. | PR #23 adds an active SIGTERM case requiring ACP cancellation, a cancelled terminal result and absent/terminated descendants; the full corrected suite passes. | Resolved |
| R02-05 | Low | F10's Pi parity trace still names P6.4 rather than the accepted Phase 6 review P6.5 required by its actual task card. | FEATURE_REVIEW now names accepted P6.5 review; task/dependency consistency checked against P8.4 and PROJECT_PLAN. | Resolved |
| R02-06 | Medium (Grok Concern) | Grok interpreted cleanup as requiring an attempted deletion even if the worker cannot start, and suggested synchronous recursive removal as fallback. That fallback would lose the supervisor's finite wait. | `7edf6c0`, D030 and the contracts explicitly state that spawn failure leaves removal unattempted, returns 4 and warns about retained state. Primary and independent review confirm synchronous fallback is unbounded; no successful-cleanup claim is made. | Resolved |

No Critical/High defect or new feature recommendation was found. Every severity remains a pass prerequisite. Incoming remediation PR review findings, if any, are recorded at closeout with their original labels and impact mapping.

## Verification and integrated recheck

Initial root formatting/locked Clippy, all 38 Rust tests and locked release build pass. The initial production CLI, preview, dirty-project and installed-runtime edit/test/cancellation suites pass. Fresh downloaded `v0.1.0-alpha.1` archive checksum and installation smoke pass: version/help/preview, no toolchains/runtime on PATH, signature/notices and invalid-input/redaction checks. Archive SHA-256 matches `c11b6f84ff7c8b775906c2a922913a1a30c6b1d12d54484f80680588303f3e1a` and published provenance in P2.6.

Corrected source `4c7e851` passes formatting, locked Clippy, all 38 Rust tests, the full 57-case public CLI suite plus no-sync repetition, preview, real-Git preservation and installed-runtime edit/test plus post-edit cancellation. Both installed-runtime cases observe six exact grants, 16 tool events, six matching-alias requests and independently passing arithmetic; terminal/exit are end_turn/0 and cancelled/3 respectively. An initial whole-tree preservation check caught a test-instrumentation marker added by the fake runtime; gating that marker to the explicit CLI fixture opt-in restores whole-tree preservation, and the full suite passes. This was a fixture correction within R02-03 remediation, not a product preservation defect.

Locked standalone experiment build/format/Clippy and all seventeen adversarial children/five installed-runtime scenarios pass after the one-line lock repair. A final locked check recompiles the corrected root dependency successfully. No registry version is changed. Repeatable commands (root with `~/.cargo/bin` on PATH):

```sh
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --release --locked
./target/release/ah --version
python3 scripts/tests/single.py
python3 scripts/tests/preview.py
python3 scripts/tests/worktree.py
python3 scripts/tests/single_runtime.py
python3 scripts/tests/single_runtime.py --cancel
cargo build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
python3 scripts/experiments/acp_lifecycle.py --runtime --opencode /opt/homebrew/bin/opencode
gh release download v0.1.0-alpha.1 --dir /new/empty/assets --pattern '*.tar.gz' --pattern SHA256SUMS
sh scripts/release/smoke.sh /new/empty/assets 0.1.0-alpha.1
git diff --check
```

The asset directory is explicitly created/selected for validation; the download/install checks do not replace published assets. Final local Markdown file-target and task-card consistency checks pass; all 60 unique cards match tracker IDs and the post-acceptance backlog is 43 tasks. `git diff --check` passes. Independent read-only review confirms the report/contracts match the corrected source and immutable release limitations. The review does not repeat the live maintenance comparison automatically: merged P2.6 evidence is current for the pinned runtime/route, and no uncertain project is replayed.

## PR closeout

[PR #23](https://github.com/awesomejt/agent-harness/pull/23) is merged at `45deed3`; its remote/local task branches are deleted. Two Grok reviews completed. The [initial review](https://github.com/awesomejt/agent-harness/pull/23#pullrequestreview-5745720961) reported 0 Blockers, 1 Concern and 0 Nits; R02-06 maps the concern to Medium and records the verified bounded-failure contract clarification. The [follow-up review](https://github.com/awesomejt/agent-harness/pull/23#pullrequestreview-5745742462) explicitly accepts that clarification and reports 0 Blockers, 0 Concerns and 0 Nits. Only a source comment changed after behavioral verification; final formatting/whitespace checks pass. No further review is needed.

[Report PR #24](https://github.com/awesomejt/agent-harness/pull/24) follows the holistic gate and bypasses normal Grok PR review, as required by the current Git workflow. Report/status/contract corrections are kept here; all code remediation went through the linked patch PR. No accepted historical report is overwritten.

## Gate outcome

Pass proposed for this exact Phase 2 first-slice scope, effective only on [report PR #24](https://github.com/awesomejt/agent-harness/pull/24) merge. Every mandatory task and first-slice acceptance column has evidence, all six findings are resolved/verified, the required remediation PR is merged with clean review, and no unresolved finding remains. On acceptance P2.9 passes and P3.1 becomes ready. Later routes/agents/workflows and untested platforms remain gated; no core-MVP completion or updated published artifact is implied.
