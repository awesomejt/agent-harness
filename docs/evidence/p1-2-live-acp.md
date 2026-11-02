# P1.2 — Live ACP transport experiment

Date: 2026-11-01 (America/Denver). Task: [P1.2](../../tasks/01-integration.md#p1-2). Baseline: `433cfc0` (PR #8). Platform: Darwin arm64. Versions: OpenCode `1.18.30` (Homebrew `1.18.30_2`), Python `3.14.7`; remote LiteLLM server version not reported by health response headers. The locally installed LiteLLM version from the earlier probe does not identify this remote server.

## Corrected service and repeatable command

The user supplied the existing API base `http://litellm:4000/v1` and identified `.zshrc` as the credential source. Authenticated `/v1/models` succeeds with HTTP 200 using `LITELLM_API_KEY` loaded by an interactive Zsh. Both configured key variable names were checked without printing values. The existing alias `macmini-qwen3-coder-30b` appears in discovery. `/health/liveliness` and `/health/readiness` return HTTP 200. The earlier localhost failures in [PR #8 evidence](p1-2-opencode-transport.md) describe a different service endpoint; they do not block this supplied host.

```bash
zsh -ic 'python3 scripts/experiments/acp_preflight.py --opencode /opt/homebrew/bin/opencode --live --endpoint http://litellm:4000/v1 --model macmini-qwen3-coder-30b'
```

The live flag sends one fixed text-only prompt after authenticated alias discovery and local permission/configuration checks. Without `--live`, the same script retains the synthetic no-prompt mode. The API key is read from the named environment variable (default `LITELLM_API_KEY`), passed only to the isolated child environment, and referenced in the disposable project config as `{env:AH_PROBE_API_KEY}`. It is not embedded in command arguments, printed, committed or written literally into project configuration. No persistent/global config or proxy changes are made.

## Permission-enforcement preflight

The earlier probe checked project configuration only. This continuation also queries the installed runtime's resolved `build` agent before sending a prompt. Inspection of [OpenCode's pinned agent initialization](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/agent/agent.ts) identified an appended permission allowing its tool-output directory unless an exact denial for that glob exists. An initial no-prompt run correctly refused because of that effective permission widening.

The experiment now explicitly denies the disposable tool-output directory glob as well as all external directories and all other permissions. It checks the exact final three effective agent rules, all denying access. This addresses the version-specific appended allow; it is not a general capability guarantee for other versions. Config also sets `tools: {"*": false}`, leaves MCP/plugins empty, uses `--pure`, and confirms matching primary/helper models and a sole enabled provider. HOME/XDG and inherited overrides/credentials are isolated as in the earlier probe. No permission grant exists. Client filesystem/terminal capabilities are false; any client request or tool activity causes immediate refusal and process cleanup. No interactive wait/approval path is implemented.

Pinned [permission evaluation/filtering](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/permission/index.ts) uses the last matching rule and removes tools denied by wildcard rules. [ACP permission mapping](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/acp/permission.ts) maps `reject`/`reject_once` and cancelled responses to rejection. This narrow tool-free run needs no allow-once mapping or grant; the driver stops rather than accepting an unexpected request. Live callback denial, send-failure handling and explicit grants remain P1.3 evidence, not claimed here.

## Observations

First live attempt: authenticated discovery, configuration/agent checks, ACP initialize and session/new passed. The session reported `harness-preflight/macmini-qwen3-coder-30b`. A prompt asking it to follow project instructions and return the marker produced two assistant text updates and an `end_turn` result, but failed the exact marker assertion. No client request/tool activity was observed; the direct child was reaped. This is partial transport evidence, not proof of automatic project-instruction loading. P1.3 must investigate instruction loading and conformance rather than inherit a success claim.

The final fixed prompt is `Reply with exactly AH_ACP_P1_2_OK and nothing else. Do not use tools.` It distinguishes explicit prompt response from the separate project-instruction test. ACP request deadlines are 30 seconds except `session/prompt` at 180 seconds. A failed/uncertain attempt is never automatically replayed; the second attempt is a distinct diagnostic prompt with no coding side effects or permission grants.

Final result: the explicit-marker run passed. Authenticated discovery, resolved configuration and final deny-all build-agent rules passed; ACP session selection reported `harness-preflight/macmini-qwen3-coder-30b`; four assistant text updates plus one other session update arrived; `session/prompt` returned `stopReason: end_turn`; assembled text matched `AH_ACP_P1_2_OK` exactly. No client requests or tool activity were observed, and the direct child was reaped. P1.2 completion takes effect on the required continuation PR merge. No custom agent loop or native structured-output comparison was needed to establish ACP connectivity. This is a transport experiment, not Phase 2's coding milestone or full P1.3 lifecycle/effective-route acceptance. The configured runtime model and endpoint were checked; downstream physical hosting, proxy-internal routing, and cancellation/descendant cleanup remain unverified.

## Validation

The synthetic no-prompt mode passed after the effective-agent guard was added. The live explicit-marker mode passed against the supplied service. Rust formatting, Clippy (`--all-targets --locked -- -D warnings`) and all 11 tests passed. No Rust dependencies, lockfile, harness CLI interface or architecture decisions changed. The script remains phase-experiment tooling.
