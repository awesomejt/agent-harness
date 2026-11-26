# P7.12 — Go live setup (OpenCode Model Access key)

Recorded: 2026-11-26. Baseline: `fe44f2d` (`main` after
[PR #141](https://github.com/awesomejt/agent-harness/pull/141)).
Branch: `feature/07/p7-12-go-live-model-access-setup`.
Prior stops: [unclassified](p7-12-go-live-setup.md),
[`auth_required` with MacBookPro key](p7-12-go-live-result.md).
Post-D107 driver: [continuation](p7-12-go-live-continuation.md).
Task: [P7.12](../../tasks/07-native-adapters.md#p7-12).

## Scope

This is a **new** reviewed live-attempt setup, not a retry of the #141 result
and not a model request. It selects a different Personal-workspace API key after
Console evidence showed why the prior key returned `auth_required`. No
authentication, provider request, or key material is recorded here.

## Why a new setup

The 2026-11-26 MacBookPro-keyed run stopped with D107 `acp_error=auth_required`
([result](p7-12-go-live-result.md)). That record does not authorize a retry.
Operator Console screenshots (session-retained, not committed) show the
Personal workspace and two Personal API keys:

| Label | Scopes / permissions | UI preview prefix | Role in this setup |
|---|---|---|---|
| **OpenCode Model Access** | 7 scopes; last used Nov 25 | `oc_sk_e3…` | **Selected** CLI / model key (`OPENCODE_API_KEY` / `P712_KEY`) |
| **MacBookPro** | Read only; last used during the failed run | `oc_sk_bc…` | **Excluded** — explains prior `auth_required` |

Host-side identity check (hashes only, no secrets): the current
`OPENCODE_API_KEY` assignment in `~/.zshrc` matches the **OpenCode Model Access**
entry in `~/opencode-api-keys` and does **not** match MacBookPro. The driver
must load that Model Access value into `P712_KEY` and must not use MacBookPro.

## Operator attestation for the upcoming live run

| Item | Evidence in this session |
|---|---|
| Workspace | Personal (Activity workspace selector checked; General settings Name=`Personal`) |
| Key | OpenCode Model Access (7 scopes), not MacBookPro (Read only) |
| Model | `beam-free` (unchanged operator selection) |
| Plan / usage | Activity shows Go monthly ~1% used; renews Dec 3 |
| Extra Usage | **Not re-shown** in the new screenshots (Activity / API Keys / General only). Same-calendar-day prior Go-page attestation had Extra Usage **off** and $0.00 credit. Operator directed this new attempt under that same-day Extra Usage-off state. A contradicting Go-page state before launch blocks the run. |
| Host clock at setup | Thu Nov 26 02:07:25 CST 2026 |

Record the host clock again immediately before the live driver starts. Fresh
time/TZ confirmation at launch remains part of the result evidence.

## Fingerprints (rebuild before live)

Built with gate/key env vars absent. Digests match the prior continuation
binary (no Rust change since #140):

| Artifact | SHA-256 |
|---|---|
| `target/debug/ah` | `42211a23c54c3b8d8a9157c034a12d1dd87d182486bdb831495f96a165e36581` |
| Homebrew OpenCode 2.4.1 | `16a54b561fdad1a19be209ddc23990844a2368dad4864c18ca109372a46bb26a` |

Recheck both immediately before the live run after this setup merges. Runtime
must remain `opencode v2.4.1`.

## Offline checks

| Check | Result |
|---|---|
| `python3 -m py_compile scripts/tests/go_live.py` | Pass |
| Optimized Python (`-O`) | Refused: assertions required |
| `cargo build --locked` without gate/key | Pass; digests above |

## Live gate (not authorized by this PR alone)

After Grok feature review and merge of this setup:

1. Rebuild/recheck fingerprints from the reviewed revision.
2. Confirm Model Access key is loaded into `P712_KEY` (not MacBookPro); set
   `AH_P712_LIVE=operator-attested` for one driver process only; unset after.
3. Record host clock and the attestation table above in the **result** evidence.
4. Run `scripts/tests/go_live.py` once (reviewer/coder × cloud-only/local-first).
5. Any failure/uncertain stop is for review only — not permission to retry or
   to switch keys/models without a new reviewed setup.

`beam-free` still cannot prove paid entitlement or natural limit behavior. Do
not deliberately exhaust allowance. P7.12 stays open until a separate result
PR passes review; P7.14 stays blocked.

## Verification

- `python3 scripts/tests/doclinks.py`
- `git diff --check`

No live prompt in this increment.
