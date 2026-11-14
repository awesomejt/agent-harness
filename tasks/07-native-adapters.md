# Phase 7 — Local and subscription portfolio

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

D068 selects existing OpenCode/LiteLLM, accepted Claude, and separately gated ChatGPT-plan and dedicated Go routes through OpenCode. P7.3–P7.5 retain their historical cards/evidence and resume gates outside mandatory closure. One focused task/PR is active at a time. Recommended order: P7.8 → P7.9 → P7.10 → P7.11/P7.12 (delivery order from evidence) → P7.13 → P7.6 → P7.7; IDs are stable, not numeric execution order.

<a id="p7-1"></a>
## P7.1 — Select next native adapter

- **Depends on:** [P4.9](04-core-mvp.md#p4-9)
- **Deliverable and boundary:** Choose a native target from real-use needs under the current portfolio decision (D068) and verify supported authentication/integration terms, interface and version baseline.
- **Acceptance evidence:** Decision entry names the selected target and capability/permission/model/event questions. Other adapters stay deferred until explicitly selected.
- **Decision/readiness gate:** Only one new adapter active at a time by default; no fixed provider ordering implied by task IDs.
- **Contract:** [docs/FRAMEWORKS.md](../docs/FRAMEWORKS.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-2"></a>
## P7.2 — Claude native adapter

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Claude, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Activation gate: Claude is the currently selected target from P7.1 or a later recorded selection. Reuse official authentication; no token scraping or prohibited proxying. Terms: [D067](../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage) accepts plan-login use for operator-started runs only, with a re-check at each Claude Code pin change and by 2027-02-08.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-3"></a>
## P7.3 — Codex native adapter (deferred from mandatory portfolio)

P7.3 is delivered in focused increments. First record target/interface selection and the installed schema/handshake baseline. Then prove effective tool restrictions and isolation while retaining official login before implementing production launch or submitting any model turn. Launch/events, trusted permissions, named roles/model/effort, workflows, fallback and live acceptance may each need separate PRs. Selection alone does not satisfy this card's acceptance evidence; [PROJECT.md](../PROJECT.md) owns current selection and status.

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Codex, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Reactivation gate under D068: explicitly select Codex, satisfy its original control/terms evidence and deliver a separately reviewed increment; historical P7.1 selection alone does not reactivate it. Reuse official authentication; no token scraping or prohibited proxying. Deprioritized by [D067](../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage): OpenCode or Pi on the ChatGPT plan is the preferred OpenAI path; this adapter stays paused under D055 and is not retired.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-4"></a>
## P7.4 — Grok native adapter (deferred from mandatory portfolio)

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Grok, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Reactivation gate under D068: explicitly select Grok, satisfy its original control/terms evidence and deliver a separately reviewed increment; historical P7.1 selection alone does not reactivate it. Reuse official authentication; no token scraping or prohibited proxying. [D067](../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage) keeps SuperGrok use first-party while xAI has no statement on third-party ACP clients; the adapter stays paused under D058.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-5"></a>
## P7.5 — Antigravity native adapter (blocked outside mandatory portfolio)

D061 replaces the former Gemini CLI target at the same stable task ID. First prove installed `agy acp` permission/isolation controls using the [readiness assessment](../docs/evidence/p7-1-antigravity-readiness.md); selection and help discovery do not satisfy adapter acceptance. Historical Gemini evidence remains historical. The [contained startup/initialize increment](../docs/evidence/p7-5-antigravity-feasibility.md) (D062) establishes transport discovery only; the [supported-control assessment](../docs/evidence/p7-5-antigravity-control-assessment.md) (D063) pauses production/inference pending specific installed deny/source/login proof.

**Blocked on terms ([D066](../DECISIONS.md#2026-11-08--d066-block-antigravity-on-consumer-plan-terms)).** Google's [Antigravity FAQ](https://antigravity.google/docs/faq/) says wrapping `agy` inside third-party coding agents or applications is not supported under consumer plans. The harness driving `agy acp` or `agy -p` on the operator's consumer Google AI Pro login is that case. Resume only with written confirmation from Google, or an enterprise or API-key path chosen in a new decision; D063's control gate still applies after that. No authentication, session or inference against Antigravity meanwhile. Sources: [provider terms check](../docs/evidence/p7-native-terms-check.md).

- **Depends on:** [P7.1](07-native-adapters.md#p7-1)
- **Deliverable and boundary:** For Antigravity, deliver narrow PRs for supported launch/authentication, progress/terminal mapping, model/effort, cancellation and constrained agent mapping. Include capability/setup docs as part of this adapter, not only at Phase 7 closeout.
- **Acceptance evidence:** Fixture/policy/lifecycle tests plus one live project task and enforced constrained-role evidence. Unsupported features/version/platform limits are documented before advertising support.
- **Decision/readiness gate:** Reactivation gate under D068: explicitly select Antigravity, satisfy its original control/terms evidence and deliver a separately reviewed increment; historical P7.1 selection alone does not reactivate it. Reuse official authentication; no token scraping or prohibited proxying. Blocked: D066's terms condition and D063's control gate must both be met.
- **Contract:** [docs/EXECUTION.md](../docs/EXECUTION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-8"></a>
## P7.8 — Reconcile subscription scope and dependencies

- **Depends on:** D066/D067 and the subscription action plan.
- **Deliverable and boundary:** Record the successor portfolio decision and align goals, acceptance, dependencies, feature dispositions and task cards. Preserve stable IDs and historical acceptance; no code/probe/route changes.
- **Acceptance evidence:** Consistent mandatory portfolio and deferrals, unchanged Pi and Phase 9 gates, explicit next task, documentation-link checks and required PR review/merge.
- **Decision/readiness gate:** D068 takes effect on this task's review/merge; scope selection alone does not establish runtime support.
- **Contract:** [Subscription action plan](../docs/SUBSCRIPTION_ACTION_PLAN.md), [implementation](../docs/IMPLEMENTATION.md).

<a id="p7-9"></a>
## P7.9 — OpenCode ChatGPT-plan feasibility

- **Depends on:** [P7.8](07-native-adapters.md#p7-8).
- **Deliverable and boundary:** Select/version the supported integration from fresh official sources, then record a contained no-inference control plan before installed checks. Prove runtime-owned login can coexist with private configuration-source isolation, exact provider/model/helper/endpoint selection and effective permissions. No auth-store read/copy, login/authentication/session/model call or production change in this task.
- **Acceptance evidence:** Reproducible pinned documentation/source and synthetic-control evidence, supported login ownership and account-control verification plan, limitations and explicit pass/block decision. A TUI login or handshake alone is insufficient. If the integration requires evidence outside this boundary, record a blocker and select a separate bounded follow-up before claiming feasibility.
- **Decision/readiness gate:** A failed gate blocks P7.11; Pi is a separately selected alternative requiring a new decision, not an automatic replacement. D067 spend/use boundaries apply.
- **Contract:** [Action plan step 2](../docs/SUBSCRIPTION_ACTION_PLAN.md), [execution](../docs/EXECUTION.md). The [bounded assessment and continuation plan](../docs/evidence/p7-9-chatgpt-feasibility.md) records the selected candidate and remaining proof; the [contained diagnostic continuation](../docs/evidence/p7-9-contained-diagnostics.md) supplies the experimental transport and its limits; the [source/state assessment](../docs/evidence/p7-9-source-state-controls.md) records the selected interface blocker and separate resume plan (D071). The [shared source-boundary design](../docs/evidence/p7-9-source-boundary-design.md) (D073) supplies a synthetic macOS candidate and separately gated installed continuation. The [pre-launch resource matrix](../docs/evidence/p7-9-resource-observation-matrix.md) (D074) records incomplete coverage and stops installed expansion pending observer/refusal design. The [observer/refusal design](../docs/evidence/p7-9-observer-refusal-design.md) (D075) selects the list observer and static guards for a fresh-state no-auth continuation and keeps retained-state pairs blocked. The [installed observation](../docs/evidence/p7-9-installed-observer.md) (D076) passes every row for fresh unauthenticated state, with native-only MCP and ancestor discovery-name denials. The [exclusive-state decision](../docs/evidence/p7-9-exclusive-state-decision.md) (D077) selects a dedicated harness-owned root for an operator-run official login and a retained-state preflight, with paired proofs planned for the reused-root, well-known and Console rows. The [retained-state experiment](../docs/evidence/p7-9-retained-state-experiment.md) (D078) runs those proofs without authentication. It fixes the pinned 236-ID integration set, passes the reused root and refuses the seeded well-known and Console states, leaving only the operator login. The [login preflight](../docs/evidence/p7-9-login-preflight.md) (D085) records the operator-gated login-mode increment. The [method/endpoint/helper proof](../docs/evidence/p7-9-method-endpoint-helper.md) (D086) records redacted route checks on a retained login root. Current status remains in PROJECT.md.

<a id="p7-10"></a>
## P7.10 — Dedicated OpenCode Go feasibility

- **Depends on:** [P7.8](07-native-adapters.md#p7-8); recommended after P7.9 to preserve one active task.
- **Deliverable and boundary:** Separately select/version a contained no-inference experiment from fresh official sources. Establish dedicated Go rather than metered Zen selection, supported client identification/session headers, model/endpoint/helper and permission/source isolation, and supported account Extra Usage verification. No real credential inspection, authentication/session/model calls or production changes.
- **Acceptance evidence:** Pinned capability/control evidence with synthetic inputs, exact provider distinction and account-control verification plan/limitations. No estimate-based hard-cap claim. Record blockers or a separate bounded follow-up for proof outside this task's boundary.
- **Decision/readiness gate:** A failed gate blocks P7.12. OpenCode is the selected placement; LiteLLM/Pi placement needs another decision.
- **Contract:** [Action plan step 2](../docs/SUBSCRIPTION_ACTION_PLAN.md), [configuration](../docs/CONFIGURATION.md). The [bounded Go source assessment](../docs/evidence/p7-10-go-feasibility.md) (D072) records provider/header/helper and account-control findings; D071's shared source blocker stops installed expansion. Resume with the separately evidenced shared source-control plan before synthetic Go proof; current status remains in PROJECT.md.

<a id="p7-11"></a>
## P7.11 — Explicit OpenCode ChatGPT-plan route

- **Depends on:** [P7.9](07-native-adapters.md#p7-9) accepted feasibility.
- **Deliverable and boundary:** Finalize explicit provider/auth/schema and compatibility contracts, then implement the route in focused increments. Preserve runtime-owned authentication and existing supported behavior. Separately gate bounded live acceptance after controls pass; this scope card alone does not authorize a model turn.
- **Acceptance evidence:** Fixtures and live coding plus constrained review prove deny/trusted restrictions, source/model/helper isolation, sanitized preview/results, no metered substitution, cancellation/cleanup and explicit account post-limit-credit checks with limitations. Document tested versions and unsupported features.
- **Decision/readiness gate:** D067 own-account/operator-started and included-allowance rules; no auth-store handling. D034 remains unchanged. Workflow support awaits P7.13.
- **Contract:** [Configuration](../docs/CONFIGURATION.md), [execution](../docs/EXECUTION.md), [frameworks](../docs/FRAMEWORKS.md); update before implementation consumption.

<a id="p7-12"></a>
## P7.12 — Explicit dedicated OpenCode Go route

- **Depends on:** [P7.10](07-native-adapters.md#p7-10) accepted feasibility.
- **Deliverable and boundary:** Finalize explicit dedicated-provider/auth/schema and compatibility contracts, then implement separately from ChatGPT. Preserve exact client identification and stable session headers. Separately gate bounded live acceptance after controls pass.
- **Acceptance evidence:** Live coding and constrained review plus fixtures prove exact Go provider/model, deny/trusted restrictions, source/helper isolation, sanitized output, bounded cancellation/cleanup, Extra Usage account check and limit refusal without metered Zen or other paid substitution. Record account-control limitations and tested versions; do not deliberately exhaust a large allowance.
- **Decision/readiness gate:** D067 spend/use rules apply. No LiteLLM placement or fallback expansion. Workflow support awaits P7.13.
- **Contract:** [Configuration](../docs/CONFIGURATION.md), [execution](../docs/EXECUTION.md), [frameworks](../docs/FRAMEWORKS.md); update before implementation consumption.

<a id="p7-13"></a>
## P7.13 — Selected portfolio integrated acceptance

- **Depends on:** [P7.2](07-native-adapters.md#p7-2), [P7.11](07-native-adapters.md#p7-11), [P7.12](07-native-adapters.md#p7-12), accepted [P5.6](05-sequences.md#p5-6) and [P6.5](06-ralph.md#p6-5).
- **Deliverable and boundary:** Exercise existing OpenCode/LiteLLM, Claude and the new explicit subscription routes through single/sequence/Ralph workflows. Reuse existing policy; do not add fallback or locality behavior.
- **Acceptance evidence:** Fixture/live evidence for coding/constrained roles, explicit route/model choices, interruption/recovery, dirty-project preservation, bounded cancellation/cleanup and sanitized preview/output. Verify supported limit failures stop without metered substitution or uncertain replay; distinguish synthetic failures from observed provider behavior. Record versions, account controls, usage or unknown, friction and limitations.
- **Decision/readiness gate:** D034 fallback stays unchanged. F27/F28 remain candidates outside this milestone. P7.6 prepares the audit and P7.7 still gates phase exit; failed mandatory routes require a new scope decision.
- **Contract:** [Workflows](../docs/WORKFLOWS.md), [testing](../docs/TESTING.md), [implementation](../docs/IMPLEMENTATION.md).

<a id="p7-6"></a>
## P7.6 — Native adapter portfolio acceptance audit

- **Depends on:** [P7.13](07-native-adapters.md#p7-13) (includes P7.2/P7.11/P7.12 and accepted workflow gates).
- **Deliverable and boundary:** Audit aggregate capability/version/install coverage across D068’s selected local/subscription portfolio. Incremental per-adapter docs/tests remain mandatory inside each adapter task; this task is only the final portfolio audit/evidence preparation; P7.7 closes the phase.
- **Acceptance evidence:** Every selected route has linked fixture/live evidence and setup/capability docs; paused/blocked targets retain explicit dispositions and resume conditions. Include existing local and Claude regressions, account-control limitations and tested installation/version coverage.
- **Decision/readiness gate:** Partial milestones are usable independently. D068 replaces the four-target closure requirement; no mandatory selected route may be waived without a new decision. P7.3–P7.5 stay unchecked outside closure. P7.7 still reviews their accumulated experiments and dispositions.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-7"></a>
## P7.7 — Phase review: holistic findings and remediation

- **Depends on:** [P7.6](07-native-adapters.md#p7-6)
- **Deliverable and boundary:** Review all Phase 7 deliverables together, accumulated changes since its accepted entry baseline, acceptance/live evidence, Rust architecture/contracts, tests, regressions and operational limits. The preceding task prepares evidence; it does not close the phase.
- **Acceptance evidence:** A phase-numbered report under docs/reviews/ records the reviewed commit/PR scope, goal/feature/acceptance coverage, test/live evidence, findings, remediation and verification. A pass requires no unresolved finding; review/fix PRs follow the Git workflow.
- **Decision/readiness gate:** Dependent phase work remains gated until the whole-phase review passes, all findings are resolved/verified, and required review/fix PRs merge. Do not substitute a set of individual PR approvals.
- **Contract:** [Phase review procedure](../docs/PHASE_REVIEW.md) and [report template](PHASE_REVIEW_TEMPLATE.md); canonical status/evidence in [PROJECT.md](../PROJECT.md).
