# P7.9 — Feasibility closeout assessment and route gates

Recorded: 2026-11-14. Baseline: `972db9712d71f8fbe83197454f2b1dd6a6800848` (merged D088). Branch:
`feature/07/p7-9-feasibility-closeout`. [Task](../../tasks/07-native-adapters.md#p7-9).
D089 clarifies the acceptance boundary; [PROJECT.md](../../PROJECT.md) owns status.

## Disposition

**Feasibility remains unpassed; P7.11 remains blocked.** The D085–D088 helpers
have merged, but their evidence pages still lack authenticated installed passes.
This assessment closes only the documentation increment. It neither runs those
helpers nor establishes a new installed result. No operator login, credential
inspection, account assertion, session, model turn or production change occurs.

This is a reconciliation of repository evidence, not a fresh provider terms or
version assessment. Recheck applicable official sources at the consuming
integration/version gate under the [action plan](../SUBSCRIPTION_ACTION_PLAN.md#source-freshness).

## Evidence and acceptance boundary

The table separates what each observation can establish from its consuming gate.
It is an evidence map, not another mutable task-status board.

| Evidence | What it establishes and limits | Required consuming gate |
|---|---|---|
| [D069–D071 candidate/source assessment](p7-9-source-state-controls.md) | Pinned 2.2.5 candidate and source/state risks; initial diagnostics alone did not pass isolation. | Retain the pin and exact exclusions when evaluating the continuation. |
| [D073–D076 source/resource controls](p7-9-installed-observer.md) | Synthetic read denials and installed fresh-state resource observations on this macOS host; experimental containment, not a production sandbox. | P7.9 must preserve these controls on the retained login root; P7.11 must explicitly design their production use or an equivalently evidenced boundary. |
| [D077–D078 retained-state controls](p7-9-retained-state-experiment.md) | Dedicated-root ownership, advisory lock, fixed integration set and synthetic reused-root/well-known/Console pairs. No authenticated login pass. | P7.9 requires D085 on a dedicated operator-login root; a global login cannot substitute. |
| [D085 login-mode preflight](p7-9-login-preflight.md) | Helper and unauthenticated refusal coverage; pending authenticated installed observation. | Two consecutive passing `--root` runs, each with two contained boots, on the same dedicated root. |
| [D086 method/endpoint/helper](p7-9-method-endpoint-helper.md) | Redacted metadata validation and explicit helper config; does not prove catalog access, model availability or actual request routing. | One authenticated installed pass on the D085 root for P7.9; actual model/helper behavior belongs to P7.11's separately gated live acceptance. |
| [D087 deny/trusted permissions](p7-9-permission-proof.md) | Effective permission tails through `debug agents`; no tool invocation or request-bound trusted grant. | One authenticated installed pass on that root for P7.9; adversarial tool behavior and exact trusted grants remain P7.11 acceptance requirements. |
| [D088 credits-off assertion](p7-9-credits-off.md) | Operator attestation plus null Console/Go-only usage query; null does not verify the ChatGPT setting. | One authenticated installed pass on that root with an operator attestation at most one hour old and not future-dated; point-in-time limitation remains explicit. |
| [D034 fallback](../../DECISIONS.md#2026-11-02--d034-local-first-fallback-only-on-pre-submission-litellm-reachability-failure) | Existing fallback only before any local submission, using LiteLLM TCP reachability. No new subscription fallback is selected. | P7.9 records this compatibility boundary; P7.11 fixtures must refuse unsupported route combinations and post-submission fallback/replay. No new live exhaustion experiment is needed to restate D034. |

## Bounded operator continuation

1. Use [D085's reproduction](p7-9-login-preflight.md#reproduction) to prepare a
   fresh dedicated root and print the official login command. Under D067/D077,
   the operator personally runs login; the harness never runs, wraps or observes
   OAuth. Do not inspect or copy a normal OpenCode login store.
2. Run D085 twice with `--root` on the prepared root. Stop on any refusal or pin
   drift; do not repair a gate by widening the source or network boundary.
3. On that same root and pinned checkout, run D086, then D087, then D088 using
   their linked reproduction commands. Obtain a fresh operator credits-off
   attestation for D088. All diagnostic boots deny network and perform no
   session/model calls. A changed login/root or runtime pin requires revalidation
   of the affected chain, not reuse of results from another root.
4. Record only redacted summaries, runtime/source pins, date/time/timezone and
   an opaque shared evidence label linking the runs in the existing D085–D088
   pages. Keep tokens, raw database/log payloads and private account identifiers
   out of repository evidence. Record failures as failures.
5. Submit the evidence for the required PR review. Only after every prerequisite
   passes may a separate P7.9 closeout propose accepted feasibility and unblock
   P7.11 design. This assessment does not pre-authorize that outcome.

## P7.11 boundary after accepted feasibility

Before production implementation, finalize explicit route/provider/auth/schema,
mode compatibility, model/helper restrictions, account-control prerequisites and
sanitized preview/result contracts in the configuration/execution documents.
Runtime-owned authentication must survive source isolation without token export.
An existing native API-key route or a generic `openai` provider label is not proof
of allowance-backed selection.

Separately gate a bounded operator-started live coding task and constrained review
on the operator's own account with credits off. Verify deny/trusted enforcement,
actual model/helper selection, no metered substitution, cancellation/group cleanup,
dirty-project preservation and sanitized output. Do not deliberately exhaust a
large allowance; distinguish fixture limit failures from observed provider behavior.
D034 remains unchanged: provider failure after submission stops without automatic
fallback or uncertain replay. F27/F28 require their own promotion decisions.
P7.13 still owns sequence/Ralph portfolio acceptance.

P7.10's dedicated Go proof and Extra Usage check remain separate; this evidence
does not transfer ChatGPT login or account-control conclusions to Go. Pi's accepted
Phase 8 scope and paused/blocked provider dispositions are unchanged.

## Validation

This documentation increment is checked with `scripts/tests/doclinks.py`, its
anchor fixtures and `git diff --check`. No installed or live test is claimed.
