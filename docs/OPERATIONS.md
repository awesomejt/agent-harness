# Operations and distribution contract

Status: P4.5 core-MVP runbook for `0.1.0-alpha.2` (D041): the declared platform matrix, installation, separate prerequisites, sample configuration and agents, setup check, upgrade from `0.1.0-alpha.1`, rollback and the maintainer release procedure. All three routing modes, named agents and machine output ship in this artifact. Workflow and additional native-adapter guidance remains prospective. See [P4.5 evidence](evidence/p4-5-mvp-artifacts.md); the first artifact's [P2.5 evidence](evidence/p2-5-installable-binary.md) remains the historical record for alpha.1.

The [deployment diagram](ARCHITECTURE.md) separates the release pipeline, local executable, installed runtime and external services. Rust library dependencies are linked/packaged for the target as required; binary users do not install Cargo packages manually.

## Installation and prerequisites

Distribute prebuilt harness binaries for explicitly supported OS/architecture targets. Users of these binaries need no Rust/Python toolchain. Cargo source installation may be optional; it is not the only installation path. Include version information, artifact checksums, release notes and dependency/license notices as applicable.

Document OpenCode/other CLI installation and official login separately from harness installation. LiteLLM is an existing service with its own endpoint, model aliases and optional environment key reference. Do not imply the harness installs, upgrades or manages the proxy service. No automatic provider installation or silent self-update is planned.

### Supported platforms (D041)

Support is declared only where an actual artifact was installed and run. Rust portability and successful compilation are not support claims.

| Component | Supported for `0.1.0-alpha.2` | Owner |
|---|---|---|
| `ah` executable | `aarch64-apple-darwin` archive, tested on Apple Silicon macOS 27.0.1 | this release |
| Coding runtime | OpenCode **2.2.5** exactly, on an absolute PATH entry; other versions refuse at preflight (exit 2) | installed separately |
| `local-only` / `local-first` primary | An existing LiteLLM `/v1` endpoint, its key and the selected proxy model groups | operator-owned proxy |
| `cloud-only` / `local-first` fallback | OpenCode's built-in `opencode` provider with a Console/Zen API key | user's OpenCode account |
| Git (optional) | macOS system Git for dirty-project reporting; absent Git reports an unavailable baseline | macOS Command Line Tools |

Not supported: Intel macOS (no artifact or test), macOS releases other than 27.0.1 (the 14.0 deployment setting is a build setting, not a test claim), Linux and Windows (no artifact; coding runs refuse non-macOS hosts even from source, and preview reports `execution platform: unsupported`). Developer ID signing, notarization and browser/Gatekeeper installation are not provided.

### Install v0.1.0-alpha.2

The executable links only macOS system libraries; no Rust, Cargo, Python, Node
or OpenCode is required for harness version/help/preview. Coding runs require
OpenCode separately. The artifact has an ad hoc signature, with no Developer ID
signing or notarization. Managed macOS policies may prevent execution; use an
approved local build or wait for signed distribution rather than disable security
controls. Browser/quarantine/Gatekeeper approval was not verified by the terminal
installation smoke.

