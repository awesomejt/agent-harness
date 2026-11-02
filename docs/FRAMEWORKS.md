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
