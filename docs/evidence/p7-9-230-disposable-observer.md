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

Installed execution is pending helper/setup review. No containment pass,
source-equivalence pass or catalog/retained/authenticated acceptance is claimed
by the initial helper revision. Review findings, installed results and the
next boundary will be recorded here before merge.
