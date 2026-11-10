# P7.9 — Source and persistent-state control assessment

Date: 2026-11-09. Entry: `aa7244c8cdc7ded43570f0d74f842dd76a789c48`
(PR #84 merged). Prior [contained diagnostics](p7-9-contained-diagnostics.md), D070.

## Plan recorded before installed checks

Review the same pinned official v2.2.5 source for configuration/resource discovery,
managed preferences, compatibility directories and persistent integration state.
Record exact files and hashes, distinguishing tagged source from installed build
provenance. Use only the D070 private server and allowlisted debug config/agents/paths
commands, with the same pinned copied executable, cleared environment, disposable
HOME/XDG roots, network/home-read/outside-write containment and bounded cleanup.
Seed inert global and compatibility source canaries with paired discovery controls.
Do not load executable plugins, start MCP, query authentication, create sessions,
submit inference or inspect the operator's real configuration/credentials.

If source review identifies a startup source which cannot safely be excluded,
stop installed expansion at that boundary and record the blocker. Assess dedicated
persistent state from public source and synthetic files only; never open/copy the
normal database or manufacture credentials. Any runtime-owned login decision and
effective tool enforcement remain separate consuming gates. This focused assessment
does not claim full P7.9 acceptance or add production support.

## Result: stop at the source-isolation boundary

The review found the conditional stop in the plan before any installed expansion.
No OpenCode process was launched in this increment and no synthetic resource or
persistent-state canary was executed. D070's installed observations remain historical
evidence. This assessment supplies a reproducible source inventory and a concrete
blocker; **P7.9 remains unchecked and P7.11 blocked**.

The accepted diagnostic transport does not exclude machine-wide configuration.
Private HOME/XDG changes user paths but not macOS system/MDM paths. The inspected
CLI/server chain exposes no system/global exclusion parameter, although core has
those options. This is a source-based limit of the selected interface, not proof
that every OpenCode integration is incapable. Do not expand the installed probe,
seed machine-wide files or preserve the normal database to bridge this gap.

## Pinned source and reproduction

Official source: [OpenCode v2.2.5](https://github.com/anomalyco/opencode/tree/9bbb8ce18c80f099e0e448775f59d965ead40a21),
commit `9bbb8ce18c80f099e0e448775f59d965ead40a21`. A fresh shallow checkout of tag
`v2.2.5` resolved to that commit on 2026-11-09. Tagged source is not verified build
provenance for the installed executable (whose accepted hash remains in D070).
Current official [config](https://opencode.ai/docs/config/) and
[skills](https://opencode.ai/docs/skills/) docs were also re-read; pinned code,
not moving documentation examples, determines this assessment's claims.

Reproduce without launching OpenCode or accessing user state:

```sh
git clone --depth 1 --branch v2.2.5 https://github.com/anomalyco/opencode.git /tmp/ah-opencode-source-review
git -C /tmp/ah-opencode-source-review rev-parse HEAD
cd /tmp/ah-opencode-source-review
shasum -a 256 packages/core/src/config/discovery.ts packages/server/src/options.ts packages/server/src/routes.ts packages/cli/src/server-process.ts
```

The destination must be absent; use a fresh disposable path if it already exists.
No upstream dependency installation or source execution is needed. Inventory paths
below are relative to this checkout; fingerprints link directly to the pinned files.

## Discovery and resource inventory

| Source | Pinned behavior and consequence |
|---|---|
| User config | `config/discovery.ts` includes the configured global directory unless core `global: false`. Private XDG/config paths move it without disabling other scopes. |
| Project and ancestors | `project: false` suppresses the ancestor walk, including direct documents, `.opencode`, `.claude` and `.agents` project roots. D070 proved only its seeded config/agent cases on this host. |
| Global compatibility | Global HOME `.claude` and `.agents` remain eligible with global discovery enabled. CLI Claude-disable flags gate `.claude` skills only, not `.agents` or all resources. Disposable HOME avoids operator roots without proving retained login. |
| Machine directory | macOS `/Library/Application Support/opencode` is independent of HOME/XDG. When present, its directory/documents load as managed configuration. Private inline content does not remove it. |
| MDM | The first present `/Library/Managed Preferences/<OS username>/ai.opencode.managed.plist` or `/Library/Managed Preferences/ai.opencode.managed.plist` wins. Username comes from `os.userInfo()`, not disposable HOME. Managed settings load after inline content; managed policies have stronger authority. |
| Agent files | Config agent plugin scans directory entries for `agent/agents` plus legacy `mode/modes`, and merges agent documents. Empty `agents` is not source exclusion. |
| Commands | Config command plugin loads directory Markdown and document commands. Omitted inline commands do not exclude inherited registrations. |
| Skills | Config skill plugin adds `skill/skills` under directory entries and configured local/HTTP sources. Compatibility plugin separately scans `.claude/skills` and `.agents/skills`. Empty `skills` does not clear discovered directories. |
| Instructions | Instruction plugin separately discovers global and project/ancestor `AGENTS.md`; explicit paths/globs/URLs come from all config documents. Server routes wire only project discovery. Empty inline instructions do not disable every source. |
| Plugins and hooks | Plugin source scans directory entries, then applies explicit package directives. `plugins: []` supplies no removal directives. Executable plugins can register behavior/hooks; an empty package array is not complete hook exclusion or tool enforcement. |
| MCP | Config MCP plugin accumulates named servers from documents. An empty map does not delete inherited names. No MCP process/connection was started here. |
| Well-known integration | Registered origins load from persistent KV; remote/cached documents are separate from private file discovery. Network denial alone does not eliminate cached configuration. |
| OpenCode Console | Built-in OpenCode provider resolves its active connection and can fetch/publish a restricted integration document, separately from well-known cached documents. Exclusive persistent-state design must account for both. |

This inventories the inspected discovery/registration paths, not a complete adversarial
execution audit. Directory resources and instruction/plugin lifecycle still need
paired installed controls after selecting a safe launch boundary. Model/helper/
endpoint, complete no-tool denial and exact trusted grants remain unproven.

## Missing interface control

`packages/core/src/config.ts` declares `global` and `system` options.
`config/discovery.ts` honors `global: false`, `system: false` and a custom system
directory (also skipping host MDM). These are **core API controls**.
`packages/server/src/options.ts` includes only `directory`, `project`, `claude`,
`file` and `content` in config options. `server/src/routes.ts` forwards only
project/claude/file/content to Config, and only project to InstructionDiscovery.
`cli/src/server-process.ts` maps the corresponding environment variables into
those server options; global/system are not forwarded in this chain.

Undocumented environment variables or `system: false` in ordinary config content
are therefore not accepted enforcement. Rebuilding/embedding core with different
replacements would require a new integration decision. A version bump alone is
insufficient; exact control and installed proof must precede consumption.

D070's sandbox denies network, operator-home data reads and outside writes, but
allows reads elsewhere. It does not supply the missing machine-source barrier.
Its exact current-host source list cannot demonstrate exclusion when system/MDM
resources exist or appear after startup. No such operator resources were inspected;
no assertion is made about whether they currently exist.

## Persistent state and login ownership

`credential.ts` acquires Database; `credential/sql.ts` defines secret values and
connector/method identity. Independently, `kv.ts` uses that same Database service.
`wellknown.ts` reads `wellknown:sources`, persists manifests and resolved configs,
and falls back to cached manifests/configs when refresh or usable credentials
fail. `config.ts` loads those documents before user/project/inline content.
Private config paths therefore do not restrict database access to credential rows.
Only managed policies can withhold integration-supplied configuration, and withheld
documents retain their policies; ordinary inline policies cannot supply that lockdown.

The Console path differs: `plugin/provider/opencode.ts` resolves the active
connection, fetches remote config and publishes it through `ConfigIntegration.make`.
`config/integration.ts` limits Console documents to providers, remote MCP, policies
and websearch, excluding local commands/plugins. Well-known config uses a separate
ordinary parsing path; do not generalize the Console allowlist to all sources.

- Reusing the ordinary database is not established credential-only access. Do not
  inspect/filter/copy credential rows or delete operator registrations for isolation.
- A fresh exclusively owned data root avoids importing ordinary persistent state
  but has no established login. D070 proves path selection only. Operator-created
  login in exclusive runtime state is a candidate for a separate D047 decision,
  with credential handling left to OpenCode; it was not exercised here.
- Exclusive state can later acquire registrations. Ongoing inventory/refusal and
  mutation boundaries need proof beyond a one-time empty-directory assertion.
- Neither network containment, inline `provider.use` nor empty config maps prove
  exact token-sharing method/endpoint or complete effective tool denial.

## Disposition and next work

This focused assessment closes on required PR review/merge. Full P7.9 remains
blocked on unproven source exclusion with all prior auth/tool/account gates intact.
The next independent task is **P7.10**, dedicated Go no-inference feasibility,
carrying this inventory forward instead of repeating diagnostic discovery.

P7.9 continuation requires a separate safe control plan: supported official
CLI/server exclusions with installed canaries, or a narrowly justified and tested
source-read/refusal boundary covering machine/MDM resources and changes without
touching real configuration. Any containment stays experimental until evidenced
for its consuming route; D070's diagnostic sandbox is not production enforcement.
Then assess synthetic persistent registrations and effective resource inventories
before a separate D047 exclusive-state login decision. No auth/session/model work
follows from this report. P7.10 must independently prove dedicated Go controls and
account Extra Usage verification; shared isolation limits still apply.

No Rust, public config/CLI, dependencies, production pins or fallback policy change.
No model turn, provider request, real credential/config-store access, login import
or installation occurred. Direct-tool coding comparison does not apply to static
assessment. No platform switch is needed. Fresh context is efficient at this Go
feasibility boundary; P7.13/P7.6/P7.7 remain later gates and Pi remains independent.

## Source fingerprints

SHA-256 of inspected public source, not operator state or installed-build provenance.

| File at the pinned commit | SHA-256 |
|---|---|
| [packages/core/src/config.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config.ts) | `df2d83dff70a6cb3ef3e3a1d735bd397facc96ccf15794c6eb1a3646cef17390` |
| [packages/core/src/config/discovery.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/discovery.ts) | `48118dafc1ba0ec03112e98cdd616f339262a08a42b4ae75e9014575d863434d` |
| [packages/server/src/options.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/server/src/options.ts) | `131335c86cf30eba4ec47bc3ccf6632f35b3e94b4c3ac2e7685784bf42a1c8af` |
| [packages/server/src/routes.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/server/src/routes.ts) | `284510fcdba864c46bfb382cf40acc3d473e61176b5e8999da7dc52efe5599c9` |
| [packages/cli/src/server-process.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/cli/src/server-process.ts) | `37e89b2eed32bc9324f4cdf0a639387dfe6fc0ef8e6f37fc33c43987869b4bc2` |
| [packages/core/src/config/plugin/agent.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/agent.ts) | `4d46f0ddd75dd40eab9199bef154cf388939bd1a15bc6a506f81745740d31000` |
| [packages/core/src/config/plugin/command.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/command.ts) | `e007b4e8d6934da968c0c3e9d2a9f0f59c7406f9a1870f78a19d28c4f144561e` |
| [packages/core/src/config/plugin/skill.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/skill.ts) | `114c3ac6be02289b6736159a5e80a9bb3abff39eca763b3f47106bb651c27023` |
| [packages/core/src/config/plugin/compatibility.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/compatibility.ts) | `3b060fdfbc2064d5b98c658aaf67017ad2a8047276fb7428b32f8ec7545823ee` |
| [packages/core/src/config/plugin/instruction.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/instruction.ts) | `b69cc3088bf6f5b70a2e3b1ee8d796ee81edc05a62036d4f5a6d62f5ef90a8f9` |
| [packages/core/src/config/plugin/source.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/source.ts) | `5705a52dedce1428ee8ccbd1ee9be5ada5899b8b781e3496d232148eb1f24687` |
| [packages/core/src/config/plugin/mcp.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/mcp.ts) | `b582fbbb99e98d9e5fd4df48598da12ca128f57021e038c32bf3dcc16a561330` |
| [packages/core/src/instruction-discovery.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/instruction-discovery.ts) | `b0c0da74fb26a050251f240a1299b7feeaf05205994e6fea553e283613538123` |
| [packages/core/src/credential.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/credential.ts) | `630d3cdc698d040ce65c2ab232321ee5a634c8e4c14a09db35d62f13dd039328` |
| [packages/core/src/credential/sql.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/credential/sql.ts) | `d7ab91f008837367fcb89c9c30075a50811ae75e2889c6da2cf8cf1e36d48463` |
| [packages/core/src/kv.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/kv.ts) | `40f41ca6c6d77cf42b64c1ec1e535a306b8355740f62a7b59d762068ad153e36` |
| [packages/core/src/wellknown.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/wellknown.ts) | `1983793d5ce0fbc2abec598d8f95b70b0ba118430b2ff9cce2205c4d0938c52b` |
| [packages/core/src/config/integration.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/integration.ts) | `78f52c203ec252c5dd2b423f184422617137edf1e5ceb83a1866aab035c04aab` |
| [packages/core/src/plugin/provider/opencode.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/plugin/provider/opencode.ts) | `1a757ab84e8dc2d96de1ebe75b64cbe4b8b1e82bcea07bf9ead681977d63f4ed` |

## Validation and independent review

Tag commit and fingerprints verified against the fresh public checkout. Independent
read-only security review confirms the missing server controls and mixed database
state, with no evidenced safe supported alternative at this pin. It also confirms
the missing installed system/MDM canaries, synthetic database startup test and
installed source equivalence must remain explicit. No installed experiment ran
because the plan's stop condition was met. Documentation links/anchors and Git
whitespace checks are required before PR; no Rust tests are needed for unchanged
production sources/dependencies. Grok findings are recorded at closeout.
