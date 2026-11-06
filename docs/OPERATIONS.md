# Operations and distribution contract

Status: P4.5 core-MVP runbook for `0.1.0-alpha.2` (D041): the declared platform matrix, installation, separate prerequisites, sample configuration and agents, setup check, upgrade from `0.1.0-alpha.1`, rollback and the maintainer release procedure. All three routing modes, named agents and machine output ship in that artifact. Phase 5 adds trusted verification gates (D043), ordered sequences and durable resume (D044); Phase 6 adds bounded Ralph loops (D045). The sequence and Ralph runbooks below apply to current source, not to the published alpha.2 artifact. The Claude runtime section (P7.2, D048) also applies to current source only; other native adapters remain prospective. See [P4.5 evidence](evidence/p4-5-mvp-artifacts.md); the first artifact's [P2.5 evidence](evidence/p2-5-installable-binary.md) remains the historical record for alpha.1.

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

### Native Claude cloud-only (P7.2)

Install Claude Code 2.1.314 with its official installer so `claude` is on an absolute PATH entry, then log in with `claude` itself. The harness uses that existing login and never handles it ([D047](../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login)). Use the [Claude configuration](CONFIGURATION.md#native-claude-runtime-p72--d048) and run:

```bash
ah single "Explain the build steps in this project." --preview
ah single "Explain the build steps in this project."
```

The first command launches nothing. The second draws on the operator's Claude plan or usage credits. `deny` (the default) offers no tool, so Claude answers from the prompt and the project `AGENTS.md` alone. `--permissions trusted` lets Claude read, search, edit and run shell commands with host privileges and no OS sandbox. The harness grants each prompted edit or command once, and Claude Code allows project reads and read-only commands by itself. Its shell sources a snapshot of the operator's login shell (`PATH`, aliases, functions) ([D049](../DECISIONS.md#2026-11-06--d049-claude-trusted-permissions-through-the-host-prompt-path)). Named agents, sequences and Ralph are not yet supported on Claude. A missing or expired login, an unavailable model or a rate limit exits 1 with no retry or fallback. A different Claude Code version, admin-managed settings or any configured setting source refuses before the prompt with exit 2 ([D048](../DECISIONS.md#2026-11-06--d048-claude-runtime-launch-preflight-and-deny-profile-single-runs)).

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
| Claude runtime refuses with `preflight failed` | Check `claude --version` is exactly 2.1.314, and that no admin-managed (policy) settings apply. The harness loads no user, project or local settings, MCP servers or plugins, so changing those does not help. |
| Claude runtime exits 1 after `prompt submitted` | Run `claude` directly to confirm the login and model access; the harness never reads the login and does not show the CLI's error text. |
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

Prefer a harness gate over the generic exit 0 branch. Declare the project check in `ah.json` `checks` and add `--verify NAME` (D043). Exit 0 then means the backend turn succeeded *and* the check passed. Exit 1 with `.verification.status` `failed`, `timed_out` or `error` means the agent finished but the check did not pass. `.verification.agent_outcome` keeps the two apart. The check's own output is on stderr. It runs with host privileges in the checkout, so declare only commands you would run there yourself.

```bash
jq -e 'select(.type == "result") | .verification.status == "passed"' ah-records.jsonl
```

Do not retry automatically on exit 1, 3 or 4: the harness never replays a submitted prompt, and a manual rerun is a new run that may repeat effects. Refuse records whose `v` is not 1. A `succeeded` result for an edit task whose attempts report `tool_events: 0` deserves scrutiny: the backend ended its turn without visible tool work (P4.6 R1). Treat it as a reason to check the project, not as a harness failure; never use it to justify a retry. A missing result line (abrupt termination or blocked stdout) leaves only the exit code. `trusted` grants host file/shell access; reserve it for disposable CI checkouts.

### Ordered sequences (P5.2–P5.3)

`ah sequence run prompts/ --permissions trusted --verify test` runs `prompts/N-slug.md` files in numeric order. Each step is a fresh `ah single` run with the same options, so the project files are the only thing that carries over between steps. The run stops at the first step whose agent does not succeed or whose check does not pass, and exits with that step's code. A step file may begin with a `---` block that sets `agent: NAME` or, when `--verify` is given, `verify: CHECK`. Run `--preview` first: it lists each step's hash, agent, route and check, and launches nothing.

Each run prints its run ID and keeps a record in `$XDG_STATE_HOME/agent-harness/sequences/` (else `~/.local/state/agent-harness/`), outside the project, readable only by you. Records hold names, hashes, routes, outcomes and check status, never prompt text, responses, check output or keys. `ah sequence show` lists this project's runs; `ah sequence show RUN_ID` shows every step and attempt and the next action. An `interrupted` run was killed or lost its record write mid-step; its effects are unknown.

To continue a stopped run, pass the same route options to `ah sequence resume RUN_ID`. It re-reads the folder: completed steps must be unchanged, while the stopping step's prompt and later steps can be edited, added or removed (the stopping step keeps its name). If the stopping step never submitted its prompt, resume retries it. Otherwise inspect the project and choose: `--retry` runs a new agent attempt, `--accept` records the step as done without an agent turn (a gated step must pass its check again, with the same `--verify` name). A new `run` always starts at step 1 and lists unfinished runs. Only one sequence or Ralph run can act on a project at a time (the lock is shared); a second gets exit 2 before launching. Running `ah single` alongside a sequence in the same project is unsupported and not detected. Delete record files yourself when no sequence is running; there is no pruning command. See [WORKFLOWS](WORKFLOWS.md#durable-records-and-resume).

**Locks.** The project lock lives beside the records under `locks/` in the same state root. A second `run` or `resume` for that project exits 2 with `another sequence or Ralph run holds this project's lock` before launching. If a harness process dies without releasing the lock, inspect `ah sequence show RUN_ID` (or list runs with `show --project PATH`); when no process is running, remove the stale lock file yourself. New launches refuse state directories or lock files that are not owned by you or are group/world accessible (exit 2).

**Interrupted runs.** Status `interrupted` means the step was active when the process lost control (signal, crash or an incomplete record write). Treat project effects as unknown: use `show` attempt lines (`unknown` for interrupted attempts) and inspect the checkout before `--retry` or `--accept`. Do not assume a step with zero tool events made no edits (see the verification paragraph above).

**Verification in sequences.** Declare checks in `ah.json` and pass `--verify NAME` on `run` and `resume` when gating applies. Step frontmatter may set `verify: OTHER` to substitute another declared check for that step only; it never disables gating. A stopping step whose last attempt was gated requires `--verify` with the same check name on every resume path (`--retry`, `--accept`, or bare resume when effects are possible). Resume also refuses (exit 2, nothing launched) when that check's program or arguments changed since the step's last attempt; restore the check or start a new run.

### Ralph loops (P6.2–P6.4)

`ah ralph run TASK.md --permissions trusted --verify test --config ../ah.json` repeats fresh single runs of one task file until the agent claims completion (a final response line of exactly `AH-RALPH-COMPLETE`) and the `test` check passes. Run `--preview` first. Bounds are `--max-iterations` (default 10, at most 100 per run) and `--max-runtime-secs` (default 3600 per invocation), which also caps each iteration's `--timeout-secs`. Write the task with an explicit scope and stopping rule (see [WORKFLOWS use guidance](WORKFLOWS.md#ralph-loop)). With `--permissions trusted`, keep the config outside the project, because the agent can read an in-project `ah.json` and its check.

Records are `ralph/RUN_ID.json` (run IDs start with `r`) beside the sequence records, private and outside the project. `ah ralph show` lists this project's runs. `ah ralph show RUN_ID` prints every invocation and iteration (outcome, claim, check status, route, hashes, backend-reported cost when known) and the next command. An accept row shows its route policy as `n/a (no agent turn)`.

- **Outcomes.** `completed` (exit 0): a claim's check passed, or an operator `--accept` passed the check. `exhausted` (exit 1): a bound was reached at an iteration boundary without completion, including the 100-recorded-iteration limit. `stopped`: an iteration did not succeed, a check ended `error` or `cancelled`, a deadline was reached mid-turn (exit 3 or 4), or a signal arrived. A rejected claim (check `failed` or `timed_out`) is not a stop; the next iteration is the bounded repair.
- **Resume.** `ah ralph resume RUN_ID --verify test` re-reads the task file from its recorded path, so you can steer the task between invocations. Bare resume continues only when the last iteration had no possible effects or the loop would have continued. After a submitted failure, a deadline, an interrupted iteration or a check that stopped the run, inspect the project and pass `--retry` (new agent iteration) or `--accept` (no agent turn; the check must pass). A reached iteration bound needs `--max-iterations` greater than the counted iterations; `--accept` needs no larger bound. Resume refuses (exit 2, record unchanged) a check whose program or arguments changed since it was recorded; restore it or start a new run. A run that reached 100 recorded iterations cannot be resumed. A completed run's resume exits 0 even when the task file is gone. Each invocation has its own wall bound; resume does not inherit the previous one.
- **Locks and interruption.** Ralph takes the same per-project lock as sequences, and the lock and interrupted-run guidance above applies. An `interrupted` iteration's submission and effects are unknown; inspect the checkout before choosing.

## Project and data handling

The harness works in the selected project, including normal dirty worktrees. It does not automatically stash, reset, clean, commit or roll back user changes. Backend tools may change files as allowed by explicit permissions; preserve that distinction in user docs.

Logs/records must not contain literal credentials. Project code, prompts and tool output can themselves be sensitive; do not enable full transcript retention, telemetry or remote uploading by default. Single-run diagnostics may be transient. Sequence records (D044, P5.3) are private files outside the project, kept until the user deletes them, with the content limits above. User-driven export, if later added, must make included data explicit.

Retain enough sanitized attempt and verification information to explain routing/recovery. Do not claim a universal secret scrubber or sandbox: configured key redaction cannot guarantee removal of every secret echoed by an arbitrary tool. Minimize collection and test known-secret handling.

## Release and maintenance

Follow the repository PR/Grok review workflow. Release documentation must list supported harness/runtime versions, platform constraints, schema/output changes and migration needs. Machine output is versioned by D039 (`v` 1) and sequence records by D044 (`v` 1); unknown versions are refused, never silently reinterpreted.

Upgrades must preserve user-owned config and workflow evidence. Document recovery/downgrade limitations for incompatible state rather than imply every version is reversible. New adapters require their own tests/live evidence and capability documentation before being advertised as supported.

Build-host adjustment: the initial release build hit a macOS 27 dylib loader
failure in proc macros (`mis-aligned LINKEDIT string pool`). Packaging explicitly
sets `CARGO_PROFILE_RELEASE_STRIP=none`, avoiding Rust's stripping path; see
[upstream Rust issue #157750](https://github.com/rust-lang/rust/issues/157750).
The MSRV and dependency pins remain unchanged.
