# OpenCode 2.3.0 compatibility upgrade

Recorded: 2026-11-14, America/Denver. Baseline: `ee08804`.
Branch: `patch/opencode-2-3-0`. Decision: D092.

## Scope and outcome

The operator's Homebrew upgrade replaced OpenCode 2.2.5 with **2.3.0**.
Current-source harness requirements move to exactly 2.3.0 after compatibility
verification. Older and newer versions still refuse before ACP or model work.
The published `v0.1.0-alpha.2` archive remains unchanged and requires 2.2.5;
using 2.3.0 requires building the reviewed source. This increment does not publish
new release assets, widen permissions, add subscription routes or accept P7.9.

The upgrade contains meaningful changes. Passing production-route regression
tests cannot transfer the separate P7.9 resource/containment/OAuth proof. Those
helpers retain their existing 2.2.5 pins and refuse the upgraded executable.
No retained operator root or credentials are read, copied, migrated or modified.
No provider login or live inference is performed.

## Executable and public source

- Installed executable: `/opt/homebrew/Cellar/opencode/2.3.0/bin/opencode`.
- Executable SHA-256: `95af97f3638e0f0c0e6d4ae6b9b9ec546dde49a570344365ea60fab22e602db7`.
- Baseline official source: `9bbb8ce18c80f099e0e448775f59d965ead40a21` (`v2.2.5`).
- Candidate official source: `a6b15d33daf6ab7d35569f6d711fdb630b9f04e7` (`v2.3.0`).
- [Official release notes](https://github.com/anomalyco/opencode/releases/tag/v2.3.0).
- [Public-source hash comparison](opencode-2-3-0-source-hashes.json): 57 selected reviewed files,
  30 changed. This is an audit record, not a refreshed P7.9 accepted manifest.

Both source checkouts are clean at their recorded commits. Reproduce the source
comparison with clean official checkouts, then `git diff --no-index` on the
corresponding `packages/` files named in the JSON. Hash the bytes with SHA-256;
revalidate all baseline and candidate hashes before consuming the comparison.
The installed binary identity is host/package-specific; a matching version
string does not establish the P7.9 binary/source containment qualification.

## Relevant upstream changes and consuming gates

| Change | Compatibility impact and boundary |
|---|---|
| Background subagents are now the default; fork notices and new MCP event tools join built-ins | Harness roles still execute directly and effective rules deny subagent/MCP capabilities. Installed inherited-capability tests check those restrictions. No background delegation is selected. |
| Shell commands survive server handoffs; process handling and interruption changed | Add a real in-flight shell cancellation test with a labelled synthetic Python parent/child. It must observe both gone before its fallback reaper runs, and require the harness's confirmed cleanup/state-removal terminal fields. |
| Config discovery uses directory listings, concurrent resolution, explicit missing entries and a fallback when ancestor listing is denied | Existing production source/agent checks and inherited-capability tests are rerun. P7.9's macOS source-denial pairs must be requalified separately; old file fingerprints are not sufficient. |
| Console can fetch workspace instruction/skill lists, cache downloads and watch updates | Independent review found that the old child `OPENCODE_API_KEY` activates a Console connection and exposes remote instructions/skills outside config-source checks. The fix uses only private `AH_RUNTIME_API_KEY` and a settings-only native provider key overlay, preserving built-in routing without a Console connection. The installed metadata-only regression verifies zero connections after plugin activation in the actual generated runtime environment. P7.9 forbids Console connections and retains that invariant; its containment/observer qualification must precede any refreshed installed proof. |
| OAuth redirect submission, cancellation and refresh changed; integration listing no longer awaits plugin activation in its handler | Do not update authenticated helpers by replacing hashes. New-plugin derivation and settling rules need review before fresh installed proofs, followed by separately authorized same-root D085–D088 evidence. |
| Models.dev adds freeform capability handling and HTTP refresh changes | Source snapshot bytes, KV implementation/table and CLI model-file/fetch option wiring are unchanged. This supports retaining the conceptual explicit-file/cache experiment, not claiming it passed on 2.3.0. |
| Provider TLS and experimental MCP/background-shell options exist | The harness adds no settings or flags for them. Exact configuration checks and effective permission ceilings remain required. |

The [prior catalog helper](p7-9-catalog-control.md) remains useful experimental
code with a visible pin refusal. Next P7.9 work is a fresh 2.3.0 source/plugin/
observer/containment requalification on disposable unauthenticated roots, then
synthetic catalog evidence. Its fixed 236-ID gate is not widened by this upgrade.
Authenticated expansion and P7.11 remain blocked. D034 pre-submission fallback
and D089's feasibility/live split remain unchanged.

## Native credential change required by the audit

This is a behavior-preserving isolation fix, not just a version-string update.
2.3.0's Console plugin can load instruction/skill lists outside the normal config
entries. Checking `debug config` in preflight is therefore insufficient if the
later ACP process receives a recognized Console environment key. The previous
native child used `OPENCODE_API_KEY`; 2.3.0 turns that into an active integration
connection even though the root has no stored credentials.

Both routes now use the harness-private `AH_RUNTIME_API_KEY` only. The native
document adds a settings-only overlay:

```json
{"providers":{"opencode":{"settings":{"apiKey":"{env:AH_RUNTIME_API_KEY}"}}}}
```

The overlay keeps the built-in model catalog and endpoint; it neither creates a
provider integration connection nor enables Console resources. Existing exact
source validation checks the masked key on native too. The caller may continue
naming its configured environment variable `OPENCODE_API_KEY`; only the copied
value crosses into the child under the private name. Inherited provider keys and
all unrelated controls remain cleared. This supersedes D032’s credential
transport and D035’s empty native provider document, while preserving both routes
and the D034 fallback trigger. No live account test is needed to activate or
inspect a real Console connection.

## Verification

Results before Grok PR review:

- `cargo build --locked` and `cargo test --locked`: pass on the existing Rust
  1.88.0 toolchain (151 tests). No dependency or lockfile change.
- Final full offline suite: **43/43 passed**. After the test-only Grok fixes,
  both new installed regressions pass again (**2/2**); incomplete activation and
  unsafe-connection negative checks confirm only readiness may retry.
- `cargo fmt --check`, strict Clippy and release build: pass.
- New `opencode_process_runtime.py`: passes against installed 2.3.0, with actual
  parent/child execution and cleanup observed before the fallback reaper.
- New `opencode_native_isolation_runtime.py`: pass, including an independent
  rerun. The fixture checks the real generated native environment, awaits plugin
  activation via `provider.list`, then requires stable integration lists with
  zero connections before any ACP prompt is intercepted.
- Exact-pin refusal cases add both 2.2.5 and 2.3.1 to the local and native fake
  runtime suites. A rejected version starts no ACP turn and preserves project
  configuration. The local/native refusal suites pass, as do all 166 routing-matrix cases after
  the native key change.
- Existing local stub tests exercise real edits, independent tests, verification,
  cancellation and sequences. Native/fallback tests intercept the prompt before
  any live provider inference; they do not prove account-dependent remote config.

Independent review identified the high-severity Console connection issue above;
the native key fix and installed regression resolve it. The local archive from `1de6a49` also passes the complete installation smoke:
checksum, upgrade/rollback, version/help, sample previews, redaction and
config/login-store preservation with no toolchain/runtime/service on PATH.
No release asset is uploaded or replaced.

[PR #118](https://github.com/awesomejt/agent-harness/pull/118): Grok reviewed twice.
Initial review of `1de6a49`: 0 blockers, 0 concerns, 2 nits (readiness retry and
PID-file publication). Follow-up of `276b21b`: 0 blockers, 0 concerns, 1 additional
nit (check activation before comparing a stable list). All three are fixed:
retry only explicit missing-readiness states and connection resets, publish PID
files atomically, and reject unsafe connections before retrying incomplete
activation. Installed regressions pass after the final correction. The last
finding is minor and does not require another review under the Git workflow.
This production upgrade is effective on PR #118 merge; separate P7.9
requalification and later live/account gates remain open.
