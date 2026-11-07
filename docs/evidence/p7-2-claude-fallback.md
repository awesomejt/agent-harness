# P7.2 evidence — Claude local-first fallback

Task: [P7.2](../../tasks/07-native-adapters.md#p7-2), fifth narrow increment, after workflows merged on [PR #64](https://github.com/awesomejt/agent-harness/pull/64). Decision: [D052](../../DECISIONS.md#2026-11-06--d052-claude-as-the-configured-pre-submission-native-fallback). Date: 2026-11-06. Platform: Apple Silicon macOS; Rust 1.88.0, OpenCode 2.2.5 and Claude Code 2.1.314. Authentication uses the operator's existing official CLI login (D047).

## Change and boundaries

The native fallback resolves its configured runtime rather than always selecting OpenCode. `native.target: "claude"` now works with `local-first` for single runs, sequences and Ralph. The D034 coordinator and its pre-submission TCP-only eligibility rule are unchanged. Both runtimes' static capabilities are checked before network contact or project writes. Claude receives the same role, permission profile, project instructions, prompt and shared deadline; it performs the full control preflight and creates fresh request-bound grants. It never applies the local managed-config plan.

Preview identifies the Claude fallback and login prerequisite without reading credentials or launching anything. Workflow records keep `fallback: "claude/MODEL"`; machine output uses runtime `claude` and the bare model on attempt 2. No dependency, flag or record schema changed.

## Repeatable checks

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo build --locked`, `cargo test --locked`: 134 Rust tests pass. The new config test verifies the distinct runtimes, no native credential lookup, unchanged context/permissions and missing local-key refusal before stdin acquisition.
- `python3 scripts/tests/claude.py`: 78 cases. Added fallback checks cover deny, trusted one-shot grants, a constrained reviewer and its native model override, preflight rejection, backend failure, uncertain EOF, confirmed deadline cancellation and unconfirmed interruption. Every eligible case launches Claude exactly once and never launches local OpenCode; no project routing files are written. A reachable LiteLLM endpoint starts only OpenCode, including local success, failure, uncertainty and version rejection. The TCP listener receives no bytes.
- Preview covers fallback discovery/login, oversized role refusal and primary effort refusal without probe, runtime or state. Missing Claude stops with exit 2. Invalid `--no-sync` routing refuses; valid routing is preserved byte-for-byte when the endpoint subsequently becomes unreachable and Claude runs.
- Sequence fallback records both submission boundaries; uncertain step 2 stops, bare resume refuses, and explicit retry completes through one fresh fallback. Ralph claims through the fallback and completes only after the configured check passes.
- `python3 scripts/tests/offline.py`: all 26 offline suites, including the expanded Claude suite and installed OpenCode regressions. The full runner initially caught a fixture-only macOS error (`shutdown` on a listening socket) and an obsolete mode-matrix expectation that Claude fallback must refuse. The corrected Claude and mode suites were rerun separately through the same runner; the other 24 suites passed in the full run. The 166-case mode matrix now proves a reachable Claude-fallback config still runs only OpenCode without a native key.

## Live fallback smoke

Disposable git projects with a dirty sentinel, external config, synthetic unused LiteLLM key and a closed loopback endpoint. The native runtime uses its own existing login. The first `deny` trial asked for a marker from `AGENTS.md`: it ended `end_turn`, exit 0, with cleanup confirmed, but its response was tool-call-shaped text followed by `else`, not the requested marker. There were zero announced tools or grants and no file changes. This is not instruction-conformance or coding-success evidence; it matches the previously observed limitation of tool-shaped responses with no offered tools (D050/P7.2 workflows).

A fresh project with no `AGENTS.md` then used the explicit prompt `Reply with exactly CLAUDE-FALLBACK-OK and no other text.`:

| Route | Observed result |
|---|---|
| `local-first`, unreachable LiteLLM | Exit 0; exact marker; attempt 1 OpenCode `launched: false`, `prompt_submitted: false`; attempt 2 Claude `sonnet`, submitted, `end_turn`, cleanup confirmed; zero tools/grants. Backend-reported USD cost 0.0029465. |
| `cloud-only`, same project and prompt | Exit 0; exact marker; one Claude `sonnet` attempt, `end_turn`, cleanup confirmed; zero tools/grants. Backend-reported USD cost 0.0004037. |

The first trial's backend-reported cost was USD 0.0087298. These are runtime cost reports, not billing or a performance comparison. Both successful marker runs preserved the sentinel and created no managed OpenCode config. The comparison uses the already-supported cloud-only route, not a separate direct-CLI inference run; prior P7.2 evidence owns direct runtime probes. Raw temporary logs are not committed, and contain no inspected login store or copied credential.

## Remaining acceptance

This is fallback smoke and offline failure-policy evidence, not final P7.2 acceptance. The next increment consolidates live coding and enforced constrained-role evidence across the accepted Claude surface, capability/setup documentation and limitations. Native adapter selection stays on Claude until that closeout is reviewed and merged. Phase 7 portfolio acceptance still requires the other three adapters and P7.6/P7.7.

## PR review closeout

[PR #65](https://github.com/awesomejt/agent-harness/pull/65) received one automated Grok review, posted under the operator's account: 0 blockers, 1 concern and 1 nit. The concern adds an explicit assertion that preview reports the OpenCode primary's unsupported-effort refusal; the existing execute/refusal/no-probe checks remain. The nit updates `Invocation::resolve`'s credential comment to distinguish a Claude login from an OpenCode native key. The 78-case Claude suite and formatting checks pass after these changes. Neither finding is critical/high, so no re-review is requested under the Git workflow and the operator's instruction. Completion takes effect on merge; P7.2 final acceptance remains open.
