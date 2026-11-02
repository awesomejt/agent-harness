# P2.1 — First-slice configuration and CLI contract

Date: 2026-11-02. Baseline: merged Phase 1 review PR #13. Task completion is effective on this task PR merge. [D024](../../DECISIONS.md#2026-11-02--d024-first-slice-json-inputs-explicit-trust-and-shell-outcomes) and [CONFIGURATION.md](../CONFIGURATION.md) own the selected contract; runtime enforcement is not implemented by this task.

## Scope and acceptance

- Strict project-local `ah.json`, explicit override, complete precedence and environment key reference; unknown/duplicate fields, malformed URLs, literal key fields and unsupported modes/policies reject.
- Library parser for the selected future single-run interface: exactly one inline/file/explicit-stdin source, bounded UTF-8, existing project directory, explicit overrides, mode and choice provenance. The public CLI remains help/version only; no unused command handler or runtime skeleton is added.
- Default denial; checked-in config cannot authorize host access. Only explicit invocation `--permissions trusted` permits the future broad host read/write/shell profile. Scoped shell and interactive policies reject. Effective tool/model routing, precise callback grants and actual trusted coding permission tests remain mandatory P2.2/P2.3 gates before any coding launch.
- Shell exits fixed at 0 success, 1 known failure, 2 rejection, 3 known cancellation/deadline and 4 uncertainty. Timeout 1800 seconds by default, bounded override 1–86400. Runtime deadline/cancellation/cleanup enforcement remains P2.2/P2.4 work.
- Read-only network-free preview semantics fixed; planner/preview implementation is P2.7. No-sync never removes validation requirements.

## Repeatable verification

Platform: macOS 27.0.1 arm64, Rust/Cargo 1.88.0. Run from repository root with `~/.cargo/bin` on PATH:

```bash
cargo fmt --check
cargo test --locked
cargo clippy --all-targets --locked -- -D warnings
cargo build --release --locked
./target/release/ah --version
cargo build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
python3 scripts/experiments/acp_lifecycle.py --runtime --opencode /opt/homebrew/bin/opencode
```

Root checks passed: 27 tests (16 config/input, 6 permission, 4 CLI and 1 Unix argument test), formatting, Clippy with warnings denied, release build and `ah 0.1.0` smoke. Fixtures cover invalid schemas/aliases/URLs/environment names, duplicate options, unsupported metadata/policies/modes, empty/conflicting/oversized/non-UTF-8 prompts, missing/empty credentials before stdin, config location, invocation overrides/provenance, missing/non-directory project, file/stdin sources and Unix FIFO refusal. Sentinel secrets never appear in validation errors. Config/request types provide neither Serialize nor Debug; key lookup values are discarded after nonempty checking. Config and prompt file loading share nonblocking/no-controlling-terminal Unix open and opened-handle type inspection, with regular/missing/oversized/directory/device/FIFO config fixtures. Noncanonical URLs reject, including dot segments, empty userinfo, uppercase scheme/host and explicit default ports. Negative config/invocation fixtures assert exact redacted error categories.

The standalone experiment consumes the root library, so its lockfile was updated for the new root dependency graph (including unifying serde at 1.0.228); ACP/runtime versions and experiment source remain unchanged. Locked experiment build/check/format/Clippy passed. All 17 adversarial child cases and all five OpenCode 1.18.30 local-stub/unavailable scenarios passed (text, project instructions, permission denial, cancellation and unavailable service), including direct-child/descendant cleanup checks. No live provider was contacted.

No live model turn, project configuration write, proxy/service change or login-store access. Route/model: no production run; test alias only. No direct-tool coding comparison applies (P2.6 owns it). Only macOS is tested. Explicit stdin and caller-supplied readers remain blocking interfaces; P2.2 must make application input acquisition interruptible. No claim of OS containment, released binary installation or effective runtime readiness follows from these fixtures.

## Independent review

