# Subscription direction: action plan

Recorded 2026-11-09 from the operator's planning session. Reviewed baseline: `5af7411` (PR #80). Read this alongside [D066](../DECISIONS.md#2026-11-08--d066-block-antigravity-on-consumer-plan-terms)/[D067](../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage), the [subscription findings](evidence/p7-subscription-rescope.md) and the [provider terms check](evidence/p7-native-terms-check.md).

## Purpose and authority

Make the next milestone dependable local and subscription-backed execution through OpenCode, alongside the accepted Claude adapter. Pi can follow independently. Propose removing the requirement that paused Codex/Grok and blocked Antigravity adapters finish before useful portfolio delivery.

This document records the proposed work order, decision gates and acceptance evidence for future sessions. It does not supersede accepted decisions, change phase dependencies, authorize provider probes or inference, promote feature candidates, or declare new runtime support. Step 1 must reconcile the canonical contracts before consuming implementation starts. [PROJECT.md](../PROJECT.md) remains the only mutable task-status board; [DECISIONS.md](../DECISIONS.md) owns accepted decisions.

D068 implements step 1 through P7.8 and the aligned canonical contracts/task cards. Its finite Phase 7 exit covers local/Claude and explicit OpenCode ChatGPT/Go, with paused targets outside closure. Steps 2–3 and integrated acceptance map to P7.9–P7.13. Steps 4–5 remain candidate design work outside that exit gate; D034 remains binding. This original work-order record is retained; PROJECT.md owns execution status.

## Constraints to carry forward

- Prefer a hard usage-limit stop to overage. No metered API spend unless covered by an included subscription allowance or credit. Keep OpenAI's post-limit credit use and Go Extra Usage disabled; never silently substitute a metered provider.
- Subscription routes are for operator-started runs on the operator's own account. Other people must not be able to trigger runs on that subscription login.
- Preserve runtime-owned authentication. The harness must not read, copy, export or proxy subscription tokens or login stores, or impersonate another client.
- Keep Claude P7.2 accepted under D067's operator acceptance. Recheck Anthropic wording at each Claude Code pin change and no later than 2027-02-08.
- Keep Codex P7.3 paused/deprioritized, Grok P7.4 paused with SuperGrok first-party-only, and Antigravity P7.5 blocked under D066 in addition to its control gate. Gemini remains excluded. Preserve their historical evidence and resume conditions.
- Preserve permissions, effective routing checks, bounded lifecycle cleanup and no uncertain replay. Existing `local-only` means LiteLLM-only; it does not guarantee physical locality or zero cost.
- Keep one focused implementation task/PR active, with required PR review and holistic phase review. Passing mocks alone cannot close a live integration gate.

## Ordered work packages

### 1. Reconcile scope and dependencies

Record a successor decision to D067 that defines a finite selected portfolio, separates deferred/blocked adapters from mandatory delivery, and establishes revised P7.6/P7.7 acceptance. Preserve stable task references and historical acceptance; do not check off an unimplemented adapter as completed.

Update the affected parts of AGENTS.md, SPECIFICATION.md, IMPLEMENTATION.md, PROJECT_PLAN.md, relevant task cards, FEATURE_REVIEW.md and PROJECT.md. Update configuration/execution contracts when their consuming design choices are made. Review Phase 9 dependencies explicitly so the portfolio change neither strands them nor activates optional quota/ranking work without demand. Keep Pi independent unless a later evidenced choice makes it necessary.

**Acceptance:** consistent scope, mandatory routes, dependencies and review criteria; explicit deferrals and next task in PROJECT.md. The old four-adapter closure requirement remains effective until this decision and its contract changes are accepted.

### 2. Prove subscription integration feasibility

Assess OpenCode's ChatGPT plan path and dedicated Go provider separately, beginning with supported documentation and contained no-inference checks. Select/version each experiment before running it under the applicable gates.

The main ChatGPT risk is authentication versus isolation: today's OpenCode native route requires an API key and uses a private HOME; a TUI login alone is insufficient. Establish a supported runtime-owned login path without copying auth stores or weakening configuration-source isolation. Do not assume today's pinned OpenCode supports the current documented integration.

For Go, prove exact selection of the dedicated Go provider rather than the existing metered Zen provider, acceptable client identification, stable session headers and effective model/endpoint restrictions. Verify relevant account overage controls without reading secrets. Where account settings cannot be checked programmatically through a supported interface, document the operator check and limitation.

**Acceptance:** pinned capability/authentication evidence, configuration-source isolation, exact provider/model selection and effective permission control. A documented integration or successful handshake alone is insufficient. If OpenCode cannot meet the ChatGPT gate, record that result and assess Pi as a separate alternative; do not relax the gate implicitly.

### 3. Deliver explicit subscription routes

