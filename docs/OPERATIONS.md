# Operations and distribution contract

Status: intended operator experience, not an executable runbook. Installation URLs, supported targets, exact diagnostic commands and upgrade steps are finalized with tested artifacts in Phases 2/4. See [documentation map](README.md) for decision owners.

The [deployment diagram](ARCHITECTURE.md) separates the release pipeline, local executable, installed runtime and external services. Rust library dependencies are linked/packaged for the target as required; binary users do not install Cargo packages manually.

## Installation and prerequisites

Distribute prebuilt harness binaries for explicitly supported OS/architecture targets. Users of these binaries need no Rust/Python toolchain. Cargo source installation may be optional; it is not the only installation path. Include version information, artifact checksums, release notes and dependency/license notices as applicable.

Document OpenCode/other CLI installation and official login separately from harness installation. LiteLLM is an existing service with its own endpoint, model aliases and optional environment key reference. Do not imply the harness installs, upgrades or manages the proxy service. No automatic provider installation or silent self-update is planned.

Initial binary support covers one tested platform; the core MVP declares its broader tested matrix. Evaluate cargo-dist in Phase 2. Package-manager distribution, signing/notarization requirements and upgrade/rollback instructions are finalized for the declared targets rather than claimed in advance.

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
