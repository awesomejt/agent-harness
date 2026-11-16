# P7.9 — Disposable OpenCode 2.3.0 created-state inventory

Recorded: 2026-11-15, America/Denver. Baseline: `7fb038d`.
Branch: `feature/07/p7-9-created-state-inventory`. Decision: D099.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D098 primitive and installed stop](p7-9-230-parent-watch-primitive.md),
[D097 assessment/plan](p7-9-230-parent-watch-assessment.md).

## Why

D098's single installed pair stopped `REFUSED: state-created` on the
listing-allowed control after its watch protocol and post-exit fixture check
completed. The disposable root was removed by design, so which private XDG root
was written, and what, is unobserved. The denied leg, and therefore the primitive
question, remains unanswered. D099 makes that refusal informative without
weakening it.

## Scope and review boundary

`chatgpt_230_state_inventory.py` imports the merged D098 helper unchanged and
runs the same source qualification, executable pin, owned roots, sandbox
profile, protocol, fixture and cleanup. The only difference is the final state
gate: when any of CONFIG/DATA/CACHE/STATE is non-empty, a finite inventory is
collected inside the still-locked root, then printed after child, lock and root
cleanup, followed by the unchanged `REFUSED: state-created` and nonzero exit.
State-created still refuses; an inventory is never an acceptance.

```sh
python3 -B scripts/tests/chatgpt_230_state_inventory_cases.py
# Only after helper/setup review:
python3 -B scripts/experiments/chatgpt_230_state_inventory.py --source <clean-v2.3.0-checkout>
```

If the control leg leaves the roots empty, the helper proceeds to the D098
denied leg unchanged, and that leg's state is gated and inventoried the same
way. One installed attempt; the first unexpected observation stops without retry.

## Inventory contract

- Metadata only: `scandir`/`lstat` without following links; no file, link
  target or directory content is opened or read. Each root's identity is
  checked as an owned non-link directory first.
- Each entry: root, depth (1 = direct child), type `DIR`/`FILE`/`LINK`/`OTHER`
  and, for files, a size bucket `ZERO`/`LE_4K`/`LE_1M`/`GT_1M`.
- Names: a fixed allowlist of hypothesized names (`bun`, `.bun`, `@t@`,
  `install`, `cache`, `opencode`, `tmp`, `log`, `bin`) is emitted as `N:<name>`
  because those bytes are the helper's own. Any other name is emitted only as
  `H:` plus the first 16 hex digits of its SHA-256, so later hypotheses can be
  checked offline without a rerun; raw child-influenced names never appear.
- Unreadable state is recorded, never escalated: a directory that cannot be
  listed is marked `unreadable`, an unlistable root is named in
  `unreadable_roots` (and is not treated as empty), and an entry that cannot
  be `lstat`ed has type `UNSTATABLE`.
- Bounds: depth 6 and 128 entries, after which `truncated` is set. Entries are
  sorted by name within each directory for reproducible output.

The inventory identifies what was created, not by whom: Bun, the inert script
or any runtime component are equally possible writers and no cause follows. A
remedy (for example a pinned cache-path control) requires a separately reviewed
decision; it is not selected here.

## Boundary

No OpenCode services, retained/operator state, credential handling,
auth/session/model call, config/catalog/database access, existing helper/pin/
production change or permission expansion. No D096 retry, cases 4–6 or
catalog/authenticated migration. Full P7.9 remains open, P7.11 blocked and fixed
236-ID/D034/D089 plus Go gates unchanged.

## Offline verification and installed outcome

Offline tests use synthetic owned roots only. They cover allowlisted and
digest labels, an unknown name that never appears raw, a link whose target is
neither followed nor emitted, size buckets, depth and entry truncation, linked
root refusal, no file opens during inventory, printing only after root deletion,
stop-before-denied-leg ordering, the unchanged clean pair and sanitized entry
output. Setup review, the single installed result and result review will be
recorded below.

Setup review ([PR #125](https://github.com/awesomejt/agent-harness/pull/125),
Grok at `9205aa0`): **0 blockers/concerns, 1 nit**. An unreadable created
directory would raise `PermissionError`, bypass `StateCreated` and lose the
inventory to a generic `control-gate` refusal. Disposition: **valid, addressed**
by recording unreadable directories/roots and unstatable entries as above, with
an offline `chmod 0` subdirectory and root case. Containment and protocol are
unchanged, so no re-review is required; do not reopen this nit.

### Installed outcome (single attempt, 2026-11-15, `1b7b4e1`)

Inputs unchanged from D098: Homebrew `opencode v2.3.0` matching the D094 pin and
a clean public `v2.3.0` clone at exactly `a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`;
source qualification passed.

```text
{"entries": [{"depth": 1, "name": "N:bun", "root": "CACHE", "type": "DIR"}, {"depth": 2, "name": "N:@t@", "root": "CACHE", "type": "DIR"}, {"depth": 3, "name": "H:47a527899a79328b", "root": "CACHE", "size": "LE_1M", "type": "FILE"}], "listing": "ALLOWED", "state": "CREATED", "truncated": false, "unreadable_roots": []}
REFUSED: state-created
exit 1
```

The listing-allowed control again completed its watch protocol and post-exit
fixture check and refused only at the state gate. Created state is exactly one
chain, `CACHE/bun/@t@/<file>` with one file of 4 KiB–1 MiB; CONFIG, DATA and
STATE stayed empty, nothing was unreadable and the walk was not truncated. The
denied leg did not run; no retry.

Interpretation, bounded: `bun/@t@` under `$XDG_CACHE_HOME` matches the layout of
Bun's runtime transpiler cache. That is a structural match, not an established
writer or trigger, and the file's name and contents remain unobserved. The
primitive parent-watch question is still unanswered. Whether a pinned cache
control (for example Bun's documented transpiler-cache path setting, verified
against the pinned runtime first) may be applied, or the gate scoped to this
exact entry, requires a separately reviewed decision; D099 selects neither.
