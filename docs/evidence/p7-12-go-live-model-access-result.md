# P7.12 — Go live result (OpenCode Model Access): pass

Recorded: 2026-11-26. Source tip at launch: `f85cd1b` (`main` after
[setup PR #142](https://github.com/awesomejt/agent-harness/pull/142)).
Branch: `feature/07/p7-12-go-live-model-access-result`.
Setup: [p7-12-go-live-model-access-setup.md](p7-12-go-live-model-access-setup.md).
Prior MacBookPro stop: [p7-12-go-live-result.md](p7-12-go-live-result.md).
Task: [P7.12](../../tasks/07-native-adapters.md#p7-12).

## Operator attestation (U3/U4)

| Item | Attestation |
|---|---|
| Time given | 2:30 AM US Central Time, Thursday 2026-11-26 |
| Host clock at Extra Usage check / launch | Thu Nov 26 03:02:31 CST 2026 (driver start) |
| Workspace | Personal |
| Extra Usage | **Off** (Go page screenshot) |
| Credit | **$0.00** (Go page and Billing page) |
| Plan | Go renews Dec 3 / ~6d 22h |
| Model | `beam-free` enabled |
| Key | **OpenCode Model Access** via `~/.zshrc` `OPENCODE_API_KEY` (not MacBookPro) |

Screenshots retained by the operator session; not committed. No key material recorded.

## Pre-launch gates

| Check | Result |
|---|---|
| Rebuild without gate/key | Pass |
| `target/debug/ah` SHA-256 | `42211a23c54c3b8d8a9157c034a12d1dd87d182486bdb831495f96a165e36581` (match) |
| OpenCode 2.4.1 SHA-256 | `16a54b561fdad1a19be209ddc23990844a2368dad4864c18ca109372a46bb26a` (match) |
| Runtime | `opencode v2.4.1` |
| `P712_KEY` digest == Model Access | Pass (`e9ae4271fa05` 12-char prefix) |
| `P712_KEY` digest ≠ MacBookPro | Pass (`a274464c86e2`) |
| `AH_P712_LIVE=operator-attested` | One driver process; unset after |

## Driver adjustments before the passing invocation

Earlier same-session invocations after setup merge stopped on **driver** asserts
after harness exit 0 (auth succeeded). They are not provider `auth_required`
failures:

1. Stale `runtime_version == '2.4.1'` — machine records expose D106 constant
   `2.3.x or 2.4.x`.
2. Reviewer `grants == 0` — trusted Read/Search may grant in-project reads;
   fixture suites own deny/grant matrix proof.
3. Reviewer final-reply wording — beam-free needed an explicit ask to name
   `calc.py` and the `a - b` defect in the final reply.

`scripts/tests/go_live.py` was updated accordingly. The **passing** run is the
single full four-cell invocation below (one process; no cell re-run).

## Bounded live observation — pass

One `scripts/tests/go_live.py` process covering all four cells:

| Role | Mode | Exit | Attempts | backend_stop | cleanup | grants | tool_events | changed | acp labels |
|---|---|---|---|---|---|---|---|---|---|
| reviewer | cloud-only | 0 | 1 | end_turn | true | 4 | 15 | [] | null/null |
| coder | cloud-only | 0 | 1 | end_turn | true | 5 | 16 | `[calc.py]` | null/null |
| reviewer | local-first | 0 | 2 | end_turn | true | 4 | 15 | [] | null/null |
| coder | local-first | 0 | 2 | end_turn | true | 6 | 20 | `[calc.py]` | null/null |

Sanitized driver stdout ended with
`PASS: Go live coding and constrained roles on cloud-only and local-first`.
Local-first legs used a bound non-listening loopback LiteLLM endpoint (D034
unreachable-proxy fallback to Go). Reviewers left the project unchanged and did
not emit the outside-file sentinel. Coders changed only `calc.py`; independent
`python3 -B test_calc.py` passed. Instruction marker present on all four.
`beam-free` still does not prove paid entitlement or natural limit behavior.

## Disposition

P7.12 **live coding and constrained-review acceptance passes** for the OpenCode
Go native target on cloud-only and local-first fallback under this attestation,
Model Access key, OpenCode 2.4.1, and `beam-free`. Workflow portfolio acceptance
remains P7.13. P7.14 stays separately gated. Do not deliberately exhaust
allowance.

## Verification

- Fingerprint and key-digest gates before launch
- Single four-cell driver PASS with sanitized counters
- `python3 scripts/tests/doclinks.py` and `git diff --check` with the result PR
