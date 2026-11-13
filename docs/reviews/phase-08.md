# Phase 8 holistic review

## Review scope

- **Task:** P8.5 ([card](../../tasks/08-pi.md#p8-5)); consolidating reviewer: Grok (2026-11-12), Claude Opus (2026-11-13), Codex (2026-11-13). Independent reports: [Grok](2026-11-12-grok-phase-8-holistic-review.md) (G08-*), [Claude Opus](2026-11-13-claude-opus-phase-8-holistic-review.md) (C08-*), [Codex](2026-11-13-codex-phase-8-holistic-review.md) (X08-*).
- **Accepted entry baseline:** Phase 6 `fe4e116` ([PR #58](https://github.com/awesomejt/agent-harness/pull/58)). **Reviewed material head:** `35777fb` (P8.4 merged, [PR #104](https://github.com/awesomejt/agent-harness/pull/104)).
- **Included PRs:** P8.1–P8.4 implementation PRs per task cards; review PR [#105](https://github.com/awesomejt/agent-harness/pull/105) (`review/08-pi`) records assessments; remediation **`patch/p8-5-review-fixes`** resolves every finding.
- **Mandatory scope:** P8.1–P8.4 and P8.5; D060/D065/D079–D084; F10 and AC01–AC11 regression constraints for shared launch paths.

Review PR #105 merged under D042 with gate **changes required**. This report and `patch/p8-5-review-fixes` propose phase pass after Grok-reviewed remediation merges.

## Findings and resolution

| ID | Severity | Issue | Planned correction | Status |
|---|---|---|---|---|
| G08-01 | High | `file://` paths bypass project boundary | Align `pi_trusted_policy.mjs` with Pi 1.5.0 normalization; block `file://` and test | Resolved |
| G08-02 | Medium | `/dev/stdout` and `/dev/stderr` allowed | Block device nodes except `/dev/null` | Resolved |
| G08-03 | Low | Doc drift (FRAMEWORKS, DESIGN, OPERATIONS) | Update capability and operations text for P8.3–P8.4 and Pi module | Resolved |
| G08-04 | Low | `//` absolute paths in bash scan | Normalize `//` tokens before boundary check | Resolved |
| C08-01 | High | `@~` home escape after `@` strip order | Normalize `@` then `~`/`file://` like Pi `paths.js` | Resolved |
| C08-02 | Medium | Success on bad `stopReason` or `aborted` settle | Fail closed; coarse diagnostics only | Resolved |
| C08-03 | Medium | `fd`/`rg` on PATH undocumented | Document in FRAMEWORKS and OPERATIONS | Resolved |
| X08-01 | High | Dangling symlink write escape | `lstat`/`readlink` walk in policy | Resolved |
| X08-02 | High | Read fallback variants unchecked | `readPathCandidates` validated in policy | Resolved |
| X08-03 | High | `api_key_env` could overwrite child controls | Remap to `AH_PI_LITELLM_API_KEY` (D083) | Resolved |
| X08-04 | Medium | 30s recv cap after prompt submit | Honor full attempt deadline for post-submit recv | Resolved |
| X08-05 | Medium | Raw `errorMessage` in diagnostics | Emit coarse outcome codes only | Resolved |

**Verification:** `cargo test --locked`; `node --test scripts/tests/pi_policy_boundary.mjs` (expanded cases); `python3 scripts/tests/pi.py` (new terminal-outcome cases and `models-key`); `python3 scripts/tests/offline.py`. Rust `ui_tool_path_allowed` mirrors obvious escapes before UI grants.

## Gate outcome

**Pass proposed** when `patch/p8-5-review-fixes` merges after `/grok review`. P8.5 then closes Phase 8.
