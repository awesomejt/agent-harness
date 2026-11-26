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
authentication, provider request, secret values, or full key material is
recorded here. Console UI preview prefixes are omitted; keys are identified by
label and scope only.

## Why a new setup

The 2026-11-26 MacBookPro-keyed run stopped with D107 `acp_error=auth_required`
([result](p7-12-go-live-result.md)). That record does not authorize a retry.
Operator Console screenshots (session-retained, not committed) show the
Personal workspace and two Personal API keys:

| Label | Scopes / permissions | Role in this setup |
|---|---|---|
| **OpenCode Model Access** | 7 scopes; last used Nov 25 | **Selected** CLI / model key (`OPENCODE_API_KEY` / `P712_KEY`) |
| **MacBookPro** | Read only; last used during the failed run | **Excluded** — explains prior `auth_required` |

How the wrong key was used before: the #141 driver was instructed to load the
MacBookPro file label into `P712_KEY` directly. It did not take
`OPENCODE_API_KEY` from the shell. This setup forbids that path.

Host-side identity check at setup time (hashes only, no secrets): the current
`OPENCODE_API_KEY` assignment in `~/.zshrc` matches the **OpenCode Model Access**
entry in `~/opencode-api-keys` and does **not** match MacBookPro.

## Operator attestation for the upcoming live run

| Item | Evidence in this session |
|---|---|
| Workspace | Personal (Activity workspace selector checked; General settings Name=`Personal`) |
| Key | OpenCode Model Access (7 scopes), not MacBookPro (Read only) |
| Model | `beam-free` (unchanged operator selection) |
| Plan / usage | Activity shows Go monthly ~1% used; renews Dec 3 |
| Extra Usage | **Not re-shown** in the setup screenshots (Activity / API Keys / General only). Same-calendar-day prior Go-page UI had Extra Usage **off** and $0.00 credit. The live gate below requires a **fresh Go-page check** immediately before launch; carry-forward alone is not enough. |
| Host clock at setup | Thu Nov 26 02:07:25 CST 2026 |

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
2. **Key load check (required, record in result evidence):** set `P712_KEY` from
   the OpenCode Model Access value (via updated `OPENCODE_API_KEY` / file label —
   never MacBookPro). Immediately before launch, compute SHA-256 of `P712_KEY`
   and of each labeled entry in `~/opencode-api-keys`; require the `P712_KEY`
   digest to equal Model Access and to differ from MacBookPro. Record only the
   12-character digest prefixes and pass/fail — never the key. Set
   `AH_P712_LIVE=operator-attested` for that one driver process; unset both
   after.
3. **Extra Usage check (required, record in result evidence):** open the
   Console Go page for the Personal workspace immediately before launch;
   confirm Extra Usage is **off** and available credit is **$0.00**; record the
   host clock for that check. If the Go page is unavailable or contradicts,
   stop without launching.
4. Record host clock at driver start, workspace/key/model attestation, and the
   two checks above in the **result** evidence.
5. Run **one** `scripts/tests/go_live.py` process. That single invocation covers
   all four acceptance cells in order (cloud-only reviewer, cloud-only coder,
   local-first reviewer, local-first coder) and stops at the first failed
   assertion with no second invocation and no retry.
6. Any failure/uncertain stop is for review only — not permission to retry or
   to switch keys/models without a new reviewed setup.

`beam-free` still cannot prove paid entitlement or natural limit behavior. Do
not deliberately exhaust allowance. P7.12 stays open until a separate result
PR passes review; P7.14 stays blocked.

## Verification

- `python3 scripts/tests/doclinks.py`
- `git diff --check`

No live prompt in this increment.
