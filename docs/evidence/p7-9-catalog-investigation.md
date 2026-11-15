# P7.9 — Pinned integration catalog investigation

Recorded: 2026-11-14, America/Denver. Baseline: `82a07ab`.
Branch: `feature/07/p7-9-inventory-investigation`.
[Task](../../tasks/07-native-adapters.md#p7-9),
[failed authenticated attempt](p7-9-authenticated-inventory-refusal.md),
[closeout boundary](p7-9-feasibility-closeout.md), D090.

## Outcome and limits

**The fixed 236-ID gate remains correct to refuse the observed 336-ID set.**
Pinned public source establishes that integration IDs are partly catalog-driven,
and `OPENCODE_DISABLE_MODELS_FETCH` does not exclude a retained catalog. It disables
automatic fetching, while startup can still read a catalog from the runtime-owned
database. This is a plausible mechanism for the post-login mismatch, **not a proved
cause on the operator root**. We did not read that root, its database, credentials,
cache or logs, or launch OpenCode. Neither an authenticated pass nor a revised
installed control follows from this investigation. P7.9 remains unpassed; P7.11
remains blocked. D034 and D089 are unchanged.

## Pinned public-source trace

Source: clean official v2.2.5 checkout at
`9bbb8ce18c80f099e0e448775f59d965ead40a21`. The audit below reuses the existing
source/plugin fingerprint checks and adds hashes for the catalog loader, bundler,
CLI build and KV implementation. All source links below use that commit.

| Component | Established behavior |
|---|---|
| [Built-in catalog plugin](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/plugin/models-dev.ts) | `opencode.models.dev` registers key/env integration methods for normalized providers with nonempty environment lists. It excludes two deprecated provider aliases. A fixed plugin identity does not imply fixed catalog-derived IDs. |
| [Catalog loader](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/models-dev.ts) | `populate`: usable explicit file first; otherwise cache when no file option; then bundled snapshot; finally network fetch only if enabled. Normalization can skip invalid providers/models and unsupported model routes. |
| Same loader | Default persistent key is `models-dev:v2:catalog`, with separate `:meta`. Cache body is a JSON string, decoded to a catalog; `updatedAt` and optional digest accompany it. Startup cache selection has no age test; the five-minute TTL gates refresh. `fetch: false` prevents the scheduled refresh, not `loadFromCache`. |
| [KV service](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/kv.ts), [table](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/kv/sql.ts) | The catalog is stored through the runtime database's `kv` table. An empty XDG cache directory does not prove absence of a retained catalog. No database inspection is needed to establish this source behavior. |
| [CLI server options](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/cli/src/server-process.ts) | `OPENCODE_DISABLE_MODELS_FETCH` maps only to `models.fetch`; `OPENCODE_MODELS_PATH` supplies `models.file`. Existing contained helpers set the former, not the latter. The printed official login command does not set either option. That makes catalog fetch/cache population possible during login; it does not prove it occurred. |
| [Snapshot bundler](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/script/models-snapshot.ts), [CLI build](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/cli/script/build.ts) | Build-time `OPENCODE_MODELS_SNAPSHOT` can replace the committed snapshot. The pinned [release workflow](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/.github/workflows/release.yml) fetches a catalog artifact and supplies that variable. A pinned source snapshot alone does not establish the installed executable's embedded catalog bytes. |

Thus built-in plugin definitions, the source-committed snapshot, the release's
embedded snapshot and the runtime-retained catalog are distinct inputs. Stable
plugin fingerprints and network denial do not make them interchangeable. The
earlier fresh installed 236-ID observation remains historical evidence for that
state; it does not identify the later 336 IDs or their origin. An ID digest also
cannot prove unchanged endpoints, methods or connection metadata.

## Reproducible source and synthetic audit

Run only against the clean public-source checkout:

```sh
python3 -B scripts/experiments/chatgpt_catalog_audit.py --source <v2.2.5-checkout>
```

The script accepts no runtime/root argument and makes no network requests. It
revalidates D075/D078 fingerprints, the 91-file plugin graph digest and the added
catalog source fingerprints before projecting provider IDs with the existing
D078 helpers. This projection uses source snapshot entries with nonempty `env`
plus plugin-named IDs; it does **not** implement the runtime's catalog normalizer.
The prior D078 installed baseline corroborates that particular projection.

Observed on this checkout:

| Audit | Result |
|---|---|
| Source snapshot entries with nonempty `env` | 230 |
| Plugin-named IDs | 19; six absent from the snapshot projection |
| Union | 236; SHA-256 `2cd1b632219bbd635a2f7a5911d6c0e36d7205d75cc4c85d751cb90081de73af` |
| Plugin-only IDs | `claude-agent`, `exa`, `firecrawl`, `parallel`, `tavily`, `tinyfish` |
| Add 100 synthetic IDs | 336; unchanged fixed digest gate refuses |
| Replace one ID, keeping count 236 | Unchanged fixed digest gate refuses |
| Reorder baseline IDs | Baseline digest preserved |

The deliberately constructed 336-ID projection does not reproduce the observed
digest `e762516c…`; it demonstrates that count alone cannot diagnose or accept the
state. No synthetic payload was submitted to OpenCode and no retained catalog
selection was experimentally proved. The audit's JSON records the source hashes;
it emits only public-source summaries and synthetic results.

## Next control-plan boundary

Select a **separate disposable, unauthenticated installed experiment** before any
authenticated continuation. A candidate is a harness-owned, hash-checked explicit
catalog file via `OPENCODE_MODELS_PATH`, with model fetching disabled, to take
precedence over cached catalogs without reading or editing database rows. This
requires a reviewed helper/profile/environment change; this record does not add
that variable to the existing helpers or authorize authenticated expansion.

The next experiment must:

1. Revalidate executable/source pins, D076 containment, source exclusions, locks
   and root ownership on newly created synthetic roots only. Keep credentials,
   operator login roots and external network out of the experiment.
2. Establish the exact owned catalog bytes and effective integration/provider/
   model observations across two boots. Demonstrate a distinct synthetic cached
   catalog versus the explicit catalog, using only a reviewed synthetic-state
   setup. Avoid generic database access against any operator state.
3. Cover missing, malformed, changed and symlinked catalog files with static
   pre-launch refusals and unchanged effective-output checks. The upstream loader
   catches file-read/parse failure and can fall back to the bundled snapshot;
   merely setting the variable is insufficient. Prove that fallback cannot be
   mistaken for an accepted explicit catalog, including a same-ID metadata change.
4. Retain the 236-ID baseline and all non-catalog source/plugin/connection gates.
   Do not substitute the observed 336 count/digest, delete retained state or relax
   network/source boundaries. A changed inventory plan requires its own evidence
   and decision before consumption.
5. Review the synthetic installed evidence and revised control plan before a
   later same-root D085–D088 authenticated attempt. Then record login, method/
   endpoint/helper, permission and fresh credits-off attestation results in order.

If explicit-file behavior or a safe synthetic cache setup cannot be established,
stop and record the remaining blocker. Catalog pinning alone would not prove
credential isolation, account settings or actual inference behavior. P7.10 stays
separate and P7.11/P7.13 retain their later acceptance gates.

## Validation

The source audit and all three synthetic ID projections pass. Existing retained-
state, login-preflight and endpoint/helper offline fixtures, documentation links/
anchors, anchor fixtures and `git diff --check` pass. No production Rust or
dependency changed; no runtime/login/session/model call ran.

[PR #116](https://github.com/awesomejt/agent-harness/pull/116): Grok reviewed
`9a396a3` with 0 blockers, 0 concerns and 0 nits. No re-review was required.
This source-investigation increment is effective on merge; it does not pass P7.9.
