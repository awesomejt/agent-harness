# Grok holistic review — Phase 8

## Review scope

- **Reviewer/date:** Grok, 2026-11-12 (America/Denver).
- **Review task:** P8.5 ([card](../../tasks/08-pi.md#p8-5)). Branch `review/08-pi`. This is an independent assessment. It is not the canonical `phase-08.md` and it does not record acceptance.
- **Accepted entry baselines:** Phase 4 pass `53e1707` ([PR #43](https://github.com/awesomejt/agent-harness/pull/43)), which initial Pi work may follow, and Phase 6 pass `fe4e116` ([PR #58](https://github.com/awesomejt/agent-harness/pull/58)), which P8.4 workflow parity requires. **Reviewed head:** `35777fb` (P8.4 merged, [PR #104](https://github.com/awesomejt/agent-harness/pull/104)). Phase 8 commits are interleaved with Phase 7; this review covers the Pi deliverables and their use of the existing single-run, sequence, and Ralph paths. Pi-specific sources, probes, and `docs/evidence/p8-*` from the parent of PR #74 through `35777fb`: 20 files, +3855.
- **Included PRs:** [#74](https://github.com/awesomejt/agent-harness/pull/74) P8.1 RPC decision (D060); [#78](https://github.com/awesomejt/agent-harness/pull/78) installed discovery (D064); [#79](https://github.com/awesomejt/agent-harness/pull/79) project-trust and auth precedence (D065); [#93](https://github.com/awesomejt/agent-harness/pull/93) resource inventory and HTTP trap (D079); [#94](https://github.com/awesomejt/agent-harness/pull/94) deny-profile launch (D080); [#96](https://github.com/awesomejt/agent-harness/pull/96) trusted extension UI grants (D081); [#98](https://github.com/awesomejt/agent-harness/pull/98) named roles (D082); [#100](https://github.com/awesomejt/agent-harness/pull/100) live driver (D083); [#102](https://github.com/awesomejt/agent-harness/pull/102) project-root trust boundary; [#104](https://github.com/awesomejt/agent-harness/pull/104) sequence/Ralph fixture parity (D084). Status-only [#95](https://github.com/awesomejt/agent-harness/pull/95), [#97](https://github.com/awesomejt/agent-harness/pull/97), [#99](https://github.com/awesomejt/agent-harness/pull/99), [#101](https://github.com/awesomejt/agent-harness/pull/101), and [#103](https://github.com/awesomejt/agent-harness/pull/103).
- **Mandatory scope:** P8.1–P8.4 and the P8.5 gate; D060, D064, D065, D079–D084; the [IMPLEMENTATION Phase 8 exit criteria](../IMPLEMENTATION.md#phase-8--pi-and-portability). Mode, permission, fallback, and D044/D045 recovery rules are regression constraints because Pi reuses `single::launch`.
- **Method:** Read `src/pi.rs`, `src/pi_trusted_policy.mjs`, the Pi branches of `config`/`single`/`preview`, the P8 evidence and decisions, and the current capability/operations/configuration text. Compared the path policy with installed Pi 1.5.0 `resolvePath` and `getAgentDir`. Reproduced `boundaryBlocked` against a real temporary project. Ran the locked Rust suite and `pi_policy_boundary.mjs` on this host. No new live inference.
- **Excluded:** fixes, merge, release, Phase 7 portfolio closure, subscription Pi, and a private-HOME redesign beyond the D065 agent-directory boundary.

## Conclusion

**Changes required before Phase 8 acceptance: one High, one Medium, and two Low findings.** No Critical finding. The route shape holds: `litellm.runtime: pi` is local-only, cloud-only and local-first are rejected, non-default effort is refused, and sequence/Ralph each launch a fresh Pi single run. Deny stays on `--no-tools`. Trusted grants are one extension-UI confirm per call through the shared permission policy. Live P8.3 coder/reviewer runs are recorded. The project-root check added in PR #102 does not implement Pi's `file://` resolution, so a read/search role can still name files outside the project.

## Requirements and acceptance coverage

| Task / criterion | Assessment and evidence |
|---|---|
| P8.1 / D060 | Caller-owned `pi --mode rpc --no-session`, LiteLLM-only, canonical roles as direct invocations, skills/MCP/context disabled, model-default effort only. Card met. Subscription clients stay out. |
| P8.2 / D064–D065, D079–D082 | Installed 1.5.0 discovery, `--no-approve`, private `PI_CODING_AGENT_DIR`, synthetic `ah-litellm` provider, deny launch, trusted UI grants, and intersected `--tools` are implemented. Auth files follow `getAgentDir()`, which honors `PI_CODING_AGENT_DIR`, so a fresh directory does not load `~/.pi/agent/auth.json`. **Exception: G08-01.** |
| P8.3 | Two passing `pi_live.py` runs on 2026-11-12 cover reviewer and coder on the operator proxy ([acceptance](../evidence/p8-3-pi-acceptance.md)). Ordinary absolute outside reads are blocked. **Exception: G08-01**, which the live prompt did not exercise. |
| P8.4 / D084 | Seven fixture cases cover deny/trusted sequence, uncertain step, preview, Ralph completion, cancel/resume, and local-first refusal. Live sequence/Ralph runs stay opt-in under D084. Card met on that recorded boundary. |
| IMPLEMENTATION Phase 8 exit | Single-run tasks, route refusal, and documented limits exist. Workflow parity is fixture evidence. The project-root control for path tools is incomplete (**G08-01**). P8.5 is still the closeout. |

## Integrated assessment

### Architecture and ownership

`pi` is a macOS adapter behind `single::launch`. It owns argv, the private agent directory, RPC preflight, extension-UI grants, and `agent_settled` classification. `config` accepts `litellm.runtime` of `opencode` or `pi` and rejects `pi` outside local-only, including a mode override. `prepare_plan` does not sync `opencode.json` for Pi. No new crate dependency. Sequence and Ralph did not grow a second loop.

The child environment keeps the operator `HOME` and sets `PI_CODING_AGENT_DIR` to a new temporary directory that holds `models.json`, `settings.json`, and the policy extension. Installed 1.5.0 `getAgentDir()` uses that variable before `~/.pi/agent`. The API key is passed only as the named environment variable, and `models.json` stores the `${NAME}` interpolation.

### Routing, permissions, and fallback

Local-only Pi keeps the LiteLLM alias, `api_base`, and key name. Records use `pi/MODEL`. `supported` refuses a configured fallback before launch. Usage is reported unknown, which D060 allows when the provider report is not mapped.

Deny passes `--no-tools` and a block-all extension, and a `tool_call` event after that is an uncertain violation. Trusted passes the six built-in names that survive `grantable`, or `--no-tools` when the intersection is empty. The extension blocks kinds outside `AH_PI_GRANTABLE`, then `decide_ui` grants one allow-once for a matching kind. Duplicate UI ids fail closed. Non-default effort never launches.

The project-root check is the specialized-role control. It blocks `~`, `$HOME`, a leading `@`, `..`, symlinks, and ordinary absolute paths. It does not apply Pi's `file://` conversion (**G08-01**). It also treats `/dev/stdout` and `/dev/stderr` as safe for every path tool (**G08-02**). Trusted bash remains a host shell; the bash scan is best-effort and skips `//` paths (**G08-04**).

Preflight requires idle state, compaction off, retry not enabled, the synthetic provider/model/base URL, and empty MCP when inventories are present. Deny refuses missing tool inventories. Trusted may continue when both inventories are omitted, which D083 recorded for installed 1.5.0, with argv and the extension as the remaining controls. `piVersion` is checked only when Pi sends it.

### State, cancellation, and recovery

Each attempt uses a new agent directory, removed on drop. Prompt bytes are marked submitted before the response is required. A missing terminal after submit, a protocol violation, or failed cleanup becomes uncertain, so sequence/Ralph will not silently replay. Cancellation and the deadline send `abort`. Empty `agent_settled` text is a failure. `disposition: handled` is a failure. Workflow records reuse D044/D045, including the binding check identity. Resume still needs `--permissions trusted` when the step needs tools; OPERATIONS states that.

### Tests and evidence

`pi.py` has 41 cases on the P8.4 record. `pi_policy_boundary.mjs` has 8 cases and passes here; none use a `file://` path or a double-slash bash token. On `35777fb`, Rust 1.88.0, `cargo test --locked` passed 150 tests (49 library, 101 integration). The policy reproduction below is outside that suite. P8.3's two live runs are the required single-run model evidence. This review did not repeat them and did not run `offline.py`.

### Operations and documentation

OPERATIONS and the P8.3 capability matrix describe local-only Pi, the six-tool grant path, effort refusal, and fixture workflow parity. The P8.1 paragraph in FRAMEWORKS still says live closeout is waiting and that P8.4 is open (**G08-03**). Historical evidence that says P8.2 was still open is left as history.

## Findings

IDs are local to this review. Severities follow [PHASE_REVIEW.md](../PHASE_REVIEW.md). All findings are open. No fixes were applied.

| ID | Severity | Concrete issue / affected requirement | Proposed correction | Verification required |
|---|---|---|---|---|
| G08-01 | High | **Pi `file://` paths skip the project-root check.** `boundaryBlocked` resolves a non-absolute path with `path.resolve` against the project (`src/pi_trusted_policy.mjs`). Installed Pi 1.5.0 `resolvePath` turns `file://` URLs into filesystem paths with `fileURLToPath` before read, write, edit, find, and grep. On a real temporary project, `boundaryBlocked(root, "read", { path: "file:///etc/passwd" })` is false, and the same URL's file path is `/etc/passwd`. `file://localhost/etc/passwd` behaves the same. An ordinary `/etc/passwd` path is blocked, which is what `pi_policy_boundary.mjs` and the P8.3 reviewer note cover. A read/search role, which has no bash, can still name files outside the project. That is the P8.3 outside-read control and D060's external-path requirement. | Resolve each path field with the same rules Pi 1.5.0 uses for tool paths, including `file://`, then apply the existing inside-root check to that path. A URL Pi would reject must be blocked. Add cases for `file:///etc/passwd`, `file://localhost/etc/passwd`, and an in-project `file://` URL that stays allowed. | The outside URL cases return blocked; the in-project URL stays allowed; `node --test scripts/tests/pi_policy_boundary.mjs` passes. **Open.** |
| G08-02 | Medium | **`/dev/stdout` and `/dev/stderr` are inside the project for every path tool.** `SAFE_DEVICE` allows those two paths plus `/dev/null` from `relativeInside`, so write, edit, and read are not blocked. Pi's RPC stdout is the adapter's protocol stream. A trusted role with write and without bash can write `/dev/stdout`, or `file:///dev/stdout`, and the reader will parse the bytes as JSONL, including an `agent_settled` record. `/dev/null` is the redirection the bash cases need. | Allow only `/dev/null` in that set. Block stdout, stderr, and `file://` URLs that resolve to them for read, write, and edit. Keep the D083 note that trusted bash is still a host shell and can write its own stdout. | Policy tests: write/edit/read of `/dev/stdout` and `/dev/stderr` are blocked; `2>/dev/null` stays allowed. **Open.** |
| G08-03 | Low | **Current contract text still describes Phase 8 as open before P8.4.** [FRAMEWORKS.md](../FRAMEWORKS.md) P8.1 paragraph says single-run closeout waits on `pi_live.py` and that P8.4 and P8.5 remain open. [docs/README.md](../README.md) still lists P8.4 under what remains phase-gated. [DESIGN.md](../DESIGN.md) "Implemented mapping (Phases 2–5)" names `ralph` and does not name `pi`. [WORKFLOWS.md](../WORKFLOWS.md) and [EXECUTION.md](../EXECUTION.md) do not say that local-only Pi is a sequence/Ralph runtime. P8.3 evidence and D084 already record the live runs and the fixture parity. | Update those current-contract sentences to the merged P8.3/P8.4 surface: local-only Pi, `pi/MODEL` records, fresh runs per step or iteration, and P8.5 still open. Add `pi` to the DESIGN implementation paragraph. Leave historical evidence and earlier decisions as written. | Re-read the four documents against D083/D084; `doclinks.py` passes. **Open.** |
| G08-04 | Low | **The bash absolute-path scan drops `//` tokens.** `absolutePathTokens` ignores a token that starts with `//`. `boundaryBlocked(root, "bash", { command: "cat //etc/passwd" })` is false. On this macOS host `//etc/passwd` is the same file as `/etc/passwd` (`os.path.samefile`). The policy test blocks a single-slash absolute path. Trusted bash is already a host shell under D083; this is a hole in the check the test describes. | Resolve `//` tokens and run them through the same inside-root check. Keep `2>/dev/null` allowed. | A `cat //etc/passwd` case is blocked; the existing `python3 -B test_calc.py` and `2>/dev/null` cases stay allowed. **Open.** |

## Recommendations (not defects)

- When the Pi pin changes, require `piVersion` and both tool inventories on every preflight. D083 allows a trusted run to continue when installed 1.5.0 omits them.
- Set `cacheWarming` to `off` in the private `settings.json`. Installed 1.5.0 defaults it to `streaming`. The warmer does not schedule a refresh for the synthetic model record, which has no prompt-cache lifetime, so this is not shown to add a second request on the current route.
- Optional live sequence and Ralph runs can be appended to the P8.4 evidence. D084 already accepts fixture parity.

## Verification and integrated recheck

Host: Apple Silicon macOS, Rust 1.88.0. Reviewed source `35777fb`. No provider traffic.

- `cargo test --locked`: **150 tests passed** (49 library, 101 integration).
- `node --test scripts/tests/pi_policy_boundary.mjs`: **8/8 passed.**
- Reproduction, real temporary project, `boundaryBlocked`: `file:///etc/passwd` and `file://localhost/etc/passwd` are not blocked for read and write; `/etc/passwd` is blocked; `/dev/stdout` and `/dev/stderr` are not blocked for write; `cat //etc/passwd` is not blocked for bash; `printf x >&1` is not blocked. `os.path.samefile("//etc/passwd", "/etc/passwd")` is true.
- Not re-run: `offline.py`, `pi.py`, `pi_live.py`, fmt, Clippy. P8.4 records `offline.py` 36/36 and `pi.py` 41/41 on this head. No published-archive install or other platform was checked.

## Gate outcome and handoff

**Changes required for the Phase 8 scope at `35777fb`. P8.5 remains open.** Do not treat individual PR approvals as phase acceptance. Record these findings in the canonical `docs/reviews/phase-08.md` when that report is opened. Under D042 the review PR may merge once every finding has a disposition and a remediation plan; that merge is not a pass. Put the corrections in one `patch/p8-5-review-fixes` PR and request `/grok review` there. Dependent work waits until that patch verifies the fixes and the phase report proposes the pass.
