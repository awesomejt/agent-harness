# Codex holistic project review — Phase 3

## Review scope

- **Reviewer/date:** Codex, 2026-11-03 (America/Denver).
- **Review task:** P3.6; independent supplemental assessment of [PR #32](https://github.com/awesomejt/agent-harness/pull/32), branch `review/03-routing`.
- **Accepted entry:** `4c33b22` (Phase 2 review, PR #24). **Reviewed head:** `0011b93f88bd9612ffb8b3302781cc64d1a08855`. Range: `4c33b22..0011b93`, including implementation/evidence PRs #25–#31 and the report/documentation changes in #32. The implementation head is `dd4397a`; changes after it are Markdown only.
- **Coverage:** accumulated Phase 3 behavior and integration with Phase 2 configuration transactions, permission policy, ACP supervision, preview, project preservation and distribution. Mandatory cards P3.1–P3.5 and P3.7, plus the P3.6 gate; decisions D031–D035; goals G3/G4 and relevant G1/G2 guarantees.
- **Project-wide context:** specification and MVP acceptance matrix, implementation/phase dependencies, feature dispositions, Rust ownership, operations, documentation map and existing phase reviews. Later phases were checked for scope/dependency consistency, not reviewed as implemented features.
- **Exclusions:** fixes, merge, new release, new feature authorization, live provider/account probes and renewed legal/terms verification. Named agents, machine output, additional native CLIs, Pi, workflows and optional resource features remain later-phase work.

This file supplements the existing Claude and Grok reports; it does not overwrite them or constitute an accepted reopened revision. PR #32 was open and unmerged when inspected. Its fetched discussion timeline contained no comments. Earlier PR review dispositions are supported by the checked-in evidence; they were not independently re-audited comment by comment.

## Conclusion

**Changes required before Phase 3 acceptance: two open Low documentation findings.** No Critical, High or Medium finding, or demonstrated implementation defect, was identified in this review. The implementation and fresh checks support the intended Phase 3 routing boundary, but the current documentation does not fully agree with it.

The existing reports propose a pass with no unresolved findings. This supplemental assessment does not concur with that clean-pass conclusion until the findings below are resolved and verified. Under [PHASE_REVIEW.md](../PHASE_REVIEW.md), every severity must close before pass. No corrections were made as part of this review, and Phase 4 must continue to wait for the accepted Phase 3 gate.

## Requirements and acceptance coverage

| Scope | Assessment and evidence |
|---|---|
| P3.1 / AC03 | `recovery::decide` is a pure, conservative policy. All guards must hold; only pre-submission unavailable/rate-limit/transport classifications can qualify in local-first. Fresh recovery tests pass. The actual coordinator intentionally uses only the narrower D034 reachability evidence. |
| P3.2 / AC02, AC04 | Cloud-only uses the official OpenCode executable and built-in `opencode` API-key provider. It bypasses managed planning, clears ambient credentials/configuration and validates private sources, agents, catalog and session model. Fresh native fixtures report 40 cases and zero LiteLLM requests; installed-runtime native setup passes without forwarding inference prompts. |
| P3.3 / AC03, AC04 | Explicit `group:NAME` references resolve to one existing proxy group; groups cannot become a native model or an implicit provider pool. Proxy administration remains operator-owned. The only native fallback follows a byte-free TCP reachability failure before runtime construction or project apply. Fresh group, local-first and mode-matrix checks pass. |
| P3.4 / AC02, AC03, AC07 | The 165-case matrix checks effective environment/configuration, routes, endpoint contact, inherited settings, no-sync, uncertainty and managed writes. Fresh execution passes. Local-only cannot launch native fallback; cloud-only does not contact LiteLLM; later local-first failures are final. |
| P3.7 / AC02, AC07, AC11 | Exact OpenCode 2.2.5 pin, standalone inspection, source checks, permission-rule tails and argument-bound grants are implemented. Installed-runtime edit/test, cancellation, group selection, unsupported-tool refusal and native setup all pass again. Compatibility is established for the pinned runtime, not arbitrary newer versions. |
| P3.5 / AC01–AC03 | [Recorded live evidence](../evidence/p3-5-dual-route-use.md) describes real edits and independent tests for local-only, cloud-only, reachable local-first and native fallback on `ea9a5f4`. That source remains applicable: later changes through this reviewed head are documentation only. This review did not repeat live inference. |
| AC05, AC06, AC09 | Fresh prompt-source, dirty-project, progress/cancellation and preview regression suites pass. Backend success remains separate from independent task verification; usage has provenance or is unknown. Versioned machine output and named-role restrictions remain Phase 4 scope. |
| AC08, AC10 and remaining MVP work | Named agents are not implemented or claimed complete. Current source supports the Phase 3 routes, while published alpha.1 remains the older local-only artifact. Broader platform/artifact acceptance remains P4.5; overall core MVP remains gated by P4.9. |

F02 and the group part of F04 have substantive Phase 3 evidence; F03/F11/F12/F13/F14/F16/F20/F24 retain their applicable earlier guarantees and receive integration regression coverage. This does not accept later effort mapping, durable records, machine schemas or other deferred feature portions.

## Integrated assessment

### Architecture and routing policy

The single-crate design remains proportionate. `config` resolves inputs; `single` coordinates attempts; `recovery` decides eligibility; `probe` supplies bounded pre-submission evidence; `opencode` generates and validates the pinned runtime configuration; `runtime`, `acp` and `process` own setup, protocol and child lifetime. OpenCode owns the coding/tool loop on both routes. No raw completion substitutes for coding execution, and no general adapter framework or provider-ranking mechanism has been added.

Route and runtime remain distinct. Native requests carry only their selected key under `OPENCODE_API_KEY`; LiteLLM requests use the reserved local key name. Neither consumes the user's login store. The project source contains no added subscription-token proxy path. This is an implementation assessment of D032, not a fresh provider-terms audit.

### Recovery, permissions and state integrity

Local-first validates static inputs and prepares the read-only plan before its check. A confirmed unreachable endpoint leaves no local runtime, state or project write to recover. The coordinator links one native attempt with the same project, prompt, permissions and overall deadline; it neither reuses grants nor retries after uncertain work. A reachable endpoint commits the run to the local route even if a later provider or alias fails. DNS mistakes can therefore trigger native fallback, while reachable-but-unusable deployments cannot; this is the explicit D034 contract.

Runtime configuration is isolated through cleared environment, private HOME/XDG, disabled project discovery and effective-source/agent checks. Default deny and trusted argument-bound one-shot grants retain their distinct meanings; unsupported `other` tools are refused. Trusted shell/file access is host authority, without an OS sandbox. Process-group cleanup cannot contain detached descendants or remote work; those limits are documented rather than inferred away by passing tests.

Cloud-only bypasses the project transaction, and fallback does not apply the prepared local plan. Local sync/no-sync remains conflict-aware and project-scoped. Cleanup failure overrides an otherwise successful outcome with uncertainty. Fresh preservation and cleanup fixtures support these properties. Existing synchronous filesystem transaction limits remain; this review does not establish interruption bounds for arbitrary stalled filesystem calls.

### Evidence, operations and project records

Tests cover observed behavior and adversarial protocol/process outcomes, not only enum selection. Installed-runtime checks add actual read/edit/shell and cancellation evidence; native setup checks deliberately intercept the prompt and cannot prove authentication. Native inference/authentication and all-route live use rely on P3.5's dated record. Its free-model choice, missing proxy version, narrow task sample and untested rate-limit/group-outage scenarios remain explicit limits.

The prebuilt alpha.1/source split is clearly stated in the main installation guidance. No repackaging of that immutable artifact is implied. The existing recommendations to refresh artifacts in P4.5 and evaluate zero-grant provider-error exits in P4.7 are reasonable deferred inputs; conservative exit 4 remains the current contract. They are not new defects or implementation authorization here.

Task cards and dependency diagrams retain the Phase 3 review gate before Phase 4. Proposed completion checkboxes in the open review PR are explicitly conditional on merge. However, residual current-document drift and a misleading configuration promise remain, as detailed below.

## Findings and required follow-up

Locations refer to reviewed head `0011b93`. Suggested corrections are review instructions only; no remediation was performed.

| ID | Severity | Affected requirement/component and concrete issue | Required correction / ownership | Verification evidence and disposition |
|---|---|---|---|---|
| C03-01 | Low | **Local-first input contract:** [CONFIGURATION.md:99](../CONFIGURATION.md#local-first-route-p33--d034) and D034 say a local model default **or `--model`** suffices. A config whose own mode is `local-first` and omits top-level `model` is rejected by `Config::validate` (`src/config.rs:256–259`) before the invocation override can apply. Thus the documented combination fails even with both route blocks, both keys and `--model fixture`. | Correct the contract in the review PR to distinguish a config already declaring local-first (requires a default) from a cloud-only config switched via `--mode local-first --model ...`. Preserve the existing strict-validation decision unless a separately authorized behavioral change is intended. Check the corresponding D034 wording as well. | Reproduced using network-free preview: own mode `local-first`, no top-level model, `--model fixture` → exit 2, `local-only and local-first config require a model default`; identical config with own mode `cloud-only` plus `--mode local-first --model fixture` → exit 0. Only `ah.json` existed afterward. **Open; no correction or patch PR.** |
| C03-02 | Low | **Current documentation/ownership drift:** `docs/CONFIGURATION.md:3` still calls configured fallback pending; `docs/README.md:5` says P3.1 is next; `docs/DESIGN.md:92` names an implemented `native` module that P3.7 removed. These are current guidance, not dated historical evidence, and contradict the integrated implementation and tracker. | In the review PR, update current status text to Phase 3's implemented scope with acceptance still pending, and describe `opencode` as the shared pinned configuration/validator module. Leave historical evidence unchanged. | Compared the named passages with `src/lib.rs`, `src/opencode.rs`, `src/single.rs`, P3.3/P3.7 evidence and `PROJECT.md`. Recheck those relationships after correction. **Open; no correction or patch PR.** |

No incoming PR #32 finding labels required severity mapping. Findings already recorded as resolved in the original report are not reclassified or claimed as new fixes by Codex.

## Fresh verification

Environment: macOS 27.0.1 arm64, repository-pinned Rust/Cargo 1.88.0 and installed OpenCode 2.2.5. Commands used the local Cargo/Homebrew executable directories on PATH. All following checks passed against the reviewed source; no provider credentials or billable inference were used.

| Checks | Result |
|---|---|
| `cargo fmt --check` | Pass |
| `cargo clippy --all-targets --locked -- -D warnings` | Pass |
| `cargo test --locked` | 57 tests pass |
| `cargo build --release --locked` | Pass |
| `python3 scripts/tests/single.py` | 69 cases pass |
| `python3 scripts/tests/preview.py` and `worktree.py` | Pass |
| `python3 scripts/tests/native.py` | 40 cases pass; zero LiteLLM discovery/model requests |
| `python3 scripts/tests/local_first.py` | Pass |
| `python3 scripts/tests/modes.py` | 165 cases pass |
| `python3 scripts/tests/single_runtime.py`, then `--cancel`, `--group=coder`, `--refuse` | All pass; actual edit/independent test, confirmed cancellation, resolved group and unsupported-tool refusal |
| `python3 scripts/tests/native_runtime.py` | Pass; native deny/trusted and local-first fallback setup; zero native prompts forwarded |
| Lifecycle experiment locked build, format, Clippy and `python3 scripts/experiments/acp_lifecycle.py` | Pass in fixture mode; historical `--runtime` mode not run |

The additional C03-01 reproduction used only `--preview` and disposable configuration. Source was not mutated to create a failing test. Prior mutation-check claims remain historical evidence rather than fresh mutation runs. Fresh provider live use, direct-provider comparison and release-download smoke were not repeated; this report relies on their explicitly dated existing evidence where applicable.

## Gate outcome

**Changes required, review remains open.** Resolve C03-01 and C03-02, verify the corrected contracts against implementation, then reconcile the original report's no-open-findings conclusion and associated status claims before proposing acceptance again. No code patch is currently indicated by these findings. Report/documentation remediation belongs in the review PR under the repository workflow.

This review adds only this Codex report. It does not fix source or existing documents, mark the phase accepted, merge PR #32, or authorize dependent Phase 4 implementation.
