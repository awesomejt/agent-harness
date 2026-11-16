# P7.9 — Retire installed case 3 (listing-denied parent)

Recorded: 2026-11-15, America/Denver. Baseline: `9e5a46c`.
Branch: `feature/07/p7-9-retire-case-3`. Decision: D101.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D100 primitive result](p7-9-230-bun-cache-control.md),
[D097 assessment](p7-9-230-parent-watch-assessment.md),
[D094 case matrix](p7-9-230-disposable-observer.md).

## Scope

Source-only decision. No helper is implemented or run, and no installed
runtime, retry, retained/operator state, credential, login, session or model
call is involved. No pin, permission or production change. Cases 4–6 are not
started; this record only removes the unpassable row and names what a later
continuation must review.

## Why case 3 cannot pass

D094's matrix makes case 3 identical to case 2 (project on, Claude skills off,
no reload, ancestors denied) except for one literal `file-read-data` denial on
the owned `home/repo` parent. It exists to exercise `config/discovery.ts`'s
direct-probe fallback. The parent is already harness-owned and empty apart from
fixtures; the denial is the purpose of the case, not a protection.

The chain below is pinned to OpenCode `v2.3.0`
(`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`); both files are hash-checked by
the [D097 manifest](p7-9-230-parent-watch-source-manifest.json), and source
qualification against a clean clone passed for this record.

1. `core/src/config/discovery.ts:discover` lists each parent and, on failure,
   falls back to probing candidates directly. Its comment states the intent:
   sandboxes that deny listing an ancestor fall back to direct probes.
2. `core/src/config/watch.ts:plan` places an `entries` watch on that same parent
   (D097).
3. `core/src/filesystem/watcher.ts:nativeLayer` acquires it with
   `watch(directory, { recursive: false }, …)` inside `Effect.try`. A thrown
   error other than `ENOENT` is logged with `Effect.logError("failed to watch
   directory", …)` and yields no subscription, so no readiness callback or events.
4. D100 ran that call under the identical denial with the pinned executable:
   direct probes succeeded and `fs.watch` failed **synchronously with EPERM**.

Together these make case 3's gates unsatisfiable as designed: the WARN/ERROR
gate must refuse, and the parent's readiness/reload coverage is lost. This holds
whatever D096's three opaque errors were; D101 still does not claim to identify
them. Upstream supports discovery under a listing denial but not watching under
one, and case 3 sits exactly in that gap.

## Decision

Retire case 3 as an installed OpenCode row. Do not replace it with a widened
fixture, a warning exception, a watcher disable or an allowlisted error; D097's
rejections stand.

What case 3 uniquely covered, and where that coverage now rests:

| Property | Coverage after retirement |
| --- | --- |
| Discovery's direct-probe fallback | D094's synthetic Bun listing/fallback × candidate-read-denial pairs (all four passed) plus the pinned source above. |
| Everything else in case 3 | Identical to case 2, which passed every gate. |
| Installed end-to-end fallback discovery in OpenCode | **Not covered.** Accepted limitation: it cannot be observed without the watch failure above. |

Boundary invariant recorded for OpenCode routes: harness sandbox profiles must
not deny directory listing (`file-read-data` on a directory) for any directory
OpenCode watches, meaning the project, its ancestors, config roots and the machine parent.
Doing so loses config watch readiness and logs ERROR. Name-level denials, such as
D076's ancestor discovery-name denials, are unaffected; D076 acquired watches on
every ancestor under them. A later production sandbox design must review this
invariant, not inherit it silently.

## Next and boundary

Next is a separately reviewed continuation for D094 cases 4–6 without case 3.
It must decide, with helper/setup review, how the D094 helper runs a reduced
matrix, and whether the D100 Bun cache control or the D094 case list needs any
change. This record selects neither. A first-run stop applies as before.

Retiring the row is not a pass. D094 installed qualification, full P7.9, the
fixed 236-ID inventory, D034/D089, the catalog/retained/authenticated gates and
Go gates are unchanged; P7.11 stays blocked. No D096 rerun.
