# P7.9 — Disposable OpenCode 2.3.0 warning diagnostic

Recorded: 2026-11-15, America/Denver. Baseline: `65ad56b`.
Branch: `feature/07/p7-9-warning-diagnostic`. Decision: D096.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D095 source assessment/plan](p7-9-230-warning-assessment.md),
[D094 installed stop](p7-9-230-disposable-observer.md).

## Selected implementation and setup-review boundary

This increment implements D095 in `chatgpt_230_warning_diagnostic.py` and the
separate strict parser `chatgpt_230_warning_log.py`. It accepts only a clean
public-source checkout and an executable selection, never a root or log-file
argument. Every resource case creates and deletes a fresh locked mode-0700
root, copies/rechecks the existing D094 executable hash, reconstructs the
private HOME/XDG environment and preserves its filesystem/network profile.
No old experimental helper, production code, runtime pin or dependency changes.
No operator root/state/database/credential access, login, model turn or catalog
migration. P7.9 remains unpassed and P7.11 blocked; D034/D089 and Go gates stand.

Helper/setup review must finish before installed execution. The installed
attempt and any stop will be recorded below only after that review. Scope is
exactly inherited transport/filesystem/discovery controls, one listing-allowed
control and one listing-denied case-3 diagnostic, with project on, Claude off,
no reload and ancestor denials. The control must pass every gate before the
denied case starts. No retry or cases 4–6. A recognized warning still refuses.

```sh
python3 -B scripts/tests/chatgpt_230_warning_log_cases.py
python3 -B scripts/tests/chatgpt_230_warning_diagnostic_cases.py
# Only after setup review:
python3 -B scripts/experiments/chatgpt_230_warning_diagnostic.py --source <clean-v2.3.0-checkout>
```

## Log and process controls

The helper first runs D093's clean-source/263-file audit and verifies D095's
additional 26-file manifest. Classifier message/severity tuples are checked
against those pinned public-source logging calls. Its expected release version
is 2.3.0 and channel is `latest` (the public release build channel); drift refuses.

All three processes share only the new data-root log. After writers exit, the
parser reads the owned regular file through no-follow descriptors, refusing
links, escapes, ownership/identity changes, missing files and oversized input.
The file is bounded to the existing 2 MiB capture budget, lines to 64 KiB and
records to 10,000. Full-line parsing rejects duplicate keys, invalid encoding,
malformed quoting, literal controls and truncation. Causes and dynamic values
remain private; no rejected bytes appear in exceptions or summaries.

`cli starting` plus exact private argv/version/channel maps unique run IDs to
`SERVER`, `DEBUG_CONFIG`, `DEBUG_AGENTS`. Every log record must map to a known
writer and fall within that launcher's observed wall-clock lifetime. Startup
records and server/CLI role consistency are checked without treating a role as
a process identity. Missing/ambiguous provenance or timing drift stops rather
than guessing. Client capture requires successful child exit; the server must
exit cleanly after stdin closure, and its process group and both pipe threads
are reaped. Server stdout must contain only the exact private readiness line.

Server/client stderr is captured within existing pipe budgets and withheld.
Any nonempty stderr refuses with a static code; there is no plaintext allowlist.
This is a conservative implementation of D095, which permits but does not
require classification of structured stderr records. It cannot convert an
unobserved stderr warning into a clean file-log result.

Recognized WARN/ERROR tuples yield only finite process/family/fixture-target
labels and bounded counts. Exact owned target paths come from prelaunch
fixtures; unrecognized targets/messages refuse with fixed codes. No raw
messages, paths, argv, run IDs, causes, stacks or content digests are emitted.
Warnings produce a sanitized summary followed by `REFUSED: runtime-warning`
and nonzero exit. The existing non-warning log/watch/spawn/node_modules/MCP-command gates run
before emitting a summary for either a clean or warning case. A containment
refusal takes precedence over reporting only `runtime-warning`. Deliberately,
if a non-warning containment check fails, the already-private warning
classification is not printed: only the final static containment refusal is
recorded. This loses classification evidence in that branch and requires a
separately reviewed continuation; it never implies the warning was absent. Resource inventory, zero connections,
provider activation, exact sentinels/documents and deny tails remain mandatory.

## Offline verification

The parser suite exercises writer interleaving, server CLI/server roles,
startup/run collisions, missing/extra provenance, unknown roles/severities,
message/severity drift, strict field boundaries, encodings/bounds, owned file
links/identity changes, path refusal and secret-bearing dynamic fields.
The runner suite uses inert Python subprocesses, never installed OpenCode, to
check pipe bounds/readiness/stderr preservation, lifecycle cleanup, sanitized
warning refusals, inherited final gates and control-before-denial ordering.
Both suites are self-contained and registered with the existing targeted offline
runner; no downloaded source checkout is needed by their fixtures. The real-source
qualification is a separate read-only check. Targeted new/inherited suites pass
**8/8**, the real-source audit and finite logging-call checks pass, and repository
Markdown-link/diff checks pass.

