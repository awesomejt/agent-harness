# P4.1 — Canonical agent schema and OpenCode destinations

Date: 2026-11-03. Entry baseline: `2a2a424` (merged P3.6 PR #32).
Task branch: `feature/04/p4-1-agent-schema`. Platform: Apple Silicon macOS,
Rust 1.88.0, installed OpenCode 2.2.5.

## Delivered contract

[D036](../../DECISIONS.md#2026-11-03--d036-canonical-agent-schema-and-opencode-destinations)
and [CONFIGURATION](../CONFIGURATION.md#canonical-agents) define version-1
canonical Markdown/YAML files, validated names, descriptions, capacities,
permission ceilings, tool lists, route-specific aliases and required effort.
`src/agents.rs` parses caller-owned readers or regular files, returns static
errors, preserves body text and constructs only a safe relative destination.
The name-based catalog rejects duplicates and returns deterministic order.
`agents/coder.md` and `agents/reviewer.md` are parsed examples.

No agent CLI, production discovery/emission, capability enforcement or named
inference is delivered here. Existing runtime policy stays in force. P4.2
consumes this parser for conflict-aware emission/selection and P4.3 consumes it
for effective constraints. No passing parse grants a tool or proves read-only.

## Parser evidence

`cargo +1.88.0 test --locked --test agents` passes eight test groups:

- Examples, LF/CRLF, exact body preservation and relative destination.
- Flat lowercase names, length bounds, traversal/separators and built-in collisions.
- Required/unknown/duplicate fields, duplicate tools, invalid enums/types, null,
  custom tags, YAML merge keys, malformed/unresolved/recursive aliases and deep nesting.
- Deny/read-only tool ceilings, including explicit rejection of execute under read-only.
- Local aliases/group syntax versus native identifiers, duplicate route keys,
  missing/empty/null models and rejection of provider/URL forms and scalar coercion.
- Input/frontmatter/description bounds, UTF-8, delimiters/BOM, empty/control body,
  and static errors that do not echo a credential-shaped invalid value.
- Duplicate canonical names, deterministic ordering and catalog count bounds.
- Filename equality, regular-file checks, traversal, final symlink and device refusal.

A failing null-model fixture exposed YAML's automatic string coercion. Explicit
string visitors now reject null/number/boolean scalars for names, descriptions
and route aliases. Custom tags can also bypass ordinary typed YAML decoding;
a bounded value pass rejects them before direct struct deserialization. That
second pass preserves duplicate-field rejection. Upstream recursion and alias
repetition limits remain enabled. Parent-directory containment and project
transaction race checks are P4.2 responsibilities; no filesystem sandbox is claimed.

## Installed backend evidence

`python3 scripts/tests/agents_runtime.py` passes six network-free configuration
probes (no ACP request, key or model prompt): native document `agents.reviewer`
and project `.opencode/agents/reviewer.md`, each with primary/subagent/all modes.
Assertions verify the same ID, description, `system` body, selected structured
model, ordered deny profile followed only by built-in denials, and empty request
overrides. Each probe clears the environment and uses private HOME/XDG, disabled
model fetching/updating and `debug agents --standalone`. Project discovery is
only enabled for the disposable project-file probe. Isolated production runs
will keep discovery disabled and consume the generated native document.

The probe initially expected the supplied permissions at the absolute end;
OpenCode appends built-in denials. The corrected assertion requires the exact
ordered profile followed only by denials, matching D035's existing validator.
This is a destination/schema check, not model inference or constraint enforcement.

Version-pinned upstream references corroborate the observed fields/destinations:
[agent schema](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/schema/src/config/agent.ts)
and [agent loader](https://github.com/anomalyco/opencode/blob/v2.2.5/packages/core/src/config/plugin/agent.ts).

## Dependency review

The lockfile adds only `serde_yaml_ng` 0.10.0 and `unsafe-libyaml` 0.2.11;
all their other dependencies were already locked. Both declare MIT and include
their license files in the downloaded registry sources (`LICENSE` and
`LICENSE-MIT`, respectively). The existing package collector accepts MIT and
bundles license material plus checksummed complete registry archives; no new
license exception is required. `serde_yaml_ng` declares Rust 1.64 and the tested
locked build passes on the project's Rust 1.88.0. Current serde-saphyr 2.0.0 and
1.3.0 declare Rust 1.89; neither was added. This review is compatibility and
attribution evidence, not a vulnerability audit or a new release artifact.

## Validation and follow-up

On Rust 1.88.0: format, locked Clippy with warnings denied, all 65 root tests,
and locked release build pass. The existing read-only preview suite passes.
The six installed-OpenCode probes pass. Production routing/lifecycle code is
unchanged; this task adds no live provider call or wider platform claim.

Next: P4.2 — name-based native emission, ownership/collision handling,
read-only preview, model precedence and `--agent` selection. P4.3/P4.4 retain
effective role enforcement and live prohibited-operation acceptance.

## PR review closeout

[Grok PR #34 review](https://github.com/awesomejt/agent-harness/pull/34#pullrequestreview-5749150719):
0 blockers, 1 documentation concern and 1 nit. Both addressed: the old generic
agent backlog paragraph now explicitly assigns emission/preview/collisions to
P4.2 and capability enforcement to P4.3; descriptions also reject Unicode
U+2028/U+2029, with escaped-YAML regression fixtures. Format, locked Clippy,
all 65 root tests and locked release build pass after the fixes. No critical/high
finding or mandatory re-review. One automated first-pass review posted; an
explicit request was made while it was pending, with no additional requests.
