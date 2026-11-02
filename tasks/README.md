# Development task structure

This directory plans work on agent-harness. It is not the runtime queue/state used by `ah` workflows. [PROJECT.md](../PROJECT.md) is the only task-status board; [docs/PROJECT_PLAN.md](../docs/PROJECT_PLAN.md) defines execution order and milestones. Cards here add dependencies, boundaries and acceptance evidence to stable P IDs.

## Phase cards

| Phase | Task cards | Delivery |
|---|---|---|
| 1 | [Integration experiment](01-integration.md) | Prove the Rust/OpenCode/LiteLLM path and select minimal dependencies |
| 2 | [First usable slice](02-first-slice.md) | Ship/use one local-only coding run |
| 3 | [Routing](03-routing.md) | All modes and configured eligible fallback |
| 4 | [Core MVP](04-core-mvp.md) | Named constrained agents, automation and declared binary support |
| 5 | [Sequences](05-sequences.md) | Ordered steps, verification and durable recovery |
| 6 | [Ralph](06-ralph.md) | Fresh-context bounded iterations |
| 7 | [Native adapters](07-native-adapters.md) | One additional provider at a time |
| 8 | [Pi](08-pi.md) | Early single-run adapter, then workflow parity after Phase 6 |
| 9 | [Optional resource awareness](09-resource-awareness.md) | Demand-selected quota/ranking/scheduling increments |

## Status, readiness and ownership

- On main, a checked item in PROJECT.md means accepted evidence and required PR review/merge are complete. An unchecked item is not done; it may be ready, waiting on dependencies, selected for current work, externally blocked, or deliberately deferred.
- In an open PR, completion checkmarks are proposed post-merge state. They take effect only when the PR merges; do not report them as completed on main before then. Review findings can keep the task open until addressed.
- PROJECT.md's current-work section records the one active task/PR and any real blocker. Do not copy mutable status or checkboxes into the phase cards.
- A task is ready when its prerequisite evidence exists, the owner phase's required decisions are recorded, and any selection/external gate is satisfied. Use merged prerequisites by default. Tightly coupled tasks may share a PR, but consuming work must wait for prerequisite evidence and status remains unchecked until review/merge.
- Phase 1 permission-policy evidence must exist before any live run. For P7.2–P7.5, select one provider before activation. For Phase 9, dependency completion alone does not activate optional work. P9.4 has conditional OR dependencies, not a requirement to implement quota and scheduling together.
- The primary agent/developer owns integration and status. If bounded work is delegated under applicable instructions, give it explicit file/scope ownership and avoid overlapping edits. The plan itself does not request a multi-agent execution team.

## Task execution loop

1. Select the next ready task and read its card, contract and relevant decisions. Record active task/branch in PROJECT.md when implementation starts.
2. Finalize only choices needed by this task. If a real external prerequisite is unavailable, record observed evidence and next action; do useful independent checks without claiming the live gate passed.
3. Work on a feature branch. Prefer one focused task/PR; split a broad card into reviewable substeps without changing its acceptance boundary. Add child tasks only when useful, keep parent ID/traceability, and update dependency links when splitting.
4. Run checks proportional to the work and capture required live/fixture evidence. Update consuming contracts, decisions, capability/version notes and use observations.
5. Follow [the Git workflow](../docs/GIT_WORKFLOW.md): open PR, monitor Grok, handle findings and merge/clean up under its rules. Maximum three Grok reviews per PR; unresolved critical/high issues then require human handoff.
6. Check off completed tasks in PROJECT.md with evidence/PR links and clear active work. Close a phase only when every mandatory task and its live-use gate pass. Unselected optional scope stays deferred.

## Evidence and changes

Use a compact record: task ID, date, commit/PR, test commands/results, tested versions/target, live route/model/task when required, observed outcome, limitations and follow-ups. Keep logs/fixtures sanitized; do not commit credentials or full private transcripts.

Goals G1–G9, features F01–F26 and acceptance AC01–AC11 remain defined in docs/SPECIFICATION.md and docs/FEATURE_REVIEW.md. Decision IDs Dxxx live in DECISIONS.md. Task cards trace execution; they do not redefine scope or freeze future schemas. Native session fork, plugins, recipes and other candidates are not tasks merely because upstream tools offer them.

For a genuinely new task, use [TEMPLATE.md](TEMPLATE.md), allocate a stable ID in PROJECT.md and add explicit dependencies/evidence. Existing cards are the initial plan for all 50 remaining implementation tasks; no implementation is marked complete by this planning pass.
