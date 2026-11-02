# P2.5 — First installable binary

Date: 2026-11-02 (America/Denver). Entry baseline: `21404fc` (P2.8 PR #20 merged). Task: [P2.5](../../tasks/02-first-slice.md#p2-5). Decision: D029. Version: `0.1.0-alpha.1`; target `aarch64-apple-darwin`. Acceptance takes effect after required review/merge and publication of the tested artifact. P2.6 and P2.9 remain open.

## Scope and evidence

The [installation runbook](../OPERATIONS.md) supplies versioned download/checksum commands, installation without a language toolchain, separate pinned OpenCode and existing LiteLLM setup, preview, trusted execution, exits, upgrade/rollback/removal and release limitations. The README links it and removes stale pre-preview/development-only instructions.

`scripts/release/package.py` builds a clean checkout with pinned Rust 1.88.0 and locked production dependencies. It fixes the native Apple Silicon target and deployment setting, checks system-only dylibs, packages an executable with provenance and notices, and emits `SHA256SUMS`. The release graph contains 128 registry crates (including conservative build/proc-macro reachability), plus the harness. Registry source archives are verified against Cargo.lock and included unchanged to preserve embedded notices; recursive attribution files and selected embedded BSD/MIT/lexical notice files are directly readable. License selections are recorded per package. The schema crate's missing license text comes from its pinned upstream commit; missing attribution/unreviewed license expressions fail packaging. Rust standard-library/toolchain copyright/license resources are included conservatively. This refreshes the production graph rather than reusing the experiment inventory. An independent read-only notice review identified the source-embedded notices and Unicode requirements now included.

Maintainer tools: Rust/Cargo 1.88.0, Python 3.14.7, Xcode 27.1 (27A9275). Host: Apple Silicon macOS 27.0.1 (26A434). Build deployment setting 14.0 is not evidence for earlier macOS support. No Intel/Linux/Windows, Developer ID/notarization, browser-quarantine flow, new model call or completed Phase 2 acceptance is claimed.

## Verification

Run the required Rust formatting/test/Clippy checks, existing public CLI/preview/preservation fixtures, then package and smoke the actual release archive:

```sh
cargo fmt --all -- --check
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo build --locked
python3 scripts/tests/single.py
python3 scripts/tests/preview.py
python3 scripts/tests/worktree.py
python3 scripts/release/package.py --output dist/candidate
sh scripts/release/smoke.sh dist/candidate 0.1.0-alpha.1
```

The smoke extracts and checksum-verifies the archive, installs into a disposable HOME, verifies its ad hoc signature and invokes the installed `ah` with only its own bin directory on PATH. Rust, Python, Node, Git and OpenCode are unavailable on that PATH. Version/help and read-only preview pass; preview reports missing OpenCode without launching it or contacting the unreachable fixture endpoint, omits prompt/key/endpoint and leaves only the original config file. Unsupported cloud mode and missing key return 2. No language toolchain is required by binary users; requested coding/test tasks may need their own tools.

Final asset checksum and exact source commit are supplied by the published `SHA256SUMS` and archive `BUILD-INFO.json`, avoiding a circular source-document checksum. Publication targets the reviewed merged commit, followed by a fresh download/install smoke. Release: [v0.1.0-alpha.1](https://github.com/awesomejt/agent-harness/releases/tag/v0.1.0-alpha.1).

Build-host adjustment: the initial release build hit a macOS 27 dylib loader
failure in proc macros (`mis-aligned LINKEDIT string pool`). Packaging explicitly
sets `CARGO_PROFILE_RELEASE_STRIP=none`, avoiding Rust's stripping path; see
[upstream Rust issue #157750](https://github.com/rust-lang/rust/issues/157750).
The MSRV and dependency pins remain unchanged.
