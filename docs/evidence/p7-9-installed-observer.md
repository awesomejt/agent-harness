# P7.9 — Installed no-auth resource observation

Date: 2026-11-10. Entry: `028779b` (PR #89 merged). Prior
[observer/refusal design](p7-9-observer-refusal-design.md), D075;
[resource matrix](p7-9-resource-observation-matrix.md), D074;
[source boundary design](p7-9-source-boundary-design.md), D073;
[contained diagnostics](p7-9-contained-diagnostics.md), D070.

## Plan recorded before launch

Implement the D075 observer as an experiment helper, then run it against the installed,
hash-pinned OpenCode 2.2.5 on fresh owned roots. Compose D070's owned-port transport with
D073's machine-root read denials, and revalidate the combined boundary first. Derive the
expected built-in plugin set from the pinned checkout instead of copying it by hand. Run each
D074 row as a paired case with independent fixtures, including late-create, replace and reload
behaviour. Stop on any unsettled list, unexpected plugin, location leak or MCP start, and do
not weaken a boundary to get past a stop. Do not authenticate, start sessions, call models,
read real configuration, state or credentials, seed machine roots, or change production code,
the runtime pin, interfaces or D034.

**Result:** every D074 row now has installed paired evidence for fresh, unauthenticated state.
Two installed findings changed the boundary during the run, and both were resolved with paired
controls before acceptance:

1. **Legacy MCP entries are not inert.** A `disabled: true` entry written in the direct legacy
   shape started and failed. The pinned normaliser migrates that shape through the v1 schema,
   which has `enabled` but no `disabled` field. The stop condition caught it. Fixtures and the
   static guard now require the native `mcp.servers` shape.
2. **Project discovery watches every unowned ancestor up to `/`.** A static absence check is
   therefore not enough for late sources. The composed profile adds read denials for every
   discovery name in each ancestor above the owned HOME. A paired positive control shows a late
   ancestor source loading when it is not denied and staying excluded when it is.

Retained well-known and connected Console state remain blocked, as D075 recorded. **Full P7.9
and P7.10 remain unchecked, and P7.11 and P7.12 remain blocked.**

## Reproduction

On the accepted Apple Silicon macOS host, obtain the public v2.2.5 checkout with the D071
procedure. The helper refuses anything other than a clean worktree at
`9bbb8ce18c80f099e0e448775f59d965ead40a21` with the fingerprints below. From the repository
root:

```sh
python3 -B scripts/experiments/chatgpt_installed_observer.py --source <checkout>
python3 -B scripts/tests/chatgpt_observer_cases.py
```

The helper copies only the installed executable and requires SHA-256
`4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`. A missing executable,
byte drift, a wrong checkout and a dirty checkout each exit 1 with raw diagnostics withheld.
Each installed case uses its own temporary root, copied executable, freshly selected port,
generated server password and exclusively created data root, all discarded on exit. The
helper prints only PASS lines and a redacted JSON summary.

## Composed boundary

The profile is D070's (`/dev/null` data writes, one owned loopback TCP port, network,
operator-home read and outside-write denials) plus `file-read*` subpath denials for:

- the D073 machine roots, `/Library/Application Support/opencode` and
  `/Library/Managed Preferences`;
- `.claude`, `.agents`, `.opencode`, `opencode.json`, `opencode.jsonc`, `AGENTS.md` and
  `CLAUDE.md` in every ancestor above the owned HOME, up to and including `/`. This rule is
  new in this increment.

Combined controls run before any OpenCode server:

| Control | Observation |
|---|---|
| D070 transport matrix under the combined profile | Owned echo works; other TCP ports, ephemeral and wildcard binds, external TCP, UDP, IPv6 on another port and named Unix sockets are denied; operator-home reads and outside writes are denied. |
| Bun filesystem equivalents (`BUN_BE_BUN=1`, embedded Bun 1.4.4), paired on fresh roots | Under synthetic denials, `readFileSync`, `statSync`, `readdirSync`, `realpathSync`, `fs.watch` on the root, symlink-in reads, a late-created root and an atomic replacement all fail with `EPERM`. Without them, all succeed. An allowed sibling stays readable. |
| Existence oracle | `existsSync` still returns `true` for a denied file. Denial hides data and metadata, not `access()`-level existence. Discovery uses `stat`-based checks, so this is recorded as a limit rather than a source leak. |
| Allowed parent watch | An allowed parent's `fs.watch` reports a late child when it is not denied. When the child root is denied, it reports nothing (three of three runs), so a late machine root neither reloads nor reads. |

