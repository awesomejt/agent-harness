# P7.12 — Go native target implementation increment

The D105 contract is implemented for cloud-only and D034's single local-first
fallback. The selected `opencode-go` provider is carried separately from the
OpenCode runtime: model selection, settings-only key overlay, provider policy,
catalog and ACP session use that exact provider. Go agent preflight requires
exactly one title helper with the selected model. Existing private state, source
validation, request constraints, permission handling and cleanup remain in use.
Go limit errors stop under existing uncertainty rules; there is no chain or
classifier in this increment.

The fake OpenCode suite exercises both native providers with and without
`--no-sync`, including source/provider/catalog/helper refusals, permissions,
model mismatch, output redaction, project preservation, cancellation and Go
limit errors. Local-first fixtures exercise Go on an unreachable proxy, trusted
permissions, limit stop, helper refusal and a reachable local route. Config
fixtures verify Go key requirements, model override and fallback selection.
Machine records retain `runtime: "opencode"` and identify the Go provider in
the `opencode-go/MODEL` model field, both directly and on fallback.
These are synthetic checks and do not establish account access, paid allowance,
or installed behavior. P7.10's free-model live result is not P7.12 acceptance.

P7.12 remains open: separately reviewed live coding and constrained-review
acceptance, with a fresh same-session account and Extra Usage-off attestation,
are still required. Do not deliberately exhaust the allowance.

Validation on macOS: `cargo test --locked`, locked Clippy, the targeted native,
local-first and machine suites, doc links and `git diff --check` passed. The
full offline runner passed 52/52 suites, including installed OpenCode process
and isolation regressions. Grok reviewed the implementation with zero blockers
or concerns; its two nits were addressed with the runbook heading correction and
machine attribution fixtures. This does not replace the pending live acceptance.
