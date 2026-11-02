# Holistic phase review and progression gate

Every phase, including Phase 0, has an explicit phase-review task. A phase review examines the integrated phase as a whole; it is distinct from individual PR reviews, test runs or a live-use demonstration. PROJECT.md owns status; the final review card in each tasks/ phase file owns the gate.

## Scope and evidence

Start after all mandatory phase deliverables and acceptance evidence are ready. Record the accepted entry baseline, reviewed head/commit range and all phase PRs; identify any existing implementation outside that range needed to assess integration. Review the accumulated behavior rather than only the last diff.

Cover requirements and MVP boundaries, design/Rust ownership and dependency direction, mode/permission/fallback invariants, integration/regressions, test quality and actual live evidence where required, project/config/state integrity, supported platform/version claims, installation/diagnostics and document/task consistency. Phase 0 reviews these as planning contracts, without claiming code or live compatibility exists.

Use [the report template](../tasks/PHASE_REVIEW_TEMPLATE.md). Store revision 1 as docs/reviews/phase-NN.md; reopened revisions use docs/reviews/phase-NN-r2.md, then -r3.md and so on (for example phase-09-r2.md). Accepted reports are historical records; create a new revision rather than overwrite their accepted outcome. Record task/goal/feature/acceptance coverage and evidence locations. Do not copy credentials or private transcripts into the report.

## Findings and remediation

Use this phase-review severity scale:

| Severity | Meaning |
|---|---|
| Critical | Immediate serious security/data-loss risk or a fundamental safety invariant cannot be enforced. |
| High | A required phase acceptance condition or cross-component policy is materially broken; the phase baseline is unsafe/unusable for its intended consumer. |
| Medium | A substantive correctness, coverage, procedure or contract gap requiring correction, without demonstrated Critical/High impact. |
| Low | A localized wording, traceability or consistency defect with limited impact. |

All severities must be resolved before phase pass. Critical/High findings also trigger the Git workflow's fix/re-review and human-handoff rules. Classify incoming PR findings by impact, not label alone: a Grok Blocker is at least High, a Concern is provisionally Medium but must be escalated if its impact meets High/Critical, and a Nit is provisionally Low unless its actual impact is greater. Preserve the original label with the mapped severity/rationale in the report.

For each finding record an ID, severity, affected requirement/component, concrete issue, corrective task/change/PR and verification evidence. Address every finding before pass, including minor inconsistencies: fix behavior/docs/tests or correct an unsupported claim and verify the resulting scoped contract. Do not silently waive a defect because it is low severity.

New feature ideas outside the agreed scope can be classified as recommendations and recorded in the candidate backlog with rationale; they are not unresolved defects or automatic implementation authorization. If remediation changes scope or a decision, update DECISIONS.md and affected contracts/dependencies. If a required condition cannot be met, record the blocker and keep the review open rather than marking the phase complete.

Verify each correction with appropriate checks and, where needed, repeat the affected integrated/live scenario. Reassess the combined phase after corrections so a fix does not introduce a conflicting behavior. The primary agent/developer remains accountable; an additional reviewer can help where authorized, but this procedure does not require spawning a team.

## Pass criteria and progression

A pass requires complete mandatory task/evidence coverage, no unresolved findings, verified fixes, an internally consistent report/docs/status record, and completed required PR review/merge. Proposed completion checkmarks in an open PR become effective only on merge. Link the accepted report and PR from PROJECT.md; only then check the phase-review task and permit dependent phases to consume that baseline.

The gate is part of task dependencies, not merely a checklist note. Existing evidence-preparation tasks do not close phases by themselves. Phase branches remain possible after their common prerequisite review: after the core MVP review, sequences, native adapters and initial Pi work may be selected independently. Their own downstream work still waits for the corresponding phase review.

Phase 7's full portfolio review now precedes Phase 9 native-quota work; this deliberately supersedes the earlier first-completed-adapter shortcut. Phase 5 review precedes scheduling, and Phase 6 review precedes Pi workflow-parity work. Independent branches do not bypass reviews by using a higher phase number.

Phase 9 is reviewed against explicitly selected increments. Pass/release applies only to that snapshot; unselected work remains deferred. Selecting another increment reopens the review, requires a new revision and prevents consuming the new baseline until findings are closed. Initial Pi single-run support may be used before full Phase 8 parity exists, but the complete Phase 8 milestone is not accepted until its holistic review passes.

## Reopening an accepted review

Keep the same phase-review task ID. Before starting newly selected or materially changed phase scope, change its PROJECT.md checkbox from checked to unchecked and record the new active revision/scope plus a link to the previously accepted report in PROJECT.md's current-work/evidence notes. Do not allocate a suffixed task ID or erase prior acceptance. Use the concrete revision filenames above and preserve accepted reports unchanged.

The unchecked review blocks new dependent work against that phase until the new revision passes and merges. Previously completed consumers retain their evidence for the old accepted snapshot; assess whether the changed scope invalidates any of it and record corrective/revalidation tasks rather than silently assuming continued validity. Ongoing consumers must not advance using the changed baseline before the reopened review passes. On acceptance, link the new report and merged PR, retain the previous report link, and recheck the same task. This applies to P9.5 and any other phase review reopened by material changes.

## Relationship to Git review

Every review/fix/report change follows docs/GIT_WORKFLOW.md: feature branch, PR, Grok review, findings handling and merge/cleanup. The maximum of three Grok reviews is per PR, not a reason to skip the phase review or erase findings. After that PR limit, unresolved critical/high findings require the existing human handoff; the phase remains open. A holistic review report must state its scope and findings even if all individual PR reviews were clean.