The real machine roots receive policy rules only; nothing probes or seeds them.

## Built-in plugin set

The helper parses the `pre` and `post` arrays in the fingerprinted `plugin/internal.ts`. It
resolves each entry through its import and covers namespace re-exports, spread groups, local
factories, `id` constants and the `@opencode/plugin-browser` package export. It refuses
duplicates, unresolved shapes and paths outside `packages/`. It derives **92 IDs from 91
files** (combined content SHA-256 `68e17ecbace37051b8813c683dbaa955321fa76477c847659fc1eb0b9a919e42`).
In every installed case, `plugin.list` equals that set exactly: 92 entries, all
`source.type: builtin` and `state.status: active`, with no `local`, `package` or `sdk` source.

Pinned built-ins also contribute the commands `init`, `review` and `goal`
(`core/src/plugin/command.ts`, `goal.ts`) and the skills `opencode`, `report` and `browser`.
Those skills report the virtual paths `/builtin/<id>.md` (`core/src/plugin/skill.ts`,
`plugin-browser/src/skill.ts`). The redactor accepts that virtual path only for those three
IDs. Every other skill path must lie under the owned root, which refines D075's redaction rule.

## Observer as implemented

The helper implements D075's protocol, with these specifics:

- **Request bounds.** Basic authentication uses the generated password and the pinned username
  `opencode` (`server/src/auth.ts`). Only five paths are allowlisted. A refused route never
  opens a connection.
- **Response checks.** Each request has a 5-second timeout, sends `Connection: close` and is
  closed afterwards. The response must be status 200 exactly, so a 3xx fails, and must be
  `application/json` within 256 KiB. The response envelope must echo exactly the owned
  location.
- **Location pinning.** `debug.location` reports no location before the first list request and
  exactly the owned project afterwards. That holds again after reload.
- **Settling.** The helper polls every 250 ms until all sentinels are present and the plugin
  inventory is exact, then requires two identical reads 500 ms apart, within a 30-second
  window.
- **Recorded fields.** Recorded values stay within D075's table. Skill content is reduced to a
  SHA-256 and a byte length, and MCP and plugin error strings are never kept.

## Paired installed cases

Every case starts from identical fixture content. The global config directory holds a sentinel
command, a skill and a disabled native-shape MCP server. The owned HOME holds `.agents` and
`.claude` skills. The project holds `.opencode` command and skill markers, `.agents` and
`.claude` skills, and an `opencode.json` with an agent and a disabled MCP marker. The parent
holds an agent canary. Only these options vary between cases: project discovery
(`OPENCODE_DISABLE_PROJECT_CONFIG`), `.claude` skills (`OPENCODE_DISABLE_CLAUDE_CODE_SKILLS`)
and whether the owned ancestor-equivalent is denied. Models fetch is off and file watching
stays on.

| Case | Project | `.claude` | Reload | Ancestor denied | Settled result |
|---|---|---|---|---|---|
| 1 | off | off | yes | yes | Global sentinels, home `.agents` skill and built-ins only. Every project and `.claude` marker is absent. |
| 2 | on | off | no | yes | Adds the project command, `.opencode` and `.agents` skills, the MCP marker, and the project and parent documents and agents. The project `.claude` skill stays absent. |
| 3 | off | on | no | yes | Adds only the home `.claude` skill. |
| 4 | on | on | yes | yes | Every marker is present, including the project `.claude` skill. The late ancestor MCP server is absent. |
| 5 | on | off | yes | no | Same as case 2. The late ancestor MCP server appears with status `disabled`: the positive control for case 4. |

Commands, skills and MCP are compared as exact sets. MCP entries must report `disabled`; any
`pending` or `failed` status fails the run. `debug config` must list exactly the owned global
document, plus the parent and project documents when discovery is on. `debug agents` must show
the matching canary agents. Skill names equal their scoped IDs. Sentinels and markers in one
list are registered in the same pass (D075), so an absent marker is anchored by a present
sentinel.

