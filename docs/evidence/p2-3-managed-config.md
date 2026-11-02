# P2.3 — Managed project configuration

Date: 2026-11-02. Platform: macOS arm64. Rust/Cargo 1.88.0.

`src/project_config.rs` implements read-only plans, strict duplicate-aware raw JSON preservation, four-value provider ownership receipts, stale-plan checks, nonblocking Unix locks and flushed atomic per-file replacement. D025 and CONFIGURATION.md specify the selected policy, manual recovery and concurrency limits. `--no-sync` uses the same desired route and refuses a mismatch. Effective-config validation separately rejects provider/helper/agent routing differences; production environment/tool isolation remains P2.2.

Verification: `cargo fmt --check`, `cargo test --locked` (33 tests), `cargo clippy --locked --all-targets -- -D warnings`, and release build/version smoke (`ah 0.1.0`). Six transaction integration cases cover byte-preserved unrelated fields, idempotence, alias updates, user-owned conflicts, malformed/commented/duplicate JSON, alternate JSONC refusal, stale plans, manual owned-field changes, interrupted/missing receipts, no-sync without any file creation, effective-route/helper/agent mismatches, symlink/FIFO rejection and busy locks. A separate outside-project sentinel remains unchanged; the supplied key sentinel is absent from all generated files, including receipts/lock. Planning creates no files. No HOME paths are consulted by the module. Inactive provider siblings remain byte-preserved; malformed effective agent structures reject.

No live model or runtime launch is appropriate for this library transaction task. Existing Phase 1 transport evidence is unchanged. New files are private (0600); existing project config modes are preserved. Crash fixtures simulate the config-written/old-receipt and missing-receipt states; they establish refusal, not power-loss durability. Two-file atomicity and protection from hostile external editors are not claimed. Native-route isolation remains a consuming-phase gate rather than a native executor implemented here.

Review and PR outcome will be recorded before merge.
