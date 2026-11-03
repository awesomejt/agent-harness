# Phase 3 holistic review — Grok

**Reviewer:** Grok (xAI)  
**Date:** 2026-11-03  
**Branch:** `review/03-routing` (PR #32)  
**Reviewed head:** `dd4397a` (PR #31) plus documentation-only changes on this PR  
**Entry baseline:** `4c33b22` (Phase 2 review, PR #24)  
**Scope:** P3.1–P3.5, P3.7, P3.6; D031–D035; AC02/AC03/AC04 core-MVP columns and native-route portion of AC05/AC07.  
**Excluded:** named agents, machine output, additional platforms/artifacts, native CLIs other than OpenCode, sequences/Ralph, optional resource features.

This is an independent holistic assessment of the integrated Phase 3 surface, distinct from the individual feature-PR reviews and from the primary Claude report in `phase-03.md`. It examines accumulated behavior across the reviewed range rather than only the final diff.

## Requirements and acceptance coverage

| Task / criterion | Integrated evidence and conclusion |
|---|---|
| P3.1 / AC03 recovery | `src/recovery.rs` + `docs/evidence/p3-1-recovery-policy.md` (D031). Pure decision function. Only pre-submission Unavailable/RateLimit/Transport failures on local-first with all guards satisfied may fall back once. Cancellation, deadline, unknown, post-submission, and any same-route case stop. No automatic retry. |
| P3.2 / AC02, AC04 native isolation | `docs/evidence/p3-2-native-isolation.md` (D032). Cloud-only uses only the built-in `opencode` API-key provider, constructs no managed LiteLLM plan, clears inherited config/auth, and the trap sees zero LiteLLM discovery or model requests. Catalog and version checks are pre-ACP. |
| P3.3 groups + local-first fallback | `docs/evidence/p3-3-model-groups.md` (D033) and `docs/evidence/p3-3-local-first-fallback.md` (D034). Explicit `group:NAME` resolves to one proxy group and never appears as a harness name at the runtime. Native route rejects groups. One linked `attempt=2` native run only after a byte-free TCP reachability failure before any runtime, state, or project write. |
| P3.4 mode matrix | `docs/evidence/p3-4-mode-matrix.md`. One combined config exercises every scenario in all three modes against reachable and closed endpoints, asserting effective route, environment, endpoint contact, inherited-choice rejection, attempt lines, uncertainty without replay, and managed writes. |
| P3.7 OpenCode 2.2.5 baseline | `docs/evidence/p3-7-opencode-2-baseline.md` (D035). Exact pin on both routes with `--standalone` inspection, sources check, agent-rule tails, `opencode/`-only native catalog, and exact `rawInput` grant binding. Validator mutation is caught. |
| P3.5 dual-route live use | `docs/evidence/p3-5-dual-route-use.md`. Live local-only, cloud-only, reachable local-first, and closed-port fallback each edited a disposable project and passed an independent test (exit 0). Managed project files were byte-identical across native runs; user OpenCode directories showed 0 changes attributable to harness runs; no private state or `serve` process remained. Rejected-key and unknown-alias cases stop without fallback (exit 4, 0 grants). |
| Phase 3 exit evidence | Allowed/forbidden traffic for all modes, successful local execution, eligible fallback, no fallback on local-only, no cloud-only discovery, and native selection unaffected by managed settings are covered by P3.2/P3.4 fixtures and P3.5 live runs. Deterministic pre-execution fallback is live-demonstrated. Ambiguous failure after a possible tool action is covered by the `deny-completed`, `unexpected-write`, `eof`, and `rpc-error` scenarios (exit 4, no replay or fallback). Confirmed cancellation after an actual installed-runtime edit is covered. Both routes were used for real. |

G3 is complete: all three modes enforce their routes, and route, model, attempt, and fallback reason appear in preview and progress. G4 is extended: model groups are harness-owned, the proxy stays operator-owned, and native isolation leaves managed config untouched.

## Integrated assessment

**Ownership and module boundaries.** The package remains a single crate with a thin executable. Phase 3 adds three focused modules (`recovery`, `probe`, `opencode`) without a common adapter framework, provider pool, or new dependency. Config resolution produces an immutable `Resolved` request with at most one non-nested fallback. `single::coordinate` is the sole place that links attempts. OpenCode owns the coding loop on both routes; LiteLLM owns routing inside its route. `--mode`, `--model`, and `--no-sync` remain the CLI surface, consistent with the pre-Phase-4 contract.

**Routing, isolation, and permissions.** Local-only and cloud-only never contact the other route. Local-first sends no bytes or credentials to establish eligibility; everything after the reachability check is final. Both route keys and both static targets are validated before input acquisition. The fallback receives the identical project, permissions, timeout, deadline, and prompt, plus a fresh private runtime and grants and a full native preflight. Under the 2.2.5 profile, deny removes tools from the model, trusted binds each grant to exact `rawInput`, and `other`-kind tools are always refused. The probe worker and private-home cleanup run on plain OS threads, so an unbounded resolver or recursive deletion cannot block shutdown.

**Project integrity and lifetime.** Cloud-only bypasses the D025 transaction entirely. A local-first fallback writes nothing to the project because the plan is prepared but never applied before the check. The shared signal watcher covers the gap between attempts; cancellation or deadline wins over concurrent classification. D030 cleanup runs after every attempt and its failure overrides the outcome with exit 4. Phase 2 preservation fixtures pass unchanged.

**Tests and real use.** P3.4 asserts effective behavior rather than enum values; its mutation checks were caught. P3.7 added a validator mutation check. The P3.5 live gate uses one representative edit/test task per route on free or unpriced models. Paid native models, rate limiting, and proxy-group outages were not exercised; that limit is recorded. The reported `session_cost=0 USD` is OpenCode’s own figure.

**Platform and operations.** Verified on Apple Silicon macOS 27.0.1 with Rust 1.88.0 and OpenCode 2.2.5 (Homebrew). The published `v0.1.0-alpha.1` remains unchanged: it predates Phase 3 and D030, supports local-only only, and requires OpenCode 1.18.30. Native and local-first routes are source-only until a new artifact. Managed project `opencode.json` keeps legacy keys that 2.x translates; migration stays deferred by D035.

## Findings

No Critical or High defects were identified. No code change is required.

| ID | Severity | Concrete issue | Disposition |
|---|---|---|---|
| G3-01 | Low | README Status and Install lines were stale relative to the three implemented modes and the alpha.1 vs source OpenCode pin. | Resolved in this PR (documentation). |
| G3-02 | Low | OPERATIONS status line, preview version wording, and P3.5 residual language were stale. | Resolved in this PR (documentation). |
| G3-03 | Medium | OPERATIONS diagnostic table pointed a rejected native login at a login flow that D032 never consumes, and lacked rows for the commonest P3.5 setup failures (exit 4 with 0 grants) and unexpected local-first fallback. | Resolved in this PR (documentation). The table now matches the implemented API-key route and the observed failure modes. |
| G3-04 | Low | TESTING and EXECUTION still contained prospective wording for work that has landed. | Resolved in this PR (documentation). |
| G3-05 | Low | PROJECT.md current-state still listed P3.5 as active after its merge and the backlog count was stale. | Resolved in this PR (documentation). |

All five findings are documentation-only, localized, and resolved on this branch. No patch PR is required.

### Recommendations (not defects)

- **R-G3-1 — exit classification for zero-activity provider failures.** A rejected key or missing alias after prompt submission exits 4 (uncertain) with 0 grants and no completed tool call, even though the 2.2.5 profile gates or removes every tool. This matches D031 and the “missing trustworthy terminal response remains uncertain” rule, so it is not a defect. Reporting exit 1 in that narrow case would reduce noise but changes a public exit contract. Suitable as a P4.7 gate input; adopt only with a decision entry and fixtures, and never with fallback.
- **R-G3-2 — refresh the published artifact.** Binary users cannot use native or local-first routes, the 2.2.5 pin, or D030 cleanup until a new artifact is packaged. Suitable as a P4.5 gate input.

## Residual risks and limits (accepted for this phase)

- Reachability is not model availability. A mistyped host counts as transport and falls back (D034).
- Trusted grants confer host privileges without an OS sandbox.
- Free native models were used for the live gate; their terms may differ from paid models. The harness does not rank or price models.
- Ambient `OPENROUTER_API_KEY` is correctly excluded from the native route under D032.
- Only macOS 27.0.1 on Apple Silicon has been release-tested for the current source.

## Verification summary

On the reviewed head plus this PR’s documentation changes (macOS 27.0.1 arm64, Rust 1.88.0, OpenCode 2.2.5):

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo test --locked` (57 tests), and `cargo build --release --locked` pass.
- Python matrix and runtime suites (`single.py` 69 cases, `native.py` 40 cases with zero LiteLLM requests, `modes.py` 165 cases, `local_first.py`, installed-runtime edit/test/cancel/group/refuse, `native_runtime.py`) pass.
- No leftover `ah-runtime-*` directory or `opencode serve` process remains after the runs.
- Live dual-route evidence remains current for the reviewed head (only documentation changes after the P3.5 record).

## Gate outcome

**Pass proposed** for the exact Phase 3 scope defined above, effective on merge of this report PR. Every mandatory task and Phase 3 acceptance column has evidence. All findings are resolved and verified. No code remediation PR is required. No finding remains open.

On acceptance, P3.6 passes and P4.1 becomes ready. Named agents, machine output, additional platforms, and a refreshed published artifact remain gated; no core-MVP completion is implied.

---

*This review was performed independently of the primary Claude Phase 3 report. It reaches the same substantive conclusion (pass, documentation-only findings already addressed) while recording its own traceability and residual-risk notes.*
