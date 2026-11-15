# P7.9 — Disposable OpenCode 2.3.0 observer and containment

Recorded: 2026-11-15, America/Denver. Baseline: `798ceed`.
Branch: `feature/07/p7-9-230-disposable-observer`. Decision: D094.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D093 source/observer contract](p7-9-230-source-requalification.md),
[prior installed matrix](p7-9-installed-observer.md).

## Scope and setup review boundary

This increment adds a separately pinned disposable no-auth helper, without
changing any 2.2.5 experimental helper or production behavior. Helper/setup PR
review precedes installed execution. The installed outcome is recorded below
only after that review completes. No retained-root argument, operator-state
access, auth-store read/copy, database query/seeding, authentication, session,
model turn or external-network expansion is selected. P7.9 remains unpassed
and P7.11 blocked; D034, D089 and separate Go gates remain unchanged.

```sh
python3 -B scripts/experiments/chatgpt_230_observer.py --source <clean-v2.3.0-checkout>
python3 -B scripts/tests/chatgpt_230_observer_cases.py
```

The helper first runs D093's exact clean-source/263-file audit, then copies and
hash-checks the installed executable against
`95af97f3638e0f0c0e6d4ae6b9b9ec546dde49a570344365ea60fab22e602db7`.
This is the D092 host-specific Homebrew 2.3.0 candidate, not a version-string
acceptance. Installed boots use exclusively created mode-0700 temporary roots,
private HOME/XDG, a held advisory lock with a second-process refusal check and
an environment constructed from scratch. Resource cases copy and recheck the
executable inside each new root. No root is imported or supplied by the caller.
Temporary runtime files are deleted after shutdown, including on refusal.

## Observer and refusal contract

The only added metadata GETs are `/api/provider` and `/api/integration`, in
addition to the D076 bounded authenticated loopback resource/location routes.
`provider.list` is an activation barrier on every snapshot. Its response is
bounded and checked against the pinned top-level provider shape, then discarded;
settings, headers, body, compatibility and identity fields are never recorded,
hashed or returned. Optional object interiors are opaque to this readiness
check; they are not a provider-routing proof. Integration output is strictly
redacted using the existing schema parser, and metadata is refused on fresh
roots. Any connection, including Console or OpenAI, refuses immediately.

The fixed **236-ID** count/digest, absence of command methods, exact built-in
plugin IDs and active/built-in states are enforced. Unexpected/duplicate
resources and non-disabled MCP entries refuse before readiness can retry.
Missing expected plugins/sentinels alone may wait. Completion requires two
identical full views at least the existing settling interval apart, within the
existing overall deadline. Only connection failures at the initial activation
barrier may retry. Once a snapshot starts, connection resets, HTTP/schema errors
and unknown failures stop; an unsafe partial observation cannot disappear into
a later good one.

Built-in skill URIs changed to `skill://opencode/SKILL.md`,
`skill://report/SKILL.md` and `skill://browser/SKILL.md`. The new redactor permits
only those exact ID/URI pairs. Other skills must remain under the owned root.
Only content digests/lengths survive in-memory view comparisons; raw content
and runtime diagnostics are withheld from output.

## Planned installed controls

Before resource observation, re-run the inherited macOS process/network/file
boundary controls, ignored-stdio `/dev/null` pair, occupied-port refusal without
connecting to the conflicting listener, absent/wrong private-server password
refusals, and Bun filesystem/watch/symlink/late-root/replacement pairs. The
source's `packageManager` and release build select Bun 1.4.4; the inherited
spawn fixture still requires that version. Any drift stops this increment.

Add a synthetic Bun pair for `config/discovery.ts`'s parent-listing and
individual-probe fallback. With listing allowed, the canary is found through
the listed name. With only the parent's directory-data read denied, fallback
still finds the readable named canary. Denying the canary itself refuses in
both branches. This tests the equivalent filesystem operations, not TypeScript
execution by itself; the installed parent-agent pair below consumes it.

| Case | Project | Claude skills | Reload | Ancestor denied | Parent listing |
|---|---|---|---|---|---|
| 1 | off | off | yes | yes | allowed |
| 2 | on | off | no | yes | allowed |
| 3 | on | off | no | yes | denied; individual-probe fallback |
| 4 | off | on | no | yes | allowed |
| 5 | on | on | yes | yes | allowed |
| 6 | on | off | yes | no; owned positive control only | allowed |

Every case is a new locked root. Reuse D076's inert native-disabled MCP,
command/skill/config/agent sentinels, static instruction/plugin/symlink guards,
machine/MDM and ancestor discovery-name denials. Check exact documents and
agent canaries plus global deny tails in `debug agents`; this is diagnostic
policy evidence, not actual tool-grant or constrained-model acceptance. Late
create/replace controls must settle to exact expected resources, with the owned
ancestor MCP visible only in its positive control. Log gates reject WARN/ERROR,
failed watchers, spawns other than `git rev-parse`, unclassifiable external watcher paths,
`node_modules` and any MCP command-directory entry; the machine-parent entries
watch must be present. Existing D073 path-denial/host-git limitations remain.

