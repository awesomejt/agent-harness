# P7.3 evidence — Codex selection and integration baseline

2026-11-06. Task: [P7.3](../../tasks/07-native-adapters.md#p7-3). Decision: [D053](../../DECISIONS.md#2026-11-06--d053-select-codex-and-its-official-stdio-app-server-for-p73). Baseline: `9249775` (merged Claude acceptance PR #66). This is a selection/discovery increment, not a completed adapter. No Rust source, dependency, configuration schema, artifact or production behavior changes.

## Selection and alternatives

The operator requested the next available task for this platform. Codex is already used to work on this repository, is installed and logged in on the supported Apple Silicon macOS platform, and was identified as the natural next candidate in the [P7.1 evidence](p7-1-claude-selection.md). Claude's accepted P7.2 work is merged; no other implementation PR was open at selection. Only Codex is activated. Grok and Gemini remain deferred; P7.6 portfolio acceptance and P7.7 holistic review still require all four adapters.

| Interface | Disposition |
|---|---|
| Official `codex app-server --listen stdio://` | Selected for the feasibility experiment. Bidirectional protocol permits a host approval response and pre-turn configuration inspection. Harness keeps subprocess, environment, deadline and cleanup ownership. |
| Official `codex exec --json` | Not selected for production integration: the installed help exposes JSONL and useful isolation switches, but not a bidirectional host approval protocol. It remains a possible comparison tool. |
| Third-party ACP bridge or embedded SDK | Not selected; no need to add another runtime/dependency to discover the official protocol. |
| Shared daemon, WebSocket/remote control, resume/fork | Outside this increment. New harness attempts need fresh isolated execution, not shared interactive state. |
| Raw Responses requests or LiteLLM subscription routing | Excluded by D002/D010/D047. The official native CLI owns authentication and the coding loop. |

## Official sources checked

- [App-server](https://learn.chatgpt.com/docs/app-server): documented stdio JSONL transport, handshake, stable/experimental API distinction and host approval flow. These establish interface suitability, not our permission guarantees.
- [Authentication](https://learn.chatgpt.com/docs/auth): ChatGPT sign-in supports subscription access through local Codex clients; API-key login is a separate usage-based path. D047 already establishes the operator-owned official-login boundary. The harness does not perform login or handle credentials.

The installed binary's generated schemas are the version-specific evidence below. Current documentation can describe fields not supported by 0.166.0; implementation must verify against that binary rather than assume documentation examples are compatible.

## Installed observations and reproduction

Commands run from this checkout, with schema output under disposable `/tmp` directories:

```sh
codex --version
codex --help
codex exec --help
codex app-server --help
codex login status
codex app-server generate-json-schema --out /tmp/ah-codex-schema
codex app-server generate-json-schema --experimental --out /tmp/ah-codex-schema-experimental
```

Observed version: `codex-cli 0.166.0`, executable `~/.local/bin/codex`. Login status: logged in using ChatGPT. No credential file, token, account identity or secret was read or recorded. The executable version is a candidate compatibility baseline; production support/pinning is not yet implemented.

Installed `exec` help advertises `--ephemeral`, `--ignore-user-config` (auth still uses `CODEX_HOME`) and `--ignore-rules`. Those are **exec** flags: the installed **app-server** help does not advertise the latter two. Do not transfer them between subcommands or assume their isolation behavior exists on app-server.

Installed stable schema observations:

| Surface | Observed fields / consequence |
|---|---|
| `ThreadStartParams` | `model`, `modelProvider`, `cwd`, `approvalPolicy`, `approvalsReviewer`, `sandbox`, `config`, `baseInstructions`, `developerInstructions`, `ephemeral`. These are candidates for mapping, not selected values or proven isolation. |
| `ThreadStartResponse` | Required model/provider, cwd, approval policy/reviewer, sandbox and thread. Optional reasoning effort and instruction sources. No complete effective built-in tool inventory. |
| `TurnStartParams` | Required `threadId` and `input`; optional model, effort, approval and sandbox overrides. Decide exact model/effort mapping only after the capability gate. |
| `ThreadStartResponse.disabledPluginIds` | Description explicitly says it does not yet filter plugin capabilities. It cannot be used as an isolation guarantee. |
| Experimental `ThreadStartParams.dynamicTools` | Absent from stable output. An empty list of caller-added tools cannot establish absence of built-in tools. No experimental opt-in was used in the probe. |

SHA-256 of the stable generated files, including generated formatting:

```text
v2/ThreadStartParams.json   e9c6d3cc18d049bfbc0249add3808fb8e5a27e1a0b5a423767aafbc3859a9428
v2/ThreadStartResponse.json c655daa1616548f6b3b0960acee9dcfefa8aba5965ec4fc636c84ee840a8626a
v2/TurnStartParams.json     49e53282f327c25e7b39d97afacd038ef10ad5c4fb0431608b354d3a7bf6bcea
```

## Non-inference protocol probe

One app-server child was launched in an empty temporary directory with a cleared environment containing only the operator's `HOME`, `PATH`, `TMPDIR`, `USER`, `LOGNAME` when present, plus `RUST_LOG=off`. Real HOME retained CLI-owned login/config as D047 permits; this discovery probe **does not claim configuration isolation**. The parent used a fresh process group, a 45-second outer deadline, captured/discarded stderr and a final group kill for any remaining descendants. Only the following protocol messages were sent, in order (one JSON object per line, waiting for each request's response):

```json
{"id":1,"method":"initialize","params":{"clientInfo":{"name":"agent_harness_selection_probe","title":"agent-harness selection probe","version":"0.1.0"}}}
{"method":"initialized","params":{}}
{"id":2,"method":"model/list","params":{"limit":2,"includeHidden":false}}
```

Observed:

- Initialization succeeded; result keys were `codexHome`, `platformFamily`, `platformOs`, `userAgent`. Values were not retained.
- `model/list` returned two entries and a non-null pagination cursor. The returned `gpt-6.1-sol` and `gpt-6-astra` entries each advertised `low`, `medium`, `high`, `xhigh`, `max`, `ultra` efforts. This is a partial catalog observation, not a default-model choice or a guarantee of model access. The harness's canonical effort grammar is unchanged.
- Closing stdin ended the child with exit 0; wrapper exit 0, zero stderr bytes. Final process-group cleanup ran.
- No `thread/start` or `turn/start`, prompt, tool request, grant or model inference occurred. No project/config file was written by the probe; CLI-internal cache activity was not audited. No coding, role-enforcement, cancellation or billing claim follows from this probe.

## Consuming gate and focused implementation order

The next P7.3 increment is a **bounded isolation/permission feasibility experiment**, before production configuration or launch support. It must answer:

1. Can app-server retain official login while excluding user/project configuration, exec rules, instruction discovery outside the D040 scope, skills, plugins, MCP, hooks, delegation, background work and model/endpoint overrides? Inspect effective configuration and capabilities before a model turn; do not modify the operator's global settings or copy credentials into a private home.
2. Can the harness's no-tool `deny` profile be enforced before submission? `read-only` plus `approvalPolicy: never` still permits sandbox-allowed tools. Denying server approval requests alone is insufficient. Find a supported enforceable control and verify it, or refuse the runtime; do not rely on a prompt to avoid tools or discover violations only after execution.
3. For any later `trusted` or named role, which operations are automatic and which require host approval? Can the role's exact read/search/edit/execute intersection and outside-project ceiling be enforced, and can grants be request-bound allow-once without session-wide approval? If unsupported, refuse the profile/role before submission.
4. Which stable events correlate tool announcements, approval requests and results? Verify unknown/malformed/duplicate request handling, terminal statuses, submission boundary, usage, cooperative cancellation and process-group cleanup with fixtures and then live evidence after the permission gate is met.

After feasibility passes: narrow launch/preflight/events/deny PR; trusted permissions; canonical role/model/effort mapping; sequences/Ralph; eligible pre-submission fallback; final live coding and constrained-role acceptance. Combine only tightly coupled proven work. Keep P7.3 unchecked through final acceptance. A failed feasibility result is evidence for an explicit supported-interface reassessment, not permission to weaken constraints. P7.7 is a later portfolio gate, not an immediate platform switch. The next experiment can continue on this Codex platform.

## Validation

Selection checks: installed help/version/login, stable and experimental schema generation/comparison, non-inference handshake/model-list with bounded cleanup, relative Markdown links and whitespace checks. No production code changed, so Rust/offline runtime suites are not rerun for this documentation increment. Required Grok review and merge remain part of the Git workflow; PROJECT.md records the final PR outcome.
