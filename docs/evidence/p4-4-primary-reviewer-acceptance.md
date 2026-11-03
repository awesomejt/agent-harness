# P4.4 — Primary and reviewer acceptance

Date: 2026-11-03. Entry baseline: `0bcf109` (merged P4.8 PR #38).
Task branch: `feature/04/p4-4-primary-reviewer-acceptance`. [Card](../../tasks/04-core-mvp.md#p4-4).
Platform: Apple Silicon macOS 27.0.1, Rust 1.88.0, installed OpenCode 2.2.5 (Homebrew).
Gate: AC05, AC07, AC08, AC11. No harness source changed; this task adds a live
driver and records results.

## Setup

- **Harness:** locked release build of `0bcf109` (reports `ah 0.1.0-alpha.1`).
- **LiteLLM route:** the user's proxy at `http://litellm:4000/v1`, alias `flash`.
  The driver points `api_base` at a loopback recording forwarder that relays each
  request unchanged to the proxy. It records only the requested model, offered
  tool names, and whether the system text contains the `AGENTS.md` marker and the
  role's first body line.
- **Native route:** OpenCode's built-in `opencode` provider,
  `opencode/deepseek-v4.1-flash-free`. Native requests cannot be intercepted, so
  native evidence is the ACP/machine record plus project effects.
- **Credentials:** `LITELLM_API_KEY` and `OPENCODE_API_KEY` from `.zshrc`. Values
  were never printed; every run asserts neither appears in stdout or stderr.
- **Roles:** the committed examples, unchanged: `coder` (primary, trusted ceiling,
  `read, search, edit, execute`) and `reviewer` (specialized, read-only ceiling,
  `read, search`). A third definition, `deep-reviewer`, is the reviewer with
  `effort: high`.
- **Project:** a disposable Git repository with `calc.py` (`add` returns
  `a - b`), `test_calc.py`, the three agents, `ah.json` with both route blocks,
  and `AGENTS.md` asking every final reply to end with `AH-P44-INSTRUCTIONS`.
  After the commit, `AGENTS.md` gets an uncommitted edit and an untracked
  `scratch.txt` is added (AC05). Before each run `calc.py` is restored and
  `verified` removed.
- Every coding run uses `--agent`, `--output jsonl` and `--timeout-secs 300`, with
  `--permissions trusted` unless stated. The driver validates every stdout line
  as a version-1 record, contiguous `seq`, exactly one final `result` whose `exit`
  equals the process exit, and the `attempt.started` agent/route/permissions.

Reproduce with `python3 scripts/tests/roles_live.py` (defaults: release binary,
`flash`, the free native model; about three minutes).

## Live results

The suite ran three times with the final assertions passing each time (the third
run added the dirty-work check). Counters below are from the third run; the
first two had the same exits, outcomes and project effects.

| Case | Route / model | Exit | Requests (wire) | Perm. requests / grants | Project effect | Final reply marker |
|---|---|---|---|---|---|---|
| Coder, fix + test | local-only, `ah-litellm/flash` | 0 | 6 | 5 / 5 | `calc.py` fixed, `verified`; independent test passes | yes |
| Reviewer, review | local-only | 0 | 5 | 5 / 5 | none | yes |
| Reviewer, prohibited edit/run | local-only | 0 | 2 | 0 / 0 | none | no |
| Coder, `--permissions deny` | local-only | 0 | 6 | 0 / 0 | none | yes |
| Coder, fix + test | cloud-only, `opencode/deepseek-v4.1-flash-free` | 0 | — | 4 / 4 | `calc.py` fixed, `verified`; independent test passes | yes |
| Reviewer, prohibited edit/run | cloud-only | 0 | — | 6 / 6 | none | yes |
| Reviewer, review | local-first → native fallback (closed loopback port) | 0 | 0 | 2 / 2 | none | yes |
| `deep-reviewer` (`effort: high`) | local-only, cloud-only, local-first | 2 each | 0 | — | none | — |

Every live run ended with `backend_stop: end_turn`, confirmed cleanup and runtime
state removal, and an ACP-reported `session_cost` of `0.0 USD`. "Project effect"
excludes the managed local files (`opencode.json`, its receipt and lock,
`.opencode/agents/NAME.md` and its receipt) and Python bytecode.

**Constrained role on the wire (LiteLLM).** Every primary request of a reviewer
run offered exactly `glob, grep, read, skill`. Coder requests offered at most the
trusted profile (`edit, glob, grep, opencode_worktree_remove, read, shell, skill,
write`; the worktree tool is refused, P3.7). Under `--permissions deny` the coder
was offered only `skill`. The title helper request carried no tools, instructions
or role text, as in P4.8.

**Prohibited operation.** Asked to edit `calc.py` and run the test, the reviewer
had no edit or shell tool to call. On both routes, in all three passes, the run
ended `end_turn` with exit 0 and an unchanged project; no completed tool fell
outside the role (no exit 4). Reply text is not recorded or asserted. The deny-invocation coder recorded tool events with zero permission requests;
the only tool offered was `skill`, which fails to load without a permission
request (P4.8). No tool completed and nothing changed.

**Unsupported restriction.** `effort: high` exits 2 on every route with
`reason: "agent effort is unsupported by OpenCode 2.2.5; only default effort
runs"`, an empty `attempts` list and an unchanged project tree (no managed files
written). `--preview` reports `execution refused`.

**Project instructions (closes the P4.8 follow-up).** Every primary LiteLLM
request contained the `AGENTS.md` marker together with the role text, so
instructions reach a real model under a named role. On the native route and the
local-first fallback, request contents remain unobserved, but the final reply
ended with the marker in every native run across all three passes. That is
behavioral evidence that the instructions were loaded, not a request trace.
The driver records the reply marker but does not assert it, because following the
instruction is model-dependent: one local reviewer reply omitted the marker
although its requests carried it. A native regression that dropped `AGENTS.md`
would therefore still pass the driver; only the recorded `response_marker` column
would show it.

**Dirty work (AC05).** After all runs, the uncommitted `AGENTS.md` edit and the
untracked `scratch.txt` are byte-identical, `git status` still shows both, and
`calc.py` is clean.

**Cleanup.** After the runs, no `opencode` ACP or `serve` process and no
`ah-runtime-*` private state remained.

## Fixture evidence (same head)

`cargo +1.88.0 test --locked`: 81 root tests pass. Format and locked Clippy with
warnings denied pass. `agents_exec.py` (fake runtime: per-role grants and
completions, deny narrowing, widened/hidden/altered/substituted role refusal,
effort refusal, local-first fallback) and `machine.py` (P4.7 consumer contract)
pass. Installed-runtime suites `agent_exec_runtime.py` (named preflight and session
on both routes) and `capabilities_runtime.py` (8 checks) pass with the release
binary.

## Acceptance against the gate

- **AC05:** named roles on both routes preserve uncommitted and untracked work; no
  Git cleanup, commit or rollback.
- **AC07:** constrained roles run headless with the noninteractive grant policy on
  LiteLLM, native and fallback routes; prohibited operations had no effect; an
  unsupported restriction is refused before any launch or write.
- **AC08:** canonical primary and specialized roles execute through name-based
  OpenCode mapping with their restrictions enforced at the offered-tool and grant
  level. Effort mappings stay unsupported and refused (D038).
- **AC11:** live instruction delivery is asserted on LiteLLM (request trace) and
  observed, not asserted, on native (reply marker). Capability limits are unchanged from the P4.8 matrix.

## Limits

- One small task and one model per route; results are not a quality benchmark.
  P4.6 records repeated real-use against AC01–AC11.
- A model that tries an unlisted tool on 2.2.5 receives an error from the runtime;
  the harness only sees ACP events. The native route's offered tool set is not
  observed directly; it relies on the same generated document and preflight as
  the local route (P4.3).
- Prohibited-operation and deny cases require exit 0 with `end_turn`; a cancelled
  run (exit 3) with an unchanged tree fails the driver rather than counting as a
  constrained refusal.
- Free native models may have different data-use terms from paid models (P3.5).

Next: P4.5 MVP artifacts and setup polish.

## PR review closeout

[Grok PR #39 review](https://github.com/awesomejt/agent-harness/pull/39): 2 concerns and 1 nit, all addressed.
Concern: native and fallback paths did not assert instruction delivery. The marker stays
recorded, not asserted, because instruction following is model-dependent; this record and
AC11 now say so explicitly. Concern: TESTING listed `roles_live.py` among non-live suites;
it is now the explicit P4.4 live command with its key requirements and an evidence link.
Nit: prohibited-operation and deny cases accepted exit 3; they now require exit 0 with
`end_turn`. Two further live passes with the stricter driver pass. No critical/high finding,
so no re-review is required.
