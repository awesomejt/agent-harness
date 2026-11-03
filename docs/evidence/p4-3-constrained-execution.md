# P4.3 — Constrained primary and specialized execution

Date: 2026-11-03. Entry baseline: `0e90561` (merged P4.2 PR #35).
Task branch: `feature/04/p4-3-constrained-execution`. Platform: Apple Silicon
macOS, Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered contract

[D038](../../DECISIONS.md#2026-11-03--d038-directly-invoked-named-roles-with-intersected-runtime-rules)
and [CONFIGURATION](../CONFIGURATION.md#p43-enforced-named-execution-d038) define:

- Invocation: `ah single --agent NAME` runs the role directly as the session's
  default agent for every capacity; capacity is reported as the role.
  Specialized is not a backend subagent.
- Runtime document: `agents.NAME` (`mode: primary`, resolved route model,
  effective rules, body as `system`) and `default_agent: NAME`; global
  `permissions` equal the effective rules, so every helper/subagent shares them.
- Intersection: deny invocation → deny profile for any role; trusted invocation
  → the agent's D037 ceiling rules. Grants also require the permission's ACP kind
  to be a listed tool; a completed call of an unlisted/unknown kind under a named
  role is a violation.
- Verification: preflight requires the named agent as a visible primary with the
  exact model, description and system text, and every agent ending with the
  effective rules; the ACP session `mode` must equal NAME before the prompt.
- Effort: only `default` runs; any other value exits 2 before runtime discovery,
  reachability checks or writes. Preview reports the mapping and any refusal.
- Local-first: the fallback carries the agent; the recovery guard also compares
  agent name and effective rules.

The P4.2 execution gate is removed.

## Runtime observations (installed 2.2.5, no prompt)

Direct `debug agents --standalone` and ACP `initialize` + `session/new` probes
with a generated document, private HOME/XDG and disabled project config:

- `default_agent: reviewer` with a `primary` entry selects session mode
  `reviewer`. A `subagent` entry with the same default silently selects `build`,
  with no error, so the runtime entry is always primary and the session mode is
  checked. `all` also selects the named agent.
- A configured agent's rules are appended after the global rules and before the
  built-in denials; built-in agents (`build`, `general`, `explore`, `plan`,
  helpers) carry the global rules, so setting them to the effective rules
  constrains every agent.
- `system` is echoed byte-for-byte, including leading spaces, CRLF and trailing
  blank lines.
- `session/new` advertises an `effort` option (`low`, `medium`, `high`,
  `default`; current `default`) for the tested LiteLLM model. Its translation into
  provider requests was not verified; `max` is not offered. Recorded as an
  unsupported mapping.

## Test evidence

`cargo +1.88.0 test --locked`: 76 root tests pass (74 before this task). New
units in `src/opencode.rs`:

- `named_role_is_the_primary_default_with_intersected_rules_everywhere`: document
  shape, global rules equal agent rules, CRLF body preserved, grantable kinds for
  trusted/deny/deny-ceiling/no-agent, unnamed config unchanged, effort support.
- `named_role_must_be_visible_primary_with_exact_model_and_system`: `build` alone
  no longer satisfies a named request; subagent/hidden/altered system/description
  and missing model refuse; a helper keeping the wider trusted profile refuses.

The CLI test now checks preview reports `effective permissions ["read", "search"]`
(trusted) or `deny (invocation)`, and that a `high`-effort agent previews the
refusal and exits 2 with no project change.

`python3 scripts/tests/agents_exec.py` (new; fake 2.2.5, 21 CLI runs):

- Trusted read-only reviewer: document as above; `read`/`search` granted once and
  file emitted; `edit`/`execute` requests rejected (turn cancelled, exit 3);
  completed read exits 0, completed edit or unannounced kind exits 4.
- Trusted coder gets the full trusted profile and an edit grant; with deny
  invocation the coder's global and agent rules are the deny profile, edit is
  rejected and a completed read exits 4.
- Preflight refuses (exit 2, no launch) a widened named agent, a hidden one, an
  altered system text and a widened built-in subagent; a session that selects
  `build` instead stops before the prompt (exit 1).
- `low`/`medium`/`high`/`max` effort exit 2 with no runtime config, launch or
  emission; explicit `default` runs.
- Local-first with an unreachable LiteLLM falls back natively with the same
  default agent, read-only rules and `opencode` model; nothing is emitted.

`python3 scripts/tests/agent_exec_runtime.py` (new; installed 2.2.5, prompt
intercepted by the existing `native_runtime.py` shim): the two direct mode probes
above, then 4 full `ah` preflight + ACP session runs pass with the real runtime:
local-only reviewer (trusted and deny) and coder (trusted), and the local-first
native fallback for the reviewer on `opencode/gpt-5.4`.

Format, locked Clippy with warnings denied and the locked release build pass.
Existing suites pass unchanged in result: `single.py` (69), `preview.py`,
`worktree.py`, `native.py` (40), `local_first.py`, `modes.py` (165 matrix, 14
invalid), `agents_runtime.py` (6) and `agent_emission_runtime.py` (8). The fake
runtime now also emits the session `mode` option and configured agents.

## Limits and follow-up

- No live named-role inference or prohibited-operation trial: P4.4.
- Effort mapping is unsupported rather than approximated; enabling it requires
  evidence that the session option reaches provider requests.
- `capacity` does not restrict `ah single`; workflow placement uses it later.
- Harness completion checks rely on announced ACP kinds; an unannounced kind fails
  closed, which may surface as exit 4 if a backend omits kinds.

Next: P4.7 machine result/event output, then P4.8 inherited capabilities, then
P4.4 live primary and reviewer acceptance.

## PR review closeout

[Grok PR #36 review](https://github.com/awesomejt/agent-harness/pull/36): 0 blockers,
1 concern and 1 nit, both addressed. The concern was stale P4.1 destinations prose
in CONFIGURATION (a future intersection and an unchanged `build` check); both
sentences now describe the D038 behavior. The nit was progress reporting a `both`
agent as a primary role; it now reports `capacity primary|specialized|both`,
matching preview, and D038 says so. Format, locked Clippy, 76 root tests and
`agents_exec.py` pass. No critical/high finding, so no mandatory re-review.
