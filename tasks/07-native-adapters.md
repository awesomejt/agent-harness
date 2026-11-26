# Phase 7 — Local and subscription portfolio

Status checkboxes live only in [PROJECT.md](../PROJECT.md). These cards specify dependencies and evidence; their order is the recommended work order, not a second status board. See [task conventions](README.md).

D103 replaces D068's portfolio. The mandatory portfolio is existing OpenCode/LiteLLM, accepted Claude, the OpenCode Go native target, and an **operator-configured ordered fallback chain** for `local-first` (recommended local → Go → Claude, with opt-in Zen last). ChatGPT-plan P7.9/P7.11 are deferred outside mandatory closure with their evidence and gates kept, as are P7.3–P7.5. One focused task/PR is active at a time. Recommended order: P7.10 → P7.12 → P7.14 → P7.13 → P7.6 → P7.7; IDs are stable, not numeric execution order.

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
## P7.9 — OpenCode ChatGPT-plan feasibility (deferred outside mandatory portfolio, D103)

- **Disposition (D103):** Deferred with all D069–D102 evidence and gates kept. Resume requires explicit reselection, then the D091 catalog-control migration to 2.3.0, then same-root authenticated D085–D088 passes.

- **Depends on:** [P7.8](07-native-adapters.md#p7-8).
- **Deliverable and boundary:** Select/version the supported integration from fresh official sources, then record a contained no-inference control plan before installed checks. Prove runtime-owned login can coexist with private configuration-source isolation, exact provider/model/helper/endpoint selection and effective permissions. The harness performs no auth-store read/copy, OAuth execution/observation, session/model call or production change. The operator personally runs the official login under D067/D077; D085–D088 diagnostics then use that retained root without inference.
- **Acceptance evidence:** Reproducible pinned documentation/source and synthetic-control evidence, supported login ownership and account-control verification plan, limitations and explicit pass/block decision. A TUI login or handshake alone is insufficient. If the integration requires evidence outside this boundary, record a blocker and select a separate bounded follow-up before claiming feasibility.
- **Decision/readiness gate:** A failed gate blocks P7.11; Pi is a separately selected alternative requiring a new decision, not an automatic replacement. D067 spend/use boundaries apply.
- **Contract:** [Action plan step 2](../docs/SUBSCRIPTION_ACTION_PLAN.md), [execution](../docs/EXECUTION.md). The [bounded assessment and continuation plan](../docs/evidence/p7-9-chatgpt-feasibility.md) records the selected candidate and remaining proof; the [contained diagnostic continuation](../docs/evidence/p7-9-contained-diagnostics.md) supplies the experimental transport and its limits; the [source/state assessment](../docs/evidence/p7-9-source-state-controls.md) records the selected interface blocker and separate resume plan (D071). The [shared source-boundary design](../docs/evidence/p7-9-source-boundary-design.md) (D073) supplies a synthetic macOS candidate and separately gated installed continuation. The [pre-launch resource matrix](../docs/evidence/p7-9-resource-observation-matrix.md) (D074) records incomplete coverage and stops installed expansion pending observer/refusal design. The [observer/refusal design](../docs/evidence/p7-9-observer-refusal-design.md) (D075) selects the list observer and static guards for a fresh-state no-auth continuation and keeps retained-state pairs blocked. The [installed observation](../docs/evidence/p7-9-installed-observer.md) (D076) passes every row for fresh unauthenticated state, with native-only MCP and ancestor discovery-name denials. The [exclusive-state decision](../docs/evidence/p7-9-exclusive-state-decision.md) (D077) selects a dedicated harness-owned root for an operator-run official login and a retained-state preflight, with paired proofs planned for the reused-root, well-known and Console rows. The [retained-state experiment](../docs/evidence/p7-9-retained-state-experiment.md) (D078) runs those proofs without authentication. It fixes the pinned 236-ID integration set, passes the reused root and refuses the seeded well-known and Console states, leaving only the operator login. The [login preflight](../docs/evidence/p7-9-login-preflight.md) (D085) records the operator-gated login-mode increment. The [method/endpoint/helper proof](../docs/evidence/p7-9-method-endpoint-helper.md) (D086) records redacted route checks on a retained login root. The [permission proof](../docs/evidence/p7-9-permission-proof.md) (D087) records deny/trusted `debug agents` checks on a retained login root. The [credits-off assertion](../docs/evidence/p7-9-credits-off.md) (D088) adds the point-in-time operator account check. The [closeout assessment](../docs/evidence/p7-9-feasibility-closeout.md) (D089) maps the evidence chain to P7.9 and P7.11 gates: same-root authenticated D085–D088 passes precede any accepted feasibility closeout, while actual tool/model and live coding acceptance belongs to separately gated P7.11. D034 remains unchanged. The [post-login inventory refusal](../docs/evidence/p7-9-authenticated-inventory-refusal.md) led to the [pinned catalog investigation](../docs/evidence/p7-9-catalog-investigation.md) (D090): preserve the fixed gate and require reviewed disposable no-auth explicit-catalog/cache proof before authenticated expansion. The [D091 disposable catalog-control experiment](../docs/evidence/p7-9-catalog-control.md) keeps authenticated expansion separate. The [D092 upgrade audit](../docs/evidence/opencode-2-3-0-upgrade.md) moves production support to 2.3.0 but leaves these experimental pins unchanged: fresh source/plugin/observer/containment requalification on disposable roots precedes new catalog proof or authenticated continuation. The [D093 source qualification](../docs/evidence/p7-9-230-source-requalification.md) provides the new public-source/plugin manifest and next observer/containment contract without migrating existing helper pins or claiming installed qualification. The [D094 disposable observer](../docs/evidence/p7-9-230-disposable-observer.md) selects a separately pinned no-auth helper and setup-review-before-installed-execution boundary. The [D095 warning assessment/diagnostic plan](../docs/evidence/p7-9-230-warning-assessment.md) requires an offline-tested classifier and helper/setup review before the bounded disposable diagnostic pair; the D094 warning refusal and later gates remain unchanged. The [D096 diagnostic helper](../docs/evidence/p7-9-230-warning-diagnostic.md) implements that separately reviewed setup and bounded attempt, preserving every refusal and later gate. The [D097 parent-watch assessment](../docs/evidence/p7-9-230-parent-watch-assessment.md) selects a separately reviewed synthetic primitive pair before any remedy/OpenCode continuation; global watcher disable and warning exceptions are rejected. The [D098 primitive helper](../docs/evidence/p7-9-230-parent-watch-primitive.md) implements that separate setup/result-reviewed pair without starting OpenCode services; its control refused on created state. The [D099 created-state inventory](../docs/evidence/p7-9-230-state-inventory.md) keeps that refusal and adds a metadata-only inventory for one further reviewed attempt, which isolated a Bun transpiler-cache write. The [D100 Bun cache control](../docs/evidence/p7-9-230-bun-cache-control.md) disables that cache for one setup-reviewed rerun with the state gate unchanged; its denied leg found the parent watch incompatible (synchronous EPERM). The [D101 case 3 retirement](../docs/evidence/p7-9-230-retire-case-3.md) retires that unpassable listing-denied row and leaves cases 4–6 to a separately reviewed continuation. The [D102 matrix rerun](../docs/evidence/p7-9-230-cases-4-6.md) runs D094 cases 1, 2, 4, 5 and 6 once through the unchanged helper after setup review. Current status remains in PROJECT.md.

<a id="p7-10"></a>
## P7.10 — OpenCode Go feasibility on the production ACP path

- **Depends on:** [P7.8](07-native-adapters.md#p7-8); D103.
- **Deliverable and boundary:** Re-scoped by D103 from the experimental CLI/server chain to the accepted production ACP native API-key path (D032/D092). Pin OpenCode 2.3.0 source, then establish for the dedicated `opencode-go` provider:
  - provider registration and the catalog Go endpoint, distinct from `opencode`/Zen;
  - the settings-only provider with the private `AH_RUNTIME_API_KEY`, and no `baseURL` override;
  - exact primary/helper model pinning;
  - that `validate_sources`/`validate_agents` stay fail-closed;
  - honest client identification;
  - how a `GoUsageLimitError` (`provider.go-limit`) reaches the ACP client.

  Fixture coverage uses the fake OpenCode runtime. One bounded live no-tool prompt follows only after setup review and the operator's dated Go account attestation.
- **Acceptance evidence:** Pinned source findings, fixture tests, the observed live effective provider/model, account-control attestation and its limitations. No deliberate allowance exhaustion. Record blockers rather than widening a gate.
- **Decision/readiness gate:** A failed gate blocks P7.12/P7.14 and requires a new scope decision. LiteLLM placement and Go through Pi need separate decisions (Pi: D060 revisit).
- **Contract:** [Configuration](../docs/CONFIGURATION.md), [execution](../docs/EXECUTION.md). Historical [bounded Go source assessment](../docs/evidence/p7-10-go-feasibility.md) (D072) covers the server path; its provider, header, helper and account findings carry over. Current status remains in PROJECT.md.

<a id="p7-11"></a>
## P7.11 — Explicit OpenCode ChatGPT-plan route (deferred outside mandatory portfolio, D103)

- **Depends on:** [P7.9](07-native-adapters.md#p7-9) accepted feasibility.
- **Deliverable and boundary:** Finalize explicit provider/auth/schema and compatibility contracts, then implement the route in focused increments. Preserve runtime-owned authentication and existing supported behavior. Separately gate bounded live acceptance after controls pass; this scope card alone does not authorize a model turn.
- **Acceptance evidence:** Fixtures and live coding plus constrained review prove deny/trusted restrictions, source/model/helper isolation, sanitized preview/results, no metered substitution, cancellation/cleanup and explicit account post-limit-credit checks with limitations. Document tested versions and unsupported features.
- **Decision/readiness gate:** D067 own-account/operator-started and included-allowance rules; no auth-store handling. D034 remains unchanged. Workflow support awaits P7.13.
- **Contract:** [Configuration](../docs/CONFIGURATION.md), [execution](../docs/EXECUTION.md), [frameworks](../docs/FRAMEWORKS.md); update before implementation consumption.

<a id="p7-12"></a>
## P7.12 — OpenCode Go native target and local-first fallback

- **Depends on:** [P7.10](07-native-adapters.md#p7-10) accepted feasibility.
- **Deliverable and boundary:** Finalize the schema first (for example `native.target: "opencode-go"` with `model` and `api_key_env`), then implement Go as a native target. It serves `cloud-only` and is the configured native fallback of `local-first` under unchanged D034: a pre-submission reachability failure triggers it. Preserve exact client identification and session attribution. Bounded live acceptance is separately gated after the controls pass.
- **Acceptance evidence:** Fixtures plus live coding and constrained review prove:
  - the exact Go provider/model, with no Zen or other substitution;
  - deny/trusted restrictions and source/helper isolation;
  - sanitized preview/output and bounded cancellation/cleanup;
  - local-first fallback from an unreachable proxy to Go;
  - a limit refusal that stops (P7.14 owns chain transitions);
  - the dated Extra Usage-off attestation.

  Record tested versions and account-control limitations. Do not deliberately exhaust an allowance. The 2026-11-25 live attempt stopped uncertain after submission. [D107](../DECISIONS.md#2026-11-25--d107-classify-post-submission-acp-errors) closed post-submission error labels are implemented offline; they do not replace the acceptance evidence above or authorize a live run by themselves. The 2026-11-26 attested continuation ([result](../docs/evidence/p7-12-go-live-result.md)) stopped with D107 `acp_error=auth_required` / `acp_data=unclassified` and does not pass live acceptance.
- **Decision/readiness gate:** D067 spend/use rules apply. No LiteLLM placement. Workflow acceptance awaits P7.13.
- **Contract:** [Configuration](../docs/CONFIGURATION.md), [execution](../docs/EXECUTION.md), [frameworks](../docs/FRAMEWORKS.md), [operations](../docs/OPERATIONS.md); update before implementation consumption.

<a id="p7-14"></a>
## P7.14 — Configurable ordered fallback chain

- **Depends on:** [P7.12](07-native-adapters.md#p7-12).
- **Deliverable and boundary:** Select F27's ordered chain for `local-first` and record the D034 replacement for configured chains, with the finalized schema, before implementation. The operator lists the steps in order, each naming one accepted native target (`opencode-go`, `claude` or `opencode`/Zen) and its exact model. Without a chain, the single `native` fallback is unchanged. The sample config uses local → Go → Claude; a Zen step (metered, or a free Zen model) appears only when listed. The first transition keeps D034's unreachable-proxy trigger. A later transition needs all of:
  - a classified allowance or rate-limit failure from the current step's target, using a classifier proven for that target (Go `provider.go-limit`; Claude: a `rate_limit_event` whose status is rejected, followed by an error `result`; an allowed or warning status never counts);
  - affirmative harness-side evidence that no work ran, such as no permission grant issued and no project change, with cleanup confirmed;
  - one linked attempt with fresh runtime state and grants, the same prompt and role constraints and the shared deadline.

  Cancellation, deadline, authentication, unsupported or uncertain-effect failures never transition. Steps advance forward only: no cycle and no uncertain replay. Validation rejects unaccepted targets and any step that follows a target without a proven classifier. Exhaustion after a permission grant or project change stops for explicit recovery, so the chain covers exhaustion only before the run's first permission grant or project change; document that in setup docs. Decide whether a recorded exhaustion skips a step for later steps/iterations of the same workflow. Cloud-only chains stay a candidate.
- **Acceptance evidence:** Fixture coverage of eligible and ineligible failures for each classified target, of reordered and shortened chains, and of the no-chain default, with the fake runtime. Progress/result/record fields name every attempt, its step, the cause and usage, or record it as unknown. Preview shows the resolved chain without network access. Live evidence of a real limit only from natural exhaustion during ordinary use; until then, record that limitation explicitly.
- **Decision/readiness gate:** [Action plan step 5](../docs/SUBSCRIPTION_ACTION_PLAN.md) applies in full. Metered spend is the operator's configured choice, with no hard-cap claim. Extra Usage stays off. No new CLI flag unless this task's decision selects one.
- **Contract:** [Execution](../docs/EXECUTION.md), [configuration](../docs/CONFIGURATION.md), [workflows](../docs/WORKFLOWS.md), [operations](../docs/OPERATIONS.md).

<a id="p7-13"></a>
## P7.13 — Selected portfolio integrated acceptance

- **Depends on:** [P7.2](07-native-adapters.md#p7-2), [P7.12](07-native-adapters.md#p7-12), [P7.14](07-native-adapters.md#p7-14), accepted [P5.6](05-sequences.md#p5-6) and [P6.5](06-ralph.md#p6-5).
- **Deliverable and boundary:** Exercise existing OpenCode/LiteLLM, Claude, the Go native target and the recommended configured chain (local → Go → Claude, plus an opt-in Zen step) through single/sequence/Ralph workflows. Reuse existing policy; add no fallback or locality behavior beyond P7.12/P7.14.
- **Acceptance evidence:** Fixture/live evidence for coding/constrained roles, explicit route/model choices, interruption/recovery, dirty-project preservation, bounded cancellation/cleanup and sanitized preview/output. Verify classified limit failures advance only to the next configured step, that unlisted targets are never substituted, and that unclassified or post-work failures stop without uncertain replay; distinguish synthetic failures from observed provider behavior. Record versions, account controls, usage or unknown, friction and limitations.
- **Decision/readiness gate:** D034 as amended by P7.14 only. F27's remaining parts (cloud-only chains, the fallback-model known-problem record, a reachable-proxy trigger) and all of F28 remain candidates outside this milestone. P7.6 prepares the audit and P7.7 still gates phase exit; failed mandatory routes require a new scope decision.
- **Contract:** [Workflows](../docs/WORKFLOWS.md), [testing](../docs/TESTING.md), [implementation](../docs/IMPLEMENTATION.md).

<a id="p7-6"></a>
## P7.6 — Native adapter portfolio acceptance audit

- **Depends on:** [P7.13](07-native-adapters.md#p7-13) (includes P7.2/P7.12/P7.14 and accepted workflow gates).
- **Deliverable and boundary:** Audit aggregate capability/version/install coverage across D103’s selected local/Claude/Go portfolio and configurable chain. Incremental per-adapter docs/tests remain mandatory inside each adapter task; this task is only the final portfolio audit/evidence preparation; P7.7 closes the phase.
- **Acceptance evidence:** Every selected route has linked fixture/live evidence and setup/capability docs; paused/blocked/deferred targets (including ChatGPT-plan P7.9/P7.11) retain explicit dispositions and resume conditions. Include existing local and Claude regressions, account-control limitations and tested installation/version coverage.
- **Decision/readiness gate:** Partial milestones are usable independently. D068 replaced the four-target closure requirement and D103 the ChatGPT/Go portfolio; no mandatory selected route may be waived without a new decision. P7.3–P7.5 stay unchecked outside closure. P7.7 still reviews their accumulated experiments and dispositions.
- **Contract:** [docs/IMPLEMENTATION.md](../docs/IMPLEMENTATION.md); status/evidence summary in [PROJECT.md](../PROJECT.md).

<a id="p7-7"></a>
## P7.7 — Phase review: holistic findings and remediation

- **Depends on:** [P7.6](07-native-adapters.md#p7-6)
- **Deliverable and boundary:** Review all Phase 7 deliverables together, accumulated changes since its accepted entry baseline, acceptance/live evidence, Rust architecture/contracts, tests, regressions and operational limits. The preceding task prepares evidence; it does not close the phase.
- **Acceptance evidence:** A phase-numbered report under docs/reviews/ records the reviewed commit/PR scope, goal/feature/acceptance coverage, test/live evidence, findings, remediation and verification. A pass requires no unresolved finding; review/fix PRs follow the Git workflow.
- **Decision/readiness gate:** Dependent phase work remains gated until the whole-phase review passes, all findings are resolved/verified, and required review/fix PRs merge. Do not substitute a set of individual PR approvals.
- **Contract:** [Phase review procedure](../docs/PHASE_REVIEW.md) and [report template](PHASE_REVIEW_TEMPLATE.md); canonical status/evidence in [PROJECT.md](../PROJECT.md).
