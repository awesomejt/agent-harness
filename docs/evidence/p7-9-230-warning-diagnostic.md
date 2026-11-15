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
refusal takes precedence over reporting only `runtime-warning`. Resource inventory, zero connections,
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

Pending helper/setup review; no installed diagnostic has run in this increment.
A classified warning identifies its source family and writer only; it does not
identify an opaque OS error or establish harmlessness. Record any stop without
changing containment or warning policy. Any remedy needs a separately reviewed
decision before another installed attempt. Complete matrix, catalog proof and
revised authenticated controls remain separate gates. If the helper stops at
an observation/parser/provenance check, record that exact static refusal rather
than inferring the historical warning. Cleanup is unconditional.
