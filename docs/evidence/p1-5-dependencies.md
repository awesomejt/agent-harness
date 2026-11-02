# P1.5 — Resolved dependency/license inventory

Date: 2026-11-02. Scope: the committed standalone ACP experiment lockfile, not a released `ah` binary. [Acceptance preparation](p1-5-integration-acceptance.md) and D023 select the stack. Registry archives were fetched/verified by locked Cargo metadata; extracted manifests and the license/attribution files listed below were read. `macOS graph` means reachable in `cargo metadata --filter-platform aarch64-apple-darwin` (including build/proc-macro dependencies), not proof every package contributes linked code. Other targets/features are not tested.

Lockfile SHA-256: `d3f759aa999c9a38ab50a55edad38a0752351341d256ede1d39a199c7869792a`. There are 127 registry packages in the full resolved inventory; 101 are reachable on the tested target, plus the experiment and local harness packages (Apache-2.0). No missing license declaration or declared MSRV above 1.88 was found. Missing MSRV declarations do not prove compatibility; the locked target build is the evidence.

## Exceptions and release handoff

- `agent-client-protocol-schema` 1.13.0 omits its license text from the archive. `.cargo_vcs_info.json` records commit `97fcb0f5b88567dd91d585ea6885761365a6aa7b`; the matching [upstream LICENSE](https://github.com/agentclientprotocol/agent-client-protocol/blob/97fcb0f5b88567dd91d585ea6885761365a6aa7b/LICENSE) was retrieved/read: Apache-2.0, copyright 2025 Zed Industries, Inc. and contributors. Include that material in the production notice bundle.
- `r-efi` 6.0.0 is in the all-target lockfile but absent from the tested macOS graph. Its archive has no license text; the recorded [source commit](https://github.com/r-efi/r-efi/tree/7e1b0322d31d625f81a5656096330934f9cd835d) also has no root license file. Its manifest offers MIT OR Apache-2.0 OR LGPL-2.1-or-later. Attribution-text verification is still required if a later release target activates it; do not treat it as cleared by this macOS audit.
- `unicode-ident` requires Unicode-3.0 in addition to its MIT/Apache choice. Read/preserve `LICENSE-UNICODE`; do not reduce its expression to MIT alone. `ryu` offers Apache-2.0 OR BSL-1.0; `jiff`/`memchr` offer MIT as an alternative to Unlicense. Slash-separated legacy expressions are reproduced as published.
- This is a source/license inventory, not a vulnerability scan or complete distribution notice bundle. P2.5 must regenerate for the actual production manifest, enabled features and release target, select license alternatives, include full license/copyright/NOTICE material (including source-embedded notices), and include Rust toolchain/runtime notices as applicable. Keep build-time material traceable too. No upstream source or binary is redistributed by P1.5; production dependencies remain unlinked until their consumers land.

## Reproduction

Run `cargo metadata --locked --format-version 1 --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml` and again with `--filter-platform aarch64-apple-darwin`. For each registry package, resolve its `manifest_path`, inspect `license`, `rust_version`, `.cargo_vcs_info.json` and the listed files under that archive directory. Compare target reachability through `resolve.nodes`, not `packages` (the latter may include inactive packages). Hash the committed lockfile with SHA-256. A changed lockfile/feature set needs a refreshed inventory; this file does not authorize additional platform support.

## Archive inventory

| Package | Version | macOS graph | Declared license | Located license/attribution files |
|---|---|---|---|---|
| agent-client-protocol | 3.6.0 | yes | Apache-2.0 | `LICENSE` |
| agent-client-protocol-derive | 3.6.0 | yes | Apache-2.0 | `LICENSE` |
| agent-client-protocol-schema | 1.13.0 | yes | Apache-2.0 | **Absent; see exceptions** |
| android_system_properties | 0.1.6 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| anyhow | 1.0.104 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| autocfg | 1.5.1 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| base64 | 0.22.1 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| bitflags | 1.3.2 | yes | MIT/Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| bs58 | 0.5.1 | yes | MIT/Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| bumpalo | 3.20.3 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| bytes | 1.12.1 | yes | MIT | `LICENSE` |
| cc | 1.10.0 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| cfg-if | 1.0.5 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| chrono | 0.4.45 | yes | MIT OR Apache-2.0 | `LICENSE.txt` |
| convert_case | 0.10.0 | yes | MIT | `LICENSE` |
| core-foundation-sys | 0.8.7 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| darling | 0.23.0 | yes | MIT | `LICENSE` |
| darling_core | 0.23.0 | yes | MIT | `LICENSE` |
| darling_macro | 0.23.0 | yes | MIT | `LICENSE` |
| defmt | 1.2.0 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| defmt-macros | 1.2.0 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| defmt-parser | 1.1.0 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| deranged | 0.5.9 | yes | MIT OR Apache-2.0 | `LICENSE-Apache`, `LICENSE-MIT` |
| derive_more | 2.1.1 | yes | MIT | `LICENSE` |
| derive_more-impl | 2.1.1 | yes | MIT | `LICENSE` |
| dyn-clone | 1.0.20 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| equivalent | 1.0.3 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| errno | 0.3.14 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| fastrand | 2.5.0 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| find-msvc-tools | 0.1.15 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| fixedbitset | 0.5.7 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-channel | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-concurrency | 7.7.1 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-core | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-io | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-lite | 2.6.1 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT`, `LICENSE-THIRD-PARTY` |
| futures-macro | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-sink | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-task | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| futures-util | 0.3.34 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| getrandom | 0.4.3 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| hashbrown | 0.12.3 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| hashbrown | 0.17.1 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| heck | 0.5.0 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| hex | 0.4.3 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| iana-time-zone | 0.1.65 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| iana-time-zone-haiku | 0.1.2 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| ident_case | 1.0.1 | yes | MIT/Apache-2.0 | `LICENSE` |
| indexmap | 1.9.3 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| indexmap | 2.14.2 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| itoa | 1.0.18 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| jiff | 0.2.38 | yes | Unlicense OR MIT | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| jiff-core | 0.1.1 | yes | Unlicense OR MIT | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| jiff-static | 0.2.38 | no | Unlicense OR MIT | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| jiff-tzdb | 0.1.9 | no | Unlicense OR MIT | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| jiff-tzdb-platform | 0.1.3 | no | Unlicense OR MIT | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| js-sys | 0.3.107 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| libc | 0.2.177 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| log | 0.4.35 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| memchr | 2.8.3 | yes | Unlicense OR MIT | `COPYING`, `LICENSE-MIT`, `UNLICENSE` |
| mio | 1.1.0 | yes | MIT | `LICENSE` |
| num-conv | 0.2.2 | yes | MIT OR Apache-2.0 | `LICENSE-Apache`, `LICENSE-MIT` |
| num-traits | 0.2.19 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| once_cell | 1.21.4 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| parking | 2.2.1 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT`, `LICENSE-THIRD-PARTY` |
| pin-project | 1.1.13 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| pin-project-internal | 1.1.13 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| pin-project-lite | 0.2.17 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| portable-atomic | 1.15.0 | no | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| portable-atomic-util | 0.2.8 | no | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| powerfmt | 0.2.1 | yes | MIT OR Apache-2.0 | `LICENSE-Apache`, `LICENSE-MIT` |
| proc-macro2 | 1.0.107 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| quote | 1.0.47 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| r-efi | 6.0.0 | no | MIT OR Apache-2.0 OR LGPL-2.1-or-later | **Absent; see exceptions** |
| ref-cast | 1.0.27 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| ref-cast-impl | 1.0.27 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| rustc-hash | 2.1.3 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| rustc_version | 0.4.1 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| rustversion | 1.0.23 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| ryu | 1.0.23 | yes | Apache-2.0 OR BSL-1.0 | `LICENSE-APACHE`, `LICENSE-BOOST` |
| schemars | 0.9.0 | yes | MIT | `LICENSE` |
| schemars | 1.2.3 | yes | MIT | `LICENSE` |
| semver | 1.0.28 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde | 1.0.229 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_core | 1.0.229 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_derive | 1.0.229 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_json | 1.0.145 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_with | 3.22.0 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| serde_with_macros | 3.22.0 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| shlex | 2.0.1 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| signal-hook-registry | 1.4.8 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| slab | 0.4.12 | yes | MIT | `LICENSE` |
| smallvec | 1.16.4 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| strsim | 0.11.1 | yes | MIT | `LICENSE` |
| strum | 0.28.0 | yes | MIT | `LICENSE` |
| strum_macros | 0.28.0 | yes | MIT | `LICENSE` |
| syn | 2.0.119 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| syn | 3.0.9 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| thiserror | 2.0.21 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| thiserror-impl | 2.0.21 | yes | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| time | 0.3.55 | yes | MIT OR Apache-2.0 | `LICENSE-Apache`, `LICENSE-MIT` |
| time-core | 0.1.9 | yes | MIT OR Apache-2.0 | `LICENSE-Apache`, `LICENSE-MIT` |
| time-macros | 0.2.32 | yes | MIT OR Apache-2.0 | `LICENSE-Apache`, `LICENSE-MIT` |
| tinyvec | 1.13.3 | yes | Zlib OR Apache-2.0 OR MIT | `LICENSE-APACHE.md`, `LICENSE-MIT.md`, `LICENSE-ZLIB.md` |
| tokio | 1.48.0 | yes | MIT | `LICENSE` |
| tokio-macros | 2.6.1 | yes | MIT | `LICENSE` |
| tokio-util | 0.7.16 | yes | MIT | `LICENSE` |
| tracing | 0.1.44 | yes | MIT | `LICENSE` |
| tracing-attributes | 0.1.31 | yes | MIT | `LICENSE` |
| tracing-core | 0.1.36 | yes | MIT | `LICENSE` |
| unicode-ident | 1.0.27 | yes | (MIT OR Apache-2.0) AND Unicode-3.0 | `LICENSE-APACHE`, `LICENSE-MIT`, `LICENSE-UNICODE` |
| unicode-segmentation | 1.13.3 | yes | MIT OR Apache-2.0 | `COPYRIGHT`, `LICENSE-APACHE`, `LICENSE-MIT` |
| unicode-xid | 0.2.6 | yes | MIT OR Apache-2.0 | `COPYRIGHT`, `LICENSE-APACHE`, `LICENSE-MIT` |
| uuid | 1.26.1 | yes | Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-MIT` |
| wasi | 0.11.1+wasi-snapshot-preview1 | no | Apache-2.0 WITH LLVM-exception OR Apache-2.0 OR MIT | `LICENSE-APACHE`, `LICENSE-Apache-2.0_WITH_LLVM-exception`, `LICENSE-MIT` |
| wasm-bindgen | 0.2.130 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| wasm-bindgen-macro | 0.2.130 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| wasm-bindgen-macro-support | 0.2.130 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| wasm-bindgen-shared | 0.2.130 | no | MIT OR Apache-2.0 | `LICENSE-APACHE`, `LICENSE-MIT` |
| windows-core | 0.62.2 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
| windows-implement | 0.60.2 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
| windows-interface | 0.59.3 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
| windows-link | 0.2.1 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
| windows-result | 0.4.1 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
| windows-strings | 0.5.1 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
| windows-sys | 0.61.2 | no | MIT OR Apache-2.0 | `license-apache-2.0`, `license-mit` |
