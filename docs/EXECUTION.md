# Execution contract

Status: design contract, not a published Rust API or wire schema. See [architecture](ARCHITECTURE.md), [configuration](CONFIGURATION.md), and [workflow state](WORKFLOWS.md). Phase 1 chooses transport/permission handling, Phase 2 fixes initial request/exit behavior, and Phase 4 versions machine-readable output.

## Request resolution

Resolve one project path, prompt source, operational mode, runtime, and model alias, plus an optional canonical agent once supported. Record whether each effective choice came from the invocation or configuration. Accept inline text, a file, or stdin; reject conflicting sources and empty content before launching work. D024 and [the first-slice configuration contract](CONFIGURATION.md#selected-invocation-and-preview-syntax) fix flag names, limits and defaults. A missing input must not unexpectedly launch an interactive coding session in CI.

Keep primary versus specialized role separate from route and runtime. A request to review without writes must become enforceable runtime restrictions; advisory system text is insufficient.

The proposed Rust domain model and supervisor ownership are in [DESIGN.md](DESIGN.md); lifecycle and route diagrams are in [ARCHITECTURE.md](ARCHITECTURE.md). Internal type names do not establish a public JSON schema.

## Lifecycle

Conceptual lifecycle (names are not serialized enums): resolve -> validate -> preview, or prepare managed configuration -> launch -> active -> cleanup -> terminal outcome (succeeded, failed, cancelled, uncertain). Every active attempt passes through cleanup, including successful, failed, timed-out and cancelled attempts. Validation rejection or a known spawn failure without a child can terminate before active work; ambiguous startup or cancellation during launch still requires cleanup and an outcome reflecting uncertainty. Preview ends without executing or modifying configuration. Retrying creates a new attempt linked to the original run rather than rewriting history.

A prompt acknowledgement, text chunk, clean stdout EOF, model completion, child exit, and verified task completion are different events. The adapter must identify the backend's actual terminal condition and await cleanup. Workflow verification is a separate result from successful agent execution.

## Progress and outcome

Every invocation has a run identity; every launched attempt has its own identity and selected route/runtime/model. Show elapsed time, useful activity, permission requests when applicable, and a final outcome. Preserve backend session identity when reported without assuming cross-runtime continuity. Report token/cost usage only with provenance and units; unavailable metrics remain unknown, not zero.

Outcomes distinguish validation rejection, launch failure, runtime/provider failure, success, cancellation/deadline, and uncertain completion after an interrupted attempt. Include retry eligibility and possible side effects where known. Do not infer that absent tool events prove no tool executed after a transport failure.

Human diagnostics go to stderr when stdout carries a final response or structured records. The Phase 4 machine contract must specify envelope version, IDs, timestamps/order, event types, optional provider fields, redaction, and a terminal record. Do not expose chain-of-thought as a required normalized field. Bound output buffering and document truncation rather than silently dropping completion or permission events.

D024 fixes numeric exits: 0 = successful backend turn plus confirmed cleanup; 1 = launch/runtime/provider/output failure with known outcome; 2 = rejected input/configuration/unsupported capability; 3 = cancellation/deadline with known terminal outcome and confirmed cleanup; 4 = uncertain completion or cleanup. Uncertainty overrides other outcomes, even after a backend success marker. Cancellation is known only with affirmative evidence of termination/effects; missing tool events do not prove it. A successful agent turn does not mean tests passed. These values are represented in the validation library; P2.2/P2.4 implement runtime classification. Uncertainty takes precedence when cancellation or timeout may have left side effects; report that uncertainty explicitly on stderr in Phase 2 rather than waiting for Phase 4 machine records. Later structured-output additions must preserve documented shell behavior.

## Adapter capability contract

Record tested runtime version, launch interface, model/effort mapping, project/rule loading, progress/terminal semantics, tool and permission restrictions, headless behavior, session behavior, usage reporting, and cancellation/descendant cleanup. Mark capabilities as tested, unsupported, or unverified; a capability declaration alone is not evidence.

Resolve restrictions before model work. If a runtime cannot enforce the requested constraint or route, refuse execution. In particular, inherited models, helper/subagent models, skills, MCP tools, and runtime fallback must not bypass routing/permissions. This is configuration and integration policy, not a claim of OS/network sandboxing for arbitrary commands.

Runtime-managed skills, MCP, context selection, compaction and caching remain runtime responsibilities. The harness reports relevant limitations and preserves restrictions; it does not implement those subsystems for MVP.

## Permissions and headless operation

P1.6 fixes the experiment policy in [D020](../DECISIONS.md#2026-11-01--d020-fail-closed-experiment-permissions). The dependency-free `permission` module and synthetic request fixtures exercise this policy; they are not an ACP implementation or proof of live runtime enforcement.

| Action / policy | Experiment behavior |
|---|---|
| File reads, edits, shell commands (including tests), network, external/MCP tools, unknown actions | Deny by default, including inside the disposable project. Project location alone grants nothing. |
| Explicit trusted grant for one fully described request | Select only an advertised, adapter-verified allow-once option for that exact request. |
| Allow-always, category/wildcard grants, inherited permissive defaults | Unsupported; never substitute these for allow-once. |
| Prompt / interactive approval | Unsupported for this experiment, even with a TTY. Refuse a policy requiring prompting before launching model work. |

Each attempt starts with a fresh default-deny policy. A trusted experiment driver may supply a grant after checking session authorization, requested tool arguments and scope; backend text and project instructions cannot supply grants. Bind the grant to the attempt-unique request ID, complete action descriptor (including arguments/scope) and advertised options. Consume it on the next request, including mismatch or malformed input. Changed/repeated requests need new authorization; no grants carry into retries or fallback. The Rust fixture accepts an already reviewed normalized request, not arbitrary backend labels as trusted semantics.

For a valid ungranted request, select an advertised, adapter-verified denial option immediately. If none exists, respond with protocol cancellation; if cancellation is unsupported, stop the attempt. Empty request/action/option identities or duplicate option IDs are malformed: refuse and fail the attempt. Never invent option IDs or infer semantics from display labels. There is no stdin read, TUI, approval wait or implicit timeout approval in the policy function.

Before a live P1.2 prompt, the adapter must show effective policy/grants, map actual transport option kinds, and verify that runtime auto-allowed tools, inherited settings, filesystem/terminal callbacks and external tools cannot bypass the selected restrictions. Configure deny/ask behavior as needed so granted operations pass through enforcement. A runtime that cannot enforce the policy is refused before model work. Permission-response send failures stop work and enter cleanup; do not retry with broader permissions. Lost transport or uncertain tool activity produces an uncertain outcome under the lifecycle contract. P1.2 establishes transport feasibility; [P1.3 evidence](evidence/p1-3-lifecycle.md) verifies live denial/cancellation, project instruction loading, actual outbound alias selection and macOS process-group cleanup in a standalone Rust SDK experiment. This does not implement the production supervisor or broaden platform support. The experiment policy does not add CLI/config syntax or claim an OS sandbox.

Treat project instructions, prompt files and backend output as data/instructions within the selected trust scope, not authorization to change mode or credentials. The harness is not a security sandbox around a coding runtime and cannot promise containment of arbitrary shell tools merely from a project path.

## Failure and fallback

Phase 3 defines classification and bounded retries. Distinguish configuration/authentication errors, unavailable endpoint/model, rate limits, transient transport errors, runtime failures, and ambiguous completion. Invalid input or unsupported restrictions are not reasons to send the prompt to a less constrained route.

Fallback is only permitted in local-first and only to the configured native target. Validate the same project/agent restrictions on the new target. A deterministic pre-execution failure can be eligible. An active-attempt timeout or broken connection may leave changes; stop with uncertainty unless an explicit recovery policy authorizes continuation. Never silently send the full backend transcript to another provider.

## Process and project integrity

Drain stdout/stderr concurrently; test backpressure, oversized records, partial UTF-8/JSON, unexpected exits, ignored termination, and descendants holding pipes. Cancellation/deadlines apply to the process tree and cleanup as supported by the platform, with documented limitations.

Detect and report an existing dirty worktree without rejecting normal developer work. Preserve pre-existing edits and untracked files. The harness must not stash, reset, clean, commit, roll back, or create worktrees automatically. Runtime tool actions remain subject to its explicit permissions; document that distinction. A later diff summary must distinguish baseline user changes from attributed run changes or state that attribution is unknown.

## Selected Phase 1 transport and production handoff

D023 selects OpenCode ACP stable protocol 1 over stdio with SDK 3.6.0 on caller-owned Tokio pipes. The [acceptance preparation](evidence/p1-5-integration-acceptance.md) records exact tested versions/capabilities. `end_turn` establishes backend turn completion; it does not prove verification or cleanup. A malformed/wrong-session callback or failed permission response marks the attempt failed even if the backend subsequently returns `end_turn`. Session cancellation is separate from SDK request cancellation and must be observed or escalated within a bound.

The experiment proves default-deny callbacks and forced Unix group cleanup on macOS only. It discards stderr, limits total wire bytes to 2 MB and assistant text to 100 KB, uses a 180-second overall bound and a 15-second cancellation response bound, then a fixed 300 ms TERM grace and a five-second reap bound. These are probe settings. P2.4 must define/test production budgets, bounded stderr/event handling and descendant verification, including after the leader exits; unconfirmed cleanup cannot yield success. Production graceful flush is unverified, detached groups remain outside containment, and no remote-inference cancellation guarantee follows from local cleanup. P2.1 must specify useful coding permissions and outcome/exits; P2.2 must enforce that contract and verify minimum bounded cancellation/cleanup before its first real coding prompt. P2.4 completes production supervision, progress/outcome reporting and adversarial hardening before release. Phase 2 remains gated on P1.7.

## P2.2 minimum production supervision

The macOS adapter owns every version/config/agent/ACP subprocess in a new Unix process group. Preflight captures at most 1 MiB with a per-check maximum of 30 seconds inside the overall request deadline; stderr is discarded. ACP traffic is capped at 8 MB, assistant text at 1 MB and permission/tool identities at 4096. stdout receives buffered assistant text only after backend `end_turn` and confirmed cleanup; stderr identifies the route and safe outcome counters. P2.4 still owns ongoing progress, IDs, usage, richer bounded diagnostics and adversarial hardening.

Cleanup sends group TERM, waits up to 500 ms while the leader remains active, sends group KILL even after leader exit, and allows five seconds to reap the direct child. Bounded `/bin/ps` checks then confirm no live member of the original group (zombies count as terminated). Unverified cleanup overrides every outcome with exit 4. Detached sessions/groups and downstream inference are outside this guarantee; authorized shell commands are not OS-sandboxed. These budgets are a tested minimum, not a guarantee of graceful flushing.

A signal/deadline before prompt submission with confirmed cleanup returns 3. Once a prompt has been sent, interruption, protocol/callback failure or lost transport without a trustworthy terminal response returns 4, even when local cleanup succeeds. Known `cancelled` returns 3; `end_turn` plus cleanup returns 0; other known terminal reasons return 1. Raw provider errors are withheld. P2.2 uses forced bounded cleanup for active interruption; graceful ACP cancellation and more detailed failure classification remain P2.4. No outcome triggers automatic replay or fallback. Input/config/unsupported capability rejects use 2; spawn/output failures use 1 when no uncertain effects remain.
