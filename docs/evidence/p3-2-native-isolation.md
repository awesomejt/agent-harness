# P3.2 — Isolated native OpenCode route

Date: 2026-11-02. Entry: `bd4c1a9` (merged P3.1 / PR #25). Task branch: `feature/03/p3-2-native-opencode-isolation`. Completion takes effect on this task's required PR review/merge. [D032](../../DECISIONS.md#2026-11-02--d032-separate-built-in-native-opencode-api-key-route) and the [configuration contract](../CONFIGURATION.md#native-opencode-route-p32--d032) define the selected API-key boundary.

## Delivered behavior

- Config retains separate local `model`/`litellm` and native `target`/`model`/`api_key_env`. Only target `opencode` is supported. `--mode` selects the explicit route's defaults and credentials; `--model` overrides that route alone. Missing target/model/key and malformed inactive config refuse before input acquisition/launch.
- Cloud-only constructs its own in-memory OpenCode routing: no provider overrides, only the built-in `opencode` provider enabled, and the same explicit model for primary/helper. It never constructs/applies a managed LiteLLM plan and needs no LiteLLM credential. Both with/without `--no-sync`, it ignores conflicting project runtime config and preserves all managed files.
- Cleared environment/private HOME/XDG exclude project/global configuration, auth stores and inherited provider/catalog/endpoint overrides. The selected key crosses only as the built-in provider's `OPENCODE_API_KEY`; no literal key is serialized in config, receipt, preview or diagnostics. Exact effective routing/permissions/tools/agents/plugins/MCP, pinned version and embedded native model catalog are checked before ACP; the ACP session model must match separately. Catalog checks do not establish account access.
- Shared permission grants/denials, bounded process/private-state cleanup, cancellation and uncertainty semantics remain in force. No retry/fallback or runtime selector is enabled. OpenCode owns the coding loop on either route.

The [pinned provider implementation](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/provider/provider.ts) supports the built-in OpenCode API-key provider. Its [model catalog implementation](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/core/src/models-dev.ts) uses the embedded snapshot when fetching is disabled. Official [OpenCode Console setup](https://opencode.ai/docs/zen/) describes API-key access. The [official authentication module](https://github.com/anomalyco/opencode/blob/v1.18.30/packages/opencode/src/auth/index.ts) has a login-store path; this adapter deliberately does not import that store. No subscription/OAuth integration or custom endpoint is claimed.

## Validation

Tested on macOS 27.0.1 arm64, Rust/Cargo 1.88.0, OpenCode 1.18.30. No new dependency; published alpha.1 assets are unchanged.

| Command | Observed result |
|---|---|
| `cargo test --locked` | 43 tests pass: existing policy/config/transaction coverage plus native strict schema, mode/model/key independence and refusal of a managed plan for native requests. |
| `cargo fmt --check` and `cargo clippy --all-targets --locked -- -D warnings` | Pass. |
| `cargo build --release --locked` | Pass; source build only, no publication. |
| `python3 scripts/tests/native.py` | 32 cases pass, with/without no-sync. Loopback LiteLLM trap receives **zero discovery or model requests**. Conflicting/malformed config, JSONC, manual receipt, lock and dirty-file sentinels remain identical. Covers wrong provider/allowlist/helper/agent/permissions/version/catalog/session, absent selected key, trusted allow-once, default denial, confirmed deadline cancellation, post-prompt uncertainty, preview and redaction. Prepared runtime homes are removed. |
| `python3 scripts/tests/native_runtime.py` | Installed OpenCode passes native effective preflight, embedded catalog and ACP initialize/session-model setup in both deny and trusted profiles. A shim intercepts `session/prompt` and synthesizes `end_turn` without forwarding it to OpenCode. Project LiteLLM settings are unchanged; no ownership/lock files created. This is **setup evidence**, not a successful native model turn or credential test. |
| `python3 scripts/tests/single.py` | All 57 local CLI cases and matching no-sync repeat pass, including process/private-state cleanup, protocol/adversarial output, permission mapping, SIGINT/SIGTERM, deadlines and uncertainty. |
| `python3 scripts/tests/preview.py` and `python3 scripts/tests/worktree.py` | Pass network-free preview/redaction and real-Git preservation fixtures. Missing-key wording now identifies the selected route. |
| `python3 scripts/tests/single_runtime.py` | Actual installed runtime with deterministic local model stub reads/edits/tests a disposable project, six grants, exit 0 and independent arithmetic test pass. |
| `python3 scripts/tests/single_runtime.py --cancel` | Actual edit/test precedes confirmed cancellation; exit 3, effects preserved, cleanup confirmed, no replay. |

Build debug fixtures with `cargo build --locked` first; ensure `~/.cargo/bin` and OpenCode are on absolute PATH entries. All commands above are non-spending. Native fixture keys are synthetic. Private prompts, credentials and raw provider errors are not recorded.

## Review corrections and limits

Independent security review identified that an early draft shared one model default across modes. Corrected before PR: native config now requires its own model; distinct-default override tests cover both directions. Review also caught a stale runtime-key sentence, corrected to distinguish the two reserved environment variables. Reviewed code has no remaining routing/auth/permission/project-write blocker.

No real native API key was supplied or probed, and no native prompt was sent to a service. Native authentication success, account balance, inference, downstream physical hosting and native coding usability remain unverified. P3.5 owns live local-only/cloud-only/eligible-fallback use. Only the built-in OpenCode API-key provider is supported here; official subscription CLI adapters and login integration remain separately gated. P3.3 is next: model-group/proxy handoff followed by policy-guarded configured fallback. P3.4/P3.6 still own the complete three-mode matrix and holistic Phase 3 acceptance.
