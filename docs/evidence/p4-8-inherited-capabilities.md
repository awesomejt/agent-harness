# P4.8 — Inherited backend capabilities

Date: 2026-11-03. Entry baseline: `82bc872` (merged P4.7 PR #37).
Task branch: `feature/04/p4-8-inherited-capabilities`. Platform: Apple Silicon
macOS, Rust 1.88.0, installed OpenCode 2.2.5 (Homebrew). Decision:
[D040](../../DECISIONS.md#2026-11-03--d040-explicit-project-instructions-and-refused-runtime-commands).

## Finding that changed behavior

P1.3 verified that the runtime loads project `AGENTS.md`, but that was on
OpenCode 1.18.30. P3.7 moved the baseline to 2.2.5 and did not re-check it. On
2.2.5, `OPENCODE_DISABLE_PROJECT_CONFIG=true` also turns off project instruction
discovery. So from P3.7 through P4.7, isolated harness runs sent **no** project
instructions to the model, while CONFIGURATION still said `AGENTS.md` was an
instruction source. A direct ACP probe with the harness flags shows that the
`AGENTS.md` marker is missing from the model request, and present once the
flag is removed. Naming the file's absolute path in the generated document's
`instructions` restores it without enabling project config. A relative path
does not work.

A second finding: when the prompt's first word is the name of a built-in
command, 2.2.5 ACP runs that command instead of sending the prompt as text. The
advertised commands are `init`, `review`, `goal` and `compact`; project commands
are not loaded. Leading whitespace is ignored. In repeated probes, `/review`
sometimes reached the model as a reviewer template and sometimes made no model
request at all. `/init` and `/compact` made none. Every one of these runs
reported `end_turn` with an empty response, so `ah` exited 0 without doing the
work. This breaks the terminal-completion contract, so D040 refuses such
prompts.

## Delivered

- `Resolved.instructions`: the canonical project-root `AGENTS.md`, if present.
  The path must resolve to a regular file inside the project. A symlink to such
  a file is allowed. An outside target, a dangling link or a directory exits 2
  before key lookup, stdin, runtime discovery or writes. The local-first
  fallback carries the same value.
- The runtime document has `"instructions": [ABSOLUTE_PATH]`, or `[]`. The
  runtime reads the file. The harness neither reads it nor limits its size. The
  existing sources check confirms the echoed document, so the new entry goes
  through preflight unchanged.
- `opencode::prompt_supported`: a prompt whose first whitespace-delimited word
  is `/NAME` (where NAME is non-empty and has no further `/`) exits 2 before any
  runtime, network or write. Preview reports this as `execution refused`. A
  leading path such as `/src/main.rs fails` is still ordinary text.
- Preview adds `project instructions: project AGENTS.md (runtime-loaded)` or
  `none (no project AGENTS.md)`; skills/MCP/plugins/project config are not
  inherited. The path is not shown.

## Capability matrix (OpenCode 2.2.5, harness source at this PR)

Status values follow the [adapter contract](../EXECUTION.md#adapter-capability-contract):
**tested** (observed with installed 2.2.5 by a committed check), **unsupported**
(not loaded, denied or refused; never silently enabled), **unverified**
(runtime-owned behavior not exercised). "Stub" means the real runtime runs
against the loopback model stub in `capabilities_runtime.py`.

| Capability | Source / path | Status | Evidence and limits |
|---|---|---|---|
| Project instructions | `PROJECT/AGENTS.md` | Tested | Stub: present in every primary request under deny, trusted and named reviewer. It is not sent to the title helper. With a named role it appears alongside the role's `system` text. |
| Instructions, native route | same path | Tested (preflight); unverified (request) | The local-first native fallback passes real preflight with the entry, and the shim intercepts the prompt. No native inference ran, so the native request contents are not observed. |
| Parent `AGENTS.md` (project is a repository subdirectory) | repo root | Unsupported | Not named and not loaded (stub). The runtime's own upward search is disabled along with project config. |
| Nested `AGENTS.md` | `PROJECT/sub/AGENTS.md` | Tested, runtime-owned | Attached by the runtime only after a **granted** read inside that directory (stub). It goes through read permission, not harness selection. |
| `CLAUDE.md` | project root | Unsupported | Not loaded, with or without `AGENTS.md`. 2.2.5 also skips it natively in a private HOME. |
| Configured `instructions` | project `opencode.json`, `.opencode/opencode.json` | Unsupported | Project config is not loaded (stub marker absent). Managed sync keeps the unmanaged key in `opencode.json` for direct OpenCode use. |
| Skills | `.opencode/skill(s)/`, `.claude/skills/`, `.agents/skills/`; global skill dirs | Unsupported | The `skill` tool is offered under every profile. Loading returns "Unable to load skill" for each planted skill, with no permission request (stub). Global directories are in the private HOME, which is empty. A granted `read` of a `SKILL.md` is an ordinary file read. |
| MCP servers | project `opencode.json`, `.opencode/opencode.json`, `.mcp.json`; ACP `mcpServers` | Unsupported | The document has `mcp: {}`, and the ACP `session/new` call sends `mcpServers: []`, although 2.2.5 advertises `mcpCapabilities.http`. No planted server started (sentinels absent), and no MCP tool was offered. |
| Plugins | `.opencode/plugin(s)/`, `plugin` key | Unsupported | `plugins: []`. No planted plugin executed (sentinels absent). |
| Custom tools | `.opencode/tool(s)/` | Unsupported | Not offered or executed (stub tool sets are exact; sentinels absent). |
| Project slash commands | `.opencode/command(s)/` | Unsupported | Not advertised. `/probecmd` is refused like any command prompt. |
| Built-in slash commands | `init`, `review`, `goal`, `compact` | Unsupported (refused) | Advertised by ACP (direct probe). Command prompts exit 2 with no model request (stub). |
| Subagent delegation | `task` tool | Unsupported | Never offered. A call returns "No tool named task" (stub). Helper and subagent rules equal the effective rules (D038 preflight). |
| Web tools | `webfetch`, `websearch` | Unsupported | Never offered. A call returns "No tool named webfetch" (stub). |
| Offered tools | — | Tested | Deny: `skill`. Trusted: `edit, glob, grep, opencode_worktree_remove, read, shell, skill, write` (worktree removal refused, P3.7). Named reviewer (trusted): `glob, grep, read, skill`. |
| Title helper | `agents.title` | Tested | Same model, no tools, no instructions (stub; P3.7). |
| Context selection, compaction, caching | runtime | Unverified, runtime-owned | The `compaction`/`summary` agents carry the effective rules and no other model (preflight). Compaction was not triggered. Context/cost come only from ACP usage reports (D039). |
| Effort | agent `effort` | Unsupported (refused) | Only `default` runs (D038). |

## Test evidence

`cargo +1.88.0 test --locked`: 81 root tests pass (78 before this task). New:

- `tests/config.rs`
  `project_instructions_are_only_a_regular_root_agents_file_inside_the_project`:
  absent `AGENTS.md` with parent, nested and `CLAUDE.md` present resolves to
  none. An in-project symlink and a regular file resolve canonically. Outside,
  dangling and directory targets and an `AGENTS.md` directory are refused. The
  local-first test now checks that the fallback carries the same instructions.
- `src/opencode.rs`
  `instructions_name_only_the_resolved_path_and_command_prompts_refuse`: the
  document entry, plus refused/allowed prompt shapes.
- `tests/cli.rs`
  `preview_reports_instructions_and_command_prompts_refuse_without_writes`:
  both preview lines, the previewed refusal, and exit 2 for ` /init` with empty
  stdout and no project change.

`python3 scripts/tests/capabilities_runtime.py` (new; installed 2.2.5; 8 checks; local stub):

1. Direct ACP: `AGENTS.md` is loaded only when named. The commands are
   `init, review, goal, compact`.
2. Trusted: root `AGENTS.md` only. Skill load fails, `task`/`webfetch` are
   absent, and nested `AGENTS.md` appears only after the granted read
   (1 request, 1 grant).
3. Deny: tools `[skill]`; skill load fails; 0 requests.
4. Named reviewer: role text plus `AGENTS.md`; reviewer tool set.
5. Five slash-command prompts exit 2 with no model request. A leading-path
   prompt runs.
6. No `AGENTS.md`: no instructions.
7. No plugin, custom tool or MCP sentinel.
8. Local-first native fallback with the reviewer passes real preflight with the
   instructions entry.

Mutation check: emitting `instructions: []` makes the suite fail (direct-probe
equality and the trusted marker assertion). Source restored.

Format, locked Clippy with warnings denied and the locked release build pass.
`modes.py` now asserts the exact key set including `instructions` (`[]` for
matrix projects): 165 matrix + 14 invalid cases pass. Unchanged in result:
`single.py`, `preview.py`, `native.py` (40), `local_first.py`, `worktree.py`,
`agents_exec.py`, `machine.py`. The installed suites `agents_runtime.py`,
`agent_emission_runtime.py`, `agent_exec_runtime.py`, `native_runtime.py` and
`single_runtime.py` (default, `--jsonl`, `--refuse`) also pass.

## Limits and follow-up

- No live inference ran. P4.4 runs the named coding and reviewer roles live and
  should confirm that instructions reach a real LiteLLM model.
- The harness does not reproduce the runtime's upward or `CLAUDE.md` lookup.
  Projects that depend on parent instructions must put them in the selected
  project's `AGENTS.md`.
- The prompt rule is deliberately broad. A prompt starting with `/word` refuses
  even when `word` is not a command; rephrase, or start with other text.
- The check is a path check, not a snapshot: the runtime reads `AGENTS.md`
  later, so a concurrent replacement can change what is loaded.
- Runtime-owned compaction, caching and context selection stay unverified.
  Enabling skills or MCP needs a permission model and evidence; it is not in
  MVP scope.

Next: P4.4 primary and reviewer acceptance.
