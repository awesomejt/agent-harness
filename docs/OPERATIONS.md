# Operations and distribution contract

Status: P2.5 first binary runbook for `0.1.0-alpha.1`; later workflow/native-adapter guidance remains prospective. First-use acceptance (P2.6) and holistic phase review (P2.9) remain required. See [release evidence](evidence/p2-5-installable-binary.md).

The [deployment diagram](ARCHITECTURE.md) separates the release pipeline, local executable, installed runtime and external services. Rust library dependencies are linked/packaged for the target as required; binary users do not install Cargo packages manually.

## Installation and prerequisites

Distribute prebuilt harness binaries for explicitly supported OS/architecture targets. Users of these binaries need no Rust/Python toolchain. Cargo source installation may be optional; it is not the only installation path. Include version information, artifact checksums, release notes and dependency/license notices as applicable.

Document OpenCode/other CLI installation and official login separately from harness installation. LiteLLM is an existing service with its own endpoint, model aliases and optional environment key reference. Do not imply the harness installs, upgrades or manages the proxy service. No automatic provider installation or silent self-update is planned.

### Install v0.1.0-alpha.1

The initial archive target is `aarch64-apple-darwin`, tested on Apple Silicon
macOS 27.0.1. Intel macOS, earlier macOS versions, Linux and Windows are unverified.
The executable links only macOS system libraries; no Rust, Cargo, Python, Node
or OpenCode is required for harness version/help/preview. Coding runs require
OpenCode separately. The artifact has an ad hoc signature, with no Developer ID
signing or notarization. Managed macOS policies may prevent execution; use an
approved local build or wait for signed distribution rather than disable security
controls. Browser/quarantine/Gatekeeper approval was not verified by the terminal
installation smoke.

