# P7.2 — Claude native adapter acceptance

Date: 2026-11-06. Task: [P7.2](../../tasks/07-native-adapters.md#p7-2), final closeout after merged [PR #65](https://github.com/awesomejt/agent-harness/pull/65). This is adapter acceptance, not the Phase 7 holistic review or a new release. Completion is proposed until this feature PR is reviewed and merged. The [capability matrix](../FRAMEWORKS.md#p72-claude-capability-matrix), [setup](../OPERATIONS.md#native-claude-cloud-only-p72) and [config](../CONFIGURATION.md#native-claude-runtime-p72--d048) describe current source; published alpha.2 predates Claude support.

## Accepted surface and evidence

| P7.2 requirement | Accepted implementation / evidence |
|---|---|
| Official authentication, launch, version and context checks | [PR #61](https://github.com/awesomejt/agent-harness/pull/61), [launch evidence](p7-2-claude-launch.md), D047–D048: official login, pinned stream-json runtime and full preflight; no credential inspection or proxying |
| Permission policy and cancellation | [PR #62](https://github.com/awesomejt/agent-harness/pull/62), [trusted evidence](p7-2-claude-trusted.md), D049: exact one-shot host grants, fixed offered tools, background-tool refusal and live SIGINT cleanup |
| Named primary/specialized role, model and effort | [PR #63](https://github.com/awesomejt/agent-harness/pull/63), [role evidence](p7-2-claude-agents.md), D050: tool intersection, body append, verified high effort, reviewer outside-read denial and independently checked coding |
| Sequences / Ralph and explicit recovery | [PR #64](https://github.com/awesomejt/agent-harness/pull/64), [workflow evidence](p7-2-claude-workflows.md), D051: real edits, verification, interruption and explicit retry; fresh preflight/session per attempt |
| Local-first fallback, preview and no replay | [PR #65](https://github.com/awesomejt/agent-harness/pull/65), [fallback evidence](p7-2-claude-fallback.md), D052: one eligible pre-submission fallback; no fallback after local launch, uncertain effects or submitted failure |
| Live project task and enforced constrained-role acceptance on final surface | Repeatable `scripts/tests/claude_live.py`, observations below; both cloud-only and eligible Claude fallback |

Reviewed starting baseline: `78001d21ace19fe8da15faead16a00a8b9a2594c` (main after PR #65). No runtime behavior, schema, dependency, version pin or routing policy changes in this closeout. Earlier evidence's incremental refusals are historical; D051/D052 and the capability matrix define the final supported surface.

## Fresh live acceptance

Platform: Apple Silicon `arm64`, macOS **27.0.1**. Toolchain: Rust **1.88.0**. Runtimes: Claude Code **2.1.314**, OpenCode **2.2.5**. Model: `sonnet`, canonical default effort. Authentication uses the operator's existing official CLI login (D047); neither the driver nor the harness inspects it. Runs consume the operator's plan or usage credits; no billing claim is made.

Command: `cargo build --locked`, then `python3 scripts/tests/claude_live.py`. Each execution makes four real model turns in a disposable git project. The final driver was run successfully after adding explicit runtime/version/model/role/route and protocol-violation assertions; an earlier four-turn trial passed before those assertions were added. No raw responses, account fields or credentials are retained in this record.

The project contains deliberately broken `add(a, b)` (subtracts), two independent arithmetic assertions in `test_calc.py`, the sample `reviewer` and `coder` roles, `AGENTS.md` requiring a response marker and an indexed sentinel with uncommitted operator content. The config is outside the project. A loopback socket is bound but does not listen, ensuring the fallback endpoint is unreachable without using a live LiteLLM service; its key is synthetic and unused. The driver verifies the tests fail before coding. The reviewer is asked to review, read an outside file using `Read` and write `REVIEW.md`; then the coder is asked to fix the bug and run the tests without changing tests, roles, instructions or sentinel. The bug is restored before the second route.

| Route / role | Seconds | Attempts | Host prompts / grants | Tool events | Observed effects |
|---|---:|---:|---:|---:|---|
| cloud-only reviewer | 8.2 | 1 | 1 / 0 | 6 | Outside-read prompt denied; response references `calc.py`; no changed files or `REVIEW.md` |
| cloud-only coder | 6.6 | 1 | 2 / 2 | 8 | Only `calc.py` changed; independent `python3 -B test_calc.py` passed |
| local-first reviewer | 13.4 | 2 | 1 / 0 | 6 | Same enforced denial and unchanged project |
| local-first coder | 11.2 | 2 | 2 / 2 | 8 | Only `calc.py` changed; independent arithmetic tests passed |

Every final attempt reported Claude 2.1.314, `sonnet`, the selected role, `end_turn`, success, no protocol violation and confirmed cleanup. Every response contained the `AGENTS.md` marker. Both fallback runs recorded OpenCode attempt 1 as neither launched nor prompt-submitted, followed by exactly one Claude attempt. File hashes before/after verify dirty sentinel, test, role and instruction preservation and the absence of managed OpenCode files. The two independent tests establish coding success beyond model prose or exit 0. Timings are observations, not performance estimates.

The cloud-only rows provide a comparison against the same official runtime through the supported native route; the fallback adds the pre-submission check and uses identical role/tool policy. Earlier [launch](p7-2-claude-launch.md), [trusted](p7-2-claude-trusted.md) and [role](p7-2-claude-agents.md) records own direct CLI/control probes. This closeout does not repeat a separate direct-CLI inference benchmark. Setup friction: `cargo` was absent from the session PATH, so local checks used `~/.cargo/bin/cargo`; no runtime installation, login repair or manual coding intervention was needed.

## Checks and limitations

`cargo fmt --check`, locked Clippy with warnings denied, locked build and `cargo test --locked` pass (134 Rust tests). The live driver passes all four cases. The full `python3 scripts/tests/offline.py` run passes **26/26** suites, including the 78-case Claude fixture, the 166-case mode matrix, OpenCode installed-runtime regressions, sequence/Ralph recovery and documentation links. Live inference is deliberately excluded from that runner. Python compilation and staged-diff whitespace checks also pass.

Supported scope and limits are explicit in the [capability matrix](../FRAMEWORKS.md#p72-claude-capability-matrix). Key limits remain: one exact CLI version and platform; trusted host privileges without an OS sandbox; real HOME/login shell snapshot; role body is visible in arguments, bounded to 128 KiB and not read back; non-default effort refuses in local-first because the primary is OpenCode; tool-dependent deny prompts may produce tool-shaped text or run to the deadline. Workflow resumes must repeat trusted permission, and Ralph requires its final-line marker. Missing login/model access or rate limits stop without retry. This closeout's live driver does not re-exercise cancellation, workflow recovery or effort; linked earlier live evidence and current fixtures cover them.

## Next boundary

On merge, P7.2 is complete. The next work is a recorded target selection for **one** of P7.3 Codex, P7.4 Grok or P7.5 Gemini, based on real-use need and installed integration readiness. None is implicitly activated here. No operating-system switch is required by this closeout; each selected adapter must establish its own supported interface/version and platform evidence. P7.6 portfolio audit waits for all four adapters, then P7.7 is the mandatory holistic Phase 7 review. Phase 7 remains open and optional Phase 9 work stays gated.

## PR review closeout

[PR #66](https://github.com/awesomejt/agent-harness/pull/66) received one completed automated Grok review, posted under the operator's account: **0 blockers, 2 concerns, 1 nit**. All three are addressed: the driver checks for its built binary before any runtime probe or fixture setup, explicitly checks that fallback attempt 1 is OpenCode, and reports failed runs with role/mode/exit, stdout byte count and at most 1,200 characters of the harness's own diagnostics (raw provider stderr remains withheld). Targeted injected failures verify missing-build early refusal, mislabeled-primary rejection and the diagnostic bound.

All four live cases pass again after these changes (cloud-only reviewer/coder: 8.0/6.1 s; local-first reviewer/coder: 13.7/11.8 s). The reviewed rerun has the same effects and counters as the table above except fallback coder tool events are 10 rather than 8; grants remain 2/2 and only `calc.py` changes. Python compilation, documentation links and whitespace checks pass. Rust and the offline runner's behavior are unchanged since the successful 134-test and 26-suite checks, so those suites were not repeated. No critical/high finding required a fix; no additional review is requested under the Git workflow and operator instruction. Acceptance takes effect on merge.
