# P7.9 — Disposable explicit catalog/cache control

Recorded: 2026-11-14, America/Denver. Baseline: `2629a8b`.
Branch: `feature/07/p7-9-explicit-catalog-proof`.
[Task](../../tasks/07-native-adapters.md#p7-9),
[D090 investigation](p7-9-catalog-investigation.md),
[authenticated refusal](p7-9-authenticated-inventory-refusal.md).

## Scope and review boundary

This increment implements D090's disposable unauthenticated installed experiment.
The helper and synthetic setup receive PR review before installed execution.
Installed results are pending that review. It accepts no operator-root or database
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
The connection closes before the next boot. This is experiment-only authority;
it does not authorize SQLite access on retained operator state.

Two boots without the explicit-file option must expose the synthetic cached
provider/model and 237-ID set, which the unchanged 236-ID gate refuses. Two boots
with `OPENCODE_MODELS_PATH` restored must equal the accepted fresh observation.
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

Offline guard and metadata cases pass. Installed evidence remains pending the
initial helper/setup review; no installed catalog run has occurred yet.

Even a passing experiment establishes precedence only on disposable no-auth
state. It does not explain the operator root's 336 IDs, prove authenticated
provider metadata, account controls or inference. A separately reviewed revised
authenticated control plan must select exact catalog bytes, address file lifecycle
and metadata expectations, and retain every non-catalog gate before any later
same-root D085–D088 attempt. No authenticated helper expansion is part of this PR.