The fixed inventory must pass in every case. The helper does not add an explicit
catalog override to make a bundled inventory match. Any inventory/refusal or
unexpected boundary/source/resource result stops the run. Incomplete later
cases remain pending rather than being inferred from source or older results.
Inherited Console keys are refused before launch; a retained/synthetically
connected Console control remains a separate gate, not authority to seed or
attach existing credential state in this helper.

## Offline verification and installed outcome

The new observer suite covers route bounds, activation order/provider discard,
strict virtual-skill paths, unsafe observations during incomplete readiness,
fixed-inventory/method/plugin/resource refusals, stable settling and deadlines,
startup-only retry, inherited Console-key refusal and the separate executable
pin. New and existing source/contained/observer/retained/catalog/link suites pass
through the targeted runner (**8/8**). No Rust or dependency files change.

Independent review found and corrected a later-barrier retry edge case: after
the first successful snapshot, a wrapped barrier reset now refuses immediately.
A real-wrapper regression verifies exactly two barrier attempts. The log claim
was narrowed to match its path-classification gate; labelled owned/ancestor
watch inventories still require review after installed execution.

### Reviewed installed attempt and stop

Grok's initial setup review of `9ad82af` on
[PR #120](https://github.com/awesomejt/agent-harness/pull/120) completed with
**0 blockers, 0 concerns, 0 nits**, before any installed execution. Independent
safety review also verified the two corrections above. The reviewed helper was
then run once against the clean official source and the exact installed hash.

The installed attempt exited **1**, with this sanitized progression:

```text
PASS: ignored-stdio spawn failure and literal /dev/null correction
PASS: owned TCP echo; other TCP/binds, external TCP, UDP, Unix and filesystem denials
PASS: occupied port refused without a connection
PASS: absent and wrong private-server passwords refused
PASS: Bun read/stat/list/realpath/watch, symlink, late-root and replacement denials
PASS: Bun listing/fallback discovery branches and candidate read denials paired
PASS: disposable resource/inventory case 1
PASS: disposable resource/inventory case 2
START: disposable resource/inventory case 3
REFUSED: runtime-warning
```

| Installed row | Result |
|---|---|
| Exact source and executable guards | Passed before launch. |
| Spawn and `/dev/null` pair | Passed, including embedded Bun 1.4.4. |
| Inherited network/operator-home read/outside-write boundary | Passed. |
| Occupied port, wrong/absent server password | Passed. |
| Bun file/watch/symlink/late-root/replacement controls | Passed. As before, `existsSync` sees existence through denial; the allowed parent watch omits the denied late root. |
| Synthetic listing/fallback × candidate-read-denial pairs | All four passed. |
| Resource case 1 | Passed: project/Claude off, global/home-agent sentinels and reload; fixed 236 IDs, zero connections, exact active built-ins and all log gates. |
| Resource case 2 | Passed: project on/Claude off, ordinary listing; exact documents/parent-agent canaries, deny tails, fixed inventory and all log gates. |
| Resource case 3 | **Refused** at `logs()`'s WARN/ERROR gate after its resource/integration settling, document and deny-tail checks completed. No overall case pass. |
| Cases 4–6 | Not run after the stop. |
| Full installed qualification / catalog / retained / authenticated | Not accepted. |

The listing-denied root is fresh and distinct from cases 1–2. Its warning gate
ran after server shutdown; root/lock/process cleanup completed. No raw runtime
logs, provider bodies or skill content were emitted or retained. The helper's
sanitized code does not identify the WARN/ERROR message or cause. Therefore this
report does not attribute the warning to a specific watcher or assert that its
failure is harmless. Successful per-case watcher inventories are checked inside
the helper, but the final aggregate summary was not emitted because execution
stopped; their detailed labels are not independently recorded here.

The refusal is the required stop condition, not evidence to weaken the gate.
No warning allowlist, broader filesystem/network allowance, catalog override,
operator-root access or further installed attempt was added after the stop.
Production behavior and all old helper pins remain unchanged. This helper and
blocker-record increment may close on review/merge; it does not close D093's
installed qualification or full P7.9.

### Next reviewed boundary

Next perform a source-first assessment of warning paths reachable under the
literal parent-listing denial, then design a bounded static-code classifier
that withholds raw log fields/content. Review that diagnostic/setup increment
before another disposable installed attempt. Determine the actual warning and
its control impact before deciding whether to change the experiment. Do not
rerun case 3, advance cases 4–6 or migrate/run the catalog helper under this
record alone. Remaining rows and both catalog/retained/authenticated gates stay
pending; P7.11 remains blocked. A **fresh context** is preferred for this new
diagnostic boundary, using D093/D094 and this exact stop record.
