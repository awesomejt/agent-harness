# P7.14 — Transition evidence assessment

Recorded: 2026-11-26. Baseline: `171f9c8`.
Task: [P7.14](../../tasks/07-native-adapters.md#p7-14); policy: D103 and
[action plan step 5](../SUBSCRIPTION_ACTION_PLAN.md#5-extend-fallback-conservatively).
This is a source assessment, not a chain decision, implementation, or acceptance.

## Existing evidence is insufficient to advance

| Boundary | Current source | Consequence for the chain |
|---|---|---|
| Coordination | `single::coordinate` invokes at most one native attempt and receives an `Exit`; `recovery::decide` requires `NotAttempted` and zero prior fallbacks. | A new typed, attempt-scoped result and a separately decided policy are needed. Do not infer eligibility from a progress message or exit code. |
| Go limit | `acp::classify_acp_error` labels the exact internal ACP error shape `service=session`, `errorName=provider.go-limit`; D107 keeps this diagnostic after submission. | The shape is a candidate classifier, not proof that the prompt did no work or that a real allowance was exhausted. D107 explicitly keeps exit 4 and forbids using the label for fallback. |
| Claude limit | `claude::classify` parses `rate_limit_event` status, and the session loop logs changes. `Terminal::Other` combines error, refusal and limit outcomes; the observed limit is not returned with the terminal. | Preserve ordered rejected-event and error-result evidence in an attempt-scoped typed result; allowed, warning, missing, malformed, out-of-order and conflicting events cannot establish the required pair. An arbitrary `Terminal::Other` is insufficient. |
| No work | ACP and Claude count permission requests, grants and tool activity. Existing project observation is advisory Git status counts, may be unavailable, excludes submodule contents and does not compare file contents. | Zero grants, zero events or equal status counts cannot independently prove no work. The action plan also says unchanged files alone are insufficient. A separately reviewed evidence design must establish affirmative no-work evidence for each runtime or stop the transition. |
| Cleanup | ACP and Claude check child cleanup; OpenCode additionally checks private-home removal. Results currently affect `Exit` and progress, rather than being returned as complete typed transition evidence. | An eligible result must include every applicable cleanup result, and missing or failed cleanup must stop. |
| Workflows | Sequences and Ralph currently record one fallback model and reuse resolved requests with updated prompts/deadlines. | The decision must specify ordered attempt records, resume compatibility, and whether exhaustion is remembered across workflow steps or iterations. A chain cannot silently disappear from durable validation. |

The runtime's permission enforcement and isolated source controls are necessary,
but their current counters alone do not establish that no work ran. Filesystem
comparisons also cannot establish absence of transient or external effects on
their own. A design must state its trust boundary and cover the provider's
structured terminal evidence, permission enforcement, protocol violations,
process lifecycle, and concurrent project activity. If those controls cannot
establish the required evidence, the safe outcome is no transition, even when
it means a configured later step is not reached. No live exhaustion is claimed;
fixtures establish handling of supplied events, not actual provider behavior.

## Required next increment

Before implementation, finalize the chain schema and D034 amendment, including
exact model and credential selection, agent-model precedence, validation of
nonfinal classifiers, preview, output/state version compatibility, and the
workflow exhaustion rule. Define a testable affirmative no-work predicate for
each classified target, or explicitly record why one cannot be supported.
Cover cancellation/deadline races, malformed and contradictory event sequences,
unauthorized tool activity, dirty projects and concurrent changes, cleanup
failure, and restart/resume. Preserve D103's first transition and no-chain
behavior. Do not treat an incomplete observation as a pass or fall back based
on error text. The operator's chain order and exact models are needed for their
configuration and later acceptance; no provider or model is inferred here.