A read-only reviewer found and verified fixes for project-config trust elevation, discarded effective mode/provenance, empty-key validation ambiguity and a prompt-file FIFO swap race. All four resolved with regression coverage; independent formatting/Clippy/all 26 tests passed. Grok completed one review on [PR #15](https://github.com/awesomejt/agent-harness/pull/15): 0 blockers, 1 concern (Medium) and 2 nits (Low). Resolved all three: shared safe config-file loader with regression coverage; canonical URL spelling check and edge cases; exact expected errors in negative fixtures. The concern does not affect an executing CLI (not yet implemented) and is not Critical/High. Post-fix all 27 tests, formatting, Clippy and release smoke passed; no further Grok review is required under the Git workflow.

## Dependency inventory

Pinned direct dependencies: serde 1.0.228 with derive, serde_json 1.0.145, url 2.5.8 and Unix-only libc 0.2.177. URL parsing delegates authority/IPv6/credential handling to the structured parser, avoiding a handwritten URL parser. No ACP/async dependency is added to production. Cargo.lock contains the exact graph; Rust 1.88 builds the locked graph. Release attribution remains P2.5/P4.5 work, including Unicode notices. Local Cargo package metadata reports:

| Package | Version | License expression |
|---|---|---|
| displaydoc | 0.2.7 | MIT OR Apache-2.0 |
| form_urlencoded | 1.2.2 | MIT OR Apache-2.0 |
| icu_collections | 2.4.0 | Unicode-3.0 |
| icu_locale_core | 2.4.0 | Unicode-3.0 |
| icu_normalizer | 2.4.0 | Unicode-3.0 |
| icu_normalizer_data | 2.4.0 | Unicode-3.0 |
| icu_properties | 2.4.0 | Unicode-3.0 |
| icu_properties_data | 2.4.0 | Unicode-3.0 |
| icu_provider | 2.4.0 | Unicode-3.0 |
| idna | 1.1.0 | MIT OR Apache-2.0 |
| idna_adapter | 1.2.2 | Apache-2.0 OR MIT |
| itoa | 1.0.18 | MIT OR Apache-2.0 |
| libc | 0.2.177 | MIT OR Apache-2.0 |
| litemap | 0.8.3 | Unicode-3.0 |
| memchr | 2.8.3 | Unlicense OR MIT |
| percent-encoding | 2.3.2 | MIT OR Apache-2.0 |
| potential_utf | 0.1.6 | Unicode-3.0 |
| proc-macro2 | 1.0.107 | MIT OR Apache-2.0 |
| quote | 1.0.47 | MIT OR Apache-2.0 |
| ryu | 1.0.23 | Apache-2.0 OR BSL-1.0 |
| serde | 1.0.228 | MIT OR Apache-2.0 |
| serde_core | 1.0.228 | MIT OR Apache-2.0 |
| serde_derive | 1.0.228 | MIT OR Apache-2.0 |
| serde_json | 1.0.145 | MIT OR Apache-2.0 |
| smallvec | 1.16.4 | MIT OR Apache-2.0 |
| stable_deref_trait | 1.2.1 | MIT OR Apache-2.0 |
| syn | 2.0.119 | MIT OR Apache-2.0 |
| syn | 3.0.9 | MIT OR Apache-2.0 |
| synstructure | 0.14.0 | MIT |
| tinystr | 0.8.5 | Unicode-3.0 |
| unicode-ident | 1.0.27 | (MIT OR Apache-2.0) AND Unicode-3.0 |
| url | 2.5.8 | MIT OR Apache-2.0 |
| utf8_iter | 1.0.4 | Apache-2.0 OR MIT |
| writeable | 0.6.4 | Unicode-3.0 |
| yoke | 0.8.4 | Unicode-3.0 |
| yoke-derive | 0.8.4 | Unicode-3.0 |
| zerofrom | 0.1.8 | Unicode-3.0 |
| zerofrom-derive | 0.1.8 | Unicode-3.0 |
| zerotrie | 0.2.5 | Unicode-3.0 |
| zerovec | 0.11.9 | Unicode-3.0 |
| zerovec-derive | 0.11.7 | Unicode-3.0 |
