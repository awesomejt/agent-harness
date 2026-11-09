# Feature landscape and scope review

Reviewed 2026-11-01. This is a documentation-based comparison, not a hands-on benchmark or a claim of feature parity. Sources are upstream project documentation; our scope recommendations are judgments against G1–G9 in [SPECIFICATION.md](SPECIFICATION.md). Revalidate version-specific behavior during implementation. No finite review can guarantee every future feature is known.

## Projects reviewed

| Project/source | Documented behavior relevant here | Implication for agent-harness |
|---|---|---|
| [OpenCode CLI](https://opencode.ai/docs/cli/) and [permissions](https://opencode.ai/docs/permissions/) | Noninteractive runs, sessions, models, agents, structured output, and allow/ask/deny controls. | Preserve backend capabilities, expose setup/routing decisions, and test permissions; do not infer safe defaults from the executable. |
| [Pi overview](https://github.com/earendil-works/pi/tree/main/packages/coding-agent) and [RPC](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/rpc.md) | Extensible runtime with skills/templates; subprocess JSON records and asynchronous lifecycle events. | Model completion explicitly, drain streams continuously, and leave inner context management to the runtime. |
| [Goose recipes](https://goose-docs.ai/docs/guides/recipes/) | Reusable workflows package prompts, extensions, and settings; subrecipes compose work. | Consider reusable workflow inputs later; a recipe marketplace is not required for first use. |
| [Aider usage](https://aider.chat/docs/usage.html) and [lint/test integration](https://aider.chat/docs/usage/lint-test.html) | File-oriented coding, Git change tracking/undo, and command-based verification/repair. | Explain project changes and distinguish a successful process from verified work; do not automatically adopt commit/undo behavior. |
| [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator) | Multiple backends, specialized roles, bounded iteration, verification gates, persistent tasks, and human interaction. | Keep bounded loops and recovery in scope; treat dashboards and messaging integrations as optional. |
| [harness-cli](https://github.com/ayshptk/harness-cli) | Unified events, stdin prompts, dry-run routing, model aliases, and availability/capability checks. | Add prompt-input coverage, resolved-plan preview, diagnostics, and a machine-output contract. |
| [getlatentic/agent-harness](https://github.com/getlatentic/agent-harness) | Shared run interface/events, readiness information, CLI/ACP adapters, and optional custom tool loop. | Reuse adapter ideas without importing an inner agent loop. |
| [agents-cli](https://github.com/agentsfolder/agents-cli) | Config projection, preview, drift detection, compatibility reporting, and generated-output cleanup. | Track ownership and detect conflicts; preview generated changes before replacing user content. |

These projects are examples of feature families, not endorsements of every authentication route or dependency. This pass does not add Aider or Goose as required runtime adapters.

## Feature inventory

**Committed** means product scope, not implemented. **Backend-owned** means available only when supported and validated; never silently bypass harness restrictions. **Candidate** means considered, not approved implementation work. **Excluded** means outside the current product boundary. Phase numbers are delivery owners, not release dates.

| ID | Feature | Disposition / phase | Goal and task trace |
|---|---|---|---|
| F01 | Single project coding run | Committed / 2 | G2; P2.2, P2.6 |
| F02 | Explicit modes, failure classification, configured fallback | Committed / 2–3 | G3; P2.4, P3.1–P3.5 |
| F03 | Project-only provider sync, ownership/conflict handling | Committed / 2, 4 | G4/G5; P2.3, P4.2 |
| F04 | Model aliases/groups and supported effort mapping | Committed / 2–4 | G3/G5; P2.2, P3.3, P4.3 |
| F05 | Named primary agents | Committed / 4 | G5; P4.1–P4.4 |
| F06 | Specialized roles with enforced constraints | Committed / 4 | G5; P4.3–P4.4; not an autonomous-team scheduler |
| F07 | Ordered prompt sequences and step recovery | Committed / 5 | G6; P5.1–P5.4 |
| F08 | Fresh-context bounded Ralph loop | Committed / 6 | G7; P6.1–P6.4 |
| F09 | Additional native CLI adapters | Committed / 7, one at a time | G8; P7.1–P7.6 |
| F10 | Pi adapter and documented portability limits | Committed / 8 | G8; P8.1–P8.4; workflow parity P8.4 waits for accepted P6.5 review |
| F11 | Dependency diagnostics, resolved-plan and sync preview | Committed / basic 2, polish 4 | G1/G4; P2.7, P4.5 |
| F12 | Inline, file, and stdin prompt inputs | Committed / 2 | G2; P2.2; mutual-exclusion/empty-input rules specified before launch |
| F13 | Human progress plus machine-readable final result/events | Committed / human progress 2, versioned machine result/events 4 | G2/G8; P2.4, P4.7 |
| F14 | Attempt identity, outcome, reported usage, inspectable workflow records | Committed / transient 2, durable 5–6 | G2/G6/G7; P2.4, P5.3, P6.2; no full transcript archive by default |
| F15 | Resume interrupted sequence/loop | Committed / 5–6 | G6/G7; P5.3, P6.4; native session continuation/fork remains Candidate |
| F16 | Cancellation/deadlines, loop bounds, measured resource limits | Committed / 2, 6, 9 respectively | G2/G7/G9; P2.4, P6.3, P9.2; no guessed dollar cap guarantee |
| F17 | Explicit test/lint/verification gates and result attribution | Committed / 5–6 | G6/G7; P5.5, P6.3; backend-only verification distinguishable from harness verification |
| F18 | Skills, MCP, backend instructions and tools | Backend-owned / validate 4, 7–8 | G5/G8; P4.8, P7.6, P8.3; no harness MCP server required |
| F19 | Context selection, compaction, caching, repository indexing | Backend-owned | G2/G8; document capabilities/limitations; no new context engine |
| F20 | Dirty-worktree awareness and preservation of user changes | Committed / 2 | G2; P2.8; diff summaries Candidate, automatic commit/rollback/worktree creation Excluded |
| F21 | Plugins and user-defined lifecycle hooks | Candidate | Reassess only if adapters/workflows need an extension boundary; no current phase commitment |
| F22 | Parameterized recipes, workflow templates, shared packages | Candidate | Reassess after 5–6 real-use findings; no marketplace or general DAG engine committed |
| F23 | Non-spending quota visibility, cooldowns, optional scheduling | Committed as demand-driven increments / 9 | G9; P9.1–P9.4; no allocation ranking can override a mode |
| F24 | Headless/CI operation and explicit unanswered-permission behavior | Committed / validate 1–2, package 4 | G2/G5; P1.6, P1.3, P2.4, P4.7 |
| F25 | Platform binaries, version/capability diagnostics, install/upgrade guidance | Committed / 2, 4 | G1/G8; P2.5, P2.7, P4.5; provider auto-install and silent self-update Excluded |
| F26 | Parallel teams, distributed execution, hosted UI, remote messaging | Excluded from current roadmap | Revisit only with a separate product decision; specialized agents alone do not imply these features |
| F27 | Ordered multi-step fallback chain with allowance-exhaustion trigger and fallback-model known-problem record | Candidate | D067; [re-scope findings](evidence/p7-subscription-rescope.md); needs Go over-limit behavior evidence and a D034 replacement decision |
| F28 | Explicit private (physically local) route constraint | Candidate | D067; route labels are not locality (D002); needed before any local-to-hosted model mapping |

## Gaps closed by this review

The earlier goals covered the main workflows but underspecified input handling, plan preview, machine consumers, backend feature ownership, and dirty-project behavior. F11–F14, F17–F20, F24–F25 now have explicit task/contract coverage. This adds completeness around existing goals without moving sequences/Ralph into the first slice or adding another runtime.

Candidates remain visible here instead of becoming unchecked implementation promises. Promote one only with a use case, owner phase, acceptance evidence, decision entry, and task. Architecture details that depend on the integration experiment remain deferred under D011. The Rust blueprint and diagrams do not promote any candidate feature; AC01–AC11 in SPECIFICATION.md provide the explicit MVP acceptance boundary.

## Limits and next evidence

No candidate was installed or live-tested in this feature review. Documentation proves that a feature is described upstream, not that a specific installed version or our adapter supports it. Phase 1 still verifies the chosen OpenCode interface; each later adapter needs its own compatibility evidence. Runtime tests must cover behavior rather than just accepting a documented flag.
