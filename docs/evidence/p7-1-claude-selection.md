# P7.1 evidence — Claude native adapter selection

Task: [P7.1](../../tasks/07-native-adapters.md#p7-1). Decision: [D046](../../DECISIONS.md#2026-11-05--d046-select-claude-code-as-the-first-additional-native-adapter). Documentation only: no source, CLI, dependency or artifact change. One tool-free probe turn was run (below) to record the interface; it is not adapter evidence.

## Why Claude first

- **Real use.** The operator already drives this project with Claude Code (2.1.314) as an everyday coding agent, alongside Codex and Grok for reviews. Claude is the native CLI with the most use in this repository, so its adapter is the most likely to be exercised after it ships.
- **Interface fit.** The official CLI has a documented non-interactive mode (`-p`) with line-delimited JSON output and input, explicit tool lists, permission modes, a host-answered permission path, model and effort flags, and per-run session persistence control. That covers the progress/terminal, permission, model/effort and isolation questions the card requires, without a third-party wrapper.
- **Others stay deferred.** Codex (`codex-cli 0.166.0`) and Grok (`grok 1.0.70`) are installed; Gemini and Pi are not. Codex is the natural next candidate once the Claude adapter is reviewed and used; starting it (P7.3) needs a later recorded selection, one adapter at a time (D017/D046). No ordering is implied.

## Installed baseline (2026-11-05)

| Item | Observed |
|---|---|
| Executable | `claude` at `~/.local/bin/claude` (official native install) |
| Version | `2.1.314 (Claude Code)` from `claude --version` |
| Platform | macOS arm64, the D041 supported platform |
| Authentication seen | CLI-owned login; `apiKeySource: "none"` in the init event, so no API key was used. The harness read no credential. |

## Interface options considered

| Option | Outcome |
|---|---|
| Official `claude -p` with `--output-format stream-json` (and `--input-format stream-json` when the host must answer permission requests) | **Selected.** First-party executable and documented mode. The harness keeps process, environment, deadline and cleanup ownership, as D021/D023 require for OpenCode. |
| A third-party ACP bridge over the Agent SDK | Not selected. It would reuse our ACP client, but adds an unpinned Node package between the harness and the official CLI, and it is built on the Agent SDK, whose plan-login terms are narrower (below). |
| Embedding the Agent SDK library | Not selected. The project is Rust, the SDK is TypeScript/Python, and it is a product-building surface the terms steer to API keys. |
| Text or single-JSON output (`--output-format text|json`) | Not selected. No progress events, and nothing to verify effective tools/model before the turn. |
| Routing Claude through LiteLLM | Excluded by D001: subscription traffic never crosses LiteLLM. |

## Probe (one tool-free turn)

Run from an empty scratch git directory, stdin closed:

```
claude -p "Reply with exactly: ok" --output-format stream-json --verbose \
  --tools "" --safe-mode --strict-mcp-config --no-session-persistence \
  --permission-prompts none --model sonnet
```

Exit 0, four JSON lines: `system/init`, `rate_limit_event`, `assistant`, `result`. Session identifiers, paths and account data are not recorded here.

- **`system/init`** carried `claude_code_version` (`2.1.314`), `model` (`claude-sonnet-5-5`, the alias resolved), `permissionMode` (`default`), `tools` (`[]`), `mcp_servers` (`[]`), `apiKeySource`, `cwd`, `agents`, `skills`, `slash_commands`, `plugins` and `output_style`. This event is the candidate effective-configuration check before the first prompt: it reports the resolved model and the exact tool set.
- **`--safe-mode` is not a clean room.** Built-in skills, slash commands, subagent names and built-in plugins were still listed. With `tools` empty none could act, but P7.2 must show which flags remove or neutralise them when `Read`/`Edit`/`Bash` are enabled (for example the Task/Agent tool and Skill tool must stay off).
- **`result`** carried `subtype: "success"`, `is_error: false`, `stop_reason: "end_turn"`, `result` (final text), `num_turns`, `usage`, `modelUsage`, `total_cost_usd` and `permission_denials`. Cost is a backend report, like OpenCode `usage_update` (D039), not billing; on a plan login it does not represent a charge.
- **`rate_limit_event`** appears before the turn; P7.2 decides whether to surface it as progress.

## Authentication and terms (checked 2026-11-05)

Sources: [Claude Code legal and compliance](https://code.claude.com/docs/en/legal-and-compliance), [authentication](https://code.claude.com/docs/en/authentication), [non-interactive mode](https://code.claude.com/docs/en/headless), [Agent SDK with your Claude plan](https://support.claude.com/en/articles/15036540-use-the-claude-agent-sdk-with-your-claude-plan), [logging in](https://support.claude.com/en/articles/13189465-log-in-to-your-claude-account).

- Subscription (OAuth) login is intended for the plan purchaser's own use. Third-party developers may not offer Claude.ai login in their own products or route requests through Free/Pro/Max/Ultra credentials on behalf of their users. Tools that misrepresent their identity or route third-party traffic against plan limits are prohibited.
- Developers building products, including on the Agent SDK, are directed to API keys (Claude Console or a supported cloud provider). Anthropic may let subscribers use some third-party tools but bill them to usage credits instead of plan limits.
- `claude -p` signed in with a plan draws from that plan's limits. `--bare` never reads the plan login or keychain; it authenticates only with `ANTHROPIC_API_KEY` or an `apiKeyHelper`.
- The published pages do not explicitly address a personal orchestration script that launches the official CLI on the operator's own login. D046 therefore permits that path only as the operator's own individual use, never on behalf of other users, with no credential handling by the harness, and records API-key authentication as the supported alternative. P7.2 rechecks these pages before advertising support.

## Open questions for P7.2

Recorded in D046 with their owning PR. In short: runtime selection syntax and config shape; isolation flags versus a private HOME given plan login; the trusted-profile tool set and how built-in agents/skills are kept off; exact allow-once grants through the host permission path; event-to-progress/terminal mapping; model/effort grammar; named-agent mapping; cancellation and process-tree cleanup; project-instruction loading (D040); version pinning.
