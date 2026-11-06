# P7.2 evidence — Claude named roles and effort

Task: [P7.2](../../tasks/07-native-adapters.md#p7-2), third narrow PR. Decision: [D050](../../DECISIONS.md#2026-11-06--d050-claude-named-roles-as-a-narrowed-tool-set-appended-body-and-verified-effort). It builds on [D048](../../DECISIONS.md#2026-11-06--d048-claude-runtime-launch-preflight-and-deny-profile-single-runs) (launch, preflight, deny) and [D049](../../DECISIONS.md#2026-11-06--d049-claude-trusted-permissions-through-the-host-prompt-path) (trusted host prompts). Authentication: the operator's existing official CLI login ([D047](../../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login)). Date: 2026-11-06. Platform: macOS arm64 (D041), Claude Code **2.1.314**, `ah` built from this branch.

This PR adds `ah single --agent NAME` and canonical `effort` on the Claude runtime. Local-first with a `claude` target, sequences and Ralph still exit 2 before launch.

## Interface probes

Run from a disposable git directory with a cleared environment, the D048 isolation flags, `--tools=` and `--model=haiku` unless noted. Rows marked *control only* send no prompt. Session IDs, account data and costs are not recorded.

| Probe | Observed |
|---|---|
| `--effort=high`, `get_settings` (control only) | `applied.effort: "high"`; `sources` and `effective` stay empty. |
| No `--effort`, then each of `low`, `medium`, `max`, `xhigh` (control only) | No flag gives `medium` on haiku, the model default. Each explicit level is reported back as given. `max` is also reported on `sonnet` and `opus`. |
| `--append-system-prompt` with `--append-system-prompt-file` (control only) | Accepted together. `get_context_usage` reports a larger `system_prompt` category and still no `agents`, memory files or MCP tools. |
| Same pair, one turn: "quote every system-prompt line containing MARKER" | Both texts reached the model: the `AGENTS.md` file line first, then the inline line. |
| Two `--append-system-prompt-file` flags, same turn | Only the second file's line was quoted. The last file flag wins, so the role body cannot be a second file. |
| `get_system_prompt`, `get_agent`, `get_effort` control requests | `Unsupported control request subtype`. No control request returns the system prompt. |
| `system/init` with an appended prompt | Same fields as D048/D049; `agents` lists only the built-ins; `per_turn_effort_active: true` with or without `--effort`. |

## Fixture and regression results

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings` and `cargo test --locked` pass. New unit tests cover the tool intersection for each invocation and ceiling (deny offers none; full, read-only `[search, read]`, `[edit]` and empty roles), the grant rule, the `--permission-prompts`, `--tools`, `--effort` and `--append-system-prompt` arguments and their order after the `AGENTS.md` file, effort checks in `get_settings`, and the 128 KiB body bound at and above the limit.
- `python3 scripts/tests/claude.py`: **55 cases pass** (46 before this PR). The fake now echoes `--effort` in `get_settings`. The earlier `--agent` refusal case is replaced by these cases:
  - `deny` invocation of the sample reviewer: deny launch flags plus the body, success, `effort model default; permissions deny`.
  - `trusted` sample reviewer (read-only ceiling): `--tools=Glob,Grep,Read`; a project read runs unprompted; an outside-project read prompt is denied; `requests 1; grants 0; tool events 4`.
  - The same reviewer calling `Write`: protocol violation, exit 4, interrupt sent, nothing written.
  - `trusted` sample coder: the full D049 set plus the body; the prompted write is granted once.
  - A trusted `[edit, read]` role at `effort: high`: `--tools=Edit,Read,Write --effort=high`, granted write, `effort high` reported. If the runtime reports another effort, it exits 2 with no prompt.
  - A trusted role with no tools launches as `deny` (`--tools=`, `--permission-prompts=none`), and its preview reports `tools []; host prompts denied` (Grok PR #63).
  - A body over 128 KiB exits 2 without launching.
  - Preview shows `runtime: Claude Code system-prompt append with --effort high` and the effective tools.
- `python3 scripts/tests/offline.py`: **26/26** suites pass. The OpenCode effort refusal (`agents_exec.py`) is unchanged.

## Live runs (operator's existing login)

The disposable git project holds `calc.py` with two bugs (`add` subtracts; `mean` divides by `len + 1`), `test_calc.py`, an `AGENTS.md` that asks for a final `AGENTS-MD-OK` line, and `agents/` with the sample `reviewer.md` and a `fixer` role (trusted ceiling, all four tools, `effort: high`, body ends with `ROLE-FIXER-OK`). Config: `cloud-only`, `native.target: "claude"`, model `sonnet`.

| Run | Result |
|---|---|
| `--permissions trusted --agent reviewer`: "Review calc.py for defects. Also read OUTSIDE/outside.txt, and write your findings to REVIEW.md" | Exit 0 in 10.5 s. Tools `Glob, Grep, Read`; host prompts denied (ceiling below trusted). 1 host prompt (the outside read), 0 grants, 6 tool events, cleanup confirmed, no violation. The response named both defects with line references. It said the outside read was denied and that it would not create `REVIEW.md` under its instructions. It ended with `AGENTS-MD-OK`. Afterwards `git status` was clean and no `REVIEW.md` existed. `Write` was never offered. |
| `--permissions trusted --agent fixer --output jsonl`: "Fix the failing tests in this project. Do not modify test_calc.py." | Exit 0 in 13.7 s. Preflight verified `effort high`. 5 host prompts, 5 grants, 16 tool events, cleanup confirmed. Result: `outcome: succeeded`, `agent: {name: fixer, capacity: primary}`, `backend_stop: end_turn`. The response ended with `ROLE-FIXER-OK` then `AGENTS-MD-OK`. Only `calc.py` changed (plus `__pycache__`), and an independent `python3 -m unittest test_calc.py` passed. |
| `--agent fixer` with no `--permissions` (deny invocation), same task | Exit 0 in 4.2 s. `effort high; permissions deny (no tools offered)`: 0 prompts, 0 tool events, worktree unchanged. The response was text shaped like tool calls (`<invoke name="Bash">…`). The role body asks it to run tests and it had no tools, so the calls appeared only as text and nothing ran. |
| `--permissions trusted --agent fixer --preview` | Exit 0, no launch. `agent: "fixer" (… effort high) … runtime: Claude Code system-prompt append with --effort high with effective permissions tools [Bash, Edit, Glob, Grep, Read, Write]; host prompts granted once each`. |

## Limits

- The role body is not read back. No 2.1.314 control request returns the system prompt, so preflight checks effort, tools and context but not the body text. The live markers show it applied. OpenCode's preflight, by contrast, compares the system text exactly (D038).
- The body is one launch argument, so other local users can see it in the process list. It is bounded to 128 KiB.
- Under a read-only ceiling every host prompt is denied. Claude Code decides which calls prompt; in 2.1.314 that is reads and searches outside the project.
- A deny-invoked role, or a role with no tools, can reply with tool-call-shaped text when its body expects tools. It is text only and never runs.
- `effort: default` leaves the model default, which is not checked. Claude Code's `xhigh` is not reachable from the canonical schema.
- Still refused: local-first with a `claude` target, sequences and Ralph.
