# P7.9 — OpenCode 2.3.0 warning assessment and diagnostic plan

Recorded: 2026-11-15, America/Denver. Baseline: `cc1ce8f`.
Branch: `feature/07/p7-9-warning-assessment`. Decision: D095.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D093 source contract](p7-9-230-source-requalification.md),
[D094 installed stop](p7-9-230-disposable-observer.md).

## Scope and evidence boundary

This source-only increment assesses the server and both debug clients and
specifies a diagnostic helper. It does not implement or launch that helper,
repeat case 3, advance cases 4–6, migrate the catalog helper or change any
runtime-warning refusal. The prior raw warning was deleted with its disposable
root; no historical log or operator state is inspected here. Its cause remains
unknown. P7.9 is unpassed and P7.11 blocked; D034/D089 and Go gates stand.

The clean public source is official commit
`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7` (v2.3.0).
The [additional 26-file manifest](p7-9-230-warning-source-manifest.json)
records SHA-256 of the assessed files relative to `packages/`. It supplements,
and does not replace, D093's 263-file manifest. No dependency code or installed
behavior is inferred to be exhaustively qualified by these source files.
The source findings below name symbols so they remain reproducible without
retaining local checkout paths or runtime output.

## Log ownership and process attribution

- `util/src/global.ts` makes `Global.Path.log` the data-root `log` directory.
  `util/src/observability/logging.ts:file()` selects `opencode.log` for a
  non-local release channel; the logger appends rather than rotating it.
  `cli/src/index.ts` provides `Observability.layer` using the build channel
  for every CLI command. Thus a shared private HOME/XDG data root also shares
  the log across the server and both debug client processes.
- `Logging.formatter` writes `run`, severity, messages, causes, spans and
  annotations. `observability/shared.ts:runID()` generates an eight-character
  UUID prefix once per process. It is useful for correlation but is neither
  an OS PID nor a collision-free identity. `cli starting` includes argv;
  command arguments must be compared privately, never emitted as diagnostics.
- `cli/src/index.ts` annotates `role=cli`; `cli/src/server-process.ts` annotates
  the inner serving effect `role=server`. `serve --stdio` calls the imported
  `server/process.ts:start` in the same process. A server process therefore
  has CLI startup and may have both roles under one run ID. A role alone is
  insufficient to identify the writer. Logger/layer acquisition can also
  precede the startup message; missing provenance must refuse attribution.
- `debug/config.ts` resolves the explicit server endpoint and calls
  `client.config.get`; `debug/agents.ts` waits for plugins then calls
  `client.agent.list`. Their resource discovery runs on the server, while
  CLI startup, fatal errors and local logging belong to each client. The server
  handlers in `server/src/handlers/{config,agent}.ts` delegate to the location
  config/agent services; both endpoint files are included in this manifest.
  `services/server-connection.ts:resolve` takes the supplied `--server` branch,
  checks health and returns without managed-service/standalone startup.
  Its version-mismatch warning writes directly to stderr, outside the file
  logger. `plugin-startup.ts` ignores activation polling failures; successful
  client exit alone does not prove warning-free server operation.
- Harness `chatgpt_230_observer.py:run_case` starts the server, settles resources,
  invokes both debug commands using the same env/data root, shuts down the
  server, then calls `logs`. The shared-file parser does not attribute writers;
  a late warning could originate in any of these processes. Client stderr is
  captured but discarded by this caller; the server drain bounds then discards
  its pipes. No saved D094 output establishes which process wrote the warning.

## Source paths affected by listing denial

`policy(..., listing_denied=True)` denies directory-data reads of exactly the
owned `home/repo` parent, leaving the named child probes under the inherited
boundary. `core/src/config/discovery.ts:discover` catches a failed
`fs.readDirectory(parent)` and probes each candidate directly. Neither that
catch nor the access-denied canonicalization in `util/src/fs-util.ts:resolve`
logs a warning. Agent directory scan failures are also swallowed in
`config/plugin/agent.ts:discover`; readable malformed/unsupported agent files
can warn later in `decode`. Instruction candidate access denial is a DEBUG
`denied` event in `config/plugin/instruction.ts`, while later source-load or
activation failures can warn. These distinctions prevent a broad permission
error classification from misidentifying the source. The synthetic Bun pair already proves the equivalent operations,
not the whole installed TypeScript/watch lifecycle. No evidence attributes the
warning to the fallback itself.

