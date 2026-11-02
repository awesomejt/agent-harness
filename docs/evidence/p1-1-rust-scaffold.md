# P1.1 — Rust scaffold evidence

Date: 2026-11-01 (America/Denver). Task: [P1.1](../../tasks/01-integration.md#p1-1). Decision: [D019](../../DECISIONS.md#2026-11-01--d019-minimal-rust-scaffold-baseline). Branch: `feature/p1-1-rust-scaffold`; [PR #6](https://github.com/awesomejt/agent-harness/pull/6). Prerequisite P0.13 was accepted by merged PR #5 (baseline `e1061bb`).

## Scope and environment

One dependency-free Cargo package, `awesomejt-agent-harness` 0.1.0, Apache-2.0, with an `ah` binary over a library argument/response boundary. Edition 2024; MSRV 1.85; rustup pin 1.85.0. Cargo.lock is committed and publication is disabled. The crates.io sparse-index URL for the package returned 404 / `NoSuchKey`; this is an availability observation, not a reservation.

Tested on Darwin arm64, Rust host/target `aarch64-apple-darwin`, with the Xcode clang linker. `rustc -vV` reports 1.85.0 (`4d91de4e4`, 2025-02-17), LLVM 19.1.7. Cargo is 1.85.0 (`d73d2caf9`, 2024-12-31). No Rust installation existed initially. Installed with the official rustup installer, minimal profile plus rustfmt/Clippy, using `--no-modify-path`; source `~/.cargo/env` in the working shell. No shell startup file was modified.

## Repeatable checks and observed results

From the repository, with rustup on PATH:

```bash
# One-time lockfile creation used by P1.1, requiring no registry access:
cargo generate-lockfile --offline
cargo fmt --check
cargo build --locked
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --release --locked
./target/release/ah --version
```

All final commands passed. Formatting and Clippy had no findings; four subprocess integration tests and one Unix unit test passed. The release binary printed `ah 0.1.0` with success. Tests verify package-version output and both version flags, help/no-argument behavior, empty success stderr, and failure with empty stdout for unsupported commands/options and extra arguments. An initial `--locked` build correctly refused the absent lockfile; generating the dependency-free lockfile resolved it before the full successful check sequence.

## PR review

Grok completed one review on PR #6: 0 blockers, 0 concerns, 3 nits. Simplified the distinction between absent and non-UTF-8 arguments and added a Unix unit test for invalid UTF-8. Replaced panicking output macros with fallible writes and added a Unix closed-output subprocess test; output failure exits 1 without a panic. Updated PROJECT.md with the PR link and proposed post-merge state. The full check sequence passed again after these changes. Nit fixes do not require re-review under the Git workflow.

## Limits and follow-up

Only informational help/version behavior is implemented. There are no coding commands, runtime launches, model calls, configuration writes or external dependencies. P1.6 must define/test permissions before P1.2 live execution. P1.4 will revisit toolchain requirements when selecting dependencies. The initial target is development evidence only; release installation and broader platform claims remain P2.5/P4.5. Phase 1 is still open and requires its own P1.7 holistic review.
