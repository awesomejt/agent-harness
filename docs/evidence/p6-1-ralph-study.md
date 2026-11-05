# P6.1 evidence — Rust Ralph loop study

Task: [P6.1](../../tasks/06-ralph.md#p6-1). Decision: [D045](../../DECISIONS.md#2026-11-05--d045-ralph-claim-plus-trusted-check-completion-fresh-iterations-and-explicit-bounds). Documentation only: no source, CLI, dependency or artifact change, and no model turn.

## Sources inspected (2026-11-05)

| Project | Revision | License | Why |
|---|---|---|---|
| [mikeyobrien/ralph-orchestrator](https://github.com/mikeyobrien/ralph-orchestrator) | `b5789dfb` (2026-10-15) | MIT | Reference named in [FRAMEWORKS](../FRAMEWORKS.md); the largest Rust implementation (`ralph-core` event loop, config, history, CLI resume). |
| [martinstark/ralph-rs](https://github.com/martinstark/ralph-rs) | `5564eff6` (2026-05-02) | MIT | A minimal Rust loop over one native CLI, for contrast with the orchestrator. |

Both were shallow clones into a session scratch directory. Their source was read, not built or run, and no code is copied. A GitHub search for Rust Ralph loops found other projects that were unlicensed, GPL or tied to one issue tracker. They were not inspected further.

## Observations

**ralph-orchestrator** (`crates/ralph-core/src/event_loop/mod.rs`, `config.rs`, `loop_history.rs`):

- Completion is an agent-emitted event (`LOOP_COMPLETE` via `ralph emit`), not prose. It is rejected while configured required events are missing or runtime tasks remain open. In scratchpad mode, pending items only log a warning, "trusting agent decision".
- "Backpressure" evidence (`tests: pass`, `lint: pass`, …) is a field in the agent's own event payload. The harness reads it rather than running the checks, so it is still a model assertion.
- Limits: `max_iterations` (default 100), `max_runtime_seconds` (default 14400), optional `max_cost_usd` summed from backend-reported cost, `max_consecutive_failures`, and stale-loop/thrashing detectors (same signature 3+ times). Each has its own termination reason. Exits: 0 completion, 1 failure, 2 limit, 130 interrupt.
- State lives in the workspace (`.ralph/`): an append-only `history.jsonl`, a stop-request file and a loop lock. Resume restores the iteration count and cumulative cost.

**ralph-rs** (`src/config.rs`, README):

- Completion is the text marker `<promise>COMPLETE</promise>` in Claude's output. Verification commands listed in the PRD are run by the agent when instructed; the loop itself runs them only in `--dry-run`.
- `--max-iterations` defaults to 10, and 0 means unlimited. There is a per-call timeout (1800 s), an optional per-feature error budget, and rate-limit waits with backoff.
- Progress is an agent-appended `progress.txt` plus per-iteration logs in the project. The loop does not enforce either.

## Implications for agent-harness

| Observed approach | Disposition in D045 |
|---|---|
| Completion from a model marker or event alone | Rejected as sufficient. A claim is required but only counts with a harness-run trusted check that passes after the same iteration (D043). |
| Agent-reported "tests: pass" evidence | Rejected. Only harness-config checks authorized by `--verify` run; their output is not fed back to the model. |
| DONE/stop files or task lists inside the project | Not used as signals. The agent can write them, and they persist across iterations, so they can be stale. Cancellation stays signal-based. |
| Iteration and wall-time limits with explicit termination reasons | Adopted, with lower ceilings than the orchestrator and no "unlimited" value. |
| Cost limit from summed backend cost | Not selected. OpenCode `usage_update` cost is a backend report that may be absent ([EXECUTION](../EXECUTION.md)); it is recorded, never enforced. |
| Consecutive-failure budget, rate-limit backoff | Not needed. Any non-success agent outcome stops the loop (D031/D044 no-replay), so there is nothing to back off from. |
| Stale-loop / no-progress detectors | Deferred until real use (P6.4) shows loops that make no progress within the iteration bound. |
| State and lock files in the workspace | Replaced by the D044 store outside the project and the shared per-project lock. |
| Persistent mode, hats/roles, Telegram/web control | Out of scope; `--agent` selects one named role. |

Both projects re-send a stable prompt and rely on project files for progress. D045 keeps that model and adds a harness-authored header. The header carries only enumerated facts from the harness's own record, never response text or check output.
