# Tools and reuse candidates

Research snapshot: 2026-11-01. These are evaluation candidates, not installed dependencies or compatibility guarantees. Recheck the selected release's API, license, platform behavior, and provider integration at adoption. Do not mix repository-head examples with an older published crate without checking differences.

## Product dependencies

- Existing LiteLLM proxy: model gateway for allowed local/open-weight/OpenRouter routes; not replaced by a Rust gateway.
- OpenCode: initial coding runtime for LiteLLM-backed and native routes.
- Additional native CLIs and Pi: incrementally evaluated in Phases 7–8.

## Rust integration candidates

| Candidate | Relevant reuse | Evaluation boundary |
|---|---|---|
| [Official ACP Rust SDK](https://github.com/agentclientprotocol/rust-sdk) | Structured client/agent communication, examples, test utilities | First transport candidate; verify installed OpenCode compatibility and required client callbacks. |
| [getlatentic/agent-harness](https://github.com/getlatentic/agent-harness) | Harness trait, normalized events, CLI/ACP adapters | MIT/Apache-2.0; API is evolving. Evaluate a pinned release behind our policy layer; optional in-process tool loop is outside MVP. |
| [cli-stream](https://github.com/getlatentic/agent-harness/tree/main/crates/cli-stream) | Leaf subprocess streaming/cancellation component | Independently evaluate tree cleanup, pipe draining, backpressure, runtime fit, and supported platforms. |
| [harness-cli](https://github.com/ayshptk/harness-cli) | CLI adapters and event normalization | Manifest declares MIT; inspect invocation defaults, cancellation, noisy output, version compatibility, and license artifacts before reuse. |
| [Ralph Orchestrator](https://github.com/mikeyobrien/ralph-orchestrator) | Loop, roles, verification, persisted task examples | MIT; reference for Phase 6. Its current Unix-oriented release configuration is not evidence of Windows parity. |
| [agents-cli](https://github.com/agentsfolder/agents-cli) | Canonical config projection, preview, drift, fixtures | Its schema/settings projection differs from our named-agent format. Inspect relevant implementation/license before adoption. |
| [Goose](https://github.com/aaif-goose/goose) / [Rig](https://github.com/0xPlaygrounds/rig) | Broader agent application/framework examples | Reference material; importing a new inner agent loop would require a separate scope decision. |

[OpenCode's ACP documentation](https://opencode.ai/docs/acp/) describes `opencode acp` over stdio. Phase 1 verifies it in our actual project/model/permission setup. ACP support does not itself prove provider authentication terms or constraint compatibility.

The Rust/module direction is accepted in [DESIGN.md](DESIGN.md); the candidates below are not yet locked dependencies. No Python scaffold or embedded ai-queue runtime is planned.

## Supporting stack candidates

| Concern | Candidate |
|---|---|
| CLI | [clap](https://docs.rs/clap/latest/clap/) |
| Async process and I/O | [Tokio](https://docs.rs/tokio/latest/tokio/process/index.html), optional evaluated wrapper |
| HTTP to LiteLLM | [reqwest](https://docs.rs/reqwest/latest/reqwest/); typed serialization with Serde |
| Config/agent parsing | Serde plus an evaluated maintained parser; decide config format in Phase 2 and full agent schema in Phase 4 |
| Diagnostics/errors | tracing and typed errors; concrete selection in Phase 1–2 |
| Release binaries/installers | [cargo-dist](https://axodotdev.github.io/cargo-dist/), evaluated in Phase 2 |

## ai-queue reuse

The sibling ai-queue project supplies HTTP transport/error-classification patterns, injectable fake runners/clocks/transports, CLI response parsers, and later non-spending usage-reader examples. Its 59 tests passed during the initial review; current live integrations were not validated by that test run.

Port relevant behavior/test cases to Rust as needed. Its scheduling store, allocation-ranked routing, isolated tools-disabled sends, and simplified frontmatter parser are not drop-in implementations of our requirements.

## Adoption evidence

Before selecting a dependency, record the smallest needed feature, tested release/version, license and attribution, supported platforms, live integration evidence, and known limitations. Prefer a small adapter/leaf library when it avoids taking ownership of a new agent runtime. Do not let dependency defaults select routes, broaden permissions, or modify global configuration.

## P1.4 evaluation outcome

[D021](../DECISIONS.md#2026-11-01--d021-keep-process-policy-owned-evaluate-sdk-wire-reuse) retains direct Rust subprocess ownership. The pinned comparison rejects `cli-stream` 0.5.0 and ACP SDK 3.6.0's convenience launcher because their inherited-environment APIs cannot express the experiment's cleared/allowlisted environment. The official SDK's protocol engine over caller-owned I/O is the preferred P1.3 candidate; compatibility, runtime fit and its Rust 1.88 requirement must be validated before adoption. No Rust dependency or toolchain change has been made. P1.5 still owns final transport/dependency selection.

See [P1.4 evidence](evidence/p1-4-dependency-evaluation.md) for release hashes, license/attribution inspection, exact defaults, platform limits, alternatives and outstanding lifecycle checks. The shortlist above remains research context, not an instruction to evaluate more frameworks.

## P1.5 selection

[D023](../DECISIONS.md#2026-11-02--d023-select-acp-and-the-tested-rust-integration-boundaries) supersedes the conditional candidate status above: select ACP SDK 3.6.0 without optional SDK features, stable protocol 1, Tokio 1.48.0 and tokio-util 0.7.16 (`compat`), serde_json 1.0.145 and Unix libc 0.2.177. Rust 1.88.0 is now the scaffold baseline. P1.3 supplied locked compile/live compatibility evidence; P1.5 reruns local checks and audits the [resolved dependency/license graph](evidence/p1-5-dependencies.md). No SDK launcher or generic process framework is selected.

Selection is a production implementation decision; dependencies stay in the isolated experiment until their Phase 2 consumers exist. The current `ah` binary remains dependency-free. New config/CLI/release dependencies are chosen at their consuming tasks. Packaging must generate complete notices for the final release graph and target, including schema upstream attribution and Unicode data terms; this inventory does not ship a binary or replace that bundle. [Acceptance preparation](evidence/p1-5-integration-acceptance.md) lists evidence and remaining platform/runtime limits.

## P7.1 selection

[D046](../DECISIONS.md#2026-11-05--d046-select-claude-code-as-the-first-additional-native-adapter) selects Claude Code as the first additional native adapter: the official `claude` executable, version 2.1.314 on macOS arm64, driven in non-interactive mode with stream-json output. The harness keeps process, environment, deadline, permission and cleanup ownership. Third-party ACP bridges and the Agent SDK library are not selected. Authentication is the operator's existing official CLI login, made before the harness runs ([D047](../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login), for every native adapter); the harness never handles credentials. Codex, Grok and Gemini stay deferred until a later recorded selection. [P7.1 evidence](evidence/p7-1-claude-selection.md) records the probe, terms sources and the questions P7.2 owns.

## P7.2 Claude capability matrix

Applies to current source on **macOS 27.0.1 arm64, Claude Code 2.1.314**. The published `v0.1.0-alpha.2` predates Claude support. [Final acceptance](evidence/p7-2-claude-acceptance.md) consolidates the five implementation increments and live use; [setup](OPERATIONS.md#native-claude-cloud-only-p72) and [configuration](CONFIGURATION.md#native-claude-runtime-p72--d048) define invocation details.

| Capability | Supported behavior and boundary | Evidence |
|---|---|---|
| Authentication / transport | Existing official CLI login, native stream-json subprocess; no API-key form or credential handling | [Launch](evidence/p7-2-claude-launch.md), D047–D048 |
| Routes | `cloud-only`; one `local-first` fallback after unreachable LiteLLM before any local launch; LiteLLM always uses OpenCode | [Fallback](evidence/p7-2-claude-fallback.md), D052 |
| Tools / permissions | Default `deny` offers none; explicit `trusted` offers six built-ins with exact one-shot host grants; host privileges, no OS sandbox | [Trusted](evidence/p7-2-claude-trusted.md), D049 |
| Named primary / specialized role | Direct role invocation; appended body and intersected tools; read-only ceiling denies outside-read prompts; no runtime subagents | [Roles](evidence/p7-2-claude-agents.md), D050 |
| Model / effort | Configured alias or model; canonical role model precedence; model-default effort (not checked), or explicit `low`/`medium`/`high`/`max` verified before prompt | [Roles](evidence/p7-2-claude-agents.md), D050; non-default effort refuses in local-first because OpenCode cannot enforce it |
| Instructions / isolation | Project `AGENTS.md` plus canonical body; preflight checks context, settings, tools and model; no discovered user/project settings, MCP or custom plugins | [Launch](evidence/p7-2-claude-launch.md), [roles](evidence/p7-2-claude-agents.md); admin-managed settings refuse |
| Lifecycle / results | Deadline and SIGINT interrupt; group cleanup; only successful `end_turn` succeeds; uncertain effects never replay | [Launch](evidence/p7-2-claude-launch.md), [trusted](evidence/p7-2-claude-trusted.md), [fixture suite](../scripts/tests/claude.py) |
| Preview / machine output / usage | Preview launches nothing; version-1 single JSONL; backend-reported USD cost, unknown token/context counts | [Fallback](evidence/p7-2-claude-fallback.md), [fixture suite](../scripts/tests/claude.py) |
| Sequences / Ralph | Fresh session/preflight per step or iteration; durable runtime-named records; explicit recovery and trusted verification | [Workflows](evidence/p7-2-claude-workflows.md), D051–D052 |

Version upgrades and other platforms require new evidence before changing the pin. Unsupported: custom endpoints, Bedrock/Vertex/Foundry, background tools, runtime subagents, custom tools, slash commands, MCP and plugins. The role body is limited to 128 KiB, appears in process arguments and cannot be read back by preflight. The runtime uses the real HOME for login and its Bash tool sources the operator's shell snapshot. Tool-dependent prompts under `deny` can emit tool-shaped text or run to the deadline; tool-free success is not evidence of a coding result. Workflow resumes must repeat `--permissions trusted` when tools are needed, and Ralph's completion marker must remain the final response line. These are documented limits, not claims of sandbox isolation or prompt obedience.
