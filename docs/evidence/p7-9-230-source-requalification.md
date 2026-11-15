# P7.9 — OpenCode 2.3.0 source qualification and observer contract

Recorded: 2026-11-14, America/Denver. Baseline: `edff499`.
Branch: `feature/07/p7-9-230-source-requalification`. Decision: D093.
[Task](../../tasks/07-native-adapters.md#p7-9),
[production upgrade](opencode-2-3-0-upgrade.md),
[prior disposable catalog boundary](p7-9-catalog-control.md).

## Scope and outcome

This bounded prerequisite qualifies public source and selects the observer
contract for the next disposable no-auth containment increment. It does not
launch OpenCode, refresh any existing helper pin, inspect operator state or
perform authentication, session/model calls or database access. P7.9 remains
unpassed and P7.11 blocked. D034, D089 and the separate Go gates remain unchanged.
Installed containment and catalog proof follow as separately reviewed increments.

Official [v2.3.0 release](https://github.com/anomalyco/opencode/releases/tag/v2.3.0)
resolves to `a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`. The clean checkout was
fetched from `https://github.com/anomalyco/opencode.git`. The committed
[manifest](p7-9-230-source-manifest.json) pins 263 public files: the plugin entry
closure, its one-hop relative imports, package export maps and the additional
D092 source/control review files, provider handler, server activation helper,
managed policy and plugin service. This is a finite source-audit manifest,
not an accepted installed executable/containment manifest or a complete
transitive dependency inventory. The D092 executable hash remains a candidate
for that later qualification; this audit does not read or launch the binary.

## Reproduction and refusals

```sh
python3 -B scripts/experiments/chatgpt_230_source_audit.py --source <clean-v2.3.0-checkout>
python3 -B scripts/tests/chatgpt_230_source_cases.py
```

The audit accepts only the exact commit and a clean tracked/untracked worktree,
checks every manifest hash before derivation, refuses absolute/traversal and
symlinked manifest paths, and requires every derived input in the manifest.
There is no runtime, retained-root or database argument or pin-update switch.
It reuses only pure source parsers from the old helpers, without changing their
version/executable guards. Output contains public plugin/integration IDs and
source provenance only. Offline cases cover source-byte changes, missing files,
symlinks, unsafe paths, revision/dirty-tree refusals and unsupported registration
syntax. This does not parse arbitrary TypeScript; new source requires review.

## Fresh plugin and integration derivation

| Observation | 2.3.0 source result |
|---|---|
| Built-in plugin entries | 94 unique IDs from `pre`/`post`, 93 files |
| Plugin source byte digest | `111669bf85401fd54cfecf2a6827bf1223eb8b9eeaf7cc3fdc6904340c13e5df` |
| Snapshot providers with environment definitions | 230 |
| Plugin-named integrations | 19 |
| Plugin-only integrations | `claude-agent`, `exa`, `firecrawl`, `parallel`, `tavily`, `tinyfish` |
| Union | **236**, SHA-256 `2cd1b632219bbd635a2f7a5911d6c0e36d7205d75cc4c85d751cb90081de73af` |

The old integration literal parser alone projects 231 IDs on 2.3.0: it misses
five web-search registrations refactored into `WebSearchProvider.register`.
The new audit explicitly extracts the literal IDs at those five call sites and
pins their shared factory (`core/src/plugin/websearch/provider.ts`), which
registers key/env methods under the same `provider.id`. Unknown call shapes
refuse. The resulting original 236-ID gate is preserved, not replaced with the
incomplete projection. The complete ID/provenance lists are in the manifest.
This is a source projection; installed bundled/cache state remains unproven.

The built-in list now includes `opencode.fork-notice` and
`opencode.tools.mcp-events`. Their presence in the observer inventory must not
be interpreted as permission to run them. Effective deny/trusted ceilings and
external MCP refusals must be revalidated before any later model turn.

## Selected observer readiness and refusal contract

The next disposable helper must implement and test this contract before launch:

1. Keep the existing bounded authenticated loopback GET observer, body/type/
   location bounds, secret redaction, timeout and route allowlist. Add exactly
   `provider.list` (`GET /api/provider`) as a readiness barrier. Its pinned
   handler yields `awaitPlugins`; `integration.list` no longer does. Provider
   listing selects metadata and must not be replaced with a model/session call.
2. After that barrier, require the exact new built-in plugin ID set, every entry
   active and built-in, and all existing resource sentinels. Collect integration
   lists only after activation. Require the fixed 236-ID digest, expected method
   shapes and **zero connections**, including Console and OpenAI on fresh roots.
   Validate unsafe connections/schema/resources on every observation before
   considering whether another readiness poll is allowed.
3. Require two identical complete ready observations, with the existing settling
   interval and overall deadline. Permit retries only for explicit incomplete
   activation/sentinel state or bounded startup connection failures. Never retry
   an unsafe observation into a pass; unknown errors and warnings refuse.
4. Keep the private allowlisted environment without `OPENCODE_API_KEY`, provider
   credentials or caller-supplied flags. Do not enable any Console connection.
   `provider/opencode.ts` now supplies remote instructions/skills, shared caches
   and optional event watches. Static config checks alone cannot exclude them.
   A fresh no-connection root plus network denial is required; inherited or
   synthetic Console activation must be a separate paired refusal control.

This is a reviewed design target, not a claim that an implemented/installed
observer meets it. Existing 2.2.5 observers remain unchanged and refuse 2.3.0.

## Containment follow-up and stop conditions

Next implement a separately pinned 2.3.0 disposable helper with no retained-root
argument, and obtain helper/setup review before installed execution. Requalify
D070/D076 transport, inherited filesystem/network boundaries, `/dev/null`, port/
password refusal, native-only MCP and resource rows. In particular,
`config/discovery.ts` now lists parents and falls back to individual probes when
listing is denied: both paths need paired synthetic and installed canaries.
Recheck global/system/MDM/ancestor/symlink denials, instruction/plugin guards,
Claude/skill exclusions and watcher/resource observations. New plugin/source
fingerprints and the exact executable bytes must be checked before launch.
A version string or production regression cannot substitute for these proofs.

Any unexpected resource, connection, inventory, warning, helper, endpoint or
boundary result stops the increment and records a blocker. Do not widen the
fixed inventory, allow network access, attach the retained root or copy its
stores to make a probe pass. Only after disposable containment qualification
may the D091 synthetic catalog/cache helper be migrated and exercised under
its own reviewed setup boundary. Its paired metadata and cache persistence
controls remain required. A passing catalog result still precedes a separately
reviewed authenticated control plan and same-root D085–D088 evidence, including
a fresh operator credits-off attestation. No authenticated expansion is selected.

## Verification and review

The clean official-source audit passes. The new offline refusal cases and
existing observer, retained-state and catalog-control suites pass. Production
Rust and runtime files are unchanged; no live provider or installed runtime
experiment is used as evidence in this increment. Required PR review/merge and
any findings are recorded here before closeout.
