# P2.7 — Prerequisite diagnostics and read-only preview

Date: 2026-11-02 (America/Denver). Entry baseline: `2299f8e` (P2.4 PR #18 merged). Task: [P2.7](../../tasks/02-first-slice.md#p2-7). Platform: Apple Silicon macOS, Rust/Cargo 1.88.0, Python 3.14.7. Completion is effective on the task PR merge after required Grok review.

## Behavior and boundaries

`ah single PROMPT --preview` resolves production inputs and invokes `Plan::prepare`, returning before runtime construction, transaction apply, private-HOME setup or any child/model/network work. Existing file/stdin/override/no-sync inputs apply unchanged. Shared absolute-PATH discovery reports OpenCode presence without execution; both preview and execution ignore relative PATH entries. Missing runtime guidance is also emitted during normal execution.

Human stdout identifies harness version, expected OpenCode 1.18.30, escaped local paths, mode/model/permissions/deadline sources, no-fallback LiteLLM route, credential reference presence, sync policy and affected managed files/fields. Endpoint, credential values, prompt and unmanaged project values are omitted. Key-reference errors now include a static next action. Missing/invalid inputs and planner conflicts return 2; missing OpenCode is reported without invalidating a locally valid plan (exit 0). Runtime version/capabilities, proxy reachability and alias availability remain explicitly unverified. No health checks are permitted, including non-spending ones. Normal execution retains effective runtime preflight.

## Verification

`python3 scripts/tests/preview.py` runs public CLI fixtures with an executable trap and disposable project/HOME trees. Every invocation compares file bytes and directory entries before/after within the disposable tree. Successful inline/file/stdin plans never execute the trap or create locks, receipts, directories or any project files in that tree. Code inspection verifies that private-runtime setup outside the fixture tree is unreachable from preview. Sentinel key, prompt, endpoint and unmanaged values remain absent from stdout/stderr. A newline-bearing project path is escaped. Sources, explicit trusted host scope, model/deadline overrides and required managed changes are asserted.

Missing/relative-only PATH discovery reports installation guidance. Missing key errors report the environment-reference next action. Malformed model aliases and mismatching no-sync routes reject; an exact unowned no-sync route passes with no changes or receipt. The endpoint is an unavailable loopback port; preview makes no network request. Code inspection confirms the preview branch cannot reach any network or child-launch function.

Commands:

```bash
cargo fmt --check
cargo clippy --locked --all-targets -- -D warnings
cargo test --locked
cargo build --locked
python3 scripts/tests/preview.py
python3 scripts/tests/single.py
python3 scripts/tests/single_runtime.py
```

Formatting, Clippy, all 37 Rust tests and preview fixtures pass. All 55 existing public-CLI cases pass, including cancellation, output backpressure and no-sync coverage. The installed OpenCode 1.18.30 regression against the local deterministic model stub completed the real arithmetic edit and shell test: six exact grants, 16 tool events, `end_turn`, confirmed cleanup and exit 0; independent arithmetic verification passed. No external paid/live model request is needed for this read-only feature. First-slice packaging, dirty-project reporting and Phase 2 real-use/holistic review gates remain open.

## PR #19 review closeout

[Grok review](https://github.com/awesomejt/agent-harness/pull/19#pullrequestreview-5742558819): 0 blockers, 0 concerns, three nits. All addressed: missing-key diagnostics share a constant with the resolver; snapshot checks include directory entries and scope their private-runtime claim to code inspection; sync source explicitly reports invocation or default. Formatting, Clippy, all Rust tests and preview fixtures pass after these changes. One Grok review; no re-review required for nits. Completion is effective on [PR #19](https://github.com/awesomejt/agent-harness/pull/19) merge.
