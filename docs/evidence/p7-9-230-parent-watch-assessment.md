# P7.9 — OpenCode 2.3.0 parent-watch assessment

Recorded: 2026-11-15, America/Denver. Baseline: `95cfb31`.
Branch: `feature/07/p7-9-parent-watch-assessment`. Decision: D097.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D096 installed diagnostic stop](p7-9-230-warning-diagnostic.md).

## Scope and conclusion

This source-only increment assesses the parent-watch control after D096.
No helper implementation, installed runtime/Bun execution, retry, case 4–6,
operator-root/state/log/database/credential access, login, session/model call,
network/filesystem expansion, production or pin change occurs here. P7.9 stays
unpassed and P7.11 blocked; the fixed 236-ID inventory, D034/D089 and Go gates
remain unchanged.

The current listing-denied fixture has no accepted watch-preserving remedy.
D096 establishes three SERVER/WATCH_START/PARENT_REPO errors with other checked
gates passing. It does not reveal an OS error code, identify three distinct
subscriptions or establish causality. Source makes a listing/watch interaction
plausible, but only a new bounded primitive experiment can test that hypothesis.
Do not rerun the OpenCode diagnostic to obtain a cause.

## Reproducible public-source boundary

Official source: `anomalyco/opencode`, v2.3.0 commit
`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`.
The [parent-watch manifest](p7-9-230-parent-watch-source-manifest.json) records
all public source/test files assessed below, supplementing D093/D095 without
replacing either. These upstream tests were read, not executed; their assertions
are source evidence, not installed macOS/Bun or harness acceptance.

```sh
# Run from the harness repository; replace the source argument with its path.
python3 -B - /path/to/clean-v2.3.0-checkout <<'PYCODE'
import json, sys
from pathlib import Path
sys.path.insert(0, 'scripts/experiments')
from chatgpt_230_warning_diagnostic import qualify
from chatgpt_230_source_audit import verify_files
source = Path(sys.argv[1]).resolve()
qualify(source)  # D093 clean commit/263 files and D095 hashes/log tuples
manifest = json.loads(Path('docs/evidence/p7-9-230-parent-watch-source-manifest.json').read_text())
assert manifest['kind'] == 'p7-9-230-parent-watch-source/v1'
assert manifest['source_commit'] == 'a6b15d33daf6ab7d35569f6d711fdb630b9f04e7'
verify_files(source / 'packages', manifest['files'])
print('PASS: pinned source and', len(manifest['files']), 'parent-watch hashes')
PYCODE
```

## Source findings

Paths below are relative to `packages/`; names identify reproducible symbols.

| Source | Finding and control impact |
|---|---|
| `core/src/config/discovery.ts:discover` | Failed parent `readDirectory` silently falls back to named probes. Missing candidates remain eligible source/watch inputs. Listing success and direct-probe success do not establish watch readiness. |
| `core/src/config/watch.ts:plan` | Parent `entries` watches cover direct files and absent candidate roots, alongside recursive present-directory watches. Present roots still retain parent coverage for deletion/recreation. Upstream `core/test/config/watch.test.ts` explicitly asserts these plans. |
| `core/src/filesystem/watcher.ts:nativeLayer` | Both file and entries inputs call `node:fs.watch(directory, {recursive:false}, callback)`. Names are filtered in the callback, after acquisition. Filtering is not a narrower OS permission and does not avoid the denied parent operation. ENOENT returns no subscription silently; other startup errors log ERROR and return no subscription. |
| `core/src/filesystem/watcher.ts:layer` | Missing native subscription shuts down its pubsub. `subscribe` returns an empty stream before invoking `onReady`; acquisition failure provides neither ongoing events nor the readiness callback. RcMap structural keys share equivalent watch targets. Three log events cannot be equated to three independently identified targets. |
| `core/src/config.ts:reconcileWatches` | Watch readiness and subsequent updates request rediscovery/reload. Failed watches therefore lose both that readiness rescan and future event coverage. Other event/periodic paths do not establish equivalent config/resource coverage. |
| `core/test/filesystem/watcher.test.ts` | Tests assert empty streams on unavailable watches, non-ENOENT logging and no readiness callback without acquisition. These do not prove the error code from D096 or compatibility with its sandbox profile. |
| `cli/src/server-process.ts`, `server/src/{process,routes,options}.ts` | The selected CLI sets `fs.filewatcher` from `OPENCODE_FILEWATCHER_DISABLE ?? OPENCODE_DISABLE_FILEWATCHER`; `1` or case-insensitive `true` disables it. Routes replace both shared `Watcher` and `FileWatch` nodes. This is service-wide, not a per-parent/config-only exclusion. |
| `core/src/filesystem/{watcher,file-watch,location-watcher}.ts` | Disabled shared Watcher returns empty streams without readiness; disabled FileWatch returns DisabledError. Config/plugin and location consumers use the shared Watcher. The flag removes required coverage, including the existing MACHINE_PARENT watch gate. |
| `core/src/config/plugin/location-watcher.ts`, `core/src/filesystem/location-watcher-policy.ts` | Config `watcher.ignore` feeds location-watcher policy; location-watcher checks VCS target aliases. ConfigWatch.plan does not consult it. It cannot selectively skip or repair the parent config watch. |
| `core/src/config/plugin/source.ts` | Configured plugin-source watches also depend on shared Watcher. A global disable changes more than the denied fixture's parent watch. |

