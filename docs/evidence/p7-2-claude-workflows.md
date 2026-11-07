# P7.2 evidence — Claude sequences and Ralph

Task: [P7.2](../../tasks/07-native-adapters.md#p7-2), fourth narrow PR. Decision: [D051](../../DECISIONS.md#2026-11-06--d051-claude-sequences-and-ralph-as-fresh-single-runs-with-runtime-named-records). It builds on [D048](../../DECISIONS.md#2026-11-06--d048-claude-runtime-launch-preflight-and-deny-profile-single-runs) (launch, preflight, deny), [D049](../../DECISIONS.md#2026-11-06--d049-claude-trusted-permissions-through-the-host-prompt-path) (trusted host prompts) and [D050](../../DECISIONS.md#2026-11-06--d050-claude-named-roles-as-a-narrowed-tool-set-appended-body-and-verified-effort) (named roles and effort), under the unchanged [D044](../../DECISIONS.md#2026-11-03--d044-sequence-inputs-fresh-context-steps-stop-on-failure-and-explicit-resume) and [D045](../../DECISIONS.md#2026-11-05--d045-ralph-claim-plus-trusted-check-completion-fresh-iterations-and-explicit-bounds) workflow contracts. Authentication: the operator's existing official CLI login ([D047](../../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login)). Date: 2026-11-06. Platform: macOS arm64 (D041), Claude Code **2.1.314**, `ah` built from this branch.

This PR removes the workflow refusal for the Claude runtime. `ah sequence` and `ah ralph` now launch one D048–D050 single run per step or iteration. Workflow records and previews name the model `claude/MODEL`. Local-first with a `claude` target still exits 2 before launch.

## Change

- `single::workflow_supported` (the Claude refusal) is removed; sequences and Ralph call the same `single::supported` check as `ah single`, per step before step 1 and once per Ralph invocation.
- `Resolved::record_model` gives `claude/MODEL` for Claude and the existing `opencode/…` or `ah-litellm/…` runtime model for OpenCode. Sequence attempts, Ralph iterations and both workflow previews use it. Launch arguments and D039 machine output keep the bare model.

## Fixture and regression results

- `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings` and `cargo test --locked` pass. A new unit test checks the record and runtime models and that `supported` accepts a Claude request.
- `python3 scripts/tests/claude.py`: **60 cases pass** (55 before this PR). The fake now appends each launch's argv to `launches.jsonl`, takes an optional per-launch `cases` list, answers `error-result` on the trusted path too, and has a `claim` case whose response ends with the Ralph marker. The three workflow refusal cases are replaced by:
  - A two-step `deny` sequence: two launches with identical deny flags, each preceded by its own four control requests, each step's file as its only prompt, both responses on stdout, record `completed` with `model: claude/sonnet`, `route: cloud-only` and one submitted `end_turn` backend per step. No secret appears in output or record.
  - A `trusted` sequence whose second step fails after submission: exit 1, step 1 granted its write, step 2 `failed` with `prompt_submitted: true`. Bare resume exits 2 with no launch. `--retry` launches one fresh session with the second prompt, and the record ends `completed` with step 2 reasons `initial`, `retry`.
  - A second step that hits EOF after submission: exit 4, step `uncertain`, no replay.
  - Sequence preview: `model claude/sonnet`, no `execution refused`, no launch and no state written.
  - Ralph: an iteration without a claim, then one with a claim whose check passes. Two launches, the D045 header on each prompt, claims `[false, true]`, record `completed`, Claude usage recorded per iteration.
  - Ralph cancelled at its deadline (exit 3, interrupt sent): bare resume exits 2, `--retry` launches once and completes.
  - Local-first with a `claude` target: sequence and Ralph runs both exit 2 with no launch and no state.
- `python3 scripts/tests/offline.py`: **26/26** suites pass.

## Live runs (operator's existing login)

Disposable git project: `calc.py` with two bugs (`add` subtracts; `mean` divides by `len + 1`), `test_calc.py` (one test per function) and an `AGENTS.md`. The config lives outside the project (P6.4 guidance): `cloud-only`, `native.target: "claude"`, model `sonnet`, checks `test` (`python3 -m unittest test_calc.py`) and `add` (`python3 -m unittest test_calc.T.test_add`). All runs use `--permissions trusted` unless stated. Costs are backend reports, not billing.

| Run | Result |
|---|---|
| `sequence run` of `1-fix-add.md`, `2-fix-mean.md`, `--verify test` | Exit 1 in 6.1 s. Step 1 fixed `add` (1 prompt, 1 grant). Its gate `test` still failed on `test_mean`, so the run stopped and step 2 was never launched. That is correct D044 behavior: the gate applies to every step, and this sequence's design was wrong. Gate retention then forbids moving step 1 to a different check on resume, so a new run follows. |
| Same, step 1 with `verify: add` metadata | Exit 0 in 14.0 s. Step 1: 1 prompt, 1 grant, 4 tool events, check `add` passed. Step 2: 3 prompts, 3 grants, 8 tool events, check `test` passed. Each step ran its own preflight and session. `sequence show` lists both attempts with `model claude/sonnet`, `route cloud-only` and `prompt submitted yes`. The final `git diff` touches only the two function bodies. |
| `ralph run task.md --verify test --max-iterations 4`; the task asks for one fix per iteration | Exit 0 in 19.6 s; completed at iteration 4. Iteration 1 fixed `add` and made no claim. Iterations 2 and 3 found the work done and printed `AH-RALPH-COMPLETE`, but then added the `AGENTS-MD-OK` line that this project's `AGENTS.md` asked for. The marker was not the last line, so there was no claim, correctly (D045). Iteration 4 ended on the marker, and the check passed. |
| `ralph run`, same task, SIGINT 3 s into iteration 1 | Exit 3. One `interrupt` was sent, the backend ended `cancelled` and cleanup was confirmed (1 prompt, 1 grant). Bare `resume` exited 2 and asked for `--retry` or `--accept`, because the iteration had submitted a prompt. |
| `ralph resume RUN --retry --verify test` (`--permissions` omitted by mistake) | The iteration re-resolved as `deny` and reported `changed since iteration 1: permissions`. It produced no record until the 300 s deadline, then ended cancelled (exit 3, cleanup confirmed). See the deny finding below. |
| `ralph resume RUN --retry --permissions trusted --verify test` | Exit 0 in 11.6 s. Iteration 3 (retry) fixed `mean` (2 prompts, 2 grants) and made no claim. Iteration 4 (continue) claimed, and the check passed. `ralph show` lists all four iterations, each with its permissions, and the tests pass. |

## Finding: a tool-dependent task under `deny` can run to the deadline

The `deny` iteration above returned no record for 300 s. A reproduction gave the same result each time:

- `ah single --prompt-file task.md` under `deny` (no Ralph header) returned in 2.8 s with text shaped like tool calls, as D050 recorded.
- The same text with the D045 header, sent through `ah single`, and two `ah ralph run` iterations under `deny` each ran to a 60 s deadline and ended cancelled.
- The official CLI alone, with the D048 deny flags and the same prompt, was still running after 45 s. With `--include-partial-messages`, 25 s produced 8,245 characters of repeated `<invoke name="Bash">… echo …</invoke>` text and no turn end.

The model offered no tools keeps writing tool-call-shaped text and never ends its turn. Nothing runs, and the harness bounds the turn with its deadline, interrupt and cleanup (D048), so this is not a harness defect. It is a usage limit: give a workflow that needs tools `--permissions trusted` on every `run` and `resume`. A `deny` workflow suits tasks that need no tools.

## Limits

- Resume re-resolves `--mode`, `--model` and `--permissions` from the resuming invocation (D044). Leaving out `--permissions trusted` on a Claude resume gives a `deny` iteration. It is reported as a change, but it is not refused.
- A project instruction that asks for a fixed final line competes with the Ralph marker. In that case the marker is not the last line and the claim does not count. Keep such instructions out of `AGENTS.md` for Ralph tasks, or have them yield to task-specific markers.
- Each step or iteration costs one full preflight (four control requests, about 0.3–0.5 s before the prompt) and draws on the operator's Claude plan or usage credits.
- Still refused: local-first with a `claude` target.
