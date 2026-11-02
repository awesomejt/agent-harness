# Phase 1 holistic review

## Review scope

- Task: P1.7; reviewer: Codex primary agent; date: 2026-11-02 (America/Denver).
- Accepted entry baseline: `e1061bb` (Phase 0 review, PR #5). Integrated Phase 1 baseline: `fa4b411f44e46ef3a6959b374e2a670ebfa77237` (PR #12 merged). Reviewed material head: `6595443367434801d92e3a1b161e7f38629a7668`; range `e1061bb..6595443`. Subsequent report/tracker/README status commits record this reviewed material and PR closeout.
- Included phase PRs: [#6](https://github.com/awesomejt/agent-harness/pull/6) scaffold, [#7](https://github.com/awesomejt/agent-harness/pull/7) permissions, [#8](https://github.com/awesomejt/agent-harness/pull/8) partial transport, [#9](https://github.com/awesomejt/agent-harness/pull/9) live transport, [#10](https://github.com/awesomejt/agent-harness/pull/10) dependency evaluation, [#11](https://github.com/awesomejt/agent-harness/pull/11) lifecycle, [#12](https://github.com/awesomejt/agent-harness/pull/12) acceptance preparation. Their evidence records preserve prior Grok findings and verified remediation; this review reassesses the combined result.
- Mandatory tasks: P1.1–P1.6 and this independent whole-phase assessment. Review covers all 29 changed files in the phase baseline: root scaffold/policy/tests/toolchain, isolated Rust/Python probes/lockfile, decisions, contracts and evidence. Earlier specification, architecture, configuration, testing, operations and task/dependency contracts provide the integration context. No optional feature is selected.
- Exclusions: production coding runs, arbitrary-project sync, native routing/fallback, named agents, workflows, release artifacts and additional platforms. These remain explicitly gated future tasks, not missing Phase 1 deliverables.

## Requirements and evidence coverage

| Task / requirement | Integrated evidence and conclusion |
|---|---|
| P1.1 / D019, D023 | [Scaffold evidence](../evidence/p1-1-rust-scaffold.md), Cargo files and CLI tests establish package/binary/edition/target boundaries. D023 raises the verified floor to Rust 1.88.0; the informational binary still has no external dependencies. |
| P1.6 / D020 | [Permission evidence](../evidence/p1-6-permission-policy.md), six policy tests and actual option-kind mapping establish default denial, exact synthetic one-use grants, malformed-request refusal and headless behavior. Live grants remain unverified. |
| P1.2 / G2, G3 foundations | [Historical partial probe](../evidence/p1-2-opencode-transport.md) and [live continuation](../evidence/p1-2-live-acp.md) distinguish the unavailable old host from successful supplied-host discovery/session/stream/terminal evidence. No raw completion substitutes for a coding runtime. |
| P1.4 / D012, D021 | [Pinned evaluation](../evidence/p1-4-dependency-evaluation.md) compares a narrow leaf layer with SDK/direct process ownership. Inherited environment gaps justify rejecting convenience launchers; no general framework is adopted. |
| P1.3 / AC07 foundation, F24 | [Lifecycle evidence](../evidence/p1-3-lifecycle.md) and current reruns cover actual model payloads, project instructions, denied reads, cancellation, unavailable service, protocol faults and child/group cleanup. Observations distinguish deterministic stub evidence from live backend variability. |
| P1.5 / D023 | [Acceptance preparation](../evidence/p1-5-integration-acceptance.md) selects ACP protocol 1 and the tested SDK/Tokio stack, confirms responsibility boundaries and explicitly reassesses shutdown limits. [Inventory](../evidence/p1-5-dependencies.md) covers the resolved licenses/target graph and release follow-ups. |
| P1.7 / D018 | This report, verified remediation and the review PR form the phase progression gate. Individual earlier PR reviews alone do not pass it. |

G2/G3 receive feasibility evidence only; neither is complete. F01/F02/F04/F13/F16/F18/F24 receive narrow transport/routing/instruction/lifecycle groundwork, not complete product features. F25 receives a development toolchain target only. AC07 has Phase 1 permission/lifecycle evidence; its production obligations remain P2.4/P4.3/P4.4. AC01–AC06 and AC08–AC11 are not closed: no real edit/test binary, full routing, managed config, production input/output, named agents, diagnostics, distribution or repeated-use milestone exists yet. No G1–G9 or MVP checkbox is inferred complete from a text marker.

## Integrated assessment

**Scope and Rust ownership.** The root is one small Cargo package with a thin executable and SDK-independent policy. The separate SDK experiment shares that policy through a local path dependency, without contaminating the root graph or introducing a second agent loop. D019–D023 and DESIGN/FRAMEWORKS agree on MSRV, selected versions and responsibility boundaries; concrete production interfaces are deliberately deferred. Comparing native structured output was conditional and is unnecessary after ACP meets this phase's evidence requirements.

**Routing and permissions.** Disposable projects isolate HOME/XDG and use a cleared allowlisted child environment, `--pure`, one provider, matching primary/helper aliases, disabled plugins/MCP/sharing and effective final permission rules. The loopback recorder observes actual primary/helper alias payloads before forwarding to the explicit existing LiteLLM host. This establishes the runtime's selected alias, not the proxy's physical model location or internal routing. Rust maps actual ACP option kinds to default denial and marks invalid callbacks as sticky attempt failures even if the peer later claims success. Tool-free probes and denied reads do not prove live allow-once, write or shell enforcement. No native credentials, forbidden subscription proxying, fallback, policy widening or automatic replay is introduced.

**Project/state integrity and lifetime.** All experiment writes are disposable; the harness scaffold never mutates projects or Git. Credential values are environmental and generated live config uses an environment reference; diagnostics withhold arbitrary errors/text. Existing user/global configuration and proxy service settings are untouched. ACP session cancellation, explicit terminal results and direct-child/group verification are distinct checks. TERM-resistant descendants, including after leader exit, are covered. A 300 ms TERM delay followed by group KILL proves forced termination, not graceful flushing. Detached groups, remote inference cancellation and production backpressure remain explicit limitations. Durable recovery is N/A to this disposable experiment and remains a Phase 5 contract.

**Test quality and live evidence.** Eleven root tests cover CLI behavior and pure permission decisions. Seventeen adversarial fixtures test failure and cleanup; sticky-failure cases require explicit client rejection rather than fixture crashes. Real OpenCode/stub tests cover deterministic read denial and cooperative cancellation. Merged live evidence covers text/instructions/denial/cancellation, including the intermittent denial error and later diagnostic result. Current text/instruction reruns reconfirm authenticated live routing. No mock-only inference closes a live gate. The send-failure fixture proves termination/failure around response-path closure; it does not isolate successful delivery or a specific failed syscall. Malformed JSON may await the outer deadline. These are bounded probe limitations, not production reliability guarantees.

**Platform, dependencies and operations.** Only macOS arm64 is verified: macOS 27.0.1 (26A434), Rust/Cargo 1.88.0, OpenCode 1.18.30 (previously recorded Homebrew 1.18.30_2), Python 3.14.7. ACP SDK 3.6.0/schema 1.13.0 and exact direct dependency pins match D023. Inventory hash, counts, declared licenses and MSRVs are rechecked below; prior pinned-source license inspection remains evidence, not a new upstream audit. P2.5 must build the actual notice bundle, including schema upstream attribution and Unicode terms; r-efi is inactive on the tested graph. No binary is distributed here. Rust portability does not imply Linux/Windows support. Remote LiteLLM version remains unknown.

**Consuming contracts.** Phase 1 selects feasibility boundaries, while Phase 2 owns production config/permissions/lifetime/outcome semantics. R01-02 corrects the task-order gap: P2.1 specifies coding permissions, P2.2 verifies enforcement and minimum bounded cleanup before any real coding prompt, and P2.4 completes hardening/reporting before release. This clarifies D020/D023 and existing safety invariants without choosing new flags, schemas, permissions or dependencies. P2.1 becomes the next ready task only on accepted P1.7 merge.

## Findings and resolution

| Finding ID | Severity | Concrete issue / affected requirement | Correction/task/PR | Verification evidence | Disposition |
|---|---|---|---|---|---|
| R01-01 | Low | TESTING still claimed no Rust implementation and described Cargo checks conditionally despite the integrated scaffold and executable probes. | `c1fdb2f`: state implemented/planned boundaries and add exact current root/experiment commands plus live/inventory links. | Ran listed root/build/lint and offline/runtime suites; compared counts, paths and toolchain to manifests and evidence. | Resolved |
| R01-02 | Medium | P1.5/D023 require useful permission/lifetime enforcement before production coding, but P2.2's real project task preceded the P2.4 permission/supervision card without an explicit minimum launch gate; P2.1 did not name coding permissions. This could let a consumer mistake the text-only probe for a coding-ready supervisor. | `c1fdb2f` / `c5ad075`: clarify P2.1/P2.2 acceptance and EXECUTION handoff. Require controlled denial/cleanup checks before authorized edit/test tools; retain P2.4 hardening. | Compared amended cards with D020/D023, AC07, DESIGN and EXECUTION; dependencies remain acyclic P1.7 → P2.1 → P2.3 → P2.2 → P2.4. No production run or speculative permission choice added. | Resolved |
| R01-03 | Low | PROJECT current-work text still treated merged PR #12 as pending; the review closeout also needs a consistent phase/backlog/next-task record. | This review PR: refresh current state, P1.7 report link, proposed post-merge status and backlog; align README status. Preserve dated historical evidence. | Confirmed PR #12 merged at `fa4b411`, no open PR at entry, task checkbox/card inventory and report links; proposed P1.7 acceptance takes effect only on merge. | Resolved |
| R01-04 | Medium (Grok Concern) | The pre-review report still said pending while the board proposed P1.7 completion, which would leave inconsistent gate evidence if merged unchanged. | Final report/status commit records completed review and pass effective on PR #13 merge. | Compared closeout, gate, PROJECT and README; no pending verification remains and all completion claims are merge-conditional. | Resolved |
| R01-05 | Low (Grok Nit) | P2.2 consumed P2.1's permission contract through a transitive dependency only. | `6595443`: name P2.1 directly alongside P2.3. | Parsed P2.2 dependency line and verified both targets/cards; the existing acyclic order is preserved. | Resolved |
| R01-06 | Low (Grok Nit) | Standing validation guide repeated exact suite counts that would drift with new tests. | `6595443`: describe suite coverage and retain counts in dated evidence/report. | Checked TESTING has no hardcoded suite counts; commands and evidence links remain valid. | Resolved |

No Critical/High defect was found in the scoped experiment. There are no newly promoted feature recommendations. Production handoff limitations above retain their existing P2.x/P4.x owners rather than being silently waived or implemented in the review.

## Verification and integrated recheck

Run from repository root with `~/.cargo/bin` on PATH:

```bash
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --release --locked
./target/release/ah --version
cargo build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
python3 scripts/experiments/acp_lifecycle.py --runtime --opencode /opt/homebrew/bin/opencode
zsh -ic 'python3 scripts/experiments/acp_lifecycle.py --live --opencode /opt/homebrew/bin/opencode --endpoint http://litellm:4000/v1 --model macmini-qwen3-coder-30b --scenarios text instruction'
git diff --check
```

Root checks pass (11 tests, no lint/format findings); release smoke prints `ah 0.1.0`. Locked experiment build/format/Clippy pass. All seventeen fake cases pass with no live child/descendant. Real OpenCode local-stub text/instruction/deny/cancel pass: one read callback denied, three tool events, denied sentinel absent from wire payloads; cancellation returns `cancelled`. Unavailable service returns `promptError` with no successful wire record; child reaping and process-group absence pass. Fresh live text/instruction pass: four/two chunks respectively, `end_turn`, exact markers, zero tool/permission events, correct primary/helper alias, instruction sentinel only in primary request, child reaped and no live group members. Merged P1.3 live denial/cancellation evidence remains applicable; no automatic replay or extra grants were used. No private output or credential values are retained.

Locked Cargo metadata (full graph and `--filter-platform aarch64-apple-darwin`) confirms 127 registry packages, 101 reachable on macOS, nonempty license declarations and no declared MSRV above 1.88. The lockfile SHA-256 matches `d3f759aa999c9a38ab50a55edad38a0752351341d256ede1d39a199c7869792a`. Link/task/status/whitespace checks and final PR review outcome are recorded below. Final documentation recheck also confirms 60 planned task IDs match unique task cards (excluding twelve historical pre-card planning tasks); P2.2 directly depends on both P2.1 and P2.3. Only documentation/contracts/status change in this PR; after remediation the reviewed runtime/policy behavior is unchanged.

## PR review and final closeout

All five real OpenCode local-stub/unavailable scenarios pass. Local Markdown file-target checks pass (509 targets); tracker inventory has 52 remaining tasks after proposed acceptance; `git diff --check` passes. [Grok review on PR #13](https://github.com/awesomejt/agent-harness/pull/13#pullrequestreview-5740116110) is complete. One completed Grok review reported 0 Blocker, 1 Concern and 2 Nits. All are resolved in R01-04–R01-06; no Critical/High impact or mandatory re-review applies under the Git workflow.

## Gate outcome

Pass proposed for the exact reviewed Phase 1 experiment scope, effective only when [PR #13](https://github.com/awesomejt/agent-harness/pull/13) merges. All mandatory tasks/evidence and six findings are covered, corrections are verified, the required Grok review is complete and no unresolved finding remains. This final commit records report/tracker/README status only. On merge P1.7 passes and P2.1 becomes ready; no production coding run, release or expanded platform support is implied. Dependent work waits for that accepted merge under [PHASE_REVIEW.md](../PHASE_REVIEW.md).
