# P3.1 — Failure and recovery policy

Date: 2026-11-02. The Phase 2 review passed on PR #24 merge. Completion is effective on this task PR merge. [D031](../../DECISIONS.md#2026-11-02--d031-conservative-failure-and-recovery-policy) and the [decision table](../EXECUTION.md#failure-and-fallback) define the contract.

The table distinguishes verified pre-submission availability failures from invalid input, authentication, cancellation, unsupported constraints and uncertain work. The decision function is independent of the current execution path. Its tests cover each eligible and ineligible classification, both disallowed modes, attempted submission, unconfirmed cleanup, cancellation/deadline, missing target or constraint validation, and exhausted fallback budget. No automatic retry or native launch is added. Generic ACP provider errors remain unclassified, so P3.3 must prove adapter-specific evidence before any fallback can use them.

Validation: `cargo fmt --check`, `cargo test --locked`, and `cargo clippy --all-targets --locked -- -D warnings`. These are policy fixtures, not live evidence of native routing or fallback. P3.2 and P3.3 own those implementations; P3.5 owns live use, and P3.6 gates Phase 3 acceptance.

Grok's first review of [PR #25](https://github.com/awesomejt/agent-harness/pull/25) reported no blockers, one concern and two nits. The submission field now uses explicit attempted/not-attempted/unknown evidence, avoiding both a confusing double negative and an unsafe implicit default; unknown stops. Evidence derives `Debug`/`Clone`, and the decision is marked `must_use`. The workflow does not require re-review for these findings.