Download the archive and `SHA256SUMS` from the
[versioned release](https://github.com/awesomejt/agent-harness/releases/tag/v0.1.0-alpha.2)
into an empty directory, or use:

```sh
curl -fLO https://github.com/awesomejt/agent-harness/releases/download/v0.1.0-alpha.2/ah-v0.1.0-alpha.2-aarch64-apple-darwin.tar.gz
curl -fLO https://github.com/awesomejt/agent-harness/releases/download/v0.1.0-alpha.2/SHA256SUMS
shasum -a 256 -c SHA256SUMS
tar -xzf ah-v0.1.0-alpha.2-aarch64-apple-darwin.tar.gz
mkdir -p "$HOME/.local/bin"
# Upgrading? Keep the previous extracted download for rollback (see below).
install -m 755 ah-v0.1.0-alpha.2-aarch64-apple-darwin/ah "$HOME/.local/bin/ah"
export PATH="$HOME/.local/bin:$PATH"
ah --version
ah --help
```

Expect `ah 0.1.0-alpha.2`. Add that PATH entry to your shell startup file if
needed. The archive also holds `INSTALL.md` (this runbook), `examples/` (sample
configuration and agents), `LICENSE`, `THIRD_PARTY_NOTICES.md`, `third-party/`
and `BUILD-INFO.json`. Keep the notices alongside your archived download and
include them if you redistribute the executable. Checksums detect corruption;
they are not independent publisher authentication. No package manager, installer
script or self-update is provided.

Installation copies one executable. It never reads or writes `ah.json`, project
`opencode.json`, ownership receipts, OpenCode's global configuration or login
stores, or any environment/secret file; the archive smoke verifies these stay
byte-for-byte unchanged across an upgrade, every sample preview and a rollback.

### Separate coding prerequisites

Install **OpenCode 2.2.5**, not an automatically selected latest version. Its
[pinned official installer](https://github.com/anomalyco/opencode/blob/v2.2.5/install)
supports an explicit version:

```sh
curl -fLo opencode-install.sh https://raw.githubusercontent.com/anomalyco/opencode/v2.2.5/install
# Inspect the downloaded script, then run:
bash opencode-install.sh --version 2.2.5 --no-modify-path
export PATH="$HOME/.opencode/bin:$PATH"
opencode --version
```

OpenCode's installation is separate from the harness archive. For the LiteLLM
route, a service must already expose an authenticated `/v1` endpoint and an
existing model alias (proxy model group). The harness does not deploy the proxy
or create aliases; obtain the endpoint, alias and key from your operator. For the
native route, create an OpenCode Console/Zen API key and choose a model from the
pinned runtime's built-in `opencode` catalog. Never commit a literal key: export
it through your normal secret mechanism under the name your config references.

### Sample configuration and agents

Copy the sample for your mode into the project as `ah.json` and replace the
`your-*` placeholders. Each sample is validated by the test suite and previewed
from the actual archive by the release smoke.

| Sample | Mode | Needs |
|---|---|---|
| `examples/ah.local-only.json` | LiteLLM only | `LITELLM_API_KEY`, endpoint, alias |
| `examples/ah.cloud-only.json` | native OpenCode only | `OPENCODE_API_KEY`, catalog model |
| `examples/ah.local-first.json` | LiteLLM, one native fallback when unreachable | both keys; uses `litellm.groups` |

```sh
cd /path/to/project
cp ~/Downloads/ah-v0.1.0-alpha.2-aarch64-apple-darwin/examples/ah.local-only.json ah.json
mkdir -p agents   # optional named roles for --agent
cp ~/Downloads/ah-v0.1.0-alpha.2-aarch64-apple-darwin/examples/agents/*.md agents/
```

`agents/coder.md` is a primary role with a `trusted` ceiling and read/search/edit/execute
tools; `agents/reviewer.md` is a specialized `read-only` role. `--agent NAME` loads
only `agents/NAME.md`. See [configuration](CONFIGURATION.md) for every field and
[canonical agents](CONFIGURATION.md#canonical-agents) for the schema.

### Setup check

Run these from the project, in order. The first three make no model request,
network contact or project write.

```sh
ah --version                                   # ah 0.1.0-alpha.2
opencode --version                             # 2.2.5
ah single "Review this project" --preview      # add --agent/--mode as you will run
ah single "Summarize this project's layout" --agent reviewer --permissions trusted
```

Preview exits 0 only for a valid local plan. Check its lines: `execution platform:
macOS (supported)`; `runtime:` discovered OpenCode (it cannot verify the version);
`credentials: environment reference present`; `fallback:` for local-first;
`project instructions:`; `proxy handoff:` for groups; and the `sync:` planned
changes. The last command is the first real turn: the reviewer's read-only ceiling
keeps it to read/search tools, and it confirms the runtime version, service, alias
and key. If anything fails, find the message in [Startup and diagnosis](#startup-and-diagnosis).

Then run real work:

```sh
ah single "Fix the parser and run its tests" --agent coder --permissions trusted
```

Default `deny` grants no tools. `trusted` explicitly authorizes host file and
shell effects within the selected role's ceiling; it is not a sandbox. The
harness isolates HOME/XDG and ignores unmanaged OpenCode customizations during
execution. Git observation uses macOS system Git; without Command Line Tools it
reports an unavailable baseline, rather than installing developer tools. No
developer toolchain is needed by `ah` itself; the requested project tests may
need their own tools.

Exits: 0 confirmed backend success (independently verify task tests), 1 known
failure, 2 rejected input/capability, 3 confirmed cancellation/deadline, 4 uncertain
outcome. On 4, inspect edits and processes before a new attempt. Never assume an
interrupted attempt made no changes. See [configuration](CONFIGURATION.md) and
[execution](EXECUTION.md) for managed config conflicts and finite cleanup bounds.

### Upgrade, rollback and removal

Download and verify a specific release, keep the previous extracted download,
and replace only your installed `ah` with `install -m 755`. Installation never
touches configuration or secrets (above). Config schema 1 is the only schema;
older/future schemas are never silently reinterpreted. No durable workflow state
exists yet.

**From `0.1.0-alpha.1`:**

- Install OpenCode 2.2.5 first. alpha.2 refuses OpenCode 1.18.30 at preflight
  (exit 2, before any prompt or project write); alpha.1 conversely requires 1.18.30.
- Existing local-only `ah.json` files remain valid unchanged. The managed
  `opencode.json` values and `.ah-opencode-owner.json` receipt format are the same,
  so an alpha.1-managed project needs no reconciliation.
- New in alpha.2: `cloud-only` and `local-first` routes (`native` block), LiteLLM
  `group:` references, `--agent` named roles (emitted to `.opencode/agents/NAME.md`
  with `.ah-opencode-agents.json`), `--output jsonl` version-1 records, explicit
  project `AGENTS.md` loading (D040) and refusal of `/command` prompts.
- alpha.1 deleted private runtime state on a best-effort basis. alpha.2 checks
  removal and exits 4 if state may remain. After upgrading, inspect and remove
  stale `ah-runtime-*` directories under the system temporary directory left by
  interrupted alpha.1 runs; they can hold private session/tool state.

**Rollback** reinstalls the retained executable (and, for alpha.1, OpenCode
1.18.30); it does not undo project/runtime edits. alpha.1 has no agent support
and ignores emitted agent files; remove `.opencode/agents/` entries listed in
`.ah-opencode-agents.json` deliberately if you no longer want them.

**Removal**: delete `~/.local/bin/ah` and its PATH entry. Inspect managed
`opencode.json` fields with `.ah-opencode-owner.json`, and emitted agents with
`.ah-opencode-agents.json`, before deliberately reconciling or removing them;
uninstall performs no automatic project cleanup.

### Native cloud-only (P3.2)

Use the [native configuration example](CONFIGURATION.md#native-opencode-route-p32--d032) or `examples/ah.cloud-only.json`, install OpenCode 2.2.5 on an absolute PATH entry, and export a valid OpenCode Console/Zen API key under the configured `native.api_key_env` name. Select a model in that runtime's built-in `opencode` catalog. Then run:

```bash
ah single "Review this project" --mode cloud-only --preview
ah single "Fix the parser and run tests" --mode cloud-only --permissions trusted
```

The first command is network-free; the second can consume account credits. Authentication is the official built-in provider's API-key path. Existing `/connect` credentials, subscription logins, OAuth plugins, arbitrary native providers and endpoint overrides are not consumed. The harness uses private HOME/XDG and never copies login stores. Missing/empty selected keys reject before input acquisition or child launch; invalid keys/model access may fail at the native service and do not cause a proxy attempt or retry. Embedded catalog checks do not check account access. Managed LiteLLM config stays untouched, even with `--no-sync`. [P3.2 evidence](evidence/p3-2-native-isolation.md) records non-spending setup/boundary checks; [P3.5 evidence](evidence/p3-5-dual-route-use.md) records live native use and a rejected-key check.

### Local-first (P3.3)

Combine both route blocks as in the [local-first example](CONFIGURATION.md#local-first-route-p33--d034) or `examples/ah.local-first.json` and export both key references. Execution first makes one bounded TCP connect to the LiteLLM host/port (no request or credential sent). If the proxy cannot be resolved or reached, `ah` runs exactly one native attempt, which can consume account credits; progress shows `attempt=2 fallback from attempt=1` and the final line names the fallback. If the proxy is reachable, the run is local, and later local failures (missing group, rate limit, runtime errors) never fall back. Check `--preview` for the configured fallback target; it makes no network contact.

### Maintainer release procedure

D029 selects manual locked Cargo packaging after evaluating
[cargo-dist](https://axodotdev.github.io/cargo-dist/book/introduction.html);
D041 keeps it for the single declared target. A generated multi-stage
hosting/installer workflow is deferred until a second target or installer is
justified by demand. Build only a clean, reviewed source commit on the verified
native target, with pinned Rust 1.88.0 and Xcode linker tools. Bump the Cargo
package version first; `VERSION` below is that version.

```sh
python3 scripts/release/package.py --output dist/candidate
sh scripts/release/smoke.sh dist/candidate VERSION
```

`package.py` uses a fresh temporary build directory, explicit Cargo/Rust 1.88.0,
rejects compiler/linker/profile environment overrides, verifies Mach-O arm64/minimum
OS metadata, fixes the target and deployment build setting, verifies registry
archives against Cargo.lock, refreshes notices from the actual target-filtered resolve graph (including dev/build dependencies),
records commit/toolchain/lock/binary hashes, checks system-only dylib linkage and
bundles `examples/` (the sample configs plus the repository's `agents/*.md`).
It refuses a dirty checkout or an existing output directory. Python and Rust are
maintainer tools only. The build deployment setting 14.0 is not a test claim for
older macOS. Archives contain complete published registry archives to preserve
embedded notices, plus extracted license files and Rust runtime attributions.

`smoke.sh` installs the archive over an earlier executable in a disposable HOME
with only `ah` on PATH, then verifies the signature, contents, version/help,
network-free preview and redaction, input rejections, a preview of every sample
config with both sample agents, byte-for-byte preservation of HOME/project config
and login-store sentinels, and rollback. It needs no OpenCode or service. Live
coding evidence for a release runs the installed-runtime suites with `--binary`
pointing at the extracted archive executable (see [testing](TESTING.md)).

Complete PR/Grok review and merge first. Package the merged commit, smoke it,
create a GitHub **pre-release** tag `vVERSION` pointing to that exact commit,
and upload the archive and its `SHA256SUMS`. Never replace already published
versioned assets; use a new version for corrections. Download the published
assets into a new directory and repeat the checksum/install smoke. Package
checksums in the release and source provenance in `BUILD-INFO.json` are
authoritative for the final artifact.

## Startup and diagnosis

Diagnostics should identify missing binaries, runtime/version incompatibility, unavailable model aliases, unreadable/conflicting config, missing key references, denied permissions and unreachable permitted services. Read-only resolved-plan/sync preview is separate from launching a task. `ah single PROMPT --preview` uses the execution resolver/planner and reports local binary discovery, expected OpenCode 2.2.5, choice sources, route and configured fallback, permissions and planned managed changes. It launches no child and performs no health checks. Runtime/service/alias availability remains unverified; normal execution performs effective preflight. Set the environment variable named by the selected route's `litellm.api_key_env` or `native.api_key_env` for missing-key errors; install the pinned OpenCode on an absolute PATH entry when discovery reports it missing.

Errors explain what failed, which attempt/route was affected, whether tools may have run, and a next action that does not silently change mode or credentials. Do not suggest cloud fallback as the automatic fix to local-only unavailability.

| Symptom | Required diagnostic / next action |
|---|---|
| Binary not found | Show required runtime and install guidance; do not fetch executables automatically. |
| `preflight failed (requires OpenCode 2.2.5 ...)` (exit 2) | Preview cannot check the runtime version. Run `opencode --version` for the binary preview discovered; install exactly 2.2.5 on an absolute PATH entry ahead of other copies. No prompt was sent and no project file was written. |
| `execution platform: unsupported` / "coding runs currently support tested macOS only" (exit 2) | Only Apple Silicon macOS is supported (D041). Use a supported host; there is no fallback platform. |
| "API key environment reference is missing or empty" (exit 2) | Export the variable named by the selected route's `api_key_env` (local-first needs both) in the shell that runs `ah`. Preview fails the same way and never prints the value. |
| "agent is not defined in project agents/" or another `agent` error with `--agent NAME` (exit 2) | Only `agents/NAME.md` in the selected project is read; the filename must match the canonical `name` exactly. Compare against the packaged `examples/agents/` files. |
| LiteLLM unavailable/model missing | Show permitted endpoint/model and sanitized error; fix proxy/model config or explicitly choose another permitted mode. |
| Native API key or model access rejected (cloud-only or local-first fallback) | Check the value exported under `native.api_key_env` and the account's access to `native.model`. The harness consumes no login store, so `/connect` or CLI login does not help; never inspect token stores. A rejection after prompt submission exits 4 even with 0 grants (P3.5). |
| Provider failure after prompt submission (exit 4, 0 grants) | Seen for a bad key or a missing LiteLLM alias. The outcome is conservatively uncertain (R03-REC1 declined, D039); with `--output jsonl` the result shows `prompt_submitted: true`, `backend_stop: null`, `grants: 0`. Confirm no project change, fix the key or alias, then start a new run. local-first never falls back after the reachability check passes. |
| local-first ran the native fallback unexpectedly | Progress shows `attempt=2`; the LiteLLM host could not be resolved or reached. A mistyped `api_base` host falls back too (D034); correct it or use `--mode local-only`. |
| Project instructions not followed | Preview shows `project instructions:`. Only the selected project's root `AGENTS.md` is loaded (D040); parent-directory, `CLAUDE.md` and `opencode.json` `instructions` are not. Move needed rules into that file. A link to a file outside the project exits 2. |
| "prompt starts with a runtime slash command" (exit 2) | The first word was `/NAME`, which OpenCode would run as a command and not as a task. Rephrase so the prompt starts with other text; a leading path such as `/src/x.rs` is accepted. |
| Permission request cannot be answered | Apply documented noninteractive policy and exit/report denial; do not open a hidden TUI. |
| Managed config conflicts | Show a redacted preview and affected ownership; preserve user content. |
| Stream disconnect/timeout after work | Report uncertain outcome and project inspection/recovery guidance; do not replay automatically. |
| Workflow resume mismatch | Explain changed inputs/config/state and require an explicit phase-defined recovery choice. |

### Headless and CI use (P4.7)

Coding runs never prompt. Pass the prompt inline or with `--prompt-file PATH`; stdin is read only for `--prompt-file -`, so redirect it from `/dev/null` otherwise. Permission requests get the noninteractive `deny`/`trusted` policy, never a TTY prompt. Always set `--timeout-secs` and use `--output jsonl` for automation. stdout then carries only [version-1 records](EXECUTION.md#p47-machine-output-d039); keep stderr as a human log.

```bash
ah single --prompt-file task.txt --project . --timeout-secs 900 --output jsonl \
  </dev/null >ah-records.jsonl 2>ah-diagnostics.log
status=$?
# The exit code is authoritative; the last record is the result when present.
tail -n 1 ah-records.jsonl | jq -e 'select(.v == 1 and .type == "result") | .outcome'
case $status in
  0) echo "backend turn succeeded; run your own verification (tests are not implied)" ;;
  4) echo "uncertain: inspect project changes before any manual rerun"; exit 1 ;;
  *) exit "$status" ;;
esac
```

Do not retry automatically on exit 1, 3 or 4: the harness never replays a submitted prompt, and a manual rerun is a new run that may repeat effects. Refuse records whose `v` is not 1. A missing result line (abrupt termination or blocked stdout) leaves only the exit code. `trusted` grants host file/shell access; reserve it for disposable CI checkouts.

## Project and data handling

The harness works in the selected project, including normal dirty worktrees. It does not automatically stash, reset, clean, commit or roll back user changes. Backend tools may change files as allowed by explicit permissions; preserve that distinction in user docs.

Logs/records must not contain literal credentials. Project code, prompts and tool output can themselves be sensitive; do not enable full transcript retention, telemetry or remote uploading by default. Single-run diagnostics may be transient. Phase 5 chooses durable state location, retention, permissions, inspection and cleanup behavior before persistence ships. User-driven export, if later added, must make included data explicit.

Retain enough sanitized attempt and verification information to explain routing/recovery. Do not claim a universal secret scrubber or sandbox: configured key redaction cannot guarantee removal of every secret echoed by an arbitrary tool. Minimize collection and test known-secret handling.

## Release and maintenance

Follow the repository PR/Grok review workflow. Release documentation must list supported harness/runtime versions, platform constraints, schema/output changes and migration needs. Machine output is versioned by D039 (`v` 1); version durable state in Phase 5, before persistence ships; do not silently reinterpret unknown future versions.

Upgrades must preserve user-owned config and workflow evidence. Document recovery/downgrade limitations for incompatible state rather than imply every version is reversible. New adapters require their own tests/live evidence and capability documentation before being advertised as supported.

Build-host adjustment: the initial release build hit a macOS 27 dylib loader
failure in proc macros (`mis-aligned LINKEDIT string pool`). Packaging explicitly
sets `CARGO_PROFILE_RELEASE_STRIP=none`, avoiding Rust's stripping path; see
[upstream Rust issue #157750](https://github.com/rust-lang/rust/issues/157750).
The MSRV and dependency pins remain unchanged.