**Late-create, replace and reload.** In cases 1, 4 and 5, after the first settle, the helper
makes these changes:

- creates a global command and skill and a home `.agents` skill, in included roots;
- creates a project `.opencode` command and skill and a home `.claude` skill, which are
  gated by the case options;
- atomically replaces the global sentinel command with a new description;
- atomically rewrites the global document with an extra disabled MCP server;
- atomically writes an MCP document into the owned directory above the work root, which stands
  in for an unowned ancestor.

The second settle waits for the included late sentinels and the replaced description, then
requires exact sets. Gated markers appear only when their option is on. The ancestor document
loads only in case 5. The location pin holds afterwards.

**Runtime inventory from the synthetic server log.** The helper records only static messages,
labelled watch targets and spawned executables:

- **Watchers.** The parent entries watch on `/Library/Application Support` is acquired in every
  case, using the node backend, as D073 predicted. With project discovery on, entries watches
  are also acquired on the owned ancestor and on every unowned ancestor up to `/`. All other
  watches are under the owned work root. No `watcher failed` entry appears.
- **Spawns.** Location boot spawns only `git rev-parse` from the host developer tools. The
  allowlist accepts nothing else.
- **Warnings.** No `WARN` or `ERROR` lines appear in any case.
- **Writes.** No `node_modules` directory is created anywhere, and the write-denied MCP command
  directory stays empty. Runtime-created entries stay inside the owned root: Bun's extracted
  libraries in `TMPDIR`, the XDG directories and an `opencode` temporary directory.

The three installed runs during this increment passed with identical results, after
the two findings above were corrected.

## Row dispositions

| Row | Disposition after this increment |
|---|---|
| Config and agents | **Pass (fresh state).** `debug config`/`agents` show exact owned documents and canaries, with discovery on and off. |
| Commands | **Pass.** Sentinel-anchored pairs plus late create and atomic replace. |
| Skills | **Pass.** Global, project `.opencode`, project and home `.agents`, and project and home `.claude` are each paired. The `.claude` option gates only `.claude`. `.agents` has no switch and is safe here only because its roots are owned. |
| Instructions | **Static refusal (unchanged).** The walk up to the owned HOME and the global file stay free of `AGENTS.md`, documents and environment content carry no `instructions`, and ancestors above HOME are read-denied. Discovered-content proof remains a P7.11 gate. |
| Plugins and hooks | **Pass.** Static guards plus an exact post-activation set of 92 derived built-ins, all active. |
| MCP | **Pass, native shape only.** Disabled sentinel and marker pairs and a late addition all report `disabled`. A legacy direct entry is refused before launch because it would start. |
| Well-known integration | **Pass for fresh state; retained-cache pair blocked** (D075). |
| Console integration | **Pass for fresh state; connected pair blocked** (D075). |
| Persistent registrations | **Pass by construction.** An exclusively created data root per run is never reused. |
| Machine/MDM and changing sources | **Pass on synthetic equivalents.** The machine roots are read-denied and their parent watch is acquired. Under denial, Bun's late-root and replacement reads fail and the parent watch omits the denied late root. Unowned ancestors are read-denied, with an owned paired control. Real machine roots are never probed or seeded. |

## Limits

- **Scope.** The results cover fresh, unauthenticated state only. Any reused data root, login
  persistence, retained well-known registration or connected Console integration reopens the
  persistent-state rows (D075).
- **Path-based denial.** The denials do not track content provenance. Existence stays visible
  through `access()`, and copies, hard links, mount manipulation and inherited descriptors are
  outside the claim (D073). The ancestor rule covers only the pinned discovery names.
- **Host reads by the git child.** Location boot runs the host's git with the synthetic HOME.
  System-level git configuration outside the owned root stays readable to that child, and
  this was not inventoried.
- **Observer scope.** Instruction content and effective tool, permission, endpoint and helper
  behaviour are not observed. Fields the lists do not expose are not claimed.
- **Platform.** The evidence is for this experimental macOS host only, and the probe is opt-in
  tooling rather than production code.

## Next boundary

