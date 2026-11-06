# P7.2 evidence — Claude runtime launch, preflight and deny-profile single runs

Task: [P7.2](../../tasks/07-native-adapters.md#p7-2), first narrow PR. Decision: [D048](../../DECISIONS.md#2026-11-06--d048-claude-runtime-launch-preflight-and-deny-profile-single-runs). Authentication: the operator's existing official CLI login ([D047](../../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login)). Date: 2026-11-06. Platform: macOS arm64 (D041), Claude Code **2.1.314** from the official native install, `ah` built from this branch.

This PR covers runtime selection, launch and isolation, the pre-submission preflight, event and terminal mapping, project instructions and cancellation for `deny`. It does not cover trusted permissions and the host permission path, named agents, effort, sequences/Ralph or the local-first fallback target; those are later P7.2 PRs, and each refuses with exit 2 until then.

## Interface probes

Run from disposable git directories with a cleared environment (`HOME`, `PATH`, `USER` only) and the D048 flags. Session IDs, paths, account data and costs are not recorded.

| Probe | Observed |
|---|---|
| Stream-json input, no stdin record | No output at all: `system/init` is emitted only after the first user message, so it cannot be the pre-submission check D046 proposed. |
| `initialize` control request | Answered before any prompt with `claude_code_version`, `current_permission_mode` (`default`), `commands` (empty under `--disable-slash-commands`), `output_style`, built-in agent names, models and **account** details. The adapter checks the first four and discards the rest unread. |
| `get_settings` | `sources: []`, `effective: {}` with empty `--setting-sources`; `applied.model` is the resolved model (`sonnet` → `claude-sonnet-5-5`). Admin-managed settings would appear as a source. |
| `mcp_status` | `mcpServers: []` with `--strict-mcp-config`. |
| `get_context_usage` | Used categories `system_prompt` and `messages` only; `memoryFiles`, `mcpTools` and `agents` empty. With `--tools=Read` a `system_tools` category appears, so the check distinguishes an empty tool set before the prompt. |
| Unsupported subtypes (`get_tools`, `supported_commands`) | Error control responses; not used. |
| Turn | `system/init` (tools `[]`, MCP `[]`, slash commands `[]`, skills `[]`, `apiKeySource: "none"`, built-in plugins only), `assistant`, `rate_limit_event`, `result` (`subtype: "success"`, `is_error: false`, `stop_reason: "end_turn"`). The process stays until stdin closes. |
| `interrupt` during a long answer | `control_response` success, then `result` with `subtype: "error_during_execution"`, `is_error: true`, `terminal_reason: "aborted_streaming"`. |
| `AGENTS.md` and `CLAUDE.md` in the project | With `--safe-mode` neither is loaded on its own (the built-in `cc-plugin-agents-md` plugin does not load it); `--append-system-prompt-file=AGENTS.md` loads `AGENTS.md`. A `CLAUDE.md` marker never appeared. |
| `--name=value` option forms | Accepted for every valued flag, including empty `--tools=` and `--setting-sources=`. |

## Fixture and regression results

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings` and `cargo test --locked` pass, including five new `claude` validator tests and two new config tests (Claude target resolution without any key lookup; rejected keys, fallback and groups).
- `python3 scripts/tests/claude.py`: **33 cases pass** against a fake `claude` that records argv, environment names and stdin. They cover the exact launch flags, a cleared environment (poisoned `ANTHROPIC_*`/`CLAUDE_*` values never cross or print), the preflight order strictly before the single user message, every preflight refusal (version, permission mode, commands, control error, managed settings, MCP, tool context, memory) exiting 2 with nothing submitted, `system/init` mismatches (tools, model, API key source, a turn record before init), a tool call or host request under deny, a malformed record and EOF after submission (all exit 4), an error result (exit 1), interrupt cancellation (exit 3) and an ignored interrupt (exit 4), JSONL fields, preview, and refusals that launch nothing (trusted, agent, local-first, slash prompt, missing runtime, sequence, Ralph run and resume).
- `python3 scripts/tests/offline.py`: 25 of 26 suites passed on the first run. `modes.py` had used `target: "claude"` as its unsupported-target example; it now uses `codex` and adds a local-first `claude` target case (refused). After that change `modes.py` (166 cases) and `claude.py` pass, and the other 24 suites passed unchanged.

## Live runs (operator's existing login)

Disposable git project with `ah.json` `{"version":1,"mode":"cloud-only","native":{"target":"claude","model":"sonnet"}}`, an `AGENTS.md` asking every reply to end with a marker line, and a `CLAUDE.md` asking for a different marker.

| Run | Result |
|---|---|
| `ah single "What is 6 times 7? ..."` | Exit 0 in about 2 s; response `42` plus the `AGENTS.md` marker; no `CLAUDE.md` marker. Preflight took about 0.4 s. Human progress showed session, activity, `rate limit status=allowed`, `backend terminal=end_turn` and confirmed cleanup with 0 stderr bytes. |
| `... --output jsonl` asking for the marker line | Exit 0 in 5.6 s; records `run.started`, `attempt.started` (`runtime: "claude"`, `2.1.314`, `model: "sonnet"`), `attempt.prompt_submitted`, `attempt.session`, `attempt.activity`, `attempt.usage` (`claude-stream-json-result`, USD), `attempt.backend_stop` (`end_turn`), `attempt.cleanup`, `result` (`succeeded`, response the marker). |
| Deny constraint: "Create a file named pwned.txt ... then run ls" | Exit 0; `tool_events: 0`, `grants: 0`, no protocol violation. With no tool offered the model wrote imitation tool-call text as its answer; nothing ran: no `pwned.txt`, `git status` clean apart from the run's own output files. A deny response can look like tool use; it is text. |
| Long essay with SIGINT after 6 s (`--model haiku`, JSONL) | Exit 3, `outcome: cancelled`, `backend_stop: cancelled`, `prompt_submitted: true`, cleanup confirmed. Progress showed `signal; sending interrupt` then `backend terminal=cancelled`. |
| `--permissions trusted` | Exit 2 before launch: `trusted permissions are not yet supported on the Claude runtime; use deny`. |
| `--preview` | Exit 0; route `native Claude Code on the operator's existing official CLI login`, discovered runtime `2.1.314` (unverified), credentials `official CLI login (operator prerequisite; never read, copied or proxied by the harness)`. |

## Limits

- Deny only: the runtime cannot read, edit or run anything in this increment, so it is not yet a coding run. The live project task with edits and the enforced constrained-role evidence the card requires come with the trusted and named-agent PRs.
- `system/init` is checked after submission because the CLI emits it only after the first user message; a mismatch there is uncertain (exit 4), never retried. The control preflight is the pre-submission proof.
- The harness discards the CLI's stderr and error text, so a login, model-access or rate-limit failure shows only exit 1 and `backend terminal=failure`; running `claude` directly shows the cause.
- `total_cost_usd` is the CLI's own report. On a plan login it is not a charge, and the harness does not interpret plan limits or credits.
- Only 2.1.314 on macOS arm64 is accepted; another version refuses before the prompt until a decision moves the pin.
