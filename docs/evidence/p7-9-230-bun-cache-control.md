# P7.9 — Bun runtime transpiler cache control for the parent-watch pair

Recorded: 2026-11-15, America/Denver. Baseline: `05e9f81`.
Branch: `feature/07/p7-9-bun-cache-control`. Decision: D100.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D099 inventory and installed stop](p7-9-230-state-inventory.md),
[D098 primitive](p7-9-230-parent-watch-primitive.md).

## Why

D099's single attempt showed that the listing-allowed control's only created
state was `CACHE/bun/@t@/<one file>` (4 KiB–1 MiB). The denied leg, and with it
the primitive parent-watch question, is still unrun because the unchanged
state gate refuses first. D100 selects a source-backed control that should
prevent that write while keeping the gate exactly as strict.

## Source findings

The OpenCode `v2.3.0` checkout (`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`)
pins `"packageManager": "bun@1.4.4"`. Its release `build-cli` job compiles with
`bun-version: 1.4.4` and `BUN_COMPILE_RELEASE: bun-v1.4.4`. Public Bun tag
`bun-v1.4.4` resolves to commit `38afee6c84fcf48c0edb2466aa4b27d287a59c30`:

| File at `38afee6` | SHA-256 |
| --- | --- |
| `src/jsc/RuntimeTranspilerCache.rs` | `69ec53b0c215bbf1a6b67fb08004ab0236608a7a5083949839bb9cc9f318e7c5` |
| `test/cli/run/transpiler-cache.test.ts` | `22a30ba8154b8697518c87caba3dac79964721fea7329e286e26c86278f52184` |

In `RuntimeTranspilerCache.rs`:

- `really_get_cache_dir` consults `BUN_RUNTIME_TRANSPILER_CACHE_PATH` first. An
  empty value or exactly `0` returns length 0, which `get_cache_dir` turns into
  the process-wide `IS_DISABLED` state; no cache directory is resolved.
- Otherwise `XDG_CACHE_HOME` yields `<XDG_CACHE_HOME>/bun/@t@`, matching the
  D099 inventory exactly (macOS then falls back to `~/Library/Caches/bun/@t@`).
- Sources shorter than `MINIMUM_CACHE_SIZE` (4 KiB) are never cached. The D098
  child `chatgpt_parent_watch.mjs` is 4,817 bytes, which accounts for it being
  eligible.

Limits: the upstream test file exercises custom and unset cache paths but has
no case for the `0`/empty disable form, so that behaviour rests on source
reading. The pinned executable is the host-specific Homebrew 2.3.0 build
(D092/D094), not the release asset, so its embedded Bun version is not
established as 1.4.4. Neither limit is assumed away: the experiment decides.

## Selection and alternatives

`chatgpt_230_cache_control.py` reruns D099 unchanged except that the child
environment adds `BUN_RUNTIME_TRANSPILER_CACHE_PATH=0` (refusing if the base
environment already sets it). The D098 pins, sandbox profile, protocol,
fixtures and cleanup and the D099 state gate, inventory, print-after-cleanup
and stop-before-denied ordering are reused; an offline source-mirror test fails
if `run_case` diverges from D099's in anything but that one line.

The outcome is self-verifying. If the embedded Bun honours the setting and
nothing else writes state, the control passes the unchanged gate and the D098
denied leg runs for the first time. If the setting is ignored or another writer
appears, the gate refuses again with an inventory; no state is accepted.

Rejected: shrinking the child script below 4 KiB (depends on the same
unverified runtime internals and changes the reviewed child), redirecting the
cache to another owned path (still a write; the gate would need widening), and
allowlisting `bun/@t@` at the gate (weakens the invariant D098 set).

```sh
python3 -B scripts/tests/chatgpt_230_cache_control_cases.py
# Only after helper/setup review:
python3 -B scripts/experiments/chatgpt_230_cache_control.py --source <clean-v2.3.0-checkout>
```

## Gate and boundary

Offline tests and setup review precede one installed attempt; the first
unexpected observation stops without retry and result review precedes merge.
A compatible or incompatible denied-leg result is a primitive result only: it
needs a separately reviewed remedy/OpenCode continuation and does not pass case
3 or P7.9. The cache control is an experiment-local environment setting, not a
production or adapter change; whether OpenCode-level runs need a similar control
is a later decision.

All D098/D099 boundaries carry over: no OpenCode services, retained/operator
state, credentials, auth/session/model call, config/catalog/database access,
file-content reads, existing helper/pin/production change or permission
expansion. No D096 retry, cases 4–6 or catalog/authenticated migration. P7.11
blocked; fixed 236-ID/D034/D089 and Go gates unchanged.

## Offline verification and installed outcome

Offline tests cover the exact environment addition and collision refusal, the
D099 source mirror, inventory printing and stop-before-denied ordering, the
clean pair, incompatible denial and sanitized entry output. Setup review, the
single installed result and result review will be recorded below.
