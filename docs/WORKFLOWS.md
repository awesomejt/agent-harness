# Workflow and state contract

Status: behavioral requirements for Phases 5–6. P5.1 fixes the sequence commands, inputs, failure policy, state and resume ([D044](../DECISIONS.md#2026-11-03--d044-sequence-inputs-fresh-context-steps-stop-on-failure-and-explicit-resume)); P5.2 and P5.3 implement them. The Ralph completion protocol remains open until Phase 6. Single-run semantics live in [EXECUTION.md](EXECUTION.md).

Workflow coordinators call the same Rust application execution service described in [DESIGN.md](DESIGN.md); they cannot call providers directly or bypass capability/policy validation. They enter after core MVP; durable workflow state is not needed for the first usable single run.

## Sequence inputs and context

General requirements: resolve the ordered input list before launching and keep content identities, so changed prompts cannot silently resume as the same step. Sharing context must not imply cross-provider session portability. Revalidate route/agent restrictions at each step and attempt. Prompt metadata cannot override an explicit invocation-level route restriction.

Selected for Phase 5 (D044):

```bash
ah sequence run prompts/ --mode local-only --permissions trusted --verify test
ah sequence run prompts/ --preview
ah sequence show                       # runs for this project
ah sequence show s20261103T140000Z-1a2b3c4d
ah sequence resume s20261103T140000Z-1a2b3c4d --retry --permissions trusted --verify test
```

- **Options:** the `single` coding options plus `--preview` for `run`. Prompt sources reject; `resume` takes project, config and folder from the record. `--output jsonl` rejects for sequence commands in Phase 5.
- **Snapshot:** DIR is read once, non-recursively, before any key lookup, runtime, network, lock or state write. Names starting with `.` are ignored. Every other entry must be a regular file named `N-slug.md` (`N` 1–6 digits; slug `[A-Za-z0-9][A-Za-z0-9._-]*`; at most 128 bytes); anything else, including symlinks and directories, exits 2. Order is the numeric value of `N`; equal values exit 2. 1–256 steps, at most 16 MiB in all; an empty folder exits 2. Each file follows the single-run prompt rules. Steps run from the in-memory snapshot, so an agent's edits to later prompt files do not change the running sequence. Step identity is the file name plus the SHA-256 of its bytes.
- **Metadata:** optional frontmatter opened by a first line of exactly `---`, at most 16 KiB, strict YAML as for agents. Only `agent` and `verify` exist; unknown or duplicate keys exit 2.
  - `agent: NAME` selects `agents/NAME.md` for the step. With `--agent`, a different name exits 2.
  - `verify: NAME` substitutes another declared check for the step. It requires `--verify`, which in a sequence gates every step and names the default check. Metadata cannot disable the gate.
  - Mode, model, permissions, timeout, sync and commands cannot be set by metadata. Every step's metadata, agent and check is resolved and pinned before step 1 launches.
- **Context:** every step is a fresh single run with its own private runtime, session, grants and preflight, through the same route policy, managed sync and local-first fallback. Only the project filesystem and the step's own prompt carry over. `--timeout-secs` bounds each step attempt; there is no whole-sequence deadline.
- **Failure:** strictly linear. A step completes only on agent success and, if gated, a `passed` check. Anything else stops the sequence and leaves later steps `pending`; there is no continue-on-failure option. A signal between steps stops before the next launch (exit 3). The sequence exit is the stopping step's exit, or 0 when all steps complete.

## Durable records and resume

General requirements: record workflow, project, ordered-step, input/config/agent, attempt, route/model and verification identities and terminal status. Retain only what recovery needs. Distinguish pending, active, succeeded, failed, cancelled and uncertain attempts. A crash while active does not mean failure without effects. Resume preserves prior results; retry creates a new attempt with a recorded reason. Inspection works without a model. Never delete or rewrite failure evidence. No exactly-once side-effect guarantee or automatic project rollback is promised.

Selected for Phase 5 (D044):

- **Location:** `$XDG_STATE_HOME/agent-harness/` if that is absolute, else `$HOME/.local/state/agent-harness/` (only this fallback needs an absolute `HOME`). The root must lie outside the project. Records are `sequences/RUN_ID.json`; locks are `locks/PROJECT_KEY.lock` (SHA-256 of the canonical project path). Directories are 0700, files 0600, and symlinked components exit 2. `RUN_ID` is `sYYYYMMDDTHHMMSSZ-` plus 8 random hex characters and is checked before any path is formed.
- **Content (`v: 1`):** run identity, timestamps, canonical project/folder/config paths, run status, and ordered steps with name, hash, effective agent and check, and status. Each step attempt keeps its number, reason (`initial`, `resume`, `retry`, `accept`), timestamps, input and agent-definition hashes, check identity (name, pinned program, argv hash), route, model, fallback target, permissions, timeout, agent outcome, exit, D043 verification fields and the D039 per-backend summary. No prompt text, response, check output, argv text, environment names or keys are stored. Limits are 32 attempts per step and 4 MiB per record.
- **Atomicity:** each write is temp-file, fsync, rename, directory fsync (as D025). The record is written before step 1, an attempt is marked `active` before its runtime launches, and its result is written before the next step. A failed write before a launch exits 1 with nothing launched; after an attempt it exits 4. An `active` attempt whose lock is free is `interrupted` and treated as uncertain. The submission boundary is not persisted.
- **Concurrency:** `run` and `resume` hold a nonblocking project lock for their whole duration; contention exits 2 before launch. Single runs do not take it, so a concurrent single run in the same project is unsupported. `show` takes no lock.
- **Resume:** `run` never resumes implicitly; it starts at step 1 and lists unfinished runs for the project. `resume` re-reads the folder. The completed (`succeeded` or `accepted`) steps must still lead, with the same names and hashes in order, or it exits 2. Later steps are re-snapshotted, so a failed prompt can be edited and steps added or removed after the resume point. Route options resolve afresh. Each attempt records its own identities, and human output reports what changed from the step's previous attempt. The first incomplete step decides the next action:
  - Its last attempt never submitted a prompt (`prompt_submitted` false on every backend attempt, including a local-first fallback): resume retries it.
  - Otherwise (submitted, uncertain, interrupted or a gate that did not pass): resume exits 2 unless the caller passes exactly one of `--retry` (new agent attempt) or `--accept` (no agent turn; a gated step reruns its check and completes as `accepted` only if it passes; an ungated step is recorded `accepted` and never labeled verified).
  - `--accept` gating: a step whose last attempt had a check stays gated, needs `--verify` and the same check name (else exit 2), and re-pins that check from current config, reporting a changed identity. An `accept` attempt is always appended; if its check does not pass, the step takes that result, the run stays stopped and the exit follows D043.
  - No remaining steps: exit 0 without launching.
- **Compatibility and retention:** unknown fields, unparsable files or a `v` other than 1 exit 2 without rewriting. A schema change bumps `v` and decides its migration then. Records are kept until the user deletes them, which is safe while no sequence holds the project lock; there is no pruning command.

## Verification gates

P5.5 fixes the gate ([D043](../DECISIONS.md#2026-11-03--d043-trusted-verification-gates-for-single-runs-scheduled-before-sequence-decisions)); [EXECUTION](EXECUTION.md#p55-verification-gates-d043) owns its outcomes and exits.

- **Trust:** only harness-config `checks` define commands (argv, no shell). The invocation authorizes one by name with `--verify NAME`. Prompts, agent definitions, model output and prompt metadata cannot define a command. Sequence metadata may reference a declared name only under an invocation `--verify` (D044). A program found inside the project, or reached through an in-project symlink, is untrusted and rejects before launch.
- **Identity and execution:** the program is pinned before launch and run in the canonical project directory, in its own process group, with closed stdin, scrubbed route keys and its own timeout. Records keep the check name, status, exit code/signal, timeout, duration and cleanup. Output is not captured or persisted; sequence records keep the status fields only (D044).
- **Outcomes:** agent outcome and verification status are recorded separately. A check runs only after backend success; without a check, a task is never labeled verified.
- **Stop/repair:** the harness never repairs, retries or re-prompts after a failed gate, and never executes model-suggested commands. In sequences, a step whose gate is not `passed` stops dependent steps; Phase 5 offers no continue-on-failure option (D044). Bounded repair iterations belong to Ralph (P6.1).

## Ralph loop

Start each iteration with fresh agent context while reusing filesystem progress and explicit task state. Phase 6 selects the completion signal, how it is verified, and how stale/false signals are rejected. A model assertion, DONE file, or clean exit alone cannot bypass a configured verification gate.

Enforce iteration and wall-time bounds, cancellation and a terminal non-completion outcome. Report usage when supplied; do not claim a hard cost bound without timely trusted usage and a defined enforcement mechanism. Reset/retry behavior and backoff must not become an unbounded loop.

## Deferred candidates

Parameterized recipes/templates, native session continuation/fork, user-defined lifecycle hooks, and richer history/export are candidates listed in [FEATURE_REVIEW.md](FEATURE_REVIEW.md). A general DAG scheduler, autonomous parallel teams and automatic Git worktrees remain outside the current roadmap. Reusable prompt folders and named agents are sufficient before usage proves a larger abstraction necessary.
