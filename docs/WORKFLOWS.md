# Workflow and state contract

Status: behavioral requirements for Phases 5–6; storage format, command names, ordering rules, and completion protocol are intentionally not frozen. Single-run semantics live in [EXECUTION.md](EXECUTION.md).

Workflow coordinators call the same Rust application execution service described in [DESIGN.md](DESIGN.md); they cannot call providers directly or bypass capability/policy validation. They enter after core MVP; durable workflow state is not needed for the first usable single run.

## Sequence inputs and context

Choose deterministic filename ordering, supported file types, hidden-file behavior, empty-folder behavior, and prompt metadata precedence in Phase 5. Resolve the ordered input list before launching; retain content hashes or equivalent identities so changed prompts cannot silently resume as the same step.

Choose fresh versus shared runtime context explicitly. Sharing context must not imply cross-provider session portability. Revalidate route/agent restrictions at each step and attempt. Prompt metadata cannot override an explicit invocation-level route restriction.

## Durable records and resume

Record workflow ID, schema version, project identity, ordered steps/iterations, input/config/agent identities, attempt IDs, timestamps, selected routes/models, verification outcomes and terminal status. Retain only the context needed for recovery; secrets and full transcripts are not default state. Phase 5 fixes location, atomicity, file permissions, retention, and schema migration rules before use.

Distinguish pending, active, succeeded, failed, cancelled and uncertain attempts conceptually. A process crash while active does not mean failure without effects. On restart, reconcile durable state with available evidence and require an explicit recovery choice for uncertain work. Resume must detect changed inputs/configuration and competing runs against the same state; choose locking/conflict behavior before implementation.

Resume preserves prior completed results; retry creates a new attempt with a recorded reason. Read-only inspection must work without invoking a model. Do not delete or rewrite prior failure evidence to make a resumed run look uninterrupted. No exactly-once side-effect guarantee or automatic project rollback is promised.

## Verification gates

P5.5 fixes the gate ([D043](../DECISIONS.md#2026-11-03--d043-trusted-verification-gates-for-single-runs-scheduled-before-sequence-decisions)); [EXECUTION](EXECUTION.md#p55-verification-gates-d043) owns its outcomes and exits.

- **Trust:** only harness-config `checks` define commands (argv, no shell). The invocation authorizes one by name with `--verify NAME`. Prompts, agent definitions, model output and prompt metadata cannot define a command. P5.1 decides whether sequence metadata may reference a declared name. A program found inside the project, or reached through an in-project symlink, is untrusted and rejects before launch.
- **Identity and execution:** the program is pinned before launch and run in the canonical project directory, in its own process group, with closed stdin, scrubbed route keys and its own timeout. Records keep the check name, status, exit code/signal, timeout, duration and cleanup. Output is not yet captured; P5.3 decides a durable output reference.
- **Outcomes:** agent outcome and verification status are recorded separately. A check runs only after backend success; without a check, a task is never labeled verified.
- **Stop/repair:** the harness never repairs, retries or re-prompts after a failed gate, and never executes model-suggested commands. In sequences, a step whose gate is not `passed` stops dependent steps; any continue-on-failure option must be an explicit P5.1 choice. Bounded repair iterations belong to Ralph (P6.1).

## Ralph loop

Start each iteration with fresh agent context while reusing filesystem progress and explicit task state. Phase 6 selects the completion signal, how it is verified, and how stale/false signals are rejected. A model assertion, DONE file, or clean exit alone cannot bypass a configured verification gate.

Enforce iteration and wall-time bounds, cancellation and a terminal non-completion outcome. Report usage when supplied; do not claim a hard cost bound without timely trusted usage and a defined enforcement mechanism. Reset/retry behavior and backoff must not become an unbounded loop.

## Deferred candidates

Parameterized recipes/templates, native session continuation/fork, user-defined lifecycle hooks, and richer history/export are candidates listed in [FEATURE_REVIEW.md](FEATURE_REVIEW.md). A general DAG scheduler, autonomous parallel teams and automatic Git worktrees remain outside the current roadmap. Reusable prompt folders and named agents are sufficient before usage proves a larger abstraction necessary.