Discovery also changes eligible roots and watch targets. `config/watch.ts:plan`
keeps parent `entries` watches for roots including absent candidates, as well
as recursive config-directory watches. `config.ts` consumes those streams for
reload. A direct-probe discovery success therefore does not establish that a
parent watcher can start or deliver updates under a listing denial.

| Candidate family and pinned source | Static messages / control impact |
|---|---|
| `core/src/filesystem/watcher.ts:nativeLayer`, `subscribeDirectory` | `failed to watch directory`, `watcher callback failed`, `watcher backend not supported`, `failed to subscribe`. Non-ENOENT entry-watch failure logs ERROR and returns no subscription; a subscriber stream can end. Recursive subscription errors/timeouts also log ERROR. Watch coverage may be lost even if resource snapshots look correct. |
| `core/src/config.ts:parseInfo`, reload/background paths | `configuration normalization diagnostic`; `failed to reload config`, `failed to reload wellknown config`, `failed to reload wellknown sources`; well-known load/discovery/refresh failures and managed-preference conversion warnings. A config can be rejected, fields dropped or cached/previous state kept. None is an acceptable silent configuration success. |
| `core/src/config/variable.ts`, `config/plugin/{agent,command,skill,instruction}.ts` | Unreadable file references, `agent file skipped`, `ignored unsupported agent fields`, `command file skipped`, skill/instruction source or activation failures. Resources or policy inputs may be omitted. Compare exact sentinels and deny tails; do not infer harmlessness from a static message. |
| `core/src/config/plugin/{source,mcp}.ts` | Configured plugin path/watch and MCP reload failures. Static guards should exclude external configured plugins and active MCP, but any unexpected observation still stops. |
| `cli/src/index.ts` | `uncaught exception`, `unhandled rejection`, `cli process failed`; these can belong to server or debug clients and require a stop. |
| `cli/src/server-process.ts`, `services/server-connection.ts` | Invalid PTY handoff and service-directory warnings have explicit environment/mode predicates; a version mismatch goes to client stderr. The selected fresh env/stdio/explicit-server invocation should exclude these predicates; that expectation is not a runtime observation. |

This is a finite candidate assessment of the selected discovery/config/watch
and command chain, not an exhaustive list of dependency/plugin/HTTP logger
messages. Unlisted messages and malformed output require an unknown refusal.
All static strings above come from public source, not the withheld D094 log.

## Selected diagnostic contract for the next helper increment

The next implementation is a separate disposable, no-auth helper with offline
fixtures and its own setup review before installed execution. Keep the D093
source audit, this additional manifest, D094 executable hash, private roots,
locks, source/resource guards, bounded processes/output, network/filesystem
profile and fixed 236-ID/zero-connection gates. It must accept no retained-root
or log-file input and must not inspect operator roots, credential stores or
state databases. Do not add filesystem/network allowances or catalog overrides.

1. Parse only a newly created owned regular log file after all writers exit.
   Refuse symlinks, hardlinks, escapes, missing files and oversized input before
   reading; use an open descriptor with no-follow and identity checks to avoid
   check/read races. Limit the whole file to the existing capture byte budget,
   each line to 64 KiB, and records to 10,000. Refuse truncation, invalid UTF-8,
   malformed quoted fields, duplicate keys and incomplete lines. Do not use the
   old regex's permissive partial matches or last-key-wins dictionary behavior.
2. Build a private map from `cli starting` run IDs and exact expected argv to
   fixed labels `SERVER`, `DEBUG_CONFIG`, `DEBUG_AGENTS`. Require exactly one
   startup per expected process, unique run IDs, the known release version and
   channel, and no unexpected process. Apply the complete map after parsing so
   log ordering alone cannot change attribution. Missing/ambiguous attribution
   refuses; do not guess from time or role. Cross-check known launcher lifetimes
   and child exits. Roles are additional consistency checks, not identities.