Full P7.9 is still not feasible to claim. The next focused task is the D047 exclusive-state
decision that D075 deferred. Before any login, it must resolve retained-state safety: the
well-known cache pair, the Console connection pair and a reused data root. Seeding either
retained pair may need a separate decision on KV writes or network exceptions. Effective
provider, model, helper, endpoint, permission and account gates and D034 stay separate.
Embedding or rebuilding OpenCode for core `discovery: false` remains a different integration
decision. Independent P8.2 Pi remains available, and no platform switch is needed.

## Fingerprints

The helper verifies these pinned files beyond D075's table. Paths are under `packages/`; on
Linux, use `sha256sum`.

| Pinned path | SHA-256 |
|---|---|
| `core/src/plugin/internal.ts` | `b3bf36bd6cbc0dd849d0a55f552696c588b486e79f22963124e68a91c2769b50` |
| `core/src/plugin/command.ts` | `a8efe5fb2fd28ec14d3286ed72beda982adad8ca76dddf26278475abf5ad3aa2` |
| `core/src/plugin/goal.ts` | `158c3721a9ad3974a0add78ee4c7cdf69a2b0fd75d7cee3dfff96b555ed8dbfc` |
| `core/src/plugin/skill.ts` | `e5db6b5bf57a79f83e62510a51826c14c7822c0fdb84b7fbc4c5f7bccee75b8b` |
| `plugin-browser/src/skill.ts` | `5267aabb4c987609502769dcdcceea61770bc6884cbf9b7dbca73ffdedc5b256` |
| `server/src/auth.ts` | `d2184b996991631490d7e82c19a7bd3310576c16fa2da2678819cac0a50f55c2` |
| `core/src/config/discovery.ts` | `48118dafc1ba0ec03112e98cdd616f339262a08a42b4ae75e9014575d863434d` |
| `core/src/config/normalize.ts` | `7ceeac61d778d447211bf6dd9fa6de4b0a46c4933d391573fc612ef3a98008c5` |
| `core/src/v1/config/mcp.ts` | `3d24c839c441bea5894c84b9f26d71e8ae2e223191c6724bb3e13c5a0df2eeee` |
| `util/src/fs-util.ts` | `9b0d2c0ec98338baa4fac2be0818496f501c3a07b6c22cebbdfc323427ba8d96` |
| `core/src/config/plugin/instruction.ts` | `b69cc3088bf6f5b70a2e3b1ee8d796ee81edc05a62036d4f5a6d62f5ef90a8f9` |
| `schema/src/plugin.ts` | `b453a0749f0213f141c29500e4033e2a0008e72d758ac97711310f053fd23d6a` |
| `schema/src/command.ts` | `6091f667ccf353e2ec7ac93902cd2c58b951236823f9411fb88174f9494932ab` |
| `schema/src/location.ts` | `cc899b5b9430c1edf62f353c8f49611a382511a544c09889e2da24f9ab2ddec4` |
| `schema/src/skill.ts` | `da003f8a6fd607569adb11e789c08eede92b044faa87648c422e69b47e281b4c` |
| `schema/src/mcp.ts` | `4fc2c6cd480552130a016ccb11160043e4c58e4833480ec9e208fcf4c4f3c8d7` |
| `schema/src/config/mcp.ts` | `72c8335c68fa0d72ad41bf784dea478325a769e7a39743dc242d760fdb9d951e` |

## Validation

- **Installed probe.** Three consecutive runs passed after correction. The missing-executable,
  byte-drift, wrong-checkout and dirty-checkout refusals pass.
- **Offline suite.** `chatgpt_observer_cases.py` passes and is included in `offline.py`. It
  covers route refusal before connecting, status, type, size and location bounds, connection
  close, strict redaction and owned paths, error withholding, exact plugin readiness, settle
  reset and timeout, native-only MCP, the instruction, plugin, symlink, content and environment
  guards, ancestor denials, watch labels, and plugin-ID derivation and its refusals. Writing it
  found one helper gap, an unknown list kind accepted when empty, which is now fixed.
- **Fingerprints.** The commit and clean worktree, all 41 D075 and 26 D074 fingerprints, and
  the 17 above were verified.
- **Other checks.** Python syntax, documentation links and anchors, link-checker fixtures and
  whitespace checks pass. Rust sources and dependencies are unchanged, and no direct-tool coding
  comparison applies.
