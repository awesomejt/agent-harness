# P7.3 evidence — Codex pre-turn isolation and permission feasibility

2026-11-06. Baseline: `c5f7b91` (selection PR #67). Task: [P7.3](../../tasks/07-native-adapters.md#p7-3). Selection: D053; disposition: [D054](../../DECISIONS.md#2026-11-06--d054-hold-codex-production-support-at-the-unproven-permission-gate). No production adapter, public configuration, dependency or model request is added.

## Outcome

**The bounded discovery experiment is complete; the production gate is not passed.** Codex CLI 0.166.0's inspected controls do not establish the complete pre-turn tool enforcement and isolation required by D047/D053. Keep P7.3 unchecked and refuse production Codex launch. This is an unproven compatibility boundary, not a claim that every possible Codex integration is impossible. Do not weaken `deny`, use prompt-only restrictions, copy credentials or submit a turn to see whether a prohibited tool happens to run.

The next Codex work must reassess a supported interface/control against this evidence before launch implementation. Possible evidence includes a versioned effective tool-policy/inventory API or a supported clean-config mode retaining CLI-owned authentication, followed by fixtures and live checks only after the pre-turn gate is met. A different native target needs an explicit recorded selection; Grok/Gemini are not activated by this result. Phase 7 portfolio acceptance and holistic review remain later gates.

## Reproduction and observed checks

```sh
python3 scripts/experiments/codex_feasibility.py
```

The opt-in [experiment](../../scripts/experiments/codex_feasibility.py) pins `codex-cli 0.166.0`. It creates an empty synthetic HOME and CODEX_HOME with no login material, a synthetic config and an empty project. It retains no operator environment variables, uses a fixed system PATH and allows only `initialize`, `initialized`, and `config/read` protocol methods. It never sends `thread/start`, `turn/start`, model discovery, a tool call or an approval response. It does not exercise authentication; the existing operator-login prerequisite remains the separate [selection observation](p7-3-codex-selection.md).

Observed on the D041 Apple Silicon macOS host:

| Check | Observed result | What it establishes |
|---|---|---|
| Synthetic user config with model, developer instruction, shell feature and MCP sentinel | All four appear in `config/read` | Default app-server startup loads its user config. No operator settings were inspected. |
| `-c features.shell_tool=false -c 'mcp_servers={}'` | Shell feature reports false; developer instruction and enabled MCP sentinel remain | A scalar override works; an empty table does not erase inherited MCP entries. This recipe is insufficient isolation. |
| `-c mcp_servers.ah_sentinel.enabled=false` | Known sentinel reports disabled | Per-server disabling works; it is not evidence that unknown/inherited future servers are excluded. |
| `app-server --ignore-user-config` | Exit 2, unexpected argument | The installed app-server does not accept this exec flag. |
| `app-server --ignore-rules` | Exit 2, unexpected argument | Exec's rules-isolation flag cannot simply be reused here. |
| Stable generated `ConfigReadResponse` / `ToolsV2` | Only `web_search` in the typed tools properties | This schema does not provide a typed blanket built-in tool-disable control. It does not prove that no other control exists. |
| Stable generated `ThreadStartResponse` | No `tools` property | This response does not expose the complete effective built-in tool inventory needed by the selected preflight approach. No thread was actually started. |
| Preservation | Synthetic config unchanged; project empty; no synthetic `auth.json` | The probe neither changes the project/config fixture nor copies a login store. CLI cache/state writes elsewhere inside the disposable tree are not audited. |

All checks reproduced. Exit 0 means **observations matched**, not that adapter feasibility passed. The final line explicitly reports `GATE NOT PASSED`. An executable/version mismatch, changed observation, malformed/oversized protocol, server request or timeout fails with withheld raw diagnostics. Each RPC and installed command has a ten-second deadline; protocol output has a 2 MiB budget. Every child has a fresh process group, closes stdin, receives a bounded grace period, and has its remaining group killed/reaped. This is an experiment, not production D030 lifecycle acceptance. Generated schema files and parser/version output come from the pinned official executable; file output is not a sandbox for an arbitrary replacement executable.

The MCP sentinel uses `/usr/bin/false`, but no thread is created and it is never launched as a tool. No synthetic hook or inherited operator hook is executed intentionally. Synthetic HOME isolates ordinary user configuration; administrator/MDM requirements may still apply and are not overridden.

## Permission alternatives examined

| Candidate | Disposition |
|---|---|
| Read-only sandbox with approvals denied | Insufficient for no-tool `deny`: permitted sandbox operations may still execute. A permission profile is not a tool inventory. |
| Disable shell, delegation, web, apps and other individual capabilities | Useful building blocks, not a demonstrated complete inventory or deny policy. The shell scalar check verifies configuration reflection only, not runtime tool absence. |
| Empty experimental `dynamicTools` | Adds no caller tools, but does not establish built-in tool absence; the D053 experimental gate is unchanged. |
| `disabledPluginIds` | Installed response schema explicitly says it does not yet filter capabilities (selection evidence); not an isolation guarantee. |
| Harness-owned `PreToolUse` hook | Not accepted as the complete boundary: official documentation excludes hosted tools, permits specialized paths to opt out, and describes some hook failures as continuing the tool call. No hook is installed or trusted by this experiment. |
| Enumerate and disable inherited settings | The known-MCP positive control works, but race-free exclusion across config/rules/instructions/plugins/skills/hooks is not proven. No global settings are rewritten to make a probe pass. |
| `codex exec` isolation flags | Present on exec, rejected on app-server. Exec remains an alternative for a supported-interface reassessment; its JSONL mode has not proven the host permission/preflight requirements. |

## Sources and limits

Independent review also inspected the official `rust-v0.166.0` release source at commit `6ff1e1ca3b30fc8b914720681fcf5fe62e95f856`: [tool assembly](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/tools/spec_plan.rs#L1202-L1205) constructs shell, MCP resource, utility and collaboration tools separately; the [shell feature check](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/tools/spec_plan.rs#L1243-L1251) returns only from shell-tool assembly; [apply_patch registration](https://github.com/openai/codex/blob/6ff1e1ca3b30fc8b914720681fcf5fe62e95f856/codex-rs/core/src/tools/spec_plan.rs#L1426-L1429) depends independently on model capability. This supports the narrow conclusion that disabling shell alone cannot establish a no-tool profile. The installed-binary probe checks configuration reflection, not source/binary equivalence or actual tool exposure. Other supported controls are not exhaustively ruled out.

- [Official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference): documents user/project configuration layering and individual capability controls. Local fixtures establish the exact 0.166.0 merge behavior above.
- [Official app-server documentation](https://learn.chatgpt.com/docs/app-server): documents host approvals and configuration inspection; local schema observations delimit this experiment's preflight approach.
- [Official hooks documentation, tool coverage](https://learn.chatgpt.com/docs/hooks#tool-coverage): hosted tools bypass the local hook path, some specialized paths may opt out, and hooks are not a complete enforcement boundary. [PreToolUse](https://learn.chatgpt.com/docs/hooks#pretooluse) also describes unsupported outputs that fail the hook while continuing the call.

No live model turn, grant, denied-tool trial, role test, coding task, cancellation-under-inference, billing or login-isolation claim is made. Because the pre-turn gate is unmet, downstream runtime/event/usage/allow-once/role/workflow/fallback checks are deliberately not consumed. This closes the bounded discovery increment only; it does not satisfy the P7.3 adapter acceptance card.

## Validation and review

Installed experiment: all observations above passed. Adversarial checks: a silent fake server hit the RPC deadline and group cleanup removed both child and descendant; the method allowlist rejected `turn/start` before writing. Relative Markdown links, Python syntax and whitespace checks pass. No Rust/dependency changes, so Rust/offline runtime suites are not rerun. Independent permission-boundary review found no blocking probe defect and one Low evidence gap (pinned tool-assembly source), addressed above. Required Grok PR review is recorded in PROJECT.md at closeout.


Grok [PR #68](https://github.com/awesomejt/agent-harness/pull/68) review under the operator's account: 0 blockers, 1 concern, 1 nit. The concern identified traceback leakage on valid JSON with non-object protocol/result/config shapes; explicit protocol/result object checks and sanitized type-error handling now reject those forms. The committed fake-executable regression suite covers 11 malformed shapes through the public probe CLI, with exact sanitized stderr and no sentinel disclosure. The nit requested a code comment clarifying that installed-command file output is checked after exit rather than capped while running; added. The installed probe and link/whitespace checks pass again. No critical/high finding and no re-review requested. Completion is effective on merge; the production gate remains unpassed.
