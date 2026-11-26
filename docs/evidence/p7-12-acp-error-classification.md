# P7.12 — Bounded ACP error classification

Recorded: 2026-11-25. Baseline: `f7e5ae8`.
Branch: `feature/07/p7-12-acp-error-classification`. Decision: D107.
[Stopped attempt](p7-12-go-live-setup.md#bounded-live-observation--stopped),
[offline assessment](p7-12-go-failure-assessment.md),
[task](../../tasks/07-native-adapters.md#p7-12).

## Scope

This increment specifies how a later implementation retains a bounded ACP
error classification after prompt submission. It does not change `src/`,
launch OpenCode, read a credential or account page, or send a model request.
The 2026-11-25 `beam-free` failure stays unknown: its ACP error was discarded
with the disposable project, and this design does not reconstruct it. P7.12
stays open. No retry, model change, or weaker live gate is selected.

## What the adapter discards

On `f7e5ae8`, `src/acp.rs` reduces the foreground prompt task to
`value.is_ok()`. After `prompt submitted` (`active` is that same flag), a
finished connection with no protocol violation emits one static sentence,
`runtime/provider/transport failure or cancellation response timeout; effects unknown`,
and the attempt ends exit 4 (D039). The `agent-client-protocol` 3.6.0 /
schema 1.13.0 v1 `Error` (`code`, `message`, `data`) is dropped before any
progress event, attempt note, or machine record. A peer internal error, an
authentication error, a Go limit body, a harness response timeout, and a
connection close without an error object are indistinguishable in that
sentence. Stderr remains withheld. Zero grants and zero tool events do not
show that the provider never received the prompt.

## Closed labels

The implementation classifies with a pure function of
`&agent_client_protocol::Error` that returns two copyable enums and no
`String`. Formatting uses `match` to `'static` words. `Error`'s `Display` and
`Debug` are not written to progress, notes, machine records, or stderr.

`acp_error` is exactly one of:

| `ErrorCode` | Label |
|---|---|
| `ParseError` (−32700) | `parse_error` |
| `InvalidRequest` (−32600) | `invalid_request` |
| `MethodNotFound` (−32601) | `method_not_found` |
| `InvalidParams` (−32602) | `invalid_params` |
| `InternalError` (−32603) | `internal_error` |
| `RequestCancelled` (−32800) | `request_cancelled` |
| `AuthRequired` (−32000) | `auth_required` |
| `ResourceNotFound` (−32002) | `resource_not_found` |
| `Other(_)`, including `i32::MIN` and `i32::MAX` | `other` |

The numeric code behind `other` is not emitted. Adding a code requires a
reviewed amendment.

`acp_data` is exactly one of `absent`, `unclassified`, or `go_limit`.

- `go_limit` only when `acp_error` is `internal_error`, `data` is a JSON
  object, `errorName` is exactly `provider.go-limit`, and `service` is
  exactly `session`. That pair is the shape in pinned
  `session/to-session-error.ts` / `cli/src/acp/error.ts` as recorded for
  P7.10, and in the `go-limit-rpc` fake. Extra keys are ignored.
- `absent` when `data` is omitted or JSON null.
- `unclassified` for every other value: a near-miss name or service, a
  non-object, a string (including `Error::into_internal_error`'s message
  stuffed into `data`), an array, or a matching `errorName` whose `service`
  differs.

`message` is never copied into the result. `data.uri`, `data.sessionId`, and
any other field are never copied. A length, digest, or prefix of `message` or
`data` is not a label. For a code other than `internal_error`, a present
non-null `data` is `unclassified` and is not inspected for `errorName`.

Call sites that are not a peer error record their own labels and do not infer
them from `internal_error` plus `absent`, because a peer can send that shape:

- The cancel and deadline arms already map an elapsed five-second budget to
  `Error::internal_error()`. That elapsed case records
  `acp_error=response_timeout` and `acp_data=absent` at the arm, then drops
  the constructed error. A peer `Err` observed while waiting is classified
  with the pure function instead.
- After submission, a finished connection with no stored label and no
  protocol violation records `acp_error=unknown` and `acp_data=absent`.

Labels live in an `Arc` owned outside the foreground task, written before the
task returns, and read after `is_ok()`. A label is emitted only when `active`
is true. Pre-submission failures leave both fields null and keep today's
setup-stopped, failed, and cancelled exits.

A protocol violation stays the existing sticky flag. It is not cleared or
replaced by these labels, and exit precedence is unchanged.

## Records

Human progress may append the two words to the existing uncertain sentence,
for example
`runtime/provider/transport failure or cancellation response timeout; effects unknown; acp_error=internal_error; acp_data=go_limit`.
The words are only the closed labels.

The attempt summary gains `acp_error` and `acp_data`, initialized null with
the other unobserved facts in `progress.rs`, and set only for a
post-submission classification. One `attempt.acp_error` machine record
carries those two fields and is emitted after the `Error` is dropped.
`EXECUTION.md` names the fields in the implementation increment and keeps the
rule that records contain no provider error text. New fields are allowed in
output v1. No new `outcome` value is added.

Success, cancellation with a backend terminal, and pre-submission rejection
leave both fields null.

## Outcomes that stay put

Exit 4 remains the result of a post-submission failure without a trustworthy
terminal (D039), including `go_limit` and `auth_required`. D031 still refuses
fallback from a generic ACP error; these labels are diagnostics, not
provider-category evidence for a transition. D034 is unchanged: local-first
falls back only when the proxy is unreachable before launch. P7.14 owns any
later use of `provider.go-limit` as a chain classifier. This design does not
prove that classifier, and the implementation must not read `acp_data` when
choosing another attempt. The same route is not retried. Confirmed cleanup
and zero grants still do not prove that no work ran.

## Fixtures the implementation must add

Offline only. The pure function needs no network, key, or OpenCode process.
Each case asserts the exact enum pair and that `SECRET_SENTINEL` is absent
from every event, note, and stdout/stderr byte.

1. Every known code, with the canary in `message` and in `data`.
2. `Other` for −32099, 0, 1, `i32::MIN`, and `i32::MAX`, with a canary
   message. The label is `other` and the integer is absent.
3. `internal_error` with exact `service=session` and
   `errorName=provider.go-limit`, a canary message, and a canary extra key.
   Labels: `internal_error`, `go_limit`.
4. Near misses stay `unclassified`: trailing space, different case, a longer
   name, the canary as `errorName`, `service` other than `session`,
   `errorName` as an object, array, or number, `data` as a string, array, or
   null versus omitted.
5. `resource_not_found` with `data.uri` set to the canary, and
   `auth_required` with a canary `data` object.
6. A multi-megabyte `message` containing newlines, ANSI, and bidi overrides.
   The function must not allocate its result from `message`.
7. Elapsed cancel and deadline budgets record `response_timeout` /
   `absent` without matching on the text `Internal error`. A peer error that
   arrives during that wait keeps the peer labels.
8. Connection end after submission with no `Error` records `unknown` /
   `absent`, and the exit stays 4 when cleanup is confirmed and no terminal
   was stored.
9. Pre-submission model or launch failure leaves both fields null.
10. Success and a normal `end_turn` leave both fields null.
11. A protocol violation still ends exit 4 with `protocol_violation: true`.

Extend the existing fakes, without changing their exits or launch counts:

- `scripts/tests/native.py` `rpc-error`: exit 4, canary absent,
  `internal_error` / `unclassified`.
- `scripts/tests/native.py` `go-limit-rpc`: exit 4, one `native` launch,
  canary absent, `internal_error` / `go_limit`.
- `scripts/tests/machine.py` `rpc-error`: the current
  `prompt_submitted`, null `backend_stop`, and zero grant/tool assertions,
  plus the two labels.
- `scripts/tests/local_first.py`: reachable `rpc-error` stays one local
  attempt at exit 4; unreachable `go-limit-rpc` on `opencode-go` stays one
  native attempt at exit 4, with the labels and no further attempt.

## Rejected for this increment

Logging or hashing the raw error, emitting `Other`'s integer, taking new
`errorName` values from a live response, reading stderr or the Go account
page to explain the stopped attempt, changing exit 4 when grants are zero,
and any new CLI flag.

## Next increment and live gate

Implement the pure function, the `src/acp.rs` capture, the summary fields,
the `EXECUTION.md` note, and the fixtures above. That increment still sends
no live prompt. Review of the implementation precedes any new model request.
A later live continuation needs its own reviewed scope, a binary rebuilt and
fingerprinted from the reviewed revision, and a fresh same-session
attestation of the Go workspace, plan, and Extra Usage off. The operator
selects the model at that gate. This record accepts the design only.

## Verification

Documentation only: `python3 scripts/tests/doclinks.py` and
`git diff --check`. No executable file changes, so the Rust suite is not
required for this increment.
