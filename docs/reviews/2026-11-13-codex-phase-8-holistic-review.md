# Codex holistic review — Phase 8

## Review scope

- **Reviewer/date:** Codex, 2026-11-13 (America/Denver).
- **Task/branch:** [P8.5](../../tasks/08-pi.md#p8-5), shared `review/08-pi` branch / [PR #105](https://github.com/awesomejt/agent-harness/pull/105). This is an independent assessment alongside [Grok's](2026-11-12-grok-phase-8-holistic-review.md) and [Claude's](2026-11-13-claude-opus-phase-8-holistic-review.md). It is not the canonical `phase-08.md` or phase acceptance.
- **Accepted entry baselines:** Phase 4 `53e1707` ([PR #43](https://github.com/awesomejt/agent-harness/pull/43)) for initial Pi work; Phase 6 `fe4e116` ([PR #58](https://github.com/awesomejt/agent-harness/pull/58)) for workflow parity.
- **Reviewed implementation:** `35777fb0db0b0213b9eda23b36f50d08e055efcb`, P8.4 merged. Phase 8 changes are interleaved with independent Phase 7 work; the Pi implementation range starts at `680eb13..35777fb`, with the earlier accepted routing, permission, process, sequence and Ralph implementation also inspected where consumed. Starting review-branch head `efcad82bf2ed5d98dbd769e40d98997b45448015` differs from that material head only by the two other review reports.
- **Included implementation/evidence PRs:** [#74](https://github.com/awesomejt/agent-harness/pull/74), [#78](https://github.com/awesomejt/agent-harness/pull/78), [#79](https://github.com/awesomejt/agent-harness/pull/79), [#93](https://github.com/awesomejt/agent-harness/pull/93), [#94](https://github.com/awesomejt/agent-harness/pull/94), [#96](https://github.com/awesomejt/agent-harness/pull/96), [#98](https://github.com/awesomejt/agent-harness/pull/98), [#100](https://github.com/awesomejt/agent-harness/pull/100), [#102](https://github.com/awesomejt/agent-harness/pull/102), [#104](https://github.com/awesomejt/agent-harness/pull/104). Status-only PRs #95, #97, #99, #101 and #103 are part of the traceability check.
- **Coverage:** mandatory P8.1–P8.4 and P8.5; G5/G8 and F10, with F13–F18 and AC01–AC11 as applicable regression constraints; D060, D064/D065, D079–D084; [Phase 8 exit evidence](../IMPLEMENTATION.md#phase-8--pi-and-portability). D024/D031/D034/D039 and D043–D045 remain shared outcome, safety and recovery contracts.
- **Method:** inspected the complete Pi adapter and policy extension, configuration/single/preview integration, workflow reuse, fixtures, decisions, task cards, capability/operations/testing text and P8 evidence. Compared path resolution and actual read/write behavior with installed Pi 1.5.0 modules. Exercised additional cases through the public CLI with disposable fake runtimes and synthetic keys/files. Re-ran Rust and offline checks as recorded below.
- **Boundary:** review and report only. No fixes, status changes, phase pass, merge or release. No new live inference, provider login or real credential-store inspection. Subscription Pi, Phase 7 closure, additional platforms and a private-HOME redesign are outside this review's implementation scope.

## Outcome

**Changes required.** I confirm the seven findings in the existing reports and add **three High and two Medium findings**. Taken together, the independently assessed set has **five High, five Medium and two Low findings**, with none Critical. All remain open.

The integration shape is sound: Pi owns its coding loop, local-only routing remains explicit, roles intersect tools, and sequences/Ralph reuse fresh single runs. The main acceptance gaps are the incomplete filesystem boundary and the ability of a configured key-variable name to become a child-process control. Additional outcome, deadline, diagnostic and installation gaps need correction before P8.5 can pass.

## Requirements and integrated assessment

| Area | Assessment and evidence |
|---|---|
| P8.1 / integration decisions | D060 selects caller-owned RPC, explicit LiteLLM routing, disabled resources, direct canonical roles and model-default effort. The transport and capability choices are implemented. Final-outcome validation is incomplete (C08-02), and arbitrary credential-variable names undermine the environment boundary (X08-03). |
| P8.2 / Rust architecture and ownership | `pi` is behind `single::launch`; no second coding loop or new crate dependency. It owns private state, argv/environment, RPC preflight, extension grants and terminal classification. `config` rejects Pi cloud-only/local-first configurations and overrides. `single` refuses unsupported effort/fallback before launch and skips OpenCode project sync for Pi. Existing routing and project-configuration regression checks pass. |
| Permission and resource policy | Deny uses `--no-tools` plus a blocking extension. Trusted maps the intersected built-ins to canonical kinds and answers request-bound allow-once UI confirmations; duplicate UI IDs fail. The JavaScript boundary is the sole path check before Rust grants by tool kind. It misses URL/home forms, dangling symlinks and Pi's read fallback (G08-01, C08-01, X08-01, X08-02), and allows protocol devices (G08-02). Bash remains a documented host shell with a best-effort scan, including the narrow G08-04 defect. |
| P8.3 / actual use and support limits | [Acceptance evidence](../evidence/p8-3-pi-acceptance.md) records two real coder/reviewer runs on 2026-11-12, preserving project sentinels and passing independent coder tests. Those runs establish the ordinary task path, not the bypass cases reproduced here. Installed Pi 1.5.0 read/write modules reproduce both new filesystem findings without a model call. Required `fd`/`rg` availability is incompletely documented (C08-03). |
| P8.4 / workflow parity | [D084 evidence](../evidence/p8-4-pi-workflows.md) explicitly accepts seven fixture cases with live workflows opt-in. Each step/iteration gets a fresh single run, `pi/MODEL` identity and `agent_settled` record. D044/D045 explicit retry/accept, snapshots, verification and shared locking remain in use. C08-02 can incorrectly advance a sequence; X08-04 can unnecessarily stop either workflow as uncertain. |
| Lifecycle, state and recovery | `mkdtemp` creates a private per-attempt agent directory and drop removes it. Bounded JSONL/output, UI identity checks and common process-group cleanup are present. Lost completion after submission remains uncertain and is not automatically replayed. However, the environment can replace the private-state path before startup (X08-03); quiet work has an undocumented 30-second cutoff (X08-04); and failure diagnostics can expose provider text (X08-05). |
| Tests and live evidence | Rust and current Pi fixtures pass despite these reproductions. Existing boundary tests cover an already-resolvable outside symlink, but not a dangling one or a runtime-selected filename variant. The fake runtime omits normal final stop reasons and does not exercise long quiet success, key-name collisions or a provider-error secret canary. No new live evidence or post-fix recheck is claimed. |
| Platforms, installation and documents | Supported production evidence remains Apple Silicon macOS 27.0.1 / Rust 1.88.0 / Pi 1.5.0. No Linux, Windows, Intel, published archive or pin-upgrade validation was performed. Current capability documentation and runtime dependency diagnostics need the G08-03/C08-03 corrections. Phase 7 resource/login proofs do not establish Pi production sandboxing; trusted retains host privileges. |

## Existing findings: independent disposition

IDs below retain their original reviewer and severity. Each is **confirmed/open** and must be included in the canonical report; the linked original reports carry their detailed remediation plans.

| Finding | Severity | Independent evidence and required disposition |
|---|---|---|
| G08-01 | High | `boundaryBlocked` allows `file:///etc/passwd`, while installed Pi `resolveToCwd` resolves it outside the project. No outside operator file was read. Align normalization with the pinned runtime and test outside/inside URLs. |
| G08-02 | Medium | `/dev/stdout` and `/dev/stderr` are accepted by the path policy, including for write. Code inspection confirms the adapter parses child stdout as protocol JSONL. Remove those device exceptions and test all path tools; preserve the narrowly required `/dev/null` behavior. No protocol injection into a live Pi process was attempted. |
| G08-03 | Low | FRAMEWORKS still says passing live runs and P8.4 are pending; docs/README still lists P8.4 as gated; DESIGN's concrete module mapping omits Pi. Bring current contract/operation text into agreement with D083/D084 while retaining historical evidence. |
| G08-04 | Low | `boundaryBlocked(root, 'bash', {command: 'cat //etc/passwd'})` returns false. The scan explicitly skips `//`. Remove that exception and retain the documented best-effort shell boundary. |
| C08-01 | High | `@~/.zshrc` is accepted by the policy but resolves to the operator home with installed Pi's `resolveToCwd`. Correct normalization order together with G08-01. No operator startup file was opened. |
| C08-02 | Medium | Disposable public-CLI fixtures with partial assistant text and `stopReason: error` or `length` both exit 0; `agent_settled.aborted: true` without a harness interrupt also exits 0. Validate the actual final outcome and add failure/sequence cases. Any diagnostic changes must also satisfy X08-05. |
| C08-03 | Medium | In a cleared environment with fresh `PI_CODING_AGENT_DIR`, `PI_OFFLINE=1` and the operator PATH, installed `ensureTool('fd')` returns undefined; `ensureTool('rg')` returns `rg`. Source confirms private `bin` lookup, then PATH, with no offline download. Document/check dependencies or explicitly narrow the offered tools, as proposed in Claude's report. |

## New findings and remediation

IDs are local to this Codex review. Severities follow [PHASE_REVIEW.md](../PHASE_REVIEW.md). Proposed corrections are plans, not implemented fixes.

### X08-01 — High: dangling symlinks bypass the write boundary

**Affected:** P8.2/P8.3 project-root enforcement; [policy](../../src/pi_trusted_policy.mjs), `relativeInside`, lines 48–59.

`existsSync` follows symlinks. For an in-project symlink whose outside target does not exist, it returns false. The fallback walk discards the symlink component, finds the existing project directory and concludes that the path is inside. Pi's write tool subsequently follows the symlink and creates the outside target.

**Reproduction:** in an owned temporary tree, create `project/link.txt -> ../outside-created.txt` with the target absent. `boundaryBlocked(root, 'write', {path: 'link.txt'})` returns false. Calling installed Pi 1.5.0 `createWriteToolDefinition(root).execute` with that path creates `outside-created.txt` alongside the project. The outside file contained the synthetic content supplied by the test. This uses an ordinary relative path, no race, bash, URL or tilde. An edit-capable role can cross the boundary through a pre-existing repository symlink, so the G08-01/C08-01 normalization fixes alone are insufficient.

**Correction/task:** in a linked `patch/` PR, distinguish absent components from symlink entries using `lstat`/`readlink`; safely resolve the entire symlink chain including missing final targets, or refuse unresolved symlinks. Preserve ordinary new in-project files. Keep the documented host-policy/race limitations explicit.

**Verification required:** relative and absolute dangling symlinks, chained links and missing outside targets are blocked before a UI grant; an existing outside symlink remains blocked; creating a regular in-project file still succeeds. Exercise the installed write tool against synthetic fixtures and add policy regressions. **Disposition: open.**

### X08-02 — High: Pi read fallback selects a different, unchecked symlink

**Affected:** P8.2/P8.3 constrained reviewer reads; [policy](../../src/pi_trusted_policy.mjs), `relativeInside`; installed Pi `core/tools/path-utils.js` and `read.js`.

Pi's read tool uses `resolveReadPathAsync`, which tries filename variants after the requested path is absent, including replacing a straight apostrophe with a curly apostrophe. The policy checks only the original filename. Consequently an apparently missing inside path can select an existing outside-pointing symlink that was never checked.

**Reproduction:** create an owned outside text file and `project/curly’name` as a symlink to it, leaving `project/curly'name` absent. For `{path: "curly'name"}`, `boundaryBlocked(root, 'read', input)` returns false. Installed `createReadToolDefinition(root).execute` returns the synthetic outside file's content. The already-existing symlink would be blocked if requested directly. This is a demonstrated read-only reviewer escape with no shell or concurrent mutation.

**Correction/task:** extend the path-alignment remediation to the read tool's actual fallback resolution, not only `resolveToCwd`. Validate the final runtime-selected candidate against the root, or fail closed whenever an absent request might select an unchecked variant. Account for the pinned AM/PM, Unicode-normalization and combined variants as well as curly quotes.

**Verification required:** the synthetic curly-quote/symlink read is blocked before granting; cover each supported fallback candidate, positive in-project reads and normal nonexistent-file errors. Include a differential check using installed `resolveReadPathAsync` or the read definition. **Disposition: open.**

### X08-03 — High: a key-variable name can override runtime controls

**Affected:** D060/D065 exclusive private state and allowlisted authentication; [Pi environment construction](../../src/pi.rs), lines 152–180, and private provider configuration.

`api_key_env` accepts any syntactically valid variable name. Pi's `environment` first sets the private `PI_CODING_AGENT_DIR`, then appends the selected credential under its original name. Selecting `PI_CODING_AGENT_DIR` overwrites the owned path with the inherited value. Selecting `NODE_OPTIONS` instead passes that value to Node as a startup control. This differs from [OpenCode setup](../../src/runtime.rs), which explicitly remaps arbitrary credential names to a reserved name so they cannot become runtime controls.

**Reproduction:** use the public CLI with synthetic configuration, environment and fake runtimes. With `api_key_env: PI_CODING_AGENT_DIR`, the child observes an owned synthetic external state directory instead of `PreparedState`'s private one; preflight and the turn exit 0. In a separate Node-backed fixture, `api_key_env: NODE_OPTIONS` with a synthetic `--require` preload executes the marker-writing preload before RPC preflight, even under default deny, and the turn exits 0. This demonstrates the actual child-environment assembly. It does not claim that a real credential store was opened or that installed Pi was launched with an injected preload.

**Impact:** D065's settings/auth exclusion can be lost before effective-state validation. Node loader behavior can execute outside the intended resource/deny controls before the policy extension exists. A project config can select a control variable already present in the operator environment; this does not require model-controlled environment mutation.

**Correction/task:** mirror the established OpenCode boundary: read the selected value in the harness, expose it under a fixed harness-owned credential variable, and reference only that fixed variable from `models.json`. Do not forward the arbitrary original name. Keep the private-state/control environment authoritative.

**Verification required:** `PI_CODING_AGENT_DIR`, `NODE_OPTIONS`, `HOME`, `PATH` and loader-variable credential names either reject before launch or are safely remapped; external state/preload markers remain untouched; the private model interpolation receives the synthetic credential and normal keys still work. Add both environment-unit and public-CLI regressions. **Disposition: open.**

### X08-04 — Medium: quiet agent work is killed after 30 seconds

**Affected:** P8.2 lifecycle and P8.4 workflow parity; [Pi turn loop](../../src/pi.rs), lines 903–946.

Every post-submission `records.recv()` has a deadline of `min(request deadline, now + 30s)`. An idle timeout before the request deadline returns `Outcome::Failed`, then exit 4 because the prompt was submitted. There is no Pi heartbeat requirement establishing that 30 seconds without a JSONL event means failure. Waiting for a slow model's first event or a quiet tool can therefore fail far earlier than the requested coding budget.

**Reproduction:** modify the disposable fake runtime to acknowledge `prompt` immediately, wait 32 seconds and then emit its ordinary successful response/settled records. `ah single ... --timeout-secs 60` instead exits 4 after **30.3 seconds**, before the successful terminal can be sent. Cleanup terminates the child. Automatic replay is correctly avoided, but legitimate work is interrupted and workflow progress stops.

**Correction/task:** retain bounded preflight/acknowledgement waits, but let an active turn wait until the invocation deadline or cancellation. If progress needs a timer, emit a harness heartbeat and continue waiting without resetting or shortening the invocation deadline. Preserve bounded abort/cleanup and uncertainty on an actually lost terminal.

**Verification required:** a healthy >30-second quiet fixture succeeds inside a longer deadline; a shorter invocation deadline still cancels/stops correctly; signal and EOF cases retain their existing semantics. Cover a workflow consumer and use controlled time where practical. **Disposition: open.**

### X08-05 — Medium: provider failure text can leak into diagnostics

**Affected:** D039 / documented withholding of raw provider errors; [Pi diagnostic collection/output](../../src/pi.rs), lines 564–595 and 1082–1090.

For `stopReason: error`, `record_assistant_diagnostic` stores the assistant's `errorMessage`. `sanitize_stop_detail` only removes control characters, normalizes whitespace and truncates to 160 characters; it does not withhold provider text or redact credentials. An empty settled reply then prints that raw message as `stopReason=...` on stderr. The shared [execution contract](../EXECUTION.md) says raw provider errors are withheld.

**Reproduction:** in the public-CLI fake-runtime fixture, return an assistant message with empty content, `stopReason: error` and `errorMessage: "provider-debug synthetic-secret-canary"`, followed by non-aborted `agent_settled`. Set the synthetic key to that canary. The harness exits 1 and writes the complete canary to human stderr. No real secret was used. A provider error that echoes authentication/request details can therefore put those details into collected logs.

**Correction/task:** report an allowlisted terminal category or fixed diagnostic, withholding arbitrary `errorMessage` text. Apply this rule to the C08-02 outcome correction as well; character sanitization alone is insufficient. Do not substitute a full backend error into machine results or persistent records.

**Verification required:** secret-canary/provider-debug strings never appear in stderr, machine diagnostics or workflow records for empty and partial error outcomes; a safe reason and nonzero exit remain visible. **Disposition: open.**

## Verification and integrated recheck

Host: Apple Silicon `arm64`, macOS **27.0.1**, Rust **1.88.0**, Node **24.14.0**, installed Pi package **1.5.0**. All checks used the unchanged implementation at `35777fb` with the two report-only commits above it. Initial shell PATH omitted Cargo; Rust commands used `/Users/jason/.cargo/bin` explicitly.

| Check | Result |
|---|---|
| `cargo test --locked` | **150 passed:** 49 library and 101 integration tests. |
| `cargo build --locked` | Passed. |
| `cargo fmt --check` | Passed. |
| `cargo clippy --locked --all-targets -- -D warnings` | Passed. |
| `node --test scripts/tests/pi_policy_boundary.mjs` | **8/8 passed**, despite the additional reproduced cases. |
| `python3 -B scripts/tests/offline.py` | **36/36 suites passed**, including all **41 Pi runtime/workflow cases**, policy tests, other runtime fixtures and sequence/Ralph regressions. |
| `python3 -B scripts/tests/doclinks.py` | Passed on the starting tracked documents; repeated including this report before commit. |
| Installed-tool synthetic checks | Outside creation through dangling symlink and outside read through filename-fallback symlink both reproduced with actual Pi tool definitions. No model or operator-file access. |
| Additional public-CLI fixtures | External-state override and Node preload both exit 0; partial error/length and unsolicited aborted terminal all exit 0; quiet turn exits 4 at 30.3s despite 60s budget; provider-error canary appears in stderr on exit 1. |

The additional fixtures lived outside the repository and were removed after their runs; only this report is added. Reproduction recipe for the new filesystem cases: import `boundaryBlocked` from `src/pi_trusted_policy.mjs`, and `createWriteToolDefinition` / `createReadToolDefinition` from the installed package's `dist/core/tools/{write,read}.js`; construct the temporary symlinks described above, check the policy and invoke `.execute(id, input)` directly. All outside paths in those checks remain inside the owned temporary tree. For the CLI cases, retain the existing `fake_pi.py` state/acknowledgement protocol and change only the child environment capture, session-text stop reason, delay or error payload described in each finding.

**Not performed:** new `pi_live.py` inference, live sequence/Ralph, provider/login checks, published-archive installation or other platform validation. Existing dated P8.3 live evidence was assessed, not recreated. There are no fixes to recheck in this review.

## Gate outcome and handoff

**Changes required for Phase 8 at `35777fb`; P8.5 remains open.** Record all twelve findings, their dispositions and correction/verification plans in the canonical `docs/reviews/phase-08.md` when it is created. PROJECT.md remains the status owner.

Under D042, the review PR can merge after findings and plans are recorded; its merge does not accept Phase 8. Put corrections in linked `patch/` PRs, one open PR at a time, with explicit `/grok review` and the existing three-review limit. A practical remediation order is:

1. Close the credential/control environment boundary (X08-03) and the complete path-resolution boundary (G08-01, C08-01, X08-01, X08-02, G08-02, G08-04), with negative and positive installed-tool fixtures.
2. Correct final-outcome classification and diagnostic withholding together (C08-02, X08-05), then active-turn waiting (X08-04).
3. Resolve the tool dependency behavior and current-contract drift (C08-03, G08-03).

Repeat the affected P8.3 constrained-role live scenario with the corrected path cases, retain the existing workflow/recovery regressions, and record integrated verification. The patch resolving the last finding may propose the pass only after all severities are resolved and required evidence/reviews/merges are complete. No dependent phase may consume an unaccepted Phase 8 baseline.
