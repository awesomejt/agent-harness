# P3.4 — Three-mode boundary matrix

Date: 2026-11-02. Entry: `8800a2d` (merged P3.3 part 2 / PR #28). Task branch: `feature/03/p3-4-mode-matrix`. [Card](../../tasks/03-routing.md#p3-4) gate: AC02 and AC03, tested against effective behavior rather than selected enum values.

## Delivered

- New driver `scripts/tests/modes.py` runs one combined configuration (`litellm` + `native` + `groups`) in every mode. Each scenario runs against a reachable LiteLLM stand-in and a closed port, so a mode's route cannot depend on proxy state unless the mode allows it.
- `fake_opencode.py` gains route-independent inherited-choice cases: `inherit-agent` (a helper with another model), `inherit-subagent` (a subagent even on the selected model), `inherit-mode` and `inherit-provider` (an extra provider that is also enabled). It also gains an opt-in `track-config` record of each invocation's arguments, environment names and runtime configuration. Existing suites do not create the marker and are unchanged.
- No production source, dependency, flag or decision changed. The matrix found no policy defect. The mutation check below confirms it can detect one.

## What each run asserts

Every assertion is made on every run, in all modes and endpoint states:

| Boundary | Assertion |
|---|---|
| Forbidden launches | The launched ACP routes are exactly `[local]` for local-only, `[native]` for cloud-only, and `[local]` (reachable) or `[native]` (unreachable) for local-first, with at most one launch per run. Decoy `claude`/`codex`/`grok`/`gemini`/`pi` on `PATH` never run. |
| Runtime inputs | Every runtime invocation, including all preflight checks, receives exactly the allowlisted environment plus one route credential: `AH_RUNTIME_API_KEY` locally or `OPENCODE_API_KEY` natively. Native configuration has `provider: {}`, `enabled_providers: [opencode]` and `opencode/fixture` for both default and helper models, with no LiteLLM endpoint. Local configuration has only `ah-litellm`, the configured endpoint and the proxy group. The outbound top-level key set is exact, so no `agent`, `mode` or helper entry is sent, and the tools/permission profile matches deny or trusted. Ambient `OPENAI_BASE_URL`, `LITELLM_API_BASE`, `OPENCODE_CONFIG*` and provider keys never reach the runtime. |
| Discovery requests | Ambient endpoint variables point at a separate trap, which records zero connections over the whole run. The configured stand-in records zero connections for local-only and cloud-only, and exactly one connection for a reachable local-first run (the D034 reachability check). It Both listeners record zero received bytes. |
| Inherited choices | A different `small_model`, a helper agent, a subagent, a mode with its own model, an enabled extra provider, a widened permission or agent rule, and a wrong runtime version all exit 2 in every mode. Nothing launches or is prompted, and no managed project file is written. In local-first with an unreachable endpoint, the fallback's native preflight rejects them the same way. |
| Retry bounds | `attempt=2` appears only for an unreachable local-first run, `attempt=3` never appears, and post-launch failures (exit 1/3/4) never add an attempt. Single-route modes report no reachability check and "no automatic retry or fallback". |
| Uncertainty | `rpc-error`, `eof`, `deny-progress`, `unexpected-write` (trusted) and `home-cleanup-failure` exit 4 with the uncertain-completion diagnostic in every mode and route. None is replayed or falls back. Only `home-cleanup-failure` retains a private runtime home; the driver removes it afterward. |
| Project writes | Managed `opencode.json` and the receipt exist only after a launched local-route run. They never exist for native or fallback runs or for any exit-2 run. Dirty `user.txt` is preserved byte for byte. |

## Further groups

- **`--mode` override:** four directed pairs (cloud→local-only, local→cloud-only, local→local-first and cloud→local-first) run against both endpoint states, each with `success` and `inherit-agent`. They produce the same routes, fallback attempt, inherited rejection, runtime inputs and endpoint contact as the matrix (16 runs).
- **`--no-sync`:** cloud-only still runs the full effective preflight and rejects `inherit-agent` and `route`. Local-only and local-first on a fresh project reject statically before any check, runtime or fallback (9 runs).
- **Invalid route or fallback configuration** (14 runs): each case must exit 2 with its specific diagnostic, with no runtime invocation, endpoint contact or attempt line. The cases cover local-first without `native` or `litellm`; a native target other than `opencode`; a native `group:` model; a proxy field in `native`; a missing native or local key; an undefined group; `--mode local-first` without `native`; a group model under cloud-only; a missing key in each single-route mode; and an unsupported mode from the flag or the file.

## Validation

macOS 27.0.1 arm64, Rust/Cargo 1.88.0, OpenCode 1.18.30, Python 3.14. All commands are non-spending, and keys are synthetic.

| Command | Observed result |
|---|---|
| `python3 scripts/tests/modes.py` | 147 cases pass: 108 matrix runs (3 modes × 2 endpoint states × 18 scenarios), 16 override, 9 no-sync and 14 invalid. |
| Mutation check | Temporarily removing the runtime's `effective["agent"] != {}` preflight check made `inherit-subagent` succeed under local-only. That run exited 0 and the matrix failed on it. A second mutation made the harness send a helper `agent` entry. The fake's own clearing masked it from preflight, but the exact outbound key-set assertion failed (`('local', ['agent'])`). In both cases the source was restored and the matrix re-passed. |
| `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo test --locked`, `cargo build --release --locked` | Pass; 55 root tests. |
| `single.py`, `preview.py`, `worktree.py`, `native.py`, `local_first.py` | Pass: 59 local cases, all preview fixtures, 12 worktree fixtures, 32 native cases with zero LiteLLM requests, and 17 local-first cases with the blackholed check. |
| `single_runtime.py` (default, `--cancel`, `--group=coder`), `native_runtime.py` | Pass with installed OpenCode 1.18.30: actual edit/test, confirmed cancellation, group wire routing, and native/fallback preflight plus ACP session with 0 prompts forwarded. |

## Limits

- The fake proves what the harness sends and launches. Requests made by a real OpenCode child are covered only by the installed-runtime checks. Native preflight relies on `OPENCODE_DISABLE_MODELS_FETCH` and the built-in catalog; `native_runtime.py` exercises that path but cannot observe every outbound socket.
- The local route compares only the `ah-litellm` provider entry. An extra inherited provider that is *not* enabled is tolerated, because `enabled_providers`, `model`, `small_model` and an empty `agent`/`mode` are all pinned. The matrix tests the enabled variant, which rejects in every mode. The native route rejects any provider entry.
- Interrupt and deadline during the reachability check stay in `local_first.py`, which skips them when 10.255.255.1 is not blackholed. The matrix covers the deadline after launch on every route.
- No live LiteLLM or native inference ran. P3.5 owns live use of local-only, native cloud-only and the eligible fallback.

## Review

The Grok review of PR #29 reported 0 blockers, 2 concerns and 1 nit. All three were corrected and verified:

- **Shared listener (concern):** the ambient endpoint and the configured stand-in shared one listener, so an ambient-URL swap could pass unnoticed on reachable runs. A separate ambient trap now must stay at zero connections.
- **Outbound `agent`/`mode` (concern):** these were unasserted, so the fake's clearing could hide a leak. The matrix now pins the exact outbound key set and the permission/tools profile. The harness sends no `agent`/`mode` keys, so the check is for absence rather than `{}`. The second mutation verifies it.
- **Override coverage (nit):** it now includes cloud→local-first and an inherited-choice rejection under `--mode`.
