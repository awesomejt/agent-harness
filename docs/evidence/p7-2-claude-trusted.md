# P7.2 evidence — Claude trusted permissions through the host prompt path

Task: [P7.2](../../tasks/07-native-adapters.md#p7-2), second narrow PR. Decision: [D049](../../DECISIONS.md#2026-11-06--d049-claude-trusted-permissions-through-the-host-prompt-path), building on [D048](../../DECISIONS.md#2026-11-06--d048-claude-runtime-launch-preflight-and-deny-profile-single-runs). Authentication: the operator's existing official CLI login ([D047](../../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login)). Date: 2026-11-06. Platform: macOS arm64 (D041), Claude Code **2.1.314**, `ah` built from this branch.

This PR adds `--permissions trusted` for Claude single runs. Named agents, effort, sequences/Ralph and the local-first fallback target are still refused with exit 2 before launch.

## Interface probes

Run from disposable git directories with a cleared environment, the D048 isolation flags and `--model=haiku`, answering prompts from a probe script. Session IDs, account data and costs are not recorded.

| Probe | Observed |
|---|---|
| `--permission-prompts=host`, `--tools=Bash,Edit,Glob,Grep,Read,Write`, no prompt tool | No `can_use_tool` request reached the host. Edit, Bash and an outside-project Read each produced `system/permission_denied` and an error tool result; the turn still ended `end_turn`. The flag alone registers no handler. |
| Adding `--permission-prompt-tool=stdio` | Each prompt arrives as a `control_request` with `subtype: "can_use_tool"`, `tool_name`, the complete `input`, `tool_use_id` and `permission_suggestions` (`setMode` → `acceptEdits` for edits; `addRules` allow rules for Bash and reads). The matching assistant `tool_use` block, with the same ID, name and input, always came first. |
| Allow response `{"behavior":"allow","updatedInput":<input>}` | The call runs, and the result is marked as a temporary user decision. Edit fixed the file; Bash ran; the outside read returned content. |
| Deny response `{"behavior":"deny","message":…}` | The call does not run; an error tool result carries the message; `result.permission_denials` lists it. The model stopped as asked. |
| What prompts in `default` mode | Project `Read`, `Glob` and `Grep`, plus `ls`, `git status`, `sleep` and `echo`, ran without a prompt. `Write`, `Edit`, a `python3 -c` command and a read outside the project prompted. `--permission-mode=manual` behaved the same, and `system/init` still reported `default`. |
| `get_context_usage` with tools | Used categories `system_prompt`, `system_tools` and `messages`; `agents` empty. |
| `system/init` with tools | `tools` lists exactly the six in alphabetical order; built-in agent names are still listed (no Agent tool is offered). |
| Long foreground `sleep 47; echo finished` | Without `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS`, Claude Code blocked the foreground sleep (`<tool_use_error>Blocked: sleep 47 …`), the model reran it with `run_in_background: true`, and the turn ended `end_turn` saying it would report later. With `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1`, the command ran in the foreground and the turn waited for `finished`. |
| Bash process | `/bin/zsh -c source ~/.claude/shell-snapshots/snapshot-zsh-….sh … && eval '<command>'`. The inspected snapshot exports only `PATH`, plus aliases and functions (names checked, values not recorded). 2.1.314 lists no documented switch for it. |

## Fixture and regression results

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings` and `cargo test --locked` pass. Unit tests now cover the exact trusted tool set in `system/init` (extra, missing, duplicate and non-string entries refuse), `system_tools` context only under trusted, tool-call and tool-result classification (subagent records, `server_tool_use`, unknown blocks, malformed calls and hook requests are unsupported), and the grant decision and response shape (allow echoes the input with no `updatedPermissions`).
- `python3 scripts/tests/claude.py`: **44 cases pass**; 33 were in place before this PR. The fake now announces calls, sends `can_use_tool` prompts, waits for the harness's answer and writes a file only on a grant. New trusted cases:
  - exact launch flags (`--permission-prompts=host`, `--permission-prompt-tool=stdio`, the six tools), and `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` even when the operator sets `0`;
  - an exact prompt granted once, the file written, `requests 1; grants 1; tool events 4`, with JSONL counters;
  - denials: a prompted input that differs from the announced call, a prompt for an unannounced call, a second prompt for the same call, and a prompt after the harness's interrupt (deadline cancellation, exit 3). No file is written for any of them.
  - protocol violations (exit 4, interrupt sent, nothing written): a call outside the set, a background Bash call, a subagent record, a result with no announced call, a hook control request, and a `system/init` listing an extra tool.
  The earlier `trusted` refusal case is now a success case. The deny cases now report `tool call under deny` and `host request under deny`.
- `python3 scripts/tests/offline.py`: **26/26** suites pass.

## Live runs (operator's existing login)

| Run | Result |
|---|---|
| Disposable git project: `calc.py` with two bugs, `test_calc.py`, `AGENTS.md` asking for a marker line, `--permissions trusted`, model `sonnet`: "Run the tests, fix the bugs in calc.py, rerun until they pass; do not modify test_calc.py" | Exit 0 in 10.2 s. 4 host prompts, 4 grants, 8 tool events, cleanup confirmed, no protocol violation. The response explained both fixes and ended with the `AGENTS.md` marker. Afterwards `git status` showed only `calc.py` modified (plus `__pycache__`), `test_calc.py` was unchanged, and an independent `python3 -m unittest test_calc.py` passed. |
| First background attempt (before the environment fix): "Run … and wait for it: `sleep 47; echo finished`" | Exit 0 with 0 prompts. The response said the command was running in the background, and process-group cleanup killed it (no `sleep 47` left). This run led to the `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS=1` setting and the background-call violation. |
| Same prompt in the foreground, JSONL, SIGINT after 14 s (`haiku`) | `sleep 47` was running under Claude Code's shell at the signal. Exit 3, `outcome: cancelled`, `backend_stop: cancelled`, `prompt_submitted: true`, cleanup confirmed; no `sleep 47` process remained. Claude Code allowed the command itself, so there were 0 prompts and 2 tool events. |
| `--permissions trusted --preview` | Exit 0; `permissions: trusted: read/write/shell with host privileges; no OS sandbox (invocation)`. |
| `--permissions trusted --agent reviewer` | Exit 2 before launch (named agents are a later PR). |

## Limits

- Host privileges, no OS sandbox. Writes and shell commands outside the project are granted under `trusted`, as OpenCode's trusted profile grants external-directory requests.
- Claude Code decides which calls prompt. Project-local reads and searches, and commands it classifies as read-only, run without a host prompt; the harness still sees and checks every announced call against the set. Grant counters cover prompts only.
- `Bash` runs through the operator's login shell snapshot (`PATH`, aliases, functions) under the real `HOME`, unlike OpenCode's private HOME. 2.1.314 documents no switch to turn this off.
- A prompt whose input differs from the announced call is denied, not reconciled. None differed in the live runs.
- The constrained-role evidence the card requires comes with the named-agent PR.
