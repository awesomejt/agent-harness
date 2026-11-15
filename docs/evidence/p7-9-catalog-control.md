# P7.9 — Disposable explicit catalog/cache control

Recorded: 2026-11-14, America/Denver. Baseline: `2629a8b`.
Branch: `feature/07/p7-9-explicit-catalog-proof`.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D090 investigation](p7-9-catalog-investigation.md),
[authenticated refusal](p7-9-authenticated-inventory-refusal.md).

## Scope and review boundary

This increment implements D090's disposable unauthenticated installed experiment.
The helper and synthetic setup receive PR review before installed execution.
Grok completed the initial helper/setup review with 0 blockers, 0 concerns and
one nit. The nit is addressed below. Installed execution is blocked by the
existing executable pin, before any OpenCode launch. It accepts no operator-root or database
argument and never attaches to existing state. The operator login root and all
D085–D088 helpers remain untouched. P7.9 remains unpassed and P7.11 blocked;
D034, D089 and the separate Go gates are unchanged.

## Reproducible experiment

```sh
python3 -B scripts/experiments/chatgpt_catalog_control.py --source <v2.2.5-checkout>
```

Only macOS with the existing pinned OpenCode executable and clean official source
is supported. The D090 source audit, source/plugin fingerprints and executable
SHA-256 are rechecked before launch. D078's composed containment controls are
revalidated, including operator-home read denial, outside-write denial and network
denial except owned observer transport. No additional network allowance is used
by catalog boots. Project/ancestor/machine discovery denials, inert resource
sentinels, source guards and the exclusive root lock are retained.

The catalog starts with the hash-pinned source snapshot. An existing catalog
provider (`abacus`) carries an inert synthetic model and explicit provider/model
names plus `https://explicit.invalid/v1`. It keeps the expected 236-ID set. The
synthetic cache changes those names and endpoint to `cached.invalid`, and adds one
synthetic integration with a non-secret environment-variable name. Provider
activation is explicitly enabled for the probe's metadata, without a key,
connection, session or model turn. The other catalog definitions are unchanged.

A fresh no-auth boot must pass the exact fixed inventory digest, connection and
resource checks and the synthetic provider/default-model probe. The public
provider/model output is reduced to an in-memory SHA-256; no raw runtime output
is emitted. This baseline is compared with the restored catalog and later
explicit-file boots, including integration-method and resource digests.

## Synthetic database setup

The script creates the root itself through exclusive `create_root`/`new_case`
inside a `TemporaryDirectory`, holds its advisory lock and proves a second
process is refused. After the first server has stopped, it checks that the
runtime-owned database is a regular single-link owned file beneath that exact
new root, without symlinked ancestors. A fixed SQLite insert writes only
`models-dev:v2:catalog` with a synthetic body, encoded as the pinned KV and loader
schemas require. `mode=rw` refuses a missing database; no generic row reads,
credential queries, updates, deletes or externally supplied database path exist.
A pre-existing key gives a distinct sanitized refusal; the insert never replaces
an existing value. The connection closes before the next boot. This is experiment-only authority;
it does not authorize SQLite access on retained operator state.

Two boots without the explicit-file option must expose the synthetic cached
provider/model and 237-ID set, which the unchanged 236-ID gate refuses. Two boots
with `OPENCODE_MODELS_PATH` restored must equal the accepted fresh observation.
A further cache-only boot after each explicit-file boot must still equal the
original cache control. This proves both explicit boots override a retained seed
without adding database reads, and addresses Grok’s nit about cache persistence.
This paired control distinguishes an effective cache seed from a silent no-op.
Both sides keep model fetching disabled and external network denied.

## File and fallback controls

`owned.catalog` is pinned by SHA-256 and must be a JSON object, a regular
single-link owned file beneath the new root with no symlinked ancestors. The
helper strips only its exact catalog variable before applying the existing
source/environment allowlist. It denies writes to that literal catalog path
inside the runtime sandbox and rechecks the bytes after shutdown.

Missing, malformed, changed-byte, same-ID metadata, symlink and hardlink cases
must refuse before launch. The restored file must produce the unchanged effective
observation. The metadata probe independently requires the synthetic model ID,
provider/model names, package, endpoint and context limit: bundled fallback or a
same-ID cache metadata substitution cannot pass by matching only the ID digest.
Offline cases exercise those mismatches explicitly. There is no unsafe bypass
flag to force malformed files through the installed loader.

## Outcome and remaining gate

Offline guard and metadata cases, source audit and targeted regression suites pass.
Independent read-only safety review found no actionable defects. Grok reviewed
`8543915` on [PR #117](https://github.com/awesomejt/agent-harness/pull/117):
0 blockers, 0 concerns, 1 nit. The nit is addressed with the distinct pre-existing
key refusal and post-explicit cache-only controls, without generic database reads.

The installed attempt stopped at the executable hash check, before boundary
probes, OpenCode launch, root creation, cache seeding or integration observation.
The existing hash `4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`
remains required. The host’s Homebrew entry now points to OpenCode 2.3.0. A
separately downloaded official `v2.2.5` darwin-arm64 release asset hashes to
`abe4d88594bffb12b364375b8a6732d2d1f7a977195ed1a35c5c76f8e89c9e0e`;
the recovered Homebrew 2.2.5 arm64 bottle’s extracted executable hashes to
`76d43776676318544cab212b22755a7f066076acfc49ed8326e628079a40f902`.
Neither is the accepted executable. Both downloads stayed in temporary storage;
no installation, runtime launch or change to the host executable occurred.
The helper’s release-asset attempt exited 1 with an executable-pin refusal.

The broader offline suite finishes **30/41 passed**; all eleven failures are
installed OpenCode version/preflight cases
with the host 2.3.0 binary. `single_runtime.py` reproduces the pre-submission
failure on unchanged `main` (`2629a8b`) in a detached temporary worktree, with no
prompt or project edit. Production source, dependencies and those fixtures are
unchanged. These host-version failures do not substitute for a passing installed
catalog experiment.

Next: recover the exact accepted executable, or separately review a new executable
and source pin with all required source/plugin/catalog/containment evidence.
Then run this experiment and review its installed results before designing an
authenticated continuation. No installed precedence pass is claimed by this PR.

Even a passing experiment establishes precedence only on disposable no-auth
state. It does not explain the operator root's 336 IDs, prove authenticated
provider metadata, account controls or inference. A separately reviewed revised
authenticated control plan must select exact catalog bytes, address file lifecycle
and metadata expectations, and retain every non-catalog gate before any later
same-root D085–D088 attempt. No authenticated helper expansion is part of this PR.