Download the archive and `SHA256SUMS` from the
[versioned release](https://github.com/awesomejt/agent-harness/releases/tag/v0.1.0-alpha.1)
into an empty directory, or use:

```sh
curl -fLO https://github.com/awesomejt/agent-harness/releases/download/v0.1.0-alpha.1/ah-v0.1.0-alpha.1-aarch64-apple-darwin.tar.gz
curl -fLO https://github.com/awesomejt/agent-harness/releases/download/v0.1.0-alpha.1/SHA256SUMS
shasum -a 256 -c SHA256SUMS
tar -xzf ah-v0.1.0-alpha.1-aarch64-apple-darwin.tar.gz
mkdir -p "$HOME/.local/bin"
# Preserve an existing ah separately before deliberately replacing it.
install -m 755 ah-v0.1.0-alpha.1-aarch64-apple-darwin/ah "$HOME/.local/bin/ah"
export PATH="$HOME/.local/bin:$PATH"
ah --version
ah --help
```

Expect `ah 0.1.0-alpha.1`. Add that PATH entry to your shell startup file if
needed. Keep the extracted `LICENSE`, `THIRD_PARTY_NOTICES.md`, `third-party/`
and `BUILD-INFO.json` alongside your archived download; include them if you
redistribute the executable. Checksums detect corruption; they are not independent
publisher authentication. No package manager, installer script or self-update is
provided in this slice.

### Separate coding prerequisites

Install **OpenCode 1.18.30**, not an automatically selected latest version.
Its [pinned official installer](https://github.com/anomalyco/opencode/blob/v1.18.30/install)
supports an explicit version:

```sh
curl -fLo opencode-install.sh https://raw.githubusercontent.com/anomalyco/opencode/v1.18.30/install
# Inspect the downloaded script, then run:
bash opencode-install.sh --version 1.18.30 --no-modify-path
export PATH="$HOME/.opencode/bin:$PATH"
opencode --version
```

OpenCode's installation is separate from the harness archive. A LiteLLM service
must already expose an authenticated `/v1` endpoint and an existing model alias.
The harness does not deploy the proxy or create aliases. Obtain the endpoint,
alias and key from your operator; do not commit a literal key. In your project,
create `ah.json` (substitute your endpoint/alias):

```json
{
  "version": 1,
  "mode": "local-only",
  "model": "your-existing-alias",
  "litellm": {
    "api_base": "http://your-proxy:4000/v1",
    "api_key_env": "LITELLM_API_KEY"
  }
}
```

Set `LITELLM_API_KEY` in your shell through your normal secret mechanism. No
native cloud login is needed for this slice. Run from the project:

```sh
ah single "Review the parser" --preview
ah single "Fix the parser and run its tests" --permissions trusted
```

Preview uses no model turn or runtime child; exit 0 validates a local plan only.
Execution validates OpenCode version/capabilities and effective routing before a
prompt. Default `deny` grants no tools. `trusted` explicitly authorizes host file
and shell effects; it is not a sandbox. The harness isolates HOME/XDG and ignores
unmanaged OpenCode customizations during execution. Git observation uses macOS
system Git; without Command Line Tools it reports an unavailable baseline, rather
than installing developer tools. No developer toolchain is needed by `ah` itself;
the requested project tests may need their own tools.

Exits: 0 confirmed backend success (independently verify task tests), 1 known
failure, 2 rejected input/capability, 3 confirmed cancellation/deadline, 4 uncertain
outcome. On 4, inspect edits and processes before a new attempt. Never assume an
interrupted attempt made no changes. See [configuration](CONFIGURATION.md) and
[execution](EXECUTION.md) for managed config conflicts and finite cleanup bounds.

### Upgrade, rollback and removal

Download and verify a specific release, retain the old executable/download and
replace only your installed `ah`. The first release uses config schema 1 and no
durable workflow state; older/future schemas must not be silently reinterpreted.
Rollback restores the retained binary; it does not undo project/runtime edits.
Remove `~/.local/bin/ah` and its PATH entry to uninstall. Inspect managed
`opencode.json` fields and `.ah-opencode-owner.json` together before deliberately
reconciling/removing them; uninstall performs no automatic project cleanup.

### Maintainer release procedure

D029 selects manual locked Cargo packaging after evaluating
[cargo-dist](https://axodotdev.github.io/cargo-dist/book/introduction.html).
Its generated multi-stage hosting/installer workflow is deferred until broader
release needs justify it. Build only a clean, reviewed source commit on the
verified native target, with pinned Rust 1.88.0 and Xcode linker tools:

```sh
python3 scripts/release/package.py --output dist/candidate
sh scripts/release/smoke.sh dist/candidate 0.1.0-alpha.1
```

`package.py` fixes the target and deployment build setting, verifies registry
archives against Cargo.lock, refreshes notices from the actual production graph,
records commit/toolchain/lock/binary hashes and checks system-only dylib linkage.
It refuses a dirty checkout or an existing output directory. Python and Rust are
maintainer tools only. The build deployment setting 14.0 is not a test claim for
older macOS. Archives contain conservative full upstream sources to preserve
embedded notices, plus extracted license files and Rust runtime attributions.

Complete PR/Grok review and merge first. Package the merged commit, smoke it,
create a GitHub **pre-release** tag `v0.1.0-alpha.1` pointing to that exact commit,
and upload the archive and its `SHA256SUMS`. Never replace already published
versioned assets; use a new version for corrections. Download the published
assets into a new directory and repeat the checksum/install smoke. Package
checksums in the release and source provenance in `BUILD-INFO.json` are
authoritative for the final artifact. P4.5 owns broader platform/packaging polish.

## Startup and diagnosis

Diagnostics should identify missing binaries, runtime/version incompatibility, unavailable model aliases, unreadable/conflicting config, missing key references, denied permissions and unreachable permitted services. Read-only resolved-plan/sync preview is separate from launching a task. `ah single PROMPT --preview` uses the execution resolver/planner and reports local binary discovery, expected OpenCode 1.18.30, choice sources, permissions and planned managed changes. It launches no child and performs no health checks. Runtime/service/alias availability remains unverified; normal execution performs effective preflight. Set the environment variable named by `litellm.api_key_env` for missing-key errors; install the pinned OpenCode on an absolute PATH entry when discovery reports it missing.

Errors explain what failed, which attempt/route was affected, whether tools may have run, and a next action that does not silently change mode or credentials. Do not suggest cloud fallback as the automatic fix to local-only unavailability.

| Symptom | Required diagnostic / next action |
|---|---|
| Binary not found | Show required runtime and install guidance; do not fetch executables automatically. |
| LiteLLM unavailable/model missing | Show permitted endpoint/model and sanitized error; fix proxy/model config or explicitly choose another permitted mode. |
| Native login rejected | Use the official CLI login flow; never inspect token stores. |
| Permission request cannot be answered | Apply documented noninteractive policy and exit/report denial; do not open a hidden TUI. |
| Managed config conflicts | Show a redacted preview and affected ownership; preserve user content. |
| Stream disconnect/timeout after work | Report uncertain outcome and project inspection/recovery guidance; do not replay automatically. |
| Workflow resume mismatch | Explain changed inputs/config/state and require an explicit phase-defined recovery choice. |

## Project and data handling

The harness works in the selected project, including normal dirty worktrees. It does not automatically stash, reset, clean, commit or roll back user changes. Backend tools may change files as allowed by explicit permissions; preserve that distinction in user docs.

Logs/records must not contain literal credentials. Project code, prompts and tool output can themselves be sensitive; do not enable full transcript retention, telemetry or remote uploading by default. Single-run diagnostics may be transient. Phase 5 chooses durable state location, retention, permissions, inspection and cleanup behavior before persistence ships. User-driven export, if later added, must make included data explicit.

Retain enough sanitized attempt and verification information to explain routing/recovery. Do not claim a universal secret scrubber or sandbox: configured key redaction cannot guarantee removal of every secret echoed by an arbitrary tool. Minimize collection and test known-secret handling.

## Release and maintenance

Follow the repository PR/Grok review workflow. Release documentation must list supported harness/runtime versions, platform constraints, schema/output changes and migration needs. Version machine output in Phase 4 and durable state in Phase 5, before persistence ships; do not silently reinterpret unknown future versions.

Upgrades must preserve user-owned config and workflow evidence. Document recovery/downgrade limitations for incompatible state rather than imply every version is reversible. New adapters require their own tests/live evidence and capability documentation before being advertised as supported.

Build-host adjustment: the initial release build hit a macOS 27 dylib loader
failure in proc macros (`mis-aligned LINKEDIT string pool`). Packaging explicitly
sets `CARGO_PROFILE_RELEASE_STRIP=none`, avoiding Rust's stripping path; see
[upstream Rust issue #157750](https://github.com/rust-lang/rust/issues/157750).
The MSRV and dependency pins remain unchanged.