3. Classify WARN/ERROR by exact public-source message and severity into fixed
   codes: `WATCH_START`, `WATCH_CALLBACK`, `WATCH_BACKEND`, `WATCH_SUBSCRIBE`,
   `CONFIG_NORMALIZATION`, `CONFIG_RELOAD`, `RESOURCE_INPUT`, `PLUGIN_INPUT`,
   `CLI_FAILURE`, `OTHER_SOURCE_WARNING`, `UNKNOWN_WARNING`. The implementation
   must enumerate each accepted message/severity tuple against pinned source;
   the family table alone is not a permissive matcher. For path-bearing
   candidates, compare the source-specific field (`path`, `directory`, etc.)
   privately to exact owned fixture targets and emit only predeclared labels
   such as `PARENT_REPO` or `OTHER_OWNED`; an unknown or outside path refuses.
   Never output a raw message, run ID, argv, path, cause, stack, dynamic field,
   content digest or exception text. Unknowns produce a fixed code only.
4. Keep causes opaque. A static message/path match identifies a source family,
   not the OS error or root cause. If an exact source-supported primitive error
   discriminator is needed, define and review its parser and finite enum before
   emitting it; do not search/print arbitrary cause strings. Capture client and
   server stderr within existing limits and withhold it too. Unclassified
   nonempty stderr refuses; structured logger records may use the same strict
   classifier, with no assumption that stderr is covered by the file log.
5. Output only fixed process/family/path labels, bounded counts and boolean
   control results. Any WARN/ERROR, including a recognized one, must still exit
   nonzero with `runtime-warning`; diagnostic collection must not turn a refused
   case into a pass. Any parser/provenance/control failure exits nonzero with a
   static refusal code. Cleanup is unconditional. Do not retain raw logs in a
   results directory or include subprocess output in exceptions.
6. Offline adversarial fixtures precede review: all three process writers,
   server startup with CLI role then server role, interleaving, duplicate/run-ID
   collisions, missing/extra startup, unknown roles/messages/severities,
   duplicate/escaped/multiline/truncated fields, invalid encoding, oversized
   input, unsafe file links/identity changes, outside paths, and secret canaries
   in every dynamic field and stderr. Assert exact sanitized output and failure
   status, including recognized WARN/ERROR. No installed runtime is needed for
   these tests.

## Installed diagnostic boundary after helper/setup review

Only after that separate implementation/setup review, revalidate the exact
source/binary and inherited transport/filesystem/discovery controls. The bounded
attempt is one fresh listing-allowed control and one fresh listing-denied
case-3 diagnostic, using the same project/Claude/reload settings as D094 cases
2/3. Each root is newly created and deleted; no original root is reopened.
The control must pass all old gates before launching the denied pair. Any
unexpected control result stops. In the denied pair collect one sanitized
failure summary, clean up and stop on the first warning or other refusal.
No retry loop, cases 4–6 or catalog continuation is authorized by that diagnostic.

If both roots unexpectedly pass without a warning, record non-reproduction;
it does not establish the historical cause or complete installed qualification.
If a warning is classified, record writer/family/owned-target labels and source
control impact, preserving the refusal. Any proposed remedy or change to the
experiment then needs a separately reviewed decision. In particular, a failed
parent watch must not be excused because direct probes succeeded. Full matrix,
catalog proof and revised authenticated controls remain later gates.

## Verification and closeout

Verified clean source commit, the additional manifest's 26 file hashes and the
existing D093 audit. Documentation links and `git diff --check` pass. No runtime
launch, historical log read, root/state/database access, login or model turn.
This increment can close after required PR review and merge; it accepts the
source assessment/plan only. Next implement and review the offline diagnostic
helper above. **Continue current context** for that closely related work; this
record and the two manifests also support a clean-context handoff.


## PR review result

Grok reviewed `194ab2f` on [PR #121](https://github.com/awesomejt/agent-harness/pull/121):
**0 blockers, 0 concerns, 0 nits**. Independent read-only source review also
completed; its server-endpoint manifest coverage nit was fixed before PR open.
All 26 source hashes and local links verify. No further Grok review is needed.
This source assessment/plan increment is effective on merge; helper
implementation and setup review remain next, with no installed rerun here.