Proposed Go placement: OpenCode's dedicated provider first. This follows D067's current lean and avoids adding LiteLLM header/authentication handling and in-run fallback behavior at the same time. ChatGPT through OpenCode remains the preferred OpenAI path, subject to step 2. Decide the delivery order from feasibility evidence, then ship the routes as separate focused increments.

Finalize explicit route/provider/auth configuration and compatibility behavior before adding fields or flags. Keep existing supported behavior intact while requiring explicit allowance-backed selection for the new paths. Distinguish verified harness restrictions from provider account settings; local usage estimates cannot establish a provider-side hard cap. Do not claim zero-overage enforcement without evidence for the advertised guarantee.

**Acceptance per route:** a real coding task and constrained review; deny/trusted permission checks as advertised; model/helper isolation; cancellation and cleanup; sanitized preview/output; no accidental metered-provider selection. Preserve single-run semantics and verify sequence/Ralph reuse before advertising workflow support. Keep D034 fallback unchanged during this step.

### 4. Add physical-locality enforcement

Design F28's explicit private constraint independently of mode names. Define whether private means this host or operator-controlled local-network infrastructure, and how that property is established. A loopback/private-network proxy address alone does not prove that its downstream model is local.

Require sufficient effective downstream-route evidence or refuse the private claim. Forbid hosted alternatives and ensure runtime helpers, LiteLLM routing and invocation overrides cannot weaken the constraint. Define the enforceable model-traffic guarantee precisely rather than implying a complete network sandbox.

**Acceptance:** hosted destinations and unverified proxy routes are refused under the private constraint; allowed physical-locality cases are demonstrated. This gate precedes any automatic local-to-hosted model mapping.

### 5. Extend fallback conservatively

Only after explicit routes work, decide F27 and a replacement for D034. The proposed chain is local, then an explicitly selected Claude or ChatGPT subscription, then an explicitly selected Go model. Private runs exclude every hosted step. A chain is configuration, not an automatic policy to exhaust every subscription.

Before implementation:

1. Capture adapter-specific structured allowance-exhaustion behavior with fixtures and bounded live observation. Prefer a naturally exhausted allowance or a supported test mechanism; do not consume a large allowance merely to force an error. Synthetic cases alone do not prove provider behavior.
2. Require affirmative evidence that work did not execute and cleanup completed before a transition. Missing tool events, unchanged files or error-message text alone are insufficient. D034's submission boundary stays binding until explicitly replaced; a pre-tool limit error after submission is not automatically eligible today.
3. Preserve the prompt, role constraints and shared deadline with fresh runtime state/grants, bounded attempts and cycle prevention. Unsupported/authentication failures, cancellation, deadline expiry and uncertain effects must not become generic retry triggers.
4. Require explicit role-compatible model alternatives. A smaller sibling is not automatically the same model or an acceptable constrained-role replacement. Disable or explicitly govern runtime/proxy internal model switching.
5. Record attempted route/runtime/model, transition cause and source-attributed usage or unknown. Design a durable known-problem record for fallback-model completion without equating a successful child exit with verified task completion.

**Acceptance:** allowed/refused transition matrix, real exhaustion behavior, preserved constraints and no uncertain replay. Exhaustion after possible work stops for existing explicit recovery. Finishing an already-started task on another model is separate recovery design, outside this initial automatic chain.

### 6. Integrated acceptance and portfolio review

Exercise the supported routes through single runs, sequences and Ralph, including constrained reviewers, explicit fallback choices, limit failures, interruption/recovery and dirty-project preservation. Record tested runtime versions, provider/model, account-control prerequisites, observed usage, friction and limitations. Publish only support established by that evidence.

Complete revised capability/install coverage and the holistic P7 review; resolve and verify findings through the required workflow before phase acceptance. Pi retains its own feasibility, live acceptance, workflow and holistic gates. Quota ranking, scheduling, free-model defaults and wider provider expansion remain deferred/demand-gated.

## Future-session entry point

1. Pull the latest main and read AGENTS.md, PROJECT.md, D066/D067 and any successor decisions.
2. Use PROJECT.md to determine which work package is current; this document intentionally has no progress checkboxes.
3. If no successor scope decision has been accepted, start with step 1. Do not resume Pi feasibility merely because the older tracker paragraph named it as next.
4. Create one focused branch/PR under [GIT_WORKFLOW.md](GIT_WORKFLOW.md); keep design, experiment, production and live acceptance boundaries explicit. Required Grok review and holistic phase gates remain in force.

## Source freshness

This is a plan derived from the repository findings and the preceding planning session, not a new terms assessment. That session checked [OpenAI Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt), [OpenCode Go](https://opencode.ai/docs/console/go/), [Antigravity FAQ](https://antigravity.google/docs/faq/) and [Claude legal/authentication policy](https://code.claude.com/docs/en/legal-and-compliance). Re-read applicable official sources at each consuming integration/version gate; account entitlement, limits and installed-client compatibility remain evidence requirements.
