# P7.9 — Pre-launch resource observation matrix

Date: 2026-11-09. Entry: `f6d9f1351070acb124debbdc3603ceb788fb4906`
(PR #87 merged). Prior [source boundary design](p7-9-source-boundary-design.md), D073, and [source/state inventory](p7-9-source-state-controls.md), D071.

## Plan and result

Before any installed continuation, map every D071 resource category to the accepted
D070 diagnostics or a static refusal invariant, with paired inert canary criteria.
Inspect only public pinned source and the repository helpers. Do not launch OpenCode,
read real configuration/state/credentials, seed machine roots, install dependencies,
create sessions or authenticate. Stop before launch on missing visibility, as D073
requires. Keep production code, runtime pin, interfaces and D034 unchanged.

**The matrix is complete as an inventory; coverage does not pass. The stop condition
is met.** The accepted helper permits only `debug config`, `debug agents`, and
`debug paths`. Config returns redacted config entries; agents returns the agent
registry; paths reports storage locations. Directory resource contents, transformed
registries and loaded instruction bodies are not interchangeable with these outputs.
No installed combined-boundary, watcher/reload or persistent-state proof was run.
Full P7.9/P7.10 remain unchecked and P7.11/P7.12 blocked.

## Observation and refusal matrix

All paths below are relative to the official v2.2.5 source checkout at
`9bbb8ce18c80f099e0e448775f59d965ead40a21`. These are source observations,
not verified installed build provenance. “Candidate” means a future observer to
assess, not permission to expand the accepted command/API allowlist. Every paired
case needs independent fresh owned fixtures, identical initial content, an exact
positive marker and exact negative absence/refusal, bounded output/time/cleanup,
and no executable resource activation. None of the proposed pairs ran here.

| Category | Current observation / candidate | Paired inert criteria and unresolved coverage |
|---|---|---|
| Config and agents | Accepted config entries and agent registry (`cli/.../debug/config.ts`, `agents.ts`). | Extend D070's exact canaries to private global and compatibility roots with discovery enabled/disabled; directory entries alone do not prove resource absence. Historical D070 project/parent cases are not this expanded pair. |
| Commands | Directory Markdown is decoded into a command registry (`core/src/config/plugin/command.ts`); config entries need not contain those commands. Candidate `GET /api/command`, `command.list`. | Recognizable Markdown name/template in owned global/project roots, listed in positive and absent in excluded mode. Never execute templates (they can evaluate shell substitutions). Not observable through the current allowlist. |
| Skills | Directory/config sources plus `.claude/skills` and `.agents/skills` compatibility scanning (`config/plugin/skill.ts`, `compatibility.ts`). Candidate `GET /api/skill`, `skill.list`. | Distinct inert skill names for each scope, listed with expected paths in positive and absent in negative. No skill invocation or remote source. Current config/agent output does not prove the skill registry. |
| Instructions | `config/plugin/instruction.ts` reads global/ancestor `AGENTS.md`, configured paths/globs/URLs and maintains loaded content separately. | Candidate static refusal: owned empty global root, project discovery off, no configured instruction sources in any entry. Missing: paired proof of actual discovered content and reload under this invariant. Session instruction-entry APIs concern API-managed entries, not a complete discovered-content observer; creating a session is outside this plan. |
| Plugins and hooks | `config/plugin/source.ts` scans directory plugins separately from document directives; `core/src/plugin.ts` activates effects. Candidate `GET /api/plugin`, `plugin.list`, reports inventory/status. | Candidate static refusal: no local plugin entrypoints or package directives in any owned eligible root/document; exact expected built-in inventory. Missing: safe positive discovery fixture that cannot execute code and proof of activation ordering. A post-activation list is not a pre-activation safety guard. Empty inline plugins do not exclude directory sources or built-ins. Never load an executable canary. |
| MCP | Document servers merge through `config/plugin/mcp.ts`. Candidate `mcp.list` in `server/src/handlers/mcp.ts` reports servers separately. | Candidate static refusal: no MCP registrations in all entries and no other registration source; future positive only if a disabled inert registration is proven unable to spawn/connect before observation. Missing lifecycle/refusal proof; do not assume a GET or list operation avoids initialization effects. No process/socket canary launched. |
| Well-known integration | `wellknown.ts` loads origin registrations, manifests and cached config from KV; cached state survives remote failure. Config entries may show contributed documents, not every stored registration/cache. | Candidate static refusal: exclusively created empty synthetic data root with no reused database; this alone tests no retained-registration case. Missing paired synthetic registered/cached-document fixture, including offline cache behavior and effective-document assertion. Network denial is not cache exclusion. |
| Console integration | `plugin/provider/opencode.ts` loads active integration connection and remote config; `config/integration.ts` restricts remote fields to providers/MCP/policies/websearch. | Candidate static refusal: no connections/credentials in freshly owned synthetic state and cleared environment. Missing synthetic connection/state-to-source proof without auth/refresh. `integration.list` lists available integrations/methods and filters by policy; it is not a raw state/cache inventory. Do not use credential-list APIs (they return secret values). |
| Persistent registrations | D071 identifies mixed credential/KV storage; debug paths only names its location. | Require an explicit synthetic schema/fixture plan covering origins, cached manifests/documents and active connections before consumption. No ordinary database import, auth copying/filtering or deletion of operator registrations. No accepted observer/refusal pair yet. |
| Machine/MDM and changing sources | D073's synthetic OS data/metadata refusal candidate covers both literal roots; it does not prove installed discovery or parent watcher behavior. | Separate composed D070 + D073 network/home/write/stdio/source controls, Bun discovery equivalents and synthetic parent-watch acquisition/failure plus late-create/replace/reload pairs are still required. Never seed or explicitly probe real machine roots. |

The missing observer is a limit of the **current diagnostic plan**, not proof that
OpenCode has no API for a resource or that safe isolation is impossible. The matrix
explicitly identifies the command/skill/plugin/MCP candidates for follow-up.
Read-only HTTP semantics do not by themselves establish read-only initialization.

## Narrow continuation and boundary

Next is a focused observer/refusal design under P7.9: assess the pinned official
command/skill/plugin/MCP list APIs and their full service-initialization paths, select
an exact authenticated owned-server GET allowlist with bounded schemas/redaction and
request/redirect refusal, and resolve the instruction plus plugin pre-activation
invariants. Design paired inert fixtures for every row and synthetic cached-state
schemas before consuming any database. Do not implement an observer and immediately
launch it with unresolved rows. Reconcile this matrix with any supported alternative
that supplies the missing observations; embedding/rebuilding or changing the runtime
requires its own integration decision.

Only after coverage passes may a separately recorded installed plan compose and
revalidate D070/D073 containment and prove synthetic watchers/reload and resources.
No login follows implicitly: D047 exclusive-state setup, effective route/helper/
endpoint, permission enforcement and account controls remain separate gates. If the
missing invariant cannot be established, record that precise blocker rather than
repeat the same launch attempt. Independent P8.2 Pi continuation remains available;
no platform switch is needed. Fresh context is efficient at the observer-design gate.

## Reproduction and fingerprints

Use the D071 clone procedure to obtain a public v2.2.5 checkout; no dependencies or
upstream execution. Confirm exact commit and a clean worktree first. Run the following
from that checkout (Linux: replace `shasum -a 256` with `sha256sum`):

```sh
git rev-parse HEAD
git status --porcelain
shasum -a 256 \
  packages/cli/src/commands/handlers/debug/config.ts \
  packages/cli/src/commands/handlers/debug/agents.ts \
  packages/cli/src/commands/handlers/debug/paths.ts \
  packages/cli/src/commands/handlers/debug/redact.ts \
  packages/server/src/handlers/config.ts \
  packages/server/src/handlers/command.ts \
  packages/server/src/handlers/skill.ts \
  packages/server/src/handlers/plugin.ts \
  packages/server/src/handlers/mcp.ts \
  packages/server/src/handlers/integration.ts \
  packages/core/src/config/plugin/command.ts \
  packages/core/src/config/plugin/skill.ts \
  packages/core/src/config/plugin/compatibility.ts \
  packages/core/src/config/plugin/instruction.ts \
  packages/core/src/config/plugin/source.ts \
  packages/core/src/config/plugin/mcp.ts \
  packages/core/src/plugin.ts \
  packages/core/src/wellknown.ts \
  packages/core/src/config/integration.ts \
  packages/core/src/plugin/provider/opencode.ts \
  packages/protocol/src/groups/command.ts \
  packages/protocol/src/groups/skill.ts \
  packages/protocol/src/groups/plugin.ts \
  packages/protocol/src/groups/integration.ts \
  packages/protocol/src/groups/credential.ts \
  packages/protocol/src/groups/session.ts
```

| Pinned path | SHA-256 |
|---|---|
| `packages/cli/src/commands/handlers/debug/config.ts` | `aa22552a63332f7edc8162235026482bb9d1a366e6a4e000cd55c32729c2e4e6` |
| `packages/cli/src/commands/handlers/debug/agents.ts` | `99a3d7d08aa594c0df4daa52e8d5b7fd8dffafaa6ee3b0eba88157e461510ecf` |
| `packages/cli/src/commands/handlers/debug/paths.ts` | `ae389b26f2366136e21d68669fb94e31dff3ae9e7ef04d84167fa6867870c6c0` |
| `packages/cli/src/commands/handlers/debug/redact.ts` | `7ff1f8aeedd4631f78b1169ea5b29f52060325960be000dd48fdf05bc05e7ce5` |
| `packages/server/src/handlers/config.ts` | `618b441f7faaf35533f7634e999e5469eead2c65c9e70cc5fa38d888a9f67eaa` |
| `packages/server/src/handlers/command.ts` | `929cc7a2d368465fae5276e46f138e40d100dc19a02df9bda1ea27f7ef95674d` |
| `packages/server/src/handlers/skill.ts` | `428dc0167217bb47fb9bdcc883dcef6803a92b93e6e9ad1ccb1614ffb71bd5dc` |
| `packages/server/src/handlers/plugin.ts` | `4fb773235862811b95f8329b96703861c6018635caa507767ca063c2ed5eb7ea` |
| `packages/server/src/handlers/mcp.ts` | `059046cdd0d0722d11df04b250b7625cc7f2ebba6450bd8c3706f0a84f3a725f` |
| `packages/server/src/handlers/integration.ts` | `f2f69342bfaa56706466b547f237433c8135ecc87c2639942544d44a7fccbe78` |
| `packages/core/src/config/plugin/command.ts` | `e007b4e8d6934da968c0c3e9d2a9f0f59c7406f9a1870f78a19d28c4f144561e` |
| `packages/core/src/config/plugin/skill.ts` | `114c3ac6be02289b6736159a5e80a9bb3abff39eca763b3f47106bb651c27023` |
| `packages/core/src/config/plugin/compatibility.ts` | `3b060fdfbc2064d5b98c658aaf67017ad2a8047276fb7428b32f8ec7545823ee` |
| `packages/core/src/config/plugin/instruction.ts` | `b69cc3088bf6f5b70a2e3b1ee8d796ee81edc05a62036d4f5a6d62f5ef90a8f9` |
| `packages/core/src/config/plugin/source.ts` | `5705a52dedce1428ee8ccbd1ee9be5ada5899b8b781e3496d232148eb1f24687` |
| `packages/core/src/config/plugin/mcp.ts` | `b582fbbb99e98d9e5fd4df48598da12ca128f57021e038c32bf3dcc16a561330` |
| `packages/core/src/plugin.ts` | `1ce30b5d688d971a33501363fb1b504cac4e77cf798bd4e8bb67130cf7803bad` |
| `packages/core/src/wellknown.ts` | `1983793d5ce0fbc2abec598d8f95b70b0ba118430b2ff9cce2205c4d0938c52b` |
| `packages/core/src/config/integration.ts` | `78f52c203ec252c5dd2b423f184422617137edf1e5ceb83a1866aab035c04aab` |
| `packages/core/src/plugin/provider/opencode.ts` | `1a757ab84e8dc2d96de1ebe75b64cbe4b8b1e82bcea07bf9ead681977d63f4ed` |
| `packages/protocol/src/groups/command.ts` | `f7dc659fca84d5491055be1045446ecde81a8182a24a3149ce01379a5718dfec` |
| `packages/protocol/src/groups/skill.ts` | `18d47e5dc4cc2ec598ec37cf0222eee6f6527c38cc71f861869618b6e6541b0c` |
| `packages/protocol/src/groups/plugin.ts` | `8e810c744292ac8b1e62ce59578aca50e8add89afd73f623178c2c733ea18a43` |
| `packages/protocol/src/groups/integration.ts` | `3f3010e8b66f378b9a862b789bfc079369f5ce7c9a9b424ab2cfbf8623aceeb1` |
| `packages/protocol/src/groups/credential.ts` | `159b45805856ef68475c309ea742c6cb549ac896eee30d57c3a9471553913256` |
| `packages/protocol/src/groups/session.ts` | `5ee372848c93750bc7cd60e1b13464d4841b1c2e6e2ca93777c53ae8ffd6eea7` |

## Validation

Verified the exact source commit, clean worktree and all 26 fingerprints above.
Documentation relative links/anchors, link-checker fixtures and whitespace checks
pass. Independent read-only security/evidence review found no actionable findings
and independently verified all 26 fingerprints and documentation checks. The full
initialization/activation chain remains a consuming gate; Grok disposition follows
at closeout. No Rust changes/tests, installed runtime or direct-tool coding comparison
apply to this source-only assessment.
