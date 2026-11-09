# P7.1 evidence — Antigravity replacement and readiness

2026-11-07. **Terms paragraph superseded by [D066](../../DECISIONS.md#2026-11-08--d066-block-antigravity-on-consumer-plan-terms) on 2026-11-08: P7.5 is blocked on consumer-plan terms.** Entry: merged PR #74, `1db7875`. Task: [P7.1](../../tasks/07-native-adapters.md#p7-1); consuming task: [P7.5](../../tasks/07-native-adapters.md#p7-5). Decision: [D061](../../DECISIONS.md#2026-11-07--d061-replace-the-gemini-cli-requirement-with-antigravity-cli).

## Requirement change and disposition

The operator replaces the Gemini CLI requirement with **Google Antigravity CLI**. Keep P7.5 and the four-runtime Phase 7 portfolio; do not add a fifth mandatory adapter or mark P7.5 complete. D061 supersedes D059's future target/interface/setup steps. Earlier Gemini evidence, decisions and historical Gemini-authored reviews retain their original meaning.

Google's [May 19 transition announcement](https://developers.googleblog.com/an-important-update-transitioning-gemini-cli-to-antigravity-cli/) states that consumer free/Google AI Pro/Ultra requests ended June 18, 2026, while enterprise licenses and paid API-key access remain. The project change therefore follows the operator's chosen supported consumer path, without asserting universal Gemini CLI discontinuation. The previous readiness assessment missed this consumer-service transition; npm availability alone did not establish suitability for the selected login form.

Select official caller-owned **`agy acp`** as the feasibility candidate. Antigravity owns the inner coding loop; Rust retains route, process, permission and outcome ownership. Headless stream-json is an alternative if ACP cannot meet the contract. Do not embed the SDK, substitute an inner loop, activate remote agents/control, or introduce a production runtime/config value in this decision increment.

## Installed discovery and reproducibility

`shutil.which("agy")` resolves `/Users/jason/.local/bin/agy`; `antigravity`, `gemini` and `pi` do not resolve. Use `agy`, not the desktop editor command. This supersedes the earlier missing-Gemini setup as the next Google-runtime prerequisite. Account/login/entitlement remains unknown.

Three commands ran on the D041 Apple Silicon macOS host with a fresh disposable HOME/project, no inherited credentials/config, and no stdin prompt. Environment contained only fixed system PATH, synthetic HOME/TMPDIR, NO_COLOR, TERM and LANG. Each caller-owned process had a ten-second timeout and separate process group. All returned immediately with exit 0; the synthetic tree had no files afterward. Only version/help output was requested, no ACP initialize/login/session/model command. No claim of network tracing or authenticated isolation follows from these help checks.

| Command | Combined stdout/stderr bytes | SHA-256 |
|---|---:|---|
| `agy --version` | 6 | `c03e3824001f39b9518249b8d6522422fc4de7227e12a568c0164662b03b7758` |
| `agy --help` | 3319 | `e92946f85cec63eca61f93014ca49f53b1e84277eac7954e7fac7d8d712940fd` |
| `agy acp --help` | 2254 | `08cedbbc6d63dc2dbd9f3c108d949e048ee3a6696c31e41914384c2057d27747` |

Version output is **1.5.3**. Read-only [official latest-release API](https://api.github.com/repos/google-antigravity/antigravity-cli/releases/latest) reported tag `1.5.3`, published `2026-11-07T08:38:26Z`; [versioned release](https://github.com/google-antigravity/antigravity-cli/releases/tag/1.5.3). A matching version string is not binary provenance verification or an accepted compatibility pin. No package was downloaded, installed or updated.

Reproduce using `shutil.which`, then launch the three argument lists above through `subprocess.Popen` with `start_new_session=True`, synthetic cwd/HOME and an explicit environment; collect stdout and stderr separately, hash their concatenation, timeout and reap the process group. Keep output bounded in any reusable feasibility probe. Retain the installed binary identity and matching release sources/help at consumption; website documentation is a moving reference, not a 1.5.3 runtime guarantee.

## Capabilities and likely fit

All external sources below are official Google documentation checked 2026-11-07. “Documented” does not mean installed conformance has passed.

| Area | Research finding | Harness consequence / remaining proof |
|---|---|---|
| ACP transport and login | [ACP quickstart](https://antigravity.google/docs/cli/acp/) documents `agy acp`, caller-owned stdio JSON-RPC and reuse of the CLI's cached interactive login. | Promising fit for existing protocol/process ownership. Verify exact installed handshake, client callbacks and cancellation before adopting it. No automatic login or authentication RPC. |
| ACP client capabilities | [Editor/client guide](https://antigravity.google/docs/ide/extensions/acp) documents protocol 1, streamed tools/edits, approval callbacks, cancellation and model/thinking session options. Rules can bypass callbacks; third-party models are restricted to named editors. | Start with Google Gemini models exposed to an honestly identified generic client. Do not impersonate an editor. Approval callbacks alone do not prove every operation is intercepted. Prove effective state in the same process/session before prompt. |
| Headless alternative | [Headless guide](https://antigravity.google/docs/cli/headless/) documents JSON/stream-json, init/step/result records, stdin user events and usage. Session counters are cumulative. Soft-denied approval-required tools can leave exit 0; stream input rejects control_request/control_response. | Exit 0 is insufficient evidence of task success; require a valid terminal and account for denied work/early finish. Stream input is not a host approval channel. Any alternate transport needs separate permission/cancellation proof. |
| Model and effort | [CLI reference](https://antigravity.google/docs/cli/reference/) documents explicit model, effort and agent selection plus print deadlines and disabled slash expansion. Installed main help adds `--settings` for session-only inline/file JSON. | Validate exact resolved model/provider and effort; refuse unsupported mappings. Do not assume headless flags propagate to ACP or that overlays replace inherited sources. No new public harness flags. |
| Canonical roles | [Custom-agent guide](https://antigravity.google/docs/subagents/) describes Markdown/YAML agents and direct primary selection, as well as runtime subagents. | Candidate for name-based canonical projection. Prove body/model/tool/effort precedence and narrowing before enabling roles. Initially invoke primary/specialized roles directly; delegation is not authorized by similarity of file formats. |
| Permissions | [CLI permissions](https://antigravity.google/docs/permissions/?tab=cli) documents deny > ask > allow, wildcard action resources and automatic workspace access defaults. | Strict/no-tool feasibility must cover every tool source and indirect operation; a list of resource denials is not complete tool removal. Workspace defaults and cached grants require adversarial checks. Read-only/plan/sandbox is not `deny`. |
| Hooks | [Hook contract](https://antigravity.google/docs/hooks/) offers pre-tool decisions, tool arguments, conversation/step identity, and a pre-invocation termination option. Hooks can come from workspace, global and plugin sources. | Potential full-tool gate/host bridge, not selected enforcement yet. Prove coverage, ordering, timeout/error/disconnect refusal, argument integrity and exact one-use grants, including parallel/indirect calls. Never invoke inherited hook commands to test real configuration. |
| Configuration and instructions | [Discovery guide](https://antigravity.google/docs/customization-discovery/) includes workspace/parent/global rules, agents, skills, plugins, hooks and MCP. Some legacy skill directories outrank manifests; rules accumulate. | Synthetic source sentinels must establish complete isolation. A manifest exclusion, chosen agent or empty settings overlay cannot be presumed sufficient. Preserve planned project instructions, with no unplanned global/ancestor prompt sources. |

This is substantial functional overlap with the intended Gemini adapter: coding-agent loop, machine transport, model/effort selection and named roles. **Complete no-tool enforcement and login-preserving isolation remain unproven.** Similar product features do not establish equivalent enforceable constraints.

## Authentication and selected boundary

D001/D047 apply: operator logs into the official CLI before harness use, and the CLI alone handles credentials. No reading, copying or exporting auth stores/keychain; no subscription traffic through LiteLLM. [Authentication documentation](https://antigravity.google/docs/install/) describes shared local sign-in across Antigravity surfaces and several account methods; it does not establish this operator's login or entitlement. Existing login reuse must be verified without credential inspection. No API-key, ADC, SDK or custom-endpoint form is selected here.

[Antigravity terms](https://antigravity.google/terms) distinguish consumer and enterprise agreements and place responsibility for agent access/actions with the operator. The official documented ACP/headless interfaces are the integration candidate; this record makes no account-specific entitlement or legal conclusion. Do not spoof editor/client identity, bypass limits or share the operator's login with other users.

> **Superseded on terms (2026-11-08, [D066](../../DECISIONS.md#2026-11-08--d066-block-antigravity-on-consumer-plan-terms)).** This paragraph cited only the general terms page and missed Google's [Antigravity FAQ](https://antigravity.google/docs/faq/). The FAQ says headless `agy -p` "is intended for direct scripting and CI workflows" and that wrapping `agy` inside third-party coding agents or applications "is not supported under consumer plans". It also warns that third-party access "can result in suspension or termination of your account". The harness driving `agy` on the operator's consumer login is that case, so P7.5 is blocked on terms as well as on D063's control gate. The [provider terms check](p7-native-terms-check.md) quotes the sources. The rest of this record stays as the historical readiness assessment.

## First consuming experiment and gates

P7.5 starts with a focused **no-inference feasibility PR**, not a production adapter:

1. Establish installed control semantics before initializing. ACP help exposes `--app-data-dir`, `--gemini-dir`, `--include-default-customizations` and telemetry/log controls. Main help exposes `--settings`. These are observed option names only: verify whether each is supported for the selected surface, what sources it affects and whether it changes auth location. Never copy credentials to make private directories work. A private-state alternative needs an evidenced D047-compatible decision.
2. Use synthetic user/project/parent/settings/rules/skills/plugins/MCP/hook/agent/model/endpoint sentinels, a cleared environment, bounded stdout/stderr/deadlines, trapped network and process-group cleanup. Confirm startup effects and configuration precedence before allowing initialize. Do not modify global settings or project sentinels outside disposable fixtures.
3. Keep a strict initialize-only protocol allowlist until effective isolation is established; no authenticate/session/prompt/model invocation. Then decide the minimum safe expansion. Prove complete pre-turn no-tool control and effective inventory, including web/search, media, scheduling, subagents and indirect/hosted tools. Wildcard action rules and a successful handshake alone do not pass.
4. Trusted/constrained support additionally requires exact request-bound one-use grants, external-path refusal, permission cache behavior, tool argument integrity and fail-closed lifecycle. Unsupported profiles/roles refuse before submission. Preserve D030/D031/D034/D039 cleanup, submission-before-write, usage attribution and no uncertain replay; no retry/fallback may be inferred from Antigravity defaults.
5. After controls pass, implement narrow launch/events/deny, trusted/roles and workflow/fallback increments as warranted. P7.5 still requires fixtures plus live coding/constrained-role evidence. P7.6/P7.7 remain complete-portfolio gates; independent Pi P8.2 remains available after setup.

No development-platform switch is required. A fresh context is efficient for the isolated feasibility experiment. Missing/expired login is a CLI-owned setup failure, never a reason to extract tokens or silently switch authentication.

## Validation

Official-source research, isolated installed discovery above, relative Markdown links and whitespace checks. This change revises requirements/decisions/cards and records evidence; no production Rust or dependency behavior changed, so runtime/Rust suites and model calls are not required. PR review and merge closeout are recorded in PROJECT.md.
