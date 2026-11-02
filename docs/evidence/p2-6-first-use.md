# P2.6 — Installed first-slice real use

Date: 2026-11-02 (America/Denver). Entry baseline: `b18c68f` (P2.5 PR #21 merged). Task: [P2.6](../../tasks/02-first-slice.md#p2-6). Completion takes effect on [PR #22](https://github.com/awesomejt/agent-harness/pull/22) merge after the review closeout below. P2.9 remains the Phase 2 exit gate.

## Published binary and prerequisites

Downloaded the published [v0.1.0-alpha.1](https://github.com/awesomejt/agent-harness/releases/tag/v0.1.0-alpha.1) archive and SHA256SUMS, verified the checksum, extracted it, and ran the archive installation smoke. Archive SHA-256: `c11b6f84ff7c8b775906c2a922913a1a30c6b1d12d54484f80680588303f3e1a`. BUILD-INFO source: `b18c68fa20269d7a9b522789b032a551d200669d`; executable SHA-256: `9ecbcd3f577584ae08df4676b8f0474d353648b621ace022467cb583cfbea3f4`.

Apple Silicon macOS 27.0.1, OpenCode 1.18.30, Python 3.14.7; development checks use Rust/Cargo 1.88.0. Version/help/preview/install smoke passed with no toolchains/runtime on PATH. Coding checks separately require OpenCode and Python for this project task. LiteLLM endpoint: existing user-supplied `http://litellm:4000/v1`; alias `macmini-qwen3-coder-30b`. Existing interactive-Zsh environment supplies the credential; its value is never recorded. Remote LiteLLM version remains unreported.

## Real maintenance task and comparison method

The task improves this repository's existing `scripts/tests/single_runtime.py`: add `--binary` as a Path argument defaulting to `ROOT / target/debug/ah`, use it as the harness executable, preserve assertions, and run the script's `--help` to verify the new option. This removes a real obstacle to testing a release instead of a development build. Each trial starts with the same baseline script in a fresh disposable Git project, never the working checkout. Successful changes are inspected before integration.

The installed harness uses `single`, explicit `--permissions trusted`, and a 300-second bound. Direct OpenCode uses `run --format json --model ah-litellm/macmini-qwen3-coder-30b` with the same task and a separate private HOME/XDG tree. Direct execution explicitly allows the selected built-in read/edit/shell tools, whereas the harness validates and grants individual ACP requests. Both isolate project/global plugins, MCP, extra tools and inherited providers; helper and primary models select the same alias. These are different permission/transport paths, not a claim of identical guarantees or a performance benchmark.

A temporary loopback observer reuses the existing runtime-test HTTP handler to forward only `/v1/chat/completions` to the selected existing endpoint. It checks every request's model and tool set; raw requests/responses and credentials are not committed. Projects are independent and no uncertain project is replayed.

## Unavailable-service observation

A bound but non-listening loopback socket provides a deterministic unavailable endpoint without depending on external service state. The published binary uses default-deny tools and a 15-second bound. OpenCode did not surface an immediate terminal provider failure: after the deadline, ACP cancellation returned `cancelled`, confirmed cleanup, exit **3**, in 15.1 seconds. Zero tool events/permission grants; a pre-existing sentinel file was preserved, credentials were absent from output, and no harness retry/fallback occurred. This is a known cancellation after unavailability, not a falsely specific authentication/network diagnosis. Runtime-internal connection retries are outside the harness's single-attempt count.

## First-slice acceptance assessment

This assesses the first-slice column of [AC01–AC11](../SPECIFICATION.md#milestone-acceptance-matrix); it does not claim core MVP acceptance.

| Criterion | First-slice evidence / boundary |
|---|---|
| AC01 coding | P2.2 live edit/test success plus this published-binary maintenance task and independent verification; OpenCode owns tool turns. |
| AC02 route | P2.4 negative/native-trap fixtures; observed live primary/helper aliases; unavailable endpoint remains local-only. Later cloud/local-first modes are N/A. |
| AC03 fallback | N/A in Phase 2; no automatic harness retry/fallback, including uncertain trials. |
| AC04 config | P2.1 strict config/key references; P2.3 ownership/conflict/no-sync and global preservation; isolated live trials. |
| AC05 inputs/project | P2.2 inline/file/stdin and invalid-input fixtures; P2.8 dirty/untracked preservation; no automatic Git mutation or rollback. |
| AC06 output | P2.4 streamed progress, attempt/route identity, bounded output, usage unknown when unreported, distinct exits; current observations retain uncertainty. Machine output N/A until P4.7. |
| AC07 lifecycle/permissions | P1.6 policy; P2.2 exact grants; P2.4 cooperative/forced cleanup tests; published-binary cancellation below. Trusted shell is host access, not a sandbox. |
| AC08 agents | N/A until Phase 4; no named-agent CLI added. |
| AC09 diagnostics | P2.7 network-free preview/negative fixtures; actual published archive installation preview smoke. |
| AC10 distribution | Published checksummed Apple Silicon archive installed/smoked; separate prerequisites in OPERATIONS.md. Other targets N/A pending evidence. |
| AC11 capabilities | P1.3 live instruction loading and route/helper checks; supported pinned OpenCode 1.18.30. Skills/MCP/context expansion N/A until P4.8. |

Prior task evidence: [P2.1](p2-1-config-contract.md), [P2.2](p2-2-local-only-run.md), [P2.3](p2-3-managed-config.md), [P2.4](p2-4-progress-supervision.md), [P2.5](p2-5-installable-binary.md), [P2.7](p2-7-diagnostics-preview.md), [P2.8](p2-8-dirty-project-preservation.md), [P1.3](p1-3-lifecycle.md). P2.9 must holistically verify this assessment and all Phase 2 deliverables before Phase 3 begins.


## Observed coding outcomes and interventions

| Path | Outcome | Observations |
|---|---|---|
| Published harness binary | **0**, backend `end_turn`, cleanup confirmed, 113.2 seconds | Three exact allow-once grants, 12 tool events; six observed requests all used the selected alias; usage unknown. Script changed and independent `--help` showed `--binary`. |
| Direct OpenCode | **0**, structured step/tool/text events, 78.9 seconds | Seven observed requests all used the same alias; script changed and independent `--help` showed `--binary`. |

Each path had one fresh-project trial in this task, without automatic retry or fallback. The trials overlapped at the service, so elapsed times are observations only and cannot establish comparative overhead. Both completed the task; direct OpenCode needed the manually assembled provider/tool/environment configuration. The harness supplied validated project sync, isolation, exact grants, progress, deadline and outcome handling. Neither path's successful text substitutes for verification.

The harness candidate added an unnecessary bare `return` after server cleanup. Primary-agent inspection removed it before integration; the two useful changes were retained. Direct OpenCode produced the two requested changes without that extra statement. No model was asked to retry the same project. The candidate's `--help` and the following independent deterministic runtime checks passed before integration; final integrated checks passed again after removing the unnecessary statement, including the unchanged default development-binary path.

The published binary with the updated script completed a deterministic real-OpenCode arithmetic edit/test, exit **0**, six grants, 16 tool events, `end_turn`, cleanup confirmed. A separate fresh deterministic project cancelled after the actual edit/test: SIGINT produced `session/cancel`, backend `cancelled`, cleanup confirmed and exit **3** in about 3.1 seconds. Both the edited function and success-only marker remained; independent `python3 test_calc.py` passed after each run. This cancellation uses the local deterministic model, not external inference; remote cancellation/containment is not claimed.

## Friction and next actions

- Resolved here: the runtime checker hard-coded the development binary. `--binary` now supports release acceptance while retaining the existing default and assertions.
- Recorded for P2.9 assessment: a live model may make unrelated edits; inspect diffs and independently verify before integration. The harness does not validate semantic correctness or automatically revert changes.
- Recorded for P2.9/P3.1: an unavailable provider can remain active until the deadline; outcome is confirmed cancellation when ACP supplies that terminal response. Keep the explicit bound; do not infer an immediate network-specific failure or authorize fallback from this observation.
- Retain earlier P2.2/P2.4 uncertain-terminal evidence. This successful trial does not erase those failures or justify automatic replay.
- No provider, runtime, routing policy, release binary or architecture changes are introduced. Proceed next to P2.9 holistic review; Phase 3 stays gated.

## Repeatable verification

Install/download/checksum steps are in OPERATIONS.md. With an absolute path to the extracted published executable:

```sh
sh scripts/release/smoke.sh /path/to/downloaded-assets 0.1.0-alpha.1
python3 scripts/tests/single_runtime.py --help
python3 scripts/tests/single_runtime.py --binary /absolute/path/to/ah
python3 scripts/tests/single_runtime.py --binary /absolute/path/to/ah --cancel
# Optional fresh live arithmetic project against the configured existing endpoint:
zsh -ic 'python3 scripts/tests/single_runtime.py --binary /absolute/path/to/ah --live'
cargo fmt --all -- --check
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
python3 scripts/tests/single.py
python3 scripts/tests/preview.py
python3 scripts/tests/worktree.py
```

The unavailable-endpoint observation and direct OpenCode maintenance comparison were one-off manual trials; they are not covered by the repeatable commands above. The method sections record their setup and results for P2.9 assessment.

For the maintenance comparison, copy the entry-baseline script into two new Git-rooted projects and ask each path to add the Path-valued `--binary` argument, preserve assertions, use the argument as the subprocess executable and run `--help`. Use the isolated configuration and observer described above; never reuse an uncertain project. The optional `--live` command above is a new arithmetic trial, not a reproduction of the maintenance prompt. No private driver, raw transcript, temporary project path or credential is needed to consume the evidence.

All 38 Rust tests, formatting, locked Clippy, 55 public CLI cases plus the no-sync repetition, preview and dirty-project suites passed. Published archive smoke and the installed runtime success/cancellation checks passed. No new production binary is needed for this test-driver/documentation change. Required Grok review and PR merge complete task acceptance; the holistic review remains separate.


## PR #22 review closeout

[Grok review](https://github.com/awesomejt/agent-harness/pull/22#pullrequestreview-5744575404): 0 blockers, 0 concerns, two nits. Both addressed: binary paths expand/resolve and missing/non-executable files return an argparse error before server/project setup; the repeatability section explicitly identifies the unavailable-service and direct-comparison observations as manual trials. Missing/non-executable rejection and relative-path normalization checks passed; the final installed-binary success/cancellation and default-path checks passed again after validation was added. One review; no re-review required for nits. P2.9 remains the next gate.
