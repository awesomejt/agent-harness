# P7.9 — Resource observer and static-refusal design

Date: 2026-11-10. Entry: `eeb2c557a325c4a3758a7317997161ecf5e03321`
(PR #88 merged). Prior [pre-launch resource matrix](p7-9-resource-observation-matrix.md), D074;
[source boundary design](p7-9-source-boundary-design.md), D073; [contained diagnostics](p7-9-contained-diagnostics.md), D070.

## Plan and result

Follow D074's next step. Assess the pinned official command/skill/plugin/MCP list APIs
together with the whole service-initialization path behind them. Then select an exact
owned-server GET allowlist, response bounds and redaction, and resolve the pre-activation
invariants for instructions and plugins. Finally, design paired inert fixtures and
synthetic cached-state treatment for every matrix row. Inspect only public pinned
source. Do not launch OpenCode, implement an observer, read real configuration, state
or credentials, seed machine roots, create a database, install dependencies, or make
authentication, session or model calls. Keep production code, the runtime pin,
interfaces and D034 unchanged. Stop rather than claim coverage for any row whose
invariant cannot be established.

**Result:** the design resolves every D074 row for one scope: a fresh-state, no-auth
installed continuation. Four findings reshape the observer:

1. **No list API runs before activation.** Any location-scoped request boots the whole
   location service graph, and that boot immediately activates every plugin and forks
   MCP startup.
2. **The list handlers do not wait for activation to settle.** An empty list is not
   evidence of absence unless it is anchored by a co-registered sentinel.
3. **Instructions have no server observer.** They rely on static refusal only.
4. **Positive retained-state pairs are outside this boundary.** Retained well-known
   registrations and a connected Console integration cannot be seeded without
   unsupported database writes, a wider network exception or credential-like state.

The next continuation therefore requires an exclusively created data root for each
run, never reused. Retained-state safety stays a precise gate before any state reuse
or D047 login decision. Nothing was launched. Full P7.9/P7.10 remain unchecked and
P7.11/P7.12 blocked.

## Initialization findings

All paths are relative to `packages/` in the official v2.2.5 checkout at
`9bbb8ce18c80f099e0e448775f59d965ead40a21`. These are source observations, not
verified installed-build provenance.

- **Location boot is the activation point.** `server/src/location.ts` provides every
  location-scoped handler through `LocationServiceMap.get(requestRef(request))`.
  `core/src/location-services.ts` builds `Instance.layer(ref, …)` on first use, without
  the core `discovery: false` option. `core/src/instance.ts` compiles the full graph:
  config, plugins, the plugin supervisor, MCP, skills, instructions and the location
  watcher. `requestRef` uses `location[directory]`, then the `x-opencode-directory`
  header, then `process.cwd()`. An unpinned request can therefore boot an unintended
  directory.
- **Plugins activate during boot.** `core/src/plugin/supervisor.ts` holds the registry
  latch and starts the first `activate()` immediately when the layer is built. That
  call resolves sources, imports local modules, may install package plugins and runs
  each plugin's effect. `core/src/plugin.ts` sets `list()` to the inventory produced by
  activation. The built-in set (`plugin/internal.ts`) includes, among others, the well-known,
  provider, models, dynamic SDK, MCP, command, skill and instruction plugins, so boot
  itself carries their effects. **`plugin.list` can confirm what happened after
  activation. It cannot serve as a safety guard before activation.**
- **The plugin directory rule is narrow and static.** `plugin/source-directory.ts`
  reads only `plugin/` and `plugins/` under each directory config entry. It accepts
  `.ts`/`.js` files, any directory, and symlinks to either. `config/plugin/source.ts`
  adds document `plugins` directives, resolving relative paths against the document
  directory, and watches configured targets outside the roots.
- **MCP startup is asynchronous, and `disabled` is inert.** On the first reconcile,
  `core/src/mcp/index.ts` registers each entry, then forks `startServer` unless
  `config.disabled` is true; a disabled entry gets status `disabled` with no start.
  `register` returns immediately for non-remote entries. `config/plugin/mcp.ts`
  merges servers from all documents by name in one pass, so a later document with
  the same name replaces an earlier one.
- **The lists do not wait for activation, and no barrier is available.** The
  `command.list`, `skill.list`, `plugin.list` and `mcp.list` handlers return the
  current state. Only `usage.limits` waits on `awaitPlugins`, and it resolves the
  Console credential connection and may refresh it, so it is excluded.
  `event.subscribe` is volatile by contract and publishes only on change.
  `debug.location` lists loaded locations without booting one.
- **Commands and skills register in one pass.** `config/plugin/command.ts` loads
  every config entry and then applies a single `command.transform`. Templates are
  evaluated only in `execute`, and `Command.Info` exposes only `name` and
  `description`. `config/plugin/skill.ts` refreshes every source, including HTTP(S)
  URL sources pulled through discovery, and then applies a single `skill.transform`.
  `Skill.Info` includes the full `content` and an absolute `path`.
- **Instructions have no list API.** `config/plugin/instruction.ts` reads the global
  `AGENTS.md`, the ancestor walk under project discovery, configured paths and globs,
  and fetched instruction URLs. No server group exposes the discovered content; the
  session instruction-entry API covers API-managed entries.
- **Persistent integration state is stored in the KV table.** `core/src/wellknown.ts`
  stores `wellknown:sources`, `wellknown:manifest:<origin>` and
  `wellknown:config:<origin>` in the `kv` table (`kv/sql.ts`). A manifest that fails
  to load falls back to the cached copy. Console remote configuration starts from
  `integration.connection.active("opencode")` (`plugin/provider/opencode.ts`) and
  resolves over the network.
- **Exposed controls.** `cli/src/server-process.ts` maps environment variables to
  `config.project`, `config.claude` (the `.claude` skill roots only),
  `fs.filewatcher` and models fetch. There is still no global/system exclusion
  (D071), and the `.agents` compatibility roots have no separate switch.

## Selected observer protocol

This protocol is design only and is not implemented. A later continuation consumes
it under D070/D073 containment.

- **Endpoint allowlist.** Use authenticated `GET` with the D070 generated password on
  the owned `127.0.0.1:<port>` only, for these paths:
  - `/api/debug/location` (does not boot a location)
  - `/api/command`, `/api/skill`, `/api/plugin` and `/api/mcp`, each with an explicit
    `location[directory]=<owned project root>`

  Every other route is refused before sending, including `usage`, `integration`,
  `credential`, `plugin.check/update/gui`, `mcp.resource.catalog`, the MCP mutations,
  `location.*`, `config.update`, `debug.heapDump`, `debug.location.evict`, `event`
  and sessions.
- **Location pinning.** Before the first list request, `debug.location` must report
  no loaded location. Afterwards it must report exactly the owned root, and no other
  location may appear.
- **Transport bounds.** Do not follow redirects; a 3xx is a failure. Require a JSON
  content type and an exact successful status. Cap each body at 256 KiB, each request
  at 5 seconds and the whole observation window at 30 seconds. Close the connection
  after every response.
- **Schema and redaction.** Validate each response strictly against the pinned
  schema. Record only the fields below; any unexpected field or status fails closed:

  | Source | Recorded fields |
  |---|---|
  | Commands | `name`, `description` |
  | Skills | `id` and `name`; `path` relative to an owned root, otherwise fail; SHA-256 and byte length of `content`, never the body |
  | Plugins | `id`, `source.type`, local path relative to an owned root, `state.status` |
  | MCP | `name`, `status.status` |

  Never record error strings, titles or integration identifiers.
- **Settle rule.** Poll every 250 ms within the window until every included sentinel
  appears in its list and the plugin inventory equals the expected built-in set,
  all `active`. Then require two consecutive identical reads at least 500 ms apart
  (beyond the 100 ms source debounce) before asserting any absence. A timeout fails.

## Row dispositions

Each paired case uses independent, freshly created owned fixtures: an empty
synthetic HOME/XDG, config directory, data root, project and parent. Both cases start
from identical content; the excluded side is varied only by the documented option or
root placement. Each assertion names an exact positive marker and an exact absence.

| Row | Disposition for the fresh-state no-auth continuation |
|---|---|
| Config and agents | **Resolved.** Use D070 `debug config`/`agents` with distinct canaries in the owned global, compatibility, project and parent roots, with project discovery enabled and disabled. The agent and config outputs remain separate observations. |
| Commands | **Resolved.** Put an included sentinel command in the owned global config directory and a marker command in the varied root, both inert Markdown with unique names. The positive case lists both; the negative case lists the sentinel without the marker. Because commands register in one pass, sentinel presence anchors marker absence. Never call `command.execute` or sessions. |
| Skills | **Resolved.** Use the same sentinel/marker pattern, with skill names distinct per scope: global, project, `.claude` and `.agents`. The `config.claude` option gates `.claude` only; `.agents` roots exist only under owned HOME and project. Statically refuse any `skills` URL entry. Record the content hash, never the body. |
| Instructions | **Resolved by static refusal only, under discovery on and off.** The ancestor walk in `config/plugin/instruction.ts` runs from the resolved location directory up to `stop`, which is HOME when the location is inside HOME and otherwise the project root. Fixtures must therefore place the owned project and parent beneath the owned synthetic HOME, with no symlinked path components, so `stop` is the owned HOME and every directory the walk can reach is owned. Before launch, in both cases, require that no `AGENTS.md` exists in the owned global config directory or in any directory from the location up to and including the owned HOME, and that no `instructions` entry exists in any owned document, file or environment content. Instructions are non-executable prompt context with no observer and are consumed only by sessions, which are out of scope. Proving discovered instruction content stays a P7.11 consuming gate. |
| Plugins and hooks | **Resolved as a static guard plus post-activation confirmation.** Before launch, require that no owned eligible root contains a `plugin/` or `plugins/` entry of any type, that no owned document contains a `plugins` directive, and that no SDK or instance plugins are injected. After settling, `plugin.list` must equal the expected built-in set exactly, all `active`, with no `local` or `package` source. The expected set is the IDs of the `pre` and `post` arrays in the fingerprinted `plugin/internal.ts`, including their spread provider, web-search and optimize groups, each with `source.type` `builtin`. The helper derives this set from that file and records it, rather than relying on a hand-maintained copy; any difference in the installed build fails the run. No positive discovery fixture: an executable canary remains forbidden. |
| MCP | **Resolved.** Use an included sentinel and a varied-root marker, both `type: "local"` and `disabled: true`, each running a nonexistent absolute command under a write-denied owned path, with unique names. Positive: both report status `disabled`. Negative: only the sentinel is listed. Status `failed` or `pending` means a start was attempted and fails the run. |
| Well-known integration | **Resolved for fresh state; retained-cache pair blocked.** An exclusively created data root has no `wellknown:sources`, so no origins load (source-proven). Seeding a retained registration would require either `integration.wellknown.add`, which is a mutation that fetches the origin and needs a network exception beyond D070's single port, or direct writes to the internal KV schema. Both need a separate decision. |
| Console integration | **Resolved for fresh state; connected pair blocked.** With fresh state and a cleared environment, `connection.active` has nothing to return. A positive fixture needs a credential-like row and a network `resolve` or refresh, both outside the D047/D067 boundaries. |
| Persistent registrations | **Resolved by construction for this scope.** Create one data root per run with an exclusive create, never reuse it, and discard it on exit. Any reused root, as login persistence would need, reopens this row together with the two blocked pairs above. |
| Machine/MDM and changing sources | **Assigned to the next task.** Compose D070 with the D073 denials, set models fetch off and file watching on, and keep the location watcher's activation behaviour in scope. Add Bun discovery equivalents and synthetic late-create/replace/reload pairs using the sentinel settle rule. Never probe real machine roots. |

## Next boundary and limits

The next focused task is the installed no-auth continuation that D073 planned and
D074 deferred. It will implement this observer as an experiment helper, then compose
and revalidate D070 transport, the D073 denials and these static guards. It will run
every row's pair on fresh roots, including watcher/reload, and record any boot-time
network, install or write attempt as a refusal under containment. It stops on any
unsettled list, an unexpected plugin, a location leak or an MCP start, rather than
weakening the boundary.

Login does not follow implicitly. A D047 exclusive-state decision must first resolve
retained-state safety: the well-known cache pair, the Console connection pair and the
reused data root. The route, helper, endpoint, permission and account gates and D034
remain separate. Embedding or rebuilding OpenCode to use core `discovery: false` is a
different integration decision. Independent P8.2 Pi remains available, and no
platform switch is needed.

## Reproduction and fingerprints

Use the D071 clone procedure to obtain a public v2.2.5 checkout; no dependencies or
upstream execution are needed. Confirm the exact commit and a clean worktree, then
check that D074's 26 fingerprints still match. From the checkout, run `shasum -a 256`
over the paths below (on Linux, use `sha256sum`):

| Pinned path | SHA-256 |
|---|---|
| `packages/server/src/location.ts` | `8f8cac178efa51059b79a6ce1bd13da334b7cd1d0d4a4a0fbc2211e80ff484ea` |
| `packages/server/src/routes.ts` | `284510fcdba864c46bfb382cf40acc3d473e61176b5e8999da7dc52efe5599c9` |
| `packages/server/src/options.ts` | `131335c86cf30eba4ec47bc3ccf6632f35b3e94b4c3ac2e7685784bf42a1c8af` |
| `packages/server/src/handlers/command.ts` | `929cc7a2d368465fae5276e46f138e40d100dc19a02df9bda1ea27f7ef95674d` |
| `packages/server/src/handlers/skill.ts` | `428dc0167217bb47fb9bdcc883dcef6803a92b93e6e9ad1ccb1614ffb71bd5dc` |
| `packages/server/src/handlers/plugin.ts` | `4fb773235862811b95f8329b96703861c6018635caa507767ca063c2ed5eb7ea` |
| `packages/server/src/handlers/mcp.ts` | `059046cdd0d0722d11df04b250b7625cc7f2ebba6450bd8c3706f0a84f3a725f` |
| `packages/server/src/handlers/usage.ts` | `d82a1d7495e58d236c47a2b747df11b0b6dec5ffe0d3d20ac8d2c1b5df9762b6` |
| `packages/server/src/handlers/debug.ts` | `9672a93c7dc07f00403d4890f11e659fa3edd55d84efd5d77efb5a73b854bc81` |
| `packages/protocol/src/groups/location.ts` | `574f2502d1927d8884805bec252b11670803be9422c6ad40b533ec4492236119` |
| `packages/protocol/src/groups/command.ts` | `f7dc659fca84d5491055be1045446ecde81a8182a24a3149ce01379a5718dfec` |
| `packages/protocol/src/groups/skill.ts` | `18d47e5dc4cc2ec598ec37cf0222eee6f6527c38cc71f861869618b6e6541b0c` |
| `packages/protocol/src/groups/plugin.ts` | `8e810c744292ac8b1e62ce59578aca50e8add89afd73f623178c2c733ea18a43` |
| `packages/protocol/src/groups/mcp.ts` | `6e6f52b090957b3a411e52acfede367ac6c7bb6f80f7ce564bd1192cbb3e4db7` |
| `packages/protocol/src/groups/event.ts` | `cdf88186681b233031bdc70dd478e660680ca0334f82f98d131900c81aae7048` |
| `packages/protocol/src/groups/debug.ts` | `f025863a0a760ad308fea0efa6b2acac0f54c541334fbd695b486dc11ffee831` |
| `packages/protocol/src/groups/usage.ts` | `14bc0fe11fdd5fef9fa4a5a68b56da5a0717b0ef679e184817d9660b4b433e2d` |
| `packages/protocol/src/groups/integration.ts` | `3f3010e8b66f378b9a862b789bfc079369f5ce7c9a9b424ab2cfbf8623aceeb1` |
| `packages/core/src/location-services.ts` | `090ed9d5cc7925096bd0ccb0308fc6c535d9294704cc396861e1da76c86e82b2` |
| `packages/core/src/instance.ts` | `efcb1e89a70cca336499ec82ed9feb2ec9754b3ff83762db183eebf13b5f4d1f` |
| `packages/core/src/plugin.ts` | `1ce30b5d688d971a33501363fb1b504cac4e77cf798bd4e8bb67130cf7803bad` |
| `packages/core/src/plugin/supervisor.ts` | `eee3c55891db258811b098a3c33121d538aa0067d05e3c2deb162ba710542926` |
| `packages/core/src/plugin/internal.ts` | `b3bf36bd6cbc0dd849d0a55f552696c588b486e79f22963124e68a91c2769b50` |
| `packages/core/src/plugin/source-directory.ts` | `6cb45adda9d6798d2a6e851197c2a9a9769a61f052e2370f0d54f56a7c443214` |
| `packages/core/src/config/plugin/source.ts` | `5705a52dedce1428ee8ccbd1ee9be5ada5899b8b781e3496d232148eb1f24687` |
| `packages/core/src/config/plugin/command.ts` | `e007b4e8d6934da968c0c3e9d2a9f0f59c7406f9a1870f78a19d28c4f144561e` |
| `packages/core/src/config/plugin/skill.ts` | `114c3ac6be02289b6736159a5e80a9bb3abff39eca763b3f47106bb651c27023` |
| `packages/core/src/config/plugin/compatibility.ts` | `3b060fdfbc2064d5b98c658aaf67017ad2a8047276fb7428b32f8ec7545823ee` |
| `packages/core/src/config/plugin/instruction.ts` | `b69cc3088bf6f5b70a2e3b1ee8d796ee81edc05a62036d4f5a6d62f5ef90a8f9` |
| `packages/core/src/config/plugin/mcp.ts` | `b582fbbb99e98d9e5fd4df48598da12ca128f57021e038c32bf3dcc16a561330` |
| `packages/core/src/command.ts` | `2bcc84fb0d28480e9023223a67b3c197fc2abd2ef4acd63f410c0bd278c770fe` |
| `packages/core/src/skill.ts` | `9d5c29f5cec09375f3a70bf107c50ea3b71842374c7f8827d26541d8be0f5584` |
| `packages/core/src/mcp/index.ts` | `ca2976e4cb56e26a8542dd126f72c9ab7b2f86aa0875cbd1a06c7993f39c0876` |
| `packages/core/src/instruction-discovery.ts` | `b0c0da74fb26a050251f240a1299b7feeaf05205994e6fea553e283613538123` |
| `packages/core/src/wellknown.ts` | `1983793d5ce0fbc2abec598d8f95b70b0ba118430b2ff9cce2205c4d0938c52b` |
| `packages/core/src/kv/sql.ts` | `c2f86325662f1070fb31e0c7b6058a8fc678978d806c86b1ef973befaba41627` |
| `packages/core/src/usage-limits.ts` | `6891419fe21a037f5ed42fd282533db1692cb8797b01b6398c1dd758e6280145` |
| `packages/core/src/plugin/provider/opencode.ts` | `1a757ab84e8dc2d96de1ebe75b64cbe4b8b1e82bcea07bf9ead681977d63f4ed` |
| `packages/schema/src/skill.ts` | `da003f8a6fd607569adb11e789c08eede92b044faa87648c422e69b47e281b4c` |
| `packages/schema/src/mcp.ts` | `4fc2c6cd480552130a016ccb11160043e4c58e4833480ec9e208fcf4c4f3c8d7` |
| `packages/cli/src/server-process.ts` | `37e89b2eed32bc9324f4cdf0a639387dfe6fc0ef8e6f37fc33c43987869b4bc2` |

## Validation

Verified the exact source commit and a clean worktree. Re-verified all 26 D074
fingerprints and recorded the 41 above. Documentation relative links and anchors,
link-checker fixtures and whitespace checks pass. This assessment is source-only, so
no Rust changes or tests, installed runtime or direct-tool coding comparison apply.

Grok reviewed the first revision in [PR #89](https://github.com/awesomejt/agent-harness/pull/89)
under the operator account and found 0 blockers, 1 concern and 2 nits. All three are
addressed:

- **Concern:** the instruction refusal now holds with project discovery both on and
  off. Fixtures sit under the owned synthetic HOME, so the ancestor walk's source-pinned
  `stop` is owned, and the reachable directories are recorded.
- **Nit:** the expected built-in plugin set is defined as the IDs in the fingerprinted
  `plugin/internal.ts`, derived and recorded by the helper.
- **Nit:** finding paths are stated as relative to `packages/`.

Documentation links and anchors, link-checker fixtures, all fingerprints and whitespace
checks pass again. No critical or high finding, so no re-review was requested.
