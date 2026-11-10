# P7.9 — Shared source-read boundary design

Date: 2026-11-09. Entry: `93089957e74b58c4b641c69ece8f780d7aef5eb8`
(PR #86 merged).
Prior [source/state assessment](p7-9-source-state-controls.md), D071, and
[Go assessment](p7-10-go-feasibility.md), D072.

## Scope and result

Select a candidate macOS filesystem boundary for a separate installed no-auth
continuation. This increment runs synthetic OS controls only, without launching
OpenCode, probing real machine configuration, inspecting real persistent state,
creating authentication/session state or submitting inference. Production Rust,
dependencies, runtime pin, public interfaces and D034 fallback are unchanged.

**Design assessment passes with a synthetic candidate; full P7.9/P7.10 remain
unchecked and P7.11/P7.12 remain blocked.** D071's missing official CLI/server
exclusions remain unresolved at the interface level. This experiment establishes
kernel read-denial behavior on the tested host, not OpenCode discovery equivalence,
production isolation or route feasibility. It supplies the separate safe control
plan D071/D072 required before installed expansion.

## Pinned source and why metadata matters

Official OpenCode v2.2.5 remains commit
`9bbb8ce18c80f099e0e448775f59d965ead40a21`. The existing public checkout used
for P7.10 was rechecked at that exact commit; no dependencies were installed or
upstream code executed. This is tagged source, not installed-build provenance.
The official [configuration documentation](https://opencode.ai/docs/config/),
re-read on 2026-11-09, still describes machine directory and MDM precedence.
The pinned implementation determines the proposed boundary:

| Pinned file | Finding | SHA-256 |
|---|---|---|
| [core config discovery](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/discovery.ts) | System path is literal on macOS; MDM selects the first `isFile` match. Config tracks roots which can appear later. | `48118dafc1ba0ec03112e98cdd616f339262a08a42b4ae75e9014575d863434d` |
| [filesystem utility](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/util/src/fs-util.ts) | `isDir`/`isFile` catch stat failures and return false. `readFileStringSafe` also suppresses access-denied reads. | `9b0d2c0ec98338baa4fac2be0818496f501c3a07b6c22cebbdfc323427ba8d96` |
| [core config](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config.ts) | Only present system directories and selected MDM files load. MDM conversion invokes a `plutil` child. | `df2d83dff70a6cb3ef3e3a1d735bd397facc96ccf15794c6eb1a3646cef17390` |
| [config watch plan](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/watch.ts) | An absent system root still plans an entries watch on its parent, `/Library/Application Support`. | `1d0b5b6edf0222a0d2c763340e0469dc4fdcd3dbdcd35900498a9627228a49c1` |
| [filesystem watcher](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/filesystem/watcher.ts) | Entries watches use `fs.watch`; acquisition errors are logged and end streams. Root read denial is not watcher exclusion. | `1aa651de2352e41d30c35a5907f5005eb2be07dcf204e95d802145c484fa0d6b` |

Reproduce the five fingerprints in a public checkout at that commit:

```sh
git rev-parse HEAD
shasum -a 256 packages/core/src/config/discovery.ts \
  packages/util/src/fs-util.ts packages/core/src/config.ts \
  packages/core/src/config/watch.ts packages/core/src/filesystem/watcher.ts
```

Linux uses `sha256sum` with the same file arguments, without `-a 256`.
D071's inventory and interface fingerprints remain applicable. No version bump,
undocumented environment flag, config merge or empty array is selected as an
exclusion. Denying file data alone is insufficient evidence for discovery exclusion:
metadata can still mark a source present. An absence preflight is also insufficient
because sources can appear after startup.

## Candidate boundary

Extend the experimental D070 containment with kernel `file-read*` denials for:

- `/Library/Application Support/opencode`, recursively, including the root.
- `/Library/Managed Preferences`, recursively, including the root.

The second root deliberately covers all user-specific MDM paths without reading
an operator profile or deriving an OS username. This is a broader metadata/data
restriction than denying two literal plist names. Any installed incompatibility
requires refusal and reassessment; do not narrow it silently. Synthetic equivalents
are tested in a disposable directory; real machine roots receive policy rules only,
with no explicit stat/list/read probe. No machine-wide files are seeded or changed.

Retain D070's private copied/hash-pinned executable, empty environment allowlist,
private HOME/XDG, network restriction, outside-write denial, literal `/dev/null`
exception and bounded process-group lifecycle. The new helper has no port allowance;
when a later installed test needs D070's owned port, compose and revalidate the
combined profile explicitly. This experiment does not modify D070's accepted helper.
Start all runtime/diagnostic descendants under the boundary before any startup,
with fresh handles and private state; never attach to an existing unrestricted server.

A path denial is not a content provenance system. Copies or hard links already
placed under allowed paths are not covered by this claim. A hostile administrator,
mount manipulation, inherited open descriptors, sandbox escape and arbitrary foreign
content in allowed project/data roots are outside this synthetic proof. Disposable
roots and inherited stdio here contain only harness-owned inert fixtures. Later
installed tests must keep that ownership and establish their actual source inventory.
This is an experimental macOS candidate only; no other platform is advertised.

## Synthetic evidence

Run from the repository root on macOS with Command Line Tools Python available:

```sh
python3 -B scripts/experiments/chatgpt_source_boundary.py
```

On macOS 27.0.1 build 26A434, arm64, the paired controls passed:

- Data reads, stat and directory listing succeed without the synthetic deny rules
  and raise `PermissionError` with them; an allowed sibling remains readable.
- An allowed symlink pointing into a denied root and a symlink inside a denied
  root pointing out both remain denied, including metadata checks.
- Creating a new file, creating an initially absent source directory and atomically
  replacing an existing file after the sandboxed worker starts do not restore
  data/metadata access.
- The same matrix passes in a spawned descendant inheriting the boundary.

Both modes retain real machine-root denials and D070's base containment. Only the
synthetic root rules differ. No executable plugin, hook or MCP canary is loaded.
The existing bounded capture helper limits output/time and reaps the process group;
raw failure diagnostics are withheld. These observations do not establish Bun's
filesystem behavior, effective OpenCode resource lists or persistent-state safety.

## Separate installed continuation and stop conditions

Next take a focused P7.9 no-auth diagnostic increment:

1. Record its plan before launching. First produce a coverage matrix for every
   D071 resource category: commands, skills, instructions, plugins/hooks, MCP,
   well-known/Console integration and persistent registrations as well as agents.
   Map each to an evidenced supported read-only observation or static refusal
   invariant with paired inert canaries. Config/agents/paths output alone is not
   assumed complete. Missing visibility stops the experiment before launch.
   Reuse the exact copied 2.2.5 hash and D070
   owned-server transport; add both real-root denials before process creation.
   Verify combined network/home/write/stdio and source controls on this host.
2. Use only allowlisted config/agents/paths diagnostics. Verify actual startup
   succeeds or stops safely, with no attempt to relax machine-root denials on
   failure. Record parent-watch acquisition/failure and late-source reload
   behavior using disposable equivalents; an absent or denied system root does
   not eliminate its parent watch. Unsupported observation or unexplained reload
   behavior stops expansion. Do not mutate or watch-seed the real machine roots.
   Probe disposable source canaries through the same Bun filesystem
   implementation where possible; synthetic OS paths alone do not prove literal
   system/MDM discovery exclusion in the installed runtime. Never seed host roots.
3. Inventory effective resources with paired inert global/compatibility canaries,
   synthetic persistent registrations and current source output. Treat unexpected
   sources, executable resource activation, foreign endpoint access, unbounded
   cleanup or inability to demonstrate exclusion as a stop. Design cached-state
   fixtures before consuming any database and do not reuse the normal database.
4. If installed proof cannot safely establish the boundary without real machine
   config access, leave feasibility blocked and record the precise remaining
   evidence. No broadening, rebuild, runtime change or login follows implicitly.

Only after resource/persistent-state controls pass can a separate D047 decision
consider runtime-owned login in exclusive state. Provider/model/helper/endpoint,
permissions, account/spend checks and live acceptance remain separate route gates;
Go still needs D072's operator Extra Usage verification. Full feasibility is not
closed by this design PR. Independent P8.2 Pi work remains available. No platform
switch is needed; fresh context is efficient for the installed proof boundary.

## Validation and review

Synthetic probe, existing six-case diagnostic lifecycle/refusal suite, Python
syntax, documentation links/anchors/fixtures and whitespace checks pass. All five
pinned source fingerprints and clean checkout files were verified. Independent
security review found no critical/high issues and two medium gaps: omitted watcher
paths and incomplete diagnostic resource visibility. Both are addressed above with
watcher fingerprints, required watcher/reload observations and a coverage matrix
which must be complete before installed launch. Grok disposition follows at closeout. No Rust tests are needed for unchanged
production sources/dependencies. No direct-tool coding comparison applies.
