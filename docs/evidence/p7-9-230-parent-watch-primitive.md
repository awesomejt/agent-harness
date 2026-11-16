# P7.9 — Disposable OpenCode 2.3.0 parent-watch primitive

Recorded: 2026-11-15, America/Denver. Baseline: `b118e3a`.
Branch: `feature/07/p7-9-parent-watch-primitive`. Decision: D098.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D097 assessment/plan](p7-9-230-parent-watch-assessment.md),
[D096 installed stop](p7-9-230-warning-diagnostic.md).

## Scope and review boundary

Implements D097 in `chatgpt_230_parent_watch.py` and the inert
`chatgpt_parent_watch.mjs`. Only `--source` and executable selection are accepted;
there is no root/log/environment/profile override. D093/D095/D097 source checks
and the exact D094 executable hash precede experimental child launch. Setup review must
complete before one installed listing-allowed/denied primitive pair. Record
its sanitized result and obtain result review before merge. First unexpected
observation stops; no retry, D096 rerun or case 4–6 advancement.

This starts the copied executable in `BUN_BE_BUN=1` mode with a static owned
script. It imports only standard filesystem/path/readline/URL modules, never
OpenCode code. No service, HTTP client, provider, integration, catalog/config
loader, database, auth/session/model call or retained/operator-state access.
No existing experimental helper, production dependency, route, runtime pin or
operator root changes. P7.9 stays unpassed, P7.11 blocked; fixed 236-ID/D034/D089
and separate Go gates remain unchanged.

```sh
python3 -B scripts/tests/chatgpt_230_parent_watch_cases.py
# Only after helper/setup review:
python3 -B scripts/experiments/chatgpt_230_parent_watch.py --source <clean-v2.3.0-checkout>
```

## Containment and owned fixtures

Each leg creates and removes a fresh locked mode-0700 root, copies/rechecks the
binary and creates private HOME/XDG directories. The D070/D076 composed profile
retains machine/managed-preference and ancestor-source denials. There is no
owned TCP allowance: network remains entirely denied. Process forks are denied
and exec is restricted to the copied binary. The sole difference between legs
is the existing literal `file-read-data` denial of owned `home/repo`.

Only the private parent/project directories, one inert direct-probe file and
one phased candidate are needed. Driver checks directory/file ownership,
no-follow identities, regular-file types, link counts and contents before and
after mutation. Creation stages complete inert bytes outside the watched parent
before rename, avoiding a creation callback observing an empty file. Updates
preserve the candidate inode; deletion must leave it absent. No arbitrary
child-supplied path or content is retained or used. HOME/XDG credentials are
never populated; nonempty XDG state directories refuse after shutdown.

## Protocol, event interpretation and refusal

A fresh private nonce binds the finite line protocol to each launched child.
The selector supervisor bounds the combined pipes to 2 MiB and the whole child
lifetime to 10 seconds, rejects nonempty stderr, unknown/extra/missing output,
nonzero exit and any stage mismatch. No raw child bytes are decoded into error
messages or public summaries. Nested cleanup closes stdin, terminates/kills and
reaps the process group and closes all pipes/selectors, including failures.
Only after child cleanup, lock release and root deletion may a leg's finite
summary be printed.

The child pairs exact listing success/refusal with a successful owned direct
read, then calls the source-faithful nonrecursive parent `fs.watch` primitive.
A synchronous EPERM/EACCES on the denied leg records incompatibility and yields
a nonzero final exit. ENOENT/unknown startup errors, every asynchronous error,
probe mismatch, readiness/event/cleanup failure or unexpected output refuses.
These are primitive results, never an OpenCode warning exception or proof of
D096's opaque cause.

When acquisition succeeds, three sequential arm/mutate/event phases exercise
candidate creation, update and deletion. Names are filtered as in the pinned
source; phase matching accepts the candidate or null filename and ignores
rename/change eventType. A null filename has the source's fanout limitation and
does not identify which entry changed. Duplicate callbacks are discarded once
a phase has observed an event and during the 150 ms quiet arm interval. The
candidate's expected contents/absence must agree before acknowledging an event.

The phase handshake, state check and quiet interval bound attribution; they
cannot prove OS-event causality or rule out an arbitrarily delayed callback
coinciding with a later mutation. No claim of exact event counts, exhaustive
kernel delivery or OpenCode readiness/reload coverage follows. A compatible
primitive requires a separately reviewed OpenCode-specific continuation; an
incompatible result requires a separately reviewed source-boundary/remedy
decision. Neither result passes case 3 or permits catalog/authenticated work.

## Offline verification and installed outcome

Offline tests use inert subprocesses and disposable fixtures; they never run
installed OpenCode. Source qualification is read-only against the clean pinned
public checkout. Verification, independent safety review, Grok setup review and
the single installed result will be recorded below as they complete.

Offline verification (2026-11-15): `chatgpt_230_parent_watch_cases.py` passes
five consecutive runs and `scripts/tests/offline.py` passes **48/48**. Fixtures
cover the clean three-phase path with null filenames, the candidate filename with
swapped rename/change eventTypes plus ignored unwatched-name noise, synchronous
EPERM recorded as incompatible through the real driver, an asynchronous EACCES
arriving after READY that refuses before any mutation, a listing mismatch, a
throwing watcher close that still terminates promptly with `FAIL`, stderr,
malformed protocol and pipe-overflow refusals, owned-path drift and sanitized
entry output. Completing the suite fixed a test-string syntax error and an
async fixture ordering assumption, and the child's `stop()` was hardened so a
failed close can never silence the protocol or emit a success label. No
installed OpenCode, sandbox or source checkout was used.
