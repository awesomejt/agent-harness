# Claude Opus holistic review — Phase 8

## Review scope

- **Reviewer/date:** Claude Opus 5.5 (Claude Code), 2026-11-13. This is an independent assessment. It is not the canonical `phase-08.md` and it does not record acceptance.
- **Review task:** P8.5 ([card](../../tasks/08-pi.md#p8-5)), branch `review/08-pi`.
- **Accepted entry baselines:** Phase 4 pass `53e1707` ([PR #43](https://github.com/awesomejt/agent-harness/pull/43)) for initial Pi work. Phase 6 pass `fe4e116` ([PR #58](https://github.com/awesomejt/agent-harness/pull/58)) for P8.4 workflow parity.
- **Reviewed source head:** `35777fb` (P8.4 merged, [PR #104](https://github.com/awesomejt/agent-harness/pull/104)). The branch head `99adf54` adds only [Grok's report](2026-11-12-grok-phase-8-holistic-review.md).
- **Included PRs:** the same set Grok lists: [#74](https://github.com/awesomejt/agent-harness/pull/74), [#78](https://github.com/awesomejt/agent-harness/pull/78), [#79](https://github.com/awesomejt/agent-harness/pull/79), [#93](https://github.com/awesomejt/agent-harness/pull/93), [#94](https://github.com/awesomejt/agent-harness/pull/94), [#96](https://github.com/awesomejt/agent-harness/pull/96), [#98](https://github.com/awesomejt/agent-harness/pull/98), [#100](https://github.com/awesomejt/agent-harness/pull/100), [#102](https://github.com/awesomejt/agent-harness/pull/102), [#104](https://github.com/awesomejt/agent-harness/pull/104). Status-only PRs: #95, #97, #99, #101, #103.
- **Mandatory scope:** P8.1–P8.4 and the P8.5 gate; D060, D064, D065 and D079–D084; the [IMPLEMENTATION Phase 8 exit criteria](../IMPLEMENTATION.md#phase-8--pi-and-portability). Mode, permission, fallback and D044/D045 recovery rules are regression constraints because Pi reuses `single::launch`.
- **Method:**
  - Read `src/pi.rs` in full and `src/pi_trusted_policy.mjs`, and checked them against the installed Pi 1.5.0 package (`@earendil-works/pi-coding-agent` and `pi-ai`).
  - Checked the parts of Pi the adapter relies on: path normalization in `utils/paths.js`, tool schemas, how extension `tool_call` errors are handled, the shape of the `agent_settled` event, how `openai-completions` maps stop reasons and errors, and the lookup of the `fd` and `rg` binaries.
  - Reproduced the policy results by calling `boundaryBlocked` next to Pi's own `resolveToCwd` on a temporary project.
  - Re-ran Grok's reproductions independently.
  - No new live inference.
- **Excluded:** fixes, merge, release, Phase 7 portfolio closure, subscription Pi, and the private-HOME redesign that Grok also excluded.

## Conclusion

**Changes required before Phase 8 acceptance.** I confirm all four of Grok's findings (G08-01 High, G08-02 Medium, G08-03 Low, G08-04 Low). This review adds one High and two Medium findings. There are no Critical findings.

- **Sound:** the adapter's lifecycle, route restriction, deny profile and workflow reuse. Pi blocks the tool call when an extension `tool_call` handler throws, so a policy-extension crash fails closed.
- **Weak:** the trusted-role project-root control.
  - It does not follow Pi's own path normalization order. Pi strips a leading `@` and then expands `~`, so `@~/…` reaches the home directory for read, write and edit (C08-01). This is a separate escape from Grok's `file://` case.
- **Other gaps:**
  - The adapter does not validate the final assistant outcome, which D060 requires (C08-02).
  - One of the six advertised trusted tools does not work on a standard Pi install (C08-03).

## Requirements and acceptance coverage

| Task / criterion | Assessment and evidence |
|---|---|
| P8.1 / D060 | Caller-owned RPC, LiteLLM-only, no session, resources disabled. Card met. **Exception C08-02:** D060's terminal rule says to validate the final assistant outcome as well as `agent_settled`, and the implementation checks only for non-empty text. |
| P8.2 / D064–D065, D079–D082 | Discovery, `--no-approve`, private `PI_CODING_AGENT_DIR` (mode 0700 through `mkdtemp`), synthetic provider with `${NAME}` key interpolation, deny `--no-tools`, trusted UI grants, and intersected `--tools` are implemented and covered by fixtures. **Exceptions: G08-01, G08-02, C08-01.** |
| P8.3 | Two live `pi_live.py` runs (reviewer and coder) are recorded. **Exceptions:** the boundary escapes (G08-01, C08-01) were not exercised live. The install requirements leave out `fd` and `rg` (C08-03), which the P8.3 card requires. |
| P8.4 / D084 | Seven fixture workflow cases. Fresh `single::launch` per step or iteration; D044/D045 apply. Card met on the fixture boundary that D084 accepted. C08-02 also affects sequence steps, because a truncated reply counts as a successful step. |
| IMPLEMENTATION Phase 8 exit | "Permitted route enforcement and documented capability limits" is not met while the path control has known escapes and the `find` limit is undocumented. P8.5 remains open. |

## Integrated assessment

### Architecture and ownership

I agree with Grok's assessment. `pi` sits behind `single::launch` with no second loop and no new crate dependency. Configuration rejects `runtime: pi` outside local-only. The enforcement path has three layers:

1. The launch argv (`--no-tools` or an intersected `--tools`, plus `--no-extensions` with only the harness `-e`).
2. The harness extension (kind gate, then project-root check, then `ctx.ui.confirm`).
3. The Rust `decide_ui`, which approves by tool kind only.

The Rust layer never re-checks the paths in the confirm message. This leaves the JavaScript project-root check as the only control on where a read-only or edit-only role's path tools can reach. Both High findings sit in that check.

### Routing, permissions and fallback

- **Routing:** route, mode and fallback refusals are correct and run before launch. The fallback refusal is in `supported`; the effort refusal is in `supports`.
- **Pi's handling of extension failures:** I checked installed 1.5.0. `AgentSession._beforeToolCall` re-throws handler errors as "Extension failed, blocking execution". `ExtensionRunner.emitToolCall` stops at the first `block`. A throwing or rejecting policy handler therefore blocks the tool.
- **Path check and Pi's path normalization:** the checks run in a different order from Pi's.
  - **Pi** (`normalizePath`): replace Unicode spaces, strip one leading `@`, expand `~` and `~/`, convert `file://`, then resolve against the cwd.
  - **Policy:** tests for `~` and `$HOME` before stripping `@`, does not handle `file://`, and then resolves. A leading `@~` passes the `~` test because the string starts with `@`. After the `@` is stripped, `~/x` is resolved as a relative path inside the project (C08-01).
  - **Where the policy is stricter:** it trims whitespace and rejects any `$HOME` substring, which Pi does not need. Those differences are harmless.
- **Bash scan:** Grok's G08-04 holds. I also found `cd / && cat etc/passwd` and a bare `cd && cat .zshrc`, which the scan does not block. D083 and the capability matrix already call the bash scan best-effort and not a sandbox, so I do not raise these separately. They are evidence that G08-04's fix should stay narrow and should not grow into a shell parser.

### Lifecycle and terminal classification

- **Pi's `agent_settled` event:** installed 1.5.0 emits only `{type: "agent_settled", aborted}` (`agent-session.js` `_emitAgentSettled`). It never carries `error` or `assistantText`, so `classify_event`'s error branch never fires on the pinned runtime.
- **How the harness decides success:** it rests only on whether the assembled assistant text is non-empty. `record_assistant_diagnostic` captures `stopReason`, but the code reads it only to explain an empty reply.
- **What Pi reports when a reply fails:** `pi-ai`'s `openai-completions` keeps the accumulated content when a stream fails (`stopReason: "error"`). It maps `finish_reason: length` to `stopReason: "length"` and `content_filter` to `"error"`.
- **Result:** a truncated or failed reply that streamed some text exits 0 (C08-02).
- **`aborted: true` without a harness abort:** this also maps to success. The case is unlikely, because only an abort RPC sets the flag and the harness is the only RPC client, but it is still unvalidated.

Cancellation, deadline abort, uncertainty after submission, rejection of a repeated UI id and refusal of `disposition: handled` are correct as Grok describes.

### State and environment

- **Environment:** the child gets a cleared environment containing only `HOME`, `PATH`, `PI_CODING_AGENT_DIR`, the named key, `USER`, `LOGNAME` and `TMPDIR`.
- **Private agent directory:** it holds no binaries. Pi's `getToolPath` looks in `getAgentDir()/bin` first, then on `PATH`, and `--offline` sets `PI_OFFLINE=1`, which skips the download. On a host where `fd` exists only in Pi's managed `~/.pi/agent/bin` (the official installer layout, and this host), `find` fails with "fd is not available and could not be downloaded" (C08-03). `grep` works here only because Homebrew `rg` is on `PATH`.
- **`XDG_DATA_HOME`:** the managed launcher script finds its own Node through `${XDG_DATA_HOME:-$HOME/.local/share}/pi-node`, and the cleared environment drops `XDG_DATA_HOME`. See the recommendations.

### Tests and evidence

I re-ran the suites on `35777fb` with Rust 1.88.0 and Node 24.14.0. All pass (see Verification for counts).

None of the suites covers:

- `file://`, `@~` or device paths in the policy.
- An assistant `stopReason` of `error` or `length` with partial text.
- A `find` call under the private agent directory.

`fake_pi.py` never emits a `stopReason`. The live runs used the six-tool coder and the reviewer role, and their record does not show a `find` call.

### Operations and documentation

I confirm G08-03. In addition, the [OPERATIONS Pi section](../OPERATIONS.md#pi-local-only-p83) and the [P8.3 capability matrix](../FRAMEWORKS.md#p83-pi-capability-matrix) list six trusted tools without saying that `find` and `grep` need `fd` and `rg` on the harness `PATH` (C08-03).

## Findings

IDs are local to this review. Severities follow [PHASE_REVIEW.md](../PHASE_REVIEW.md). All findings are open, and this review applied no fixes.

### Disposition of Grok's findings

| Grok ID | Grok severity | My assessment |
|---|---|---|
| G08-01 | High | **Confirmed.** Reproduced: `file:///etc/passwd` is not blocked, and neither is `@file:///etc/passwd`. Fix together with C08-01, because both come from the policy not resolving paths the way Pi does. |
| G08-02 | Medium | **Confirmed.** Agree with the severity: it spoofs protocol records, and no escape from the project root was shown. `/dev/fd/1` is already blocked as an outside path, so allowing only `/dev/null` is sufficient. |
| G08-03 | Low | **Confirmed.** Add the C08-03 tool-dependency text in the same documentation pass. |
| G08-04 | Low | **Confirmed.** Keep it Low and narrow. Other evasions such as `cd /` and a bare `cd` exist, and the documentation already scopes the bash scan as best-effort (D083). |

### New findings

| ID | Severity | Concrete issue / affected requirement | Proposed correction | Verification required |
|---|---|---|---|---|
| C08-01 | High | **`@~` paths escape the project-root check into the home directory.** `relativeInside` calls `pathUsesPiEscapeHatch` on the raw value, and that function checks `startsWith('~')`. It then strips `@` and resolves `~/…` as a relative path inside the project. Installed Pi 1.5.0 `normalizePath` strips `@` first and then expands `~`. On a real temporary project, `boundaryBlocked` returns false for `read {path:"@~/.zshrc"}`, `write {path:"@~/ah-probe.txt"}` and `ls {path:"@~"}`, while Pi's `resolveToCwd` resolves them to `$HOME/.zshrc`, `$HOME/ah-probe.txt` and `$HOME`. `~/.zshrc` without the `@` is blocked. A read-only reviewer can read home-directory files. A trusted edit role can write shell startup files, which means code execution at the operator's next login. This breaks the outside-path control that P8.3 accepted and the D060 external-path requirement, independently of G08-01. | Replace the bespoke checks with one function that reproduces Pi 1.5.0 `normalizePath` in its order: Unicode spaces, then one `@`, then `~` and `~/`, then `file://`, then resolve against the project. Apply the existing realpath inside-root check to the result. Fail closed on anything that function cannot convert. Fix it in the same patch as G08-01. | Policy cases are blocked for `@~`, `@~/x`, `@file:///etc/passwd` and the G08-01 URLs, while `@src/x` and in-project paths stay allowed. Add a differential test that runs a fixed path corpus through both `boundaryBlocked` and the installed Pi `resolveToCwd` (skipped when Pi is absent) and asserts that every path resolving outside the project is blocked. `node --test scripts/tests/pi_policy_boundary.mjs` passes. **Open.** |
| C08-02 | Medium | **A truncated or failed model reply exits 0.** D060 requires validating the "final assistant outcome plus `agent_settled`". The pinned runtime's `agent_settled` carries only `aborted`, and `attempt` treats any non-empty assembled text as success. `pi-ai` keeps partial content with `stopReason: "error"` on stream failure, `"length"` on truncation and `"error"` on `content_filter`. Such a reply is delivered as success. In a sequence it advances the step, unlike the Claude adapter, which requires `end_turn` (D048). An `agent_settled` with `aborted: true` that the harness did not request also maps to success. | Track the stop reason of the last assistant message. Succeed only when it is `stop` (or `end_turn`) and `aborted` is false. Map `error`, `length` and `aborted` to exit 1 with the sanitized reason the code already builds. Record the rule in an addendum to D083. | Add `fake_pi.py` modes for partial text plus `stopReason: "error"`, partial text plus `"length"`, and `aborted: true` without a harness abort. Each exits non-zero. The existing success cases still pass. `pi.py` passes. **Open.** |
| C08-03 | Medium | **`find` does not work under the private agent directory on a standard Pi install, and the requirement is undocumented.** Pi's `getToolPath` checks `getAgentDir()/bin`, which is the empty private directory, and then `PATH`. `--offline` disables the download. With the operator's `PATH` and a fresh `PI_CODING_AGENT_DIR`, `ensureTool("fd")` returns undefined on this host ("Offline mode enabled, skipping download"). It finds `~/.pi/agent/bin/fd` only with the default agent directory. `rg` works here only because Homebrew provides it. The P8.3 card requires documenting install requirements, and D081 advertises six working trusted tools. | Choose and record one approach. (a) Document `fd` and `rg` on the harness `PATH` as a Pi trusted-tool prerequisite and report them in `--preview`. (b) Remove `find` and `grep` from the active `--tools` set when their binaries cannot be resolved, and say so in the progress output. Do not copy or link files from `~/.pi/agent` into the private directory without a D065 decision. | A `pi.py` case, or a recorded live check, shows the chosen behavior with `fd` missing from `PATH`. OPERATIONS and the capability matrix name the dependency. `doclinks.py` passes. **Open.** |

## Recommendations (not defects)

- **Defense in depth in Rust:** `decide_ui` already receives the tool input. Have it apply the same project-root check before granting, so a single JavaScript policy bug cannot open the home directory. This would also close the D083 limit that read-only ceilings, unlike Claude's D050 behavior, do not deny every out-of-project grant.
- **`XDG_DATA_HOME`:** pass it through, or document that the managed Pi launcher needs Node on `PATH` or at `$HOME/.local/share/pi-node` when the variable is cleared.
- I agree with Grok's recommendations on requiring `piVersion` and both tool inventories at the next pin change, and on setting `cacheWarming` to `off`.

## Verification and integrated recheck

**Environment:** Apple Silicon macOS, Rust 1.88.0, Node 24.14.0, installed Pi 1.5.0. Source `35777fb`; branch head `99adf54`. No provider traffic.

**Suites run:**

| Check | Result |
|---|---|
| `cargo test --locked` | 150 passed (49 library, 101 integration) |
| `cargo fmt --check` | Clean |
| `cargo clippy --locked --all-targets -- -D warnings` | Clean |
| `node --test scripts/tests/pi_policy_boundary.mjs` | 8/8 passed |
| `python3 -B scripts/tests/pi.py` | 41/41 passed |

**Reproductions** (scratch script outside the repository, using `boundaryBlocked` and Pi's `resolveToCwd` on a temporary project):

| Input | Policy | Pi resolves to |
|---|---|---|
| `read @~/.zshrc` | not blocked | `$HOME/.zshrc` |
| `write @~/ah-probe.txt` | not blocked | `$HOME/ah-probe.txt` |
| `ls @~` | not blocked | `$HOME` |
| `read @file:///etc/passwd` | not blocked | `/etc/passwd` |
| `read ~/.zshrc` | blocked | — |
| `bash cat /etc/passwd` | blocked | — |
| `bash cd / && cat etc/passwd` | not blocked | — |

The `ensureTool` check ran in a cleared environment with the operator `PATH` and `PI_OFFLINE=1`. With a fresh `PI_CODING_AGENT_DIR`, `fd` was undefined and `rg` resolved to `rg`. With the default agent directory, `fd` resolved to `~/.pi/agent/bin/fd`.

**Source reads:** the following were confirmed by reading installed Pi 1.5.0:

- `tool_call` handler errors block the tool.
- `agent_settled` is `{type, aborted}` only.
- `openai-completions` keeps partial content when a stream errors.

**Not re-run:** `offline.py`, `pi_live.py`, `doclinks.py`. No published-archive install or other platform was checked.

## Gate outcome and handoff

**Changes required for the Phase 8 scope at `35777fb`. P8.5 remains open.**

When the canonical `docs/reviews/phase-08.md` is opened, record these findings alongside Grok's.

Fix G08-01 and C08-01 together, because they share one cause: the policy does not resolve paths the way Pi does. Put that fix and the other open findings in `patch/` PRs with `/grok review`, one PR open at a time (D042).

The patch that resolves the last finding records verification and the integrated recheck, and then proposes the pass. The P8.3 outside-read live scenario should be repeated with `@~` and `file://` prompts after the fix.
