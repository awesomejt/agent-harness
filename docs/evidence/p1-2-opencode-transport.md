# P1.2 — OpenCode ACP preflight and external blocker

Date: 2026-11-01 (America/Denver). Task: [P1.2](../../tasks/01-integration.md#p1-2). Baseline: `1712825` (P1.6 merged via PR #7). Tested platform: Darwin arm64. **Historical partial evidence from PR #8.** The user subsequently supplied a different LiteLLM host; [live continuation evidence](p1-2-live-acp.md) supersedes the blocker for that host and records the later P1.2 result. The observations below remain the original localhost/no-prompt record.

## Repeatable no-prompt connectivity probe

```bash
python3 scripts/experiments/acp_preflight.py --opencode /opt/homebrew/bin/opencode
```

The standard-library Python probe is disposable experiment tooling, not a Python harness implementation, dependency selection, runtime adapter or new `ah` command. Tested with Python 3.14.7 and the installed Homebrew OpenCode 1.18.30 (`1.18.30_2` package). No install or upgrade was required. The normal shell PATH did not expose OpenCode; the explicit path works.

The probe creates a temporary project and HOME/XDG directories, starts with a minimal environment rather than inheriting authentication or OpenCode overrides, disables model-catalog fetching/default plugins/autoupdate, and launches with `--pure`. Project configuration denies every permission, enables only a synthetic `harness-preflight` provider, disables sharing, and supplies no MCP servers/plugins. The synthetic endpoint is `http://127.0.0.1:9/v1`; its placeholder key is `unused`. No real credentials or model endpoint are supplied. Resolved configuration is checked before ACP startup; the session's reported current model is checked separately.

Observed sequence:

1. `opencode --version` → `1.18.30`.
2. `opencode debug config --pure` → expected deny-all permission, sole synthetic enabled provider/model, empty MCP/plugins; the helper model, sharing and autoupdate settings are also checked.
3. `opencode acp --pure --cwd <temporary-project>` → JSON-RPC on stdio.
4. `initialize` with protocol version 1, filesystem read/write capabilities false, terminal capability false → protocol 1; agent `OpenCode` version `1.18.30`; capabilities include session load/close/fork/list/resume, HTTP/SSE MCP, embedded context and images.
5. `session/new` with absolute disposable cwd and `mcpServers: []` → session identity and `configOptions` with model `harness-preflight/unavailable`, mode `build`. This installed version reports the model through `configOptions`, not a `models` field.
6. No `session/prompt` is sent. Unexpected client requests cause refusal and shutdown. Request deadlines are 30 seconds. The probe signals its process group and reaps the direct child with a bounded kill escalation; this is not proof of descendant cleanup.

No runtime/model prompt, coding edit, permission grant, native subscription call or structured-native comparison occurred. ACP connectivity works; live coding feasibility is unproven.

## LiteLLM observations and blocker

Existing endpoint: `http://127.0.0.1:4000`. Installed LiteLLM CLI environment reports package `1.102.1`; the version of the already running server was not established.

| Read-only request | Observed result |
|---|---|
| `/health/liveliness`, no auth | HTTP 200, alive |
| `/health/readiness`, no auth | HTTP 200, status healthy, database not connected |
| `/v1/models`, bearer from `LITELLM_API_KEY` | HTTP 400, error type `no_db_connection` |
| `/v1/models`, bearer from `LITELLM_MASTER_KEY` | HTTP 400, error type `no_db_connection` |
| `/v1/models`, no auth | HTTP 500, error type `internal_server_error` |
| `/model/info`, configured API key / no auth | HTTP 400 `no_db_connection` / HTTP 500 `internal_server_error` |

Only status and error type were recorded; credential values and raw proxy errors were not printed or committed. Health success does not establish a usable model alias. These observations diagnose an external prerequisite failure, not its root cause. No existing alias was successfully discovered, so no live prompt was attempted. Service management is outside harness ownership ([D016](../../DECISIONS.md#2026-11-01--d016-clarify-litellm-configuration-and-service-ownership)); the proxy, its database, credentials and global OpenCode settings were not changed.

Next validation: the proxy owner restores valid authenticated model discovery and identifies an existing alias. Repeat `/v1/models` using the established authorization, record the alias and server version, then finish permission-enforcement preflight before any live prompt. No speculative service install/restart/configuration is proposed by this evidence.

## Permission mapping inspection and remaining gates

Inspected upstream sources at the installed `v1.18.30` tag: [ACP service](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/acp/service.ts), [permission handler](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/acp/permission.ts), and [configuration loader](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/config/config.ts).

The permission handler advertises `once`/`allow_once`, `always`/`allow_always`, and `reject`/`reject_once`; cancelled/unselected responses map to rejection. Configuration loading merges global/custom/project sources, which is why this probe isolates HOME/XDG and inherited overrides. Source inspection informs the future adapter; it does not prove installed runtime tool enforcement. No D020 grant handling is implemented by this no-prompt probe.

Before live work, still verify fully described attempt/request identity, actual option/cancellation mapping, effective permissions for built-in and external tools, helper/subagent model routing and response-delivery failure behavior. Default-deny tools or unavailable callbacks must never become implicit approvals. P1.3 retains live denied-action and cancellation/descendant-cleanup evidence. P1.2 still owes a repeatable existing-LiteLLM-alias prompt, streamed events and terminal result in a disposable project. P1.4 and all consuming tasks remain gated; no transport/dependency decision or phase completion is claimed.

## Validation

The final no-prompt probe passed on the installed runtime. Existing Rust formatting, Clippy (`--all-targets --locked -- -D warnings`) and all 11 tests passed. No Rust dependencies, lockfile, CLI interface or runtime behavior changed.

## PR review

[Grok review on PR #8](https://github.com/awesomejt/agent-harness/pull/8): one review, 0 blockers, 0 concerns, 4 nits. All addressed: verify helper-model/share/autoupdate settings; report only stderr byte count on failure; tolerate blank lines and describe malformed JSON/non-object messages; handle the kill escalation race and preserve the original error if final reaping times out. The final live no-prompt probe passed again. Help and missing-executable checks pass (the latter refuses before launch with exit 2). No re-review required under docs/GIT_WORKFLOW.md. This closes the preflight PR only; P1.2 live acceptance remains open.
