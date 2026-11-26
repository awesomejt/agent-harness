# P7.12 — Go live continuation setup (post-D107)

Recorded: 2026-11-26. Baseline: `4b1a295` (D107 classifier on `main` via
[PR #139](https://github.com/awesomejt/agent-harness/pull/139)).
Branch: `feature/07/p7-12-go-live-continuation`.
Prior stopped attempt:
[setup](p7-12-go-live-setup.md#bounded-live-observation--stopped),
[offline assessment](p7-12-go-failure-assessment.md),
[classifier design](p7-12-acp-error-classification.md).
Task: [P7.12](../../tasks/07-native-adapters.md#p7-12).

## Scope

This is a proposed setup for review, not live acceptance and not a model
request. It prepares a fresh continuation of the P7.12 coding and constrained
review gate after the offline ACP error classifier landed. The 2026-11-25
`beam-free` failure remains unclassified; this setup does not reconstruct it.
No authentication, provider request, account-page scrape, or key inspection
occurs in this increment.

## What changed since the stopped attempt

- D107 closed `acp_error` / `acp_data` labels are implemented on `main`. A later
  post-submission failure of the same shape will retain those labels on the
  attempt summary and an `attempt.acp_error` machine record, without provider
  error text.
- `scripts/tests/go_live.py` now asserts success leaves both labels null, and
  on a non-zero harness exit prints only sanitized counters: attempt index,
  `prompt_submitted`, `backend_stop`, `cleanup_confirmed`, closed labels,
  grant/tool counters, stdout/stderr sizes, and a bounded harness diagnostic
  tail. Response text and raw provider content stay withheld.
- The driver still requires Homebrew OpenCode 2.4.1, `AH_P712_LIVE=operator-attested`,
  and a non-synthetic `P712_KEY`, removes those two variables before other
  children, and supplies the key only to the harness. The project config names
  the env var; it does not store the value.
- One driver execution still makes at most four provider turns in a disposable
  Git project (reviewer/coder × cloud-only/local-first), stopping at the first
  failed assertion with no retry. The operator-selected model remains
  `opencode-go/beam-free`. That free model cannot establish paid entitlement,
  paid allowance consumption, or natural limit behavior.

## Offline checks (this increment)

Performed with `P712_KEY` and `AH_P712_LIVE` absent from the build environment:

| Check | Result |
|---|---|
| `python3 -m py_compile scripts/tests/go_live.py` | Pass |
| Optimized Python (`python3 -O`) | Refused: assertions required |
| Missing `AH_P712_LIVE` | Refused before project setup / provider contact |
| `P712_KEY=synthetic-unused-key` with gate set | Refused before project setup / provider contact |
| Wrong `opencode` on `PATH` | Refused: reviewed Homebrew runtime required |
| `cargo build --locked` without gate/key | Pass |

## Fingerprints (rebuild before live)

Source revision for this setup branch will be the merge tip after review; the
pre-review build used baseline `4b1a295` plus the driver/evidence changes in
this PR. Recheck both digests immediately before the live run.

| Artifact | SHA-256 |
|---|---|
| `target/debug/ah` (built without `P712_KEY` / `AH_P712_LIVE`) | `42211a23c54c3b8d8a9157c034a12d1dd87d182486bdb831495f96a165e36581` |
| Homebrew OpenCode 2.4.1 (`/opt/homebrew/Cellar/opencode/2.4.1/bin/opencode`) | `16a54b561fdad1a19be209ddc23990844a2368dad4864c18ca109372a46bb26a` |

Rebuild from the reviewed revision after merge or any further push; do not reuse
the stopped-attempt binary digest (`7618f04e…`). OpenCode digest unchanged from
the prior setup.

## Live gate (not authorized by this PR)

Before any inference:

1. Setup review of this continuation completes (Grok feature review on the PR).
2. Rebuild `target/debug/ah` from the reviewed revision with gate/key absent;
   confirm both fingerprints.
3. Fresh same-session operator attestation (U3/U4): current time and time zone;
   confirmation of the Go subscription workspace, active plan, and Extra Usage
   off. Recheck after any account or plan change. The prior 2026-11-25
   attestation does not carry forward.
4. Operator supplies `P712_KEY` (or the configured name) only for the driver
   process and sets `AH_P712_LIVE=operator-attested` for that one execution.
5. LiteLLM/Claude readiness (U7) is not required for the cloud-only legs; the
   local-first legs use a bound non-listening loopback endpoint as the
   unreachable proxy.

Any failure, interruption, uncertain effect, unexpected output, or cleanup
issue is a stop for review — not permission to retry. If the harness stops
uncertain after submission, record the closed `acp_error` / `acp_data` labels
from the sanitized driver output; do not collect raw error text, account state,
or another request merely to explain it. Do not deliberately exhaust allowance.
This setup alone does not complete P7.12. A separate result review and PR merge
are required after the live run.

## Verification

- `python3 -m py_compile scripts/tests/go_live.py`
- Offline refusal matrix above
- `python3 scripts/tests/doclinks.py`
- `git diff --check`

No live prompt in this increment.
