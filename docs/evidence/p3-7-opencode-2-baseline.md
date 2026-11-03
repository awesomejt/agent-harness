# P3.7 — OpenCode 2.x runtime baseline

Date: 2026-11-02. Entry: `9cfa72b` (merged P3.4 / PR #29). Task branch: `feature/03/p3-7-opencode-2-baseline`. [Card](../../tasks/03-routing.md#p3-7); decision [D035](../../DECISIONS.md#2026-11-02--d035-opencode-225-runtime-baseline).

The user upgraded to OpenCode 2.2.5, the latest published release, and directed that it become the baseline. With 2.2.5 installed, the merged harness failed safely: preflight exited 2 ("requires OpenCode 1.18.30"), with no launch, prompt or project write. No coding run could proceed on either route.

## Observed 2.2.5 surface

All probes ran in a disposable private HOME/XDG with a cleared environment, using a deterministic local chat stub. The user's own configuration and background service were never touched.

| Area | 1.18.30 (previous pin) | 2.2.5 (observed) |
|---|---|---|
| Version | `1.18.30` | `opencode v2.2.5` |
| Command model | In-process | Most commands attach to a shared background service unless given `--standalone`. `acp` spawns its own private `serve --stdio --port 0` child and accepts no `--pure` or `--cwd` flags. |
| Effective config | `debug config --pure` returns the merged view | `debug config --standalone` lists sources: the private config directory plus the supplied document (keys masked as `***`). With `OPENCODE_DISABLE_PROJECT_CONFIG=true`, project `opencode.json` and `.opencode/` are not listed; without it they are. |
| Config schema | `model`, `small_model`, `enabled_providers`, `provider`, `permission`, `tools` | Native keys: `model {providerID, model}`, ordered `permissions` rules, `provider.use` `policies`, `agents`, `providers`, `plugins`, `update`. Legacy keys are translated, and the native document is echoed verbatim. |
| Agents | `debug agent build --pure` | `debug agents --standalone` lists build, compaction, explore, general, plan, summary and title. Each agent's rules are built-in defaults, then configured rules, then a built-in tail (`browser * deny`, `skill browser deny`). |
| Native catalog | `models opencode --pure` | `models --standalone`. With the provider policy it lists only `opencode/` models (81). |
| Tools offered | `read/glob/grep/edit/write/apply_patch/bash` | Trusted profile offers `edit, glob, grep, read, shell, skill, write` and `opencode_worktree_remove`; deny offers only `skill`. Arguments use `path` (not `filePath`), `skill` takes `id`, and worktree removal takes `directory`. |
| Permission requests | Per tool; `other` kind for external directories | Kinds: `read`, `search` (glob), `edit` (edit/write, with a diff), `execute` (shell `{command, description, cwd}`) and `other` (worktree removal). An outside-project read raises **two byte-identical requests**. A shell command raises no separate external-directory request. Request ids start at 0. |
| Rejection | Model continues | Turn ends with `stopReason: cancelled`. |
| Deny-mode tool attempt | Tool absent | Tool absent; the call reports `in_progress` then `failed` ("No tool named …"). |
| Skills | n/a | `skill` loading is denied ("Permission denied: skill"). Project skills in `.opencode/`, `.claude/` and `.agents/` were not discovered. |
| Editor sync | `fs/write_text_file` after edits | No client file or terminal requests observed. |
| Environment | — | `OPENCODE_DISABLE_PROJECT_CONFIG`, `_MODELS_FETCH`, `_AUTOUPDATE` and `OPENCODE_API_KEY` are present in the binary; `OPENCODE_DISABLE_DEFAULT_PLUGINS` is not. |

## Delivered

- **`src/opencode.rs`** (replaces `src/native.rs`): the `2.2.5` pin; native-schema config for both routes; the ordered permission profile; and pure validators for sources, agents and catalog, with unit tests. Preview, help and diagnostics share the version constant.
- **Runtime:** generates the document from the resolved request, drops `OPENCODE_DISABLE_DEFAULT_PLUGINS`, and runs preflight as version, then sources, then (native only) catalog, then agents, all with `--standalone`.
- **ACP adapter:**
  - Launches bare `acp`.
  - A grant requires the request's `rawInput` to exactly equal the latest announced `rawInput` for that tool call, for kinds `read`/`search`/`edit`/`execute`; `other` is always refused.
  - Each identical request may repeat once.
  - Under deny, only `completed` is a violation.
  - The 1.x external-directory shape matcher and editor-sync accommodation are removed.
- **Plan:** `runtime_routing`/`validate_effective` existed only for the 1.x merged-config check and are removed, along with their test assertions; ownership/transaction tests are retained. Managed project sync is unchanged.
- **Test drivers:**
  - `fake_opencode.py` is rewritten to emulate the 2.2.5 surfaces above.
  - `single.py`, `native.py` and `modes.py` gain new preflight cases (`project-source`, `subagent-widened`, `agent-model`, `catalog-foreign`, `inherit-*`) and protocol cases (`external` doubled grant, `triplicate`, `worktree`, `deny-completed`), and their expectations follow the rejection-ends-turn semantics.
  - `single_runtime.py` uses 2.x tool names and gains `--refuse`.
- **Release smoke:** the preview check is version-agnostic, because the smoked binary reports its own pin.
- No new dependency, flag, route or mode; `Cargo.lock` is unchanged.

## Validation

macOS 27.0.1 arm64, Rust/Cargo 1.88.0, OpenCode 2.2.5 (Homebrew). All commands are non-spending.

| Command | Observed result |
|---|---|
| `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo test --locked`, `cargo build --release --locked` | Pass; 57 root tests, including the 4 new `opencode` validator tests and 2 grant-binding tests. |
| `single.py` | 69 cases pass, including 13 exit-2 rejections (12 preflight, 1 empty prompt), the doubled external grant (two independent `once` grants), and refusals ending the turn with exit 3. |
| `native.py` | 40 cases pass, with zero LiteLLM requests and project sentinels preserved. |
| `modes.py` | 165 cases pass: 3 modes × 2 endpoint states × 21 scenarios, plus overrides, `--no-sync` and invalid configurations. |
| `local_first.py`, `preview.py`, `worktree.py` | Pass. |
| `single_runtime.py` (default) | **Installed 2.2.5:** actual read, edit and shell, with five requests and five bound grants (the doubled outside read, in-project read, edit and shell). Independent arithmetic verification passes. |
| `single_runtime.py --cancel`, `--group=coder` | Pass: confirmed cancellation after edit/test; the wire carries only the proxy group. |
| `single_runtime.py --refuse` | Worktree removal (`other`) is refused with no grant. 2.2.5 ends the turn as cancelled (exit 3). The outside directory and project file are untouched. |
| `native_runtime.py` | Installed 2.2.5 native preflight (sources, catalog, agents) and the ACP session/model check pass for deny and trusted, as does the local-first fallback; 0 prompts forwarded. |
| Mutation check | Allowing any tail rule after the profile made `agent-widened` run (exit 0), and `modes.py` failed. Source restored. |
| Cleanup | After the runs, no `ah-runtime-*` directory and no `opencode serve` process remained. |
| Managed project file | 2.2.5, used directly without project-config disabling, translates the harness's legacy `opencode.json` into the equivalent native routing (`ah-litellm` model, provider policy, title model, provider settings). |
| `acp_lifecycle.py` (fixture mode) | Pass. Its `--runtime` mode fails against 2.x by design; it is historical 1.18.30 tooling and has been removed from the current checks. |

## Limits

- **Later correction (P4.8):** this baseline did not re-check instruction loading. With `OPENCODE_DISABLE_PROJECT_CONFIG=true`, 2.2.5 loads no project `AGENTS.md`. Until [D040](../../DECISIONS.md#2026-11-03--d040-explicit-project-instructions-and-refused-runtime-commands), isolated runs sent no project instructions. See [P4.8 evidence](p4-8-inherited-capabilities.md).

- No live LiteLLM or native inference ran. Whether `OPENCODE_API_KEY` authenticates native inference on 2.2.5 is unverified until P3.5.
- In 2.2.5, `opencode_worktree_remove` is offered under trusted and gated only by the adapter's refusal of the `other` kind. No permission action name was found that removes it from the profile.
- A rejected request now ends the turn, so in trusted mode an unsupported tool call ends the run (exit 3) rather than letting the model try another approach.
- Published `v0.1.0-alpha.1` still requires 1.18.30. A new release is needed before binary users can use 2.2.5.

## Review

The Grok review of PR #30 reported 0 blockers, 2 concerns and 2 nits. All four were corrected and verified:

- **Version probe (concern):** it ran without `--standalone`, against the stated invariant. It now passes `--standalone`, which 2.2.5 accepts (`opencode v2.2.5`), and the fake enforces the flag for every non-ACP invocation.
- **Stale grant contract (concern):** the trusted-grant paragraph in CONFIGURATION.md still described 1.x empty-metadata and alias correlation. It now states the exact `bound()` contract.
- **Disk vs runtime config (nit):** CONFIGURATION.md now describes the two deliberate generators: the legacy-key project file versus the native-schema runtime document.
- **`--no-sync` paragraph (nit):** it now points to the D035 effective checks instead of the 1.x merged-config validation.

After the fixes, the fixture suites (69 local, 40 native, 165 matrix, local-first and preview), installed `single_runtime.py` and `native_runtime.py` re-passed.
