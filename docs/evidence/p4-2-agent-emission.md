# P4.2 — Named emission and agent selection

Date: 2026-11-03. Entry baseline: `9f7fdac` (merged P4.1 PR #34).
Task branch: `feature/04/p4-2-agent-emission-selection`. Platform: Apple Silicon
macOS, Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered contract

[D037](../../DECISIONS.md#2026-11-03--d037-name-based-agent-selection-and-conflict-aware-opencode-emission)
and [CONFIGURATION](../CONFIGURATION.md#p42-selection-and-emission-d037) define:

- `ah single ... --agent NAME`: validated name, exact `PROJECT/agents/NAME.md`
  lookup in a real directory, case-variant refusal, no parsing of other
  definitions and no global/user sources. The definition is carried by the
  resolved request and its local-first fallback.
- Model precedence per route: `--model`, agent route model, config. The
  local-first fallback uses agent `models.native`, else `native.model`. Agent
  `group:` references resolve only on the active LiteLLM route. Preview reports
  the new `agent` model source.
- Execution gate: a named non-preview request exits 2 before runtime creation,
  reachability checks or project writes, because P4.3 has not yet enforced the
  ceiling/tools/effort or generated the runtime `agents.NAME` entry.
- Read-only preview: an `agent:` line (name, capacity, ceiling, tools, effort,
  emission status) and planned emission paths; description/body omitted.
- Emission on the managed local route only (not `--no-sync`, never native):
  `.opencode/agents/NAME.md` in native frontmatter (`description`, `mode`,
  resolved structured `model`, ceiling-derived `permissions`) plus the exact
  canonical body. Rules are deny-all plus `ask` per listed tool; none allow.
- Ownership: `.ah-opencode-agents.json` holds the exact last-emitted content per
  owned name; collisions with every tested OpenCode project agent source refuse.

Running a named role is still not possible: P4.3 owns runtime mapping and
enforcement; P4.4 owns live named-role inference. Emission is exercised through
the library transaction and is reached by `ah` once P4.3 lifts the gate.

## Test evidence

`cargo +1.88.0 test --locked`: 74 root tests pass (65 before this task).
New `tests/agent_emission.rs` (temp projects, seven groups):

- Selection: exact name, unrelated malformed definitions and `.DS_Store` ignored,
  missing/invalid/reserved/duplicate names, case-variant canonical file,
  missing and symlinked `agents/`.
- Precedence: invocation over agent over config on LiteLLM and native routes,
  omitted route inheritance, local-first primary/fallback split, agent group
  resolution and undefined-group refusal only on the active route.
- Golden emission: [coder](../../tests/fixtures/opencode-agents/coder.md) and
  [reviewer](../../tests/fixtures/opencode-agents/reviewer.md) bytes, receipt
  equality, no key/endpoint, idempotent re-plan, CRLF body preservation and
  model following `--model group:…`.
- Preview: planned paths listed, body absent, project tree byte-identical and no
  `.opencode` created; no-sync plans nothing.
- Collisions: `.opencode/agents/Reviewer.md`, `.opencode/agent/reviewer.md` and
  `REVIEWER.md`, `agent`/`agents` keys in both JSON locations,
  `.opencode/opencode.jsonc`, non-object/duplicate-key JSON, identical but
  unrecorded file, symlinked `.opencode`/`agents`/destination (outside target
  untouched); other names, nested `sub/reviewer` and unrelated keys preserved.
- Ownership: canonical change updates only the selected owned file, manual edit
  refuses without overwrite, removed file recreated, five invalid receipts refuse.
- Stale plans: a collision or user file created after planning rejects apply
  with no write.

Unit test `ceiling_never_allows_and_matches_profiles_at_the_extremes` proves the
full trusted set equals the trusted runtime profile, the empty deny set equals
the deny profile, read-only search maps to `glob`/`grep`, and no rendered rule
allows. CLI test `named_agent_preview_reports_selection_and_execution_refuses_without_writes`
runs the binary: preview exits 0 with the agent line and planned emission, no
body/key; non-preview exits 2 with the P4.3 diagnostic; project listing unchanged.
An updated config test asserts invalid/reserved `--agent` names reject at parse.

Format, locked Clippy with warnings denied and the locked release build pass.
Existing network-free suites pass unchanged: `single.py`, `preview.py`,
`worktree.py`, `native.py` (40 cases), `local_first.py`, `modes.py` (165 cases)
and `agents_runtime.py` (6 probes).

## Installed backend evidence

`python3 scripts/tests/agent_emission_runtime.py` (new; private HOME/XDG, no
key, ACP request or model prompt; 8 `debug agents --standalone` probes):

- The golden `coder.md`/`reviewer.md` load from `.opencode/agents/` with the
  expected mode (`primary`/`subagent`), description, trimmed body as `system`,
  `{providerID: ah-litellm, id: proxy}` model, the emitted rule list followed
  only by built-in denials, and empty request overrides.
- Each refused collision source really defines a same-named agent: legacy
  `.opencode/agent/`, case variant `Reviewer.md` (loaded as distinct ID
  `Reviewer`, which a case-insensitive filesystem would overwrite), `agent` and
  `agents` keys in `opencode.json`, and `agent` in `.opencode/opencode.json`.
- Project-root canonical `agents/` is not an OpenCode agent source.

An exploratory probe before implementation also showed nested
`.opencode/agents/sub/NAME.md` loads as `sub/NAME` and that a Markdown file plus
an `opencode.json` `agent` key of the same name yield a single ID (the Markdown
description won), so either source silently shadows the other; both informed D037.

## Limits and follow-up

- Frontmatter key order follows `serde_json` insertion order (its
  `preserve_order` feature is unified through existing dependencies); golden
  fixtures fail if that ever changes.
- Non-UTF-8 entries in OpenCode agent directories are treated as conflicts
  because they cannot be compared.
- Owned files whose canonical source is later removed are left in place; the
  harness never deletes project agent files.
- Specialized-role invocation semantics, runtime ceiling/invocation
  intersection, effort refusal and the `agents.NAME` runtime entry: P4.3.

Next: P4.3 — constrained primary and specialized execution.
