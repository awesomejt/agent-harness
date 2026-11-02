# Third-party notices

This distribution includes agent-harness under Apache-2.0 (see LICENSE).
`third-party/inventory.json` records the locked registry packages reachable in
Cargo's target-filtered resolve graph, including dev/build/proc-macro dependencies.
This conservative inventory does not claim all packages are linked into `ah`.

For dual-licensed dependencies, choose MIT where offered; otherwise Apache-2.0
where offered. Unicode-3.0 applies to Unicode-only packages and additionally to
unicode-ident. No LGPL alternative is selected. Preserve all additional
attributions and third-party notices supplied by upstream.

`third-party/<name>-<version>/` contains the archive's license, copyright,
COPYING and NOTICE files (including nested files). Complete, unchanged registry
source archives are also included under `third-party/sources/`, verified against
Cargo.lock checksums. These preserve source-embedded copyright/license notices
and third-party material beyond filename-based collection. The full source files
containing the futures-channel BSD queue notice, schemars copied regex MIT
notice and serde_json lexical attribution are also exposed under each package's
`embedded-notices/` directory for direct reading. Each `.crate` is a
gzip tar archive; extract with `tar -xzf NAME.crate` to inspect it.

agent-client-protocol-schema 1.13.0 omits its Apache-2.0 license text from its
registry archive. `supplemental/agent-client-protocol-schema-LICENSE` supplies
the matching upstream text from commit
97fcb0f5b88567dd91d585ea6885761365a6aa7b, retrieved from
https://github.com/agentclientprotocol/agent-client-protocol/blob/97fcb0f5b88567dd91d585ea6885761365a6aa7b/LICENSE.

`third-party/rust-1.88.0/` preserves the installed toolchain's full copyright
and license resources, including standard-library and compiler runtime
attributions. The toolchain itself is not bundled. OpenCode, LiteLLM and macOS
system libraries are separate prerequisites, not redistributed here.

Keep this notice bundle with redistributions. This is attribution material,
not a vulnerability assessment or a claim that other targets are cleared.
