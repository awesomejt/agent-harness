# P1.6 — Permission policy evidence

Date: 2026-11-01 (America/Denver). Task: [P1.6](../../tasks/01-integration.md#p1-6). Decision: [D020](../../DECISIONS.md#2026-11-01--d020-fail-closed-experiment-permissions). Branch: `feature/p1-6-permission-policy`. Prerequisite P1.1 merged in PR #6; baseline `2fb7b8f`.

## Scope and results

Added a dependency-free, transport-independent permission policy and synthetic normalized request fixtures. Default denies all tool actions. A trusted caller can grant one exact request once; changed identity, action or options consumes the grant without approval. Persistent grants and interactive prompting are unsupported. Missing denial options cancel; malformed identities/options refuse. The policy performs no I/O and has no TTY/stdin/approval wait path. Its Rust types are experimental, not a public transport or config schema.

Six permission tests cover default denial across read/write/shell/network/unknown actions and approval-like backend text; explicit allow-once and consumed/repeated grants; fresh-attempt isolation; request mutation; missing denial/empty/unknown options; allow-always refusal; malformed IDs/actions and duplicate options. Existing five scaffold tests also pass.

Tested on Darwin arm64 / `aarch64-apple-darwin`, Rust/Cargo 1.85.0 pinned by rust-toolchain.toml. From the repository, with `source "$HOME/.cargo/env"` if needed:

```bash
cargo fmt --check
cargo build --locked
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --release --locked
./target/release/ah --version
```

All checks passed: 11 tests total; no formatting/lint findings; release version `ah 0.1.0`. No external dependencies or lockfile changes, model calls, runtime launches, credentials or managed project writes.

## Limits and consuming gates

These fixtures are synthetic request objects, not captured ACP JSON. They prove deterministic policy decisions and absence of a blocking approval path in that function, not backend enforcement or process cleanup. Prompt-required policy is documented as unsupported; no config parser/launcher exists to exercise startup refusal yet.

Before a live P1.2 prompt, verify the actual adapter option/cancellation mapping, fully described request identities, and effective runtime restrictions including tools that might bypass callbacks. Show the effective policy; refuse unsupported enforcement. A grant must come from trusted session-authorized driver input, never model output. Response delivery failure must stop/clean up the attempt; uncertain side effects remain uncertain. P1.3 still requires live denial and cancellation/descendant-cleanup evidence. P1.6 resolves only the pre-live decision/fixture gate; Phase 1 remains open.

## PR review

Pending required Grok review. Completion takes effect on merge.
