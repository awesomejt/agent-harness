# P7.12 — Go live continuation result (stopped: auth_required)

Recorded: 2026-11-26. Source: `8eafbda` (`main` after
[PR #140](https://github.com/awesomejt/agent-harness/pull/140)).
Branch: `feature/07/p7-12-go-live-result`.
Setup: [p7-12-go-live-continuation.md](p7-12-go-live-continuation.md).
Prior unclassified stop: [p7-12-go-live-setup.md](p7-12-go-live-setup.md).
Task: [P7.12](../../tasks/07-native-adapters.md#p7-12).

## Operator attestation (U3/U4)

Same operator session, before the run:

| Item | Attestation |
|---|---|
| Time given | 12:57 AM Central Time (US), Thursday 2026-11-26 |
| Host clock at run start | Thu Nov 26 01:06:45 CST 2026 |
| Workspace | Personal (screenshot: Go settings header) |
| Plan | Active individual Go subscription (~$10/month); UI “Renews in 6d 23h” |
| Extra Usage | Off (screenshot toggle grey/off) |
| Credit | $0.00 available credit |
| Model | `beam-free` / Beam Free enabled in UI |
| Key instruction | Use the MacBook Pro entry from `~/opencode-api-keys` as `P712_KEY` |

Screenshot retained by the operator session; not committed. Workspace name is
visible in the UI (“Personal”). Key values are not recorded.

## Fingerprints (rechecked before run)

Rebuilt with `P712_KEY` and `AH_P712_LIVE` absent. Digests matched the
continuation setup record:

| Artifact | SHA-256 | Match |
|---|---|---|
| `target/debug/ah` | `42211a23c54c3b8d8a9157c034a12d1dd87d182486bdb831495f96a165e36581` | yes |
| Homebrew OpenCode 2.4.1 | `16a54b561fdad1a19be209ddc23990844a2368dad4864c18ca109372a46bb26a` | yes |

Runtime version: `opencode v2.4.1`. Gate: `AH_P712_LIVE=operator-attested` for
the single driver process only. The MacBook Pro–labeled key was loaded into
`P712_KEY` for that process and unset immediately after. No key material appears
in this record.

## Bounded live observation — stopped

One `scripts/tests/go_live.py` execution. First case: cloud-only reviewer on
`opencode-go/beam-free`. Isolated preflight and ACP session selected that model
on OpenCode 2.4.1; the prompt was submitted. About 0.3 seconds later the harness
ended **uncertain** (exit 4) with confirmed cleanup.

Sanitized attempt facts from the driver failure summary (D107 labels retained):

| Field | Value |
|---|---|
| Role / mode | reviewer / cloud-only |
| Harness exit | 4 |
| `prompt_submitted` | true |
| `backend_stop` | null |
| `cleanup_confirmed` | true |
| `grants` / `tool_events` / permission requests | 0 / 0 / 0 |
| `acp_error` | `auth_required` |
| `acp_data` | `unclassified` |
| Provider stderr size | 0 (raw withheld) |

No coder case and no local-first fallback case ran. No retry occurred. The
disposable project was removed with driver unwinding. Prompt submission means
provider receipt cannot be ruled out; zero tool events do not prove no work ran.

## Disposition

This does **not** pass P7.12 live acceptance. Relative to the 2026-11-25 stop,
D107 closed labels are present: the peer ACP error classified as
`auth_required` with `acp_data=unclassified` (not `go_limit`). That is a
diagnostic label only; it does not change exit 4, D031, or D034, and it is not
authorization to retry or to substitute another key or model.

Operator follow-up (outside this PR): confirm which Console API key belongs to
the attested Personal Go workspace. Any further live attempt needs its own
reviewed setup/continuation (re-fingerprint, fresh U3/U4 attestation); this
record does not authorize a retry. Do not deliberately exhaust allowance.
P7.12 remains open; P7.14 stays blocked.

## Verification

- Fingerprint match before launch
- Single driver run; sanitized counters and closed labels only
- `python3 scripts/tests/doclinks.py` and `git diff --check` on the result docs
  (recorded with the PR)