The inherited Bun controls test a wholly denied watched root and an allowed
parent whose child is denied. They do not pair `fs.watch` startup on the exact
parent with **only that parent's listing denied**. The separate discovery pairs
test listing/probing, without the source-faithful watch lifecycle. These are
specific coverage gaps, not failures of those earlier observations.

## Remedy disposition

| Candidate | Disposition |
|---|---|
| Ignore WATCH_START or accept stable initial snapshots | Rejected: lost readiness/event coverage remains a control failure; every OpenCode WARN/ERROR still refuses. |
| Set either watcher-disable environment variable | Rejected for this continuation: disables shared coverage, invalidates MACHINE_PARENT and reload evidence. Not a watch-preserving remedy. |
| Use config `watcher.ignore` | Not applicable to ConfigWatch's parent plan in this pin. |
| Remove listing denial or permit parent data reads | Not selected: widens the fixture and abandons direct-probe fallback qualification. A different source-boundary design would need separate review and paired proof. |
| Treat expected ENOENT as success or patch/vendor upstream watcher code | Not selected: cannot make an existing owned parent disappear or infer D096's cause; no binary/source change is authorized. |
| New synthetic primitive pair under unchanged listing policy | Selected only as the next diagnostic boundary, not a remedy or installed qualification pass. |

## Selected continuation: primitive parent-watch compatibility

Implement a **separate** offline-tested helper, then obtain setup review before
one bounded installed pair. It must accept only a clean pinned public-source
checkout and executable selection, never a root/log argument. Verify D093/D095
and this manifest and the exact D094 executable hash before launching anything.
Do not modify or run the D094/D096 observer or catalog/authenticated helpers.

Each leg owns a fresh locked mode-0700 disposable root and a hash-checked copied
binary. Run that binary in `BUN_BE_BUN=1` mode, using the inherited private
HOME/XDG environment, process-group/pipe/time bounds, spawn restrictions and
D070/D076 filesystem/network profile plus ancestor/machine denials. No server,
HTTP client, database, integration, provider or config loader starts. No network
operation is needed; add no network allowance. The sole experimental difference
is D094's literal `file-read-data` denial on the owned `home/repo` parent.
Do not accept environment/profile overrides or user paths. No chmod workaround,
permission expansion, alternative backend or retry.

1. **Listing-allowed control:** assert exact owned parent and inert candidate
   fixtures; require directory listing and direct reads to succeed. Acquire
   `fs.watch(parent, {recursive:false}, callback)` with the pinned names-filter
   behavior. An owned fixture writer creates/updates/deletes a named inert
   candidate after a private readiness signal. Require a bounded matching event
   for each sequential phase, empty stderr and clean watcher/process shutdown.
   Duplicate/coalesced events are not counted as separate operations; phase
   handshakes prevent pre-acquisition or cross-phase events from passing.
2. **Listing-denied leg, only after the control passes:** require listing refusal
   and the same direct candidate probes to succeed under the unchanged literal
   deny. Attempt the same watch acquisition, with bounded error listener and
   shutdown. Privately decode only finite `EPERM`, `EACCES`, `ENOENT` error codes,
   distinguishing synchronous acquisition from asynchronous callback failure.
   Every asynchronous watcher error, including recognized EPERM/EACCES/ENOENT,
   is a static refusal and never the expected synchronous incompatibility
   outcome; callback errors cannot explain D096's WATCH_START classification.
   Emit static stage/code labels, never raw errors/messages/stacks/paths/errno
   dumps. Unknown codes/shapes, missing provenance, malformed/oversized output,
   stderr, timeout or cleanup failure refuse with static codes. A synchronous
   EPERM/EACCES with correct listing/probe controls records **incompatibility**,
   not watch success. ENOENT contradicts the existing-parent fixture and refuses.
   If acquisition succeeds, apply the same phased event/close checks; this is
   only a primitive compatibility observation, not proof of OpenCode coverage.

Use separately bounded private fixture-writer coordination; validate all paths
against the owned root, refuse links/escapes/identity changes and retain no
child-supplied strings. Fixture writes are owned synthetic data only. Offline
adversarial cases must cover success, sync/async errors, unknown/secret-bearing
fields, listing/probe mismatch, premature/missing/wrong-target events, timeouts,
pipe overflow and cleanup on every exit. No raw output may escape exceptions.
Setup review must assess those fixtures and exact helper bytes before execution.
The pair has no retry; the first unexpected observation stops all later work.
A recognized synchronous denial ends the planned pair with an incompatibility
record and nonzero exit, with no attempted event phases on that failed watch.

Record the reviewed pair's sanitized result before its result review/merge.
Neither a positive primitive result nor an expected incompatibility closes case
3 or permits cases 4–6. Compatibility would require a separately reviewed
OpenCode-specific continuation; incompatibility requires a separately reviewed
source-boundary/remedy decision. Do not add warning exceptions, remove watch
requirements or migrate catalog/authenticated controls under either result.

## Validation and closeout

D093 clean-source/263-file audit, D095's 26 hashes/log-message tuples and all
parent-watch manifest hashes are checked read-only. Markdown links/anchor
fixtures and diff whitespace checks cover the documentation. No installed
runtime is invoked by those checks. Independent read-only review verified the pinned commit and 34 hashes and
identified one control-clarity concern: asynchronous watcher errors needed an
explicit refusal disposition. The plan now refuses every asynchronous error,
including recognized codes, separately from synchronous incompatibility.

All checks pass: D093/D095 qualification, **34/34** parent-watch hashes,
Markdown links/anchor fixtures and whitespace. Grok review/result and final task
handoff are recorded here before merge.