Independent safety review found and corrected cleanup on failed stdin close,
non-warning containment checks on warning cases, no-follow/nonblocking/exact-size
file reads, source-faithful quoted startup arguments, fixed warning counts and
filesystem-source mapping. Regressions cover each correction. No installed
runtime has run during this offline preparation.

## Installed outcome and next boundary

Grok's setup review of `2dea092` on
[PR #122](https://github.com/awesomejt/agent-harness/pull/122) completed with
**0 blockers, 0 concerns, 1 nit**. The nit is addressed by explicitly documenting
the deliberate suppression of warning classification when another containment
gate fails. The reviewed helper/test bytes remain unchanged; no further setup
review is required for that documentation clarification. Independent safety
review also cleared the final implementation. The one installed attempt followed that review, with the result below.
A classified warning identifies its source family and writer only; it does not
identify an opaque OS error or establish harmlessness. Record any stop without
changing containment or warning policy. Any remedy needs a separately reviewed
decision before another installed attempt. Complete matrix, catalog proof and
revised authenticated controls remain separate gates. If the helper stops at
an observation/parser/provenance check, record that exact static refusal rather
than inferring the historical warning. Cleanup is unconditional.


### Reviewed installed attempt and required stop

The reviewed helper was run once after the setup review, using the clean
official source and exact D094 executable hash. The process exited **1**.
The only recorded runtime summary was sanitized by the reviewed helper:

```text
PASS: inherited transport/network/filesystem/password/port controls
PASS: Bun filesystem/watch/symlink/late-root/replacement controls
PASS: synthetic listing/fallback discovery and candidate-denial pairs
START: listing-allowed diagnostic control
processes=3 records=85 warnings=[]
PASS: listing-allowed diagnostic control
START: listing-denied case-3 diagnostic
processes=3 records=85
warning: process=SERVER family=WATCH_START target=PARENT_REPO count=3
REFUSED: runtime-warning
```

| Installed check | Result |
|---|---|
| D093 source, D095 supplemental hashes/message tuples and D094 executable pin | Passed before launch. |
| Inherited spawn/stdio, owned TCP versus denied network/filesystem, occupied port and wrong/absent password | Passed. |
| Bun filesystem/watch/symlink/late-root/replacement and four listing/fallback × candidate-read pairs | Passed, with inherited existsSync/parent-watch limitations unchanged. |
| Fresh listing-allowed control, project on/Claude off/no reload | Passed all gates, 3 attributed writers, 85 bounded records, zero warnings and empty stderr. |
| Fresh listing-denied diagnostic, same fixture options | Resource/integration settlement, exact documents/agent canaries/deny tails and every non-warning log/filesystem gate passed. 3 attributed writers and 85 bounded records; empty stderr. Required **runtime-warning** refusal from three SERVER/WATCH_START/PARENT_REPO events. No case pass. |
| Complete matrix, catalog and retained/authenticated continuation | Not run or accepted. |

Both resource cases enforced the unchanged 236-ID digest, zero integration
connections/metadata, exact active built-ins/resources, machine-parent watcher,
spawn allowlist and absence of node_modules/MCP commands. The reviewed parser
accepted actual installed formatting, unique startup/run ownership, server/CLI
roles and observed launcher-lifetime windows. All writer processes exited
cleanly; pipe threads/groups were reaped, locks released and temporary roots
deleted before the command returned. No raw log, stderr,
cause, dynamic path, argv or provider/resource content was retained in evidence.

### Source attribution and control impact

`WATCH_START` is the exact ERROR tuple for `failed to watch directory` in
`core/src/filesystem/watcher.ts:nativeLayer`, with the `path` privately matched
to the owned parent-repo fixture. It identifies the server's entry/file watch
startup failure, rather than a debug-client warning or the silent
`ConfigDiscovery.discover` listing fallback. The source's non-ENOENT catch logs
this error and returns no subscription, so affected subscriber streams can
end without watch coverage. Direct config probes and stable initial resource
views do not replace that coverage. Three matching log events do not identify
three distinct subscriptions or establish their cause/retry ordering.

The underlying error/cause was opaque and discarded. This does not assert an
OS error code, identify which named candidate watchers were affected or prove
the failure harmless. It provides source-family/writer/owned-target attribution
and a control-impact bound for this new listing-denied stop under D094's
fixture options. The deleted historical D094 warning remains unattributed. No exception, broader
filesystem/network permission, catalog override or rerun was introduced.

Next is a **source-first parent-watch control/remediation assessment and a
separately reviewed continuation decision**, using this exact result. Do not
retry the diagnostic, advance cases 4–6 or migrate/run catalog/authenticated
helpers under this record. The helper/result increment can close after result
review/merge without passing full installed qualification or P7.9. Use a
**fresh context** for the next control/remedy design boundary.
