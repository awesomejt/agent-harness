# DECISIONS.md

Living record of important design decisions for agent-harness.

Entries record design intent, not implementation completion. Earlier entries remain historical; D009 revises D007 scope, D010 clarifies D004 execution paths, and D015–D016 align the implementation blueprint and ownership boundaries with Rust. New decisions identify superseded scope and the phase that must supply validation.

## 2026-11-01 — D001: Name

- **Decision**: Repository and project name is `agent-harness`. CLI command is `ah` (or `agent-harness`).
- **Rationale**: Explicit about the role; easy to search; leaves room for modes, agent sync, fallback, and Ralph loops.

## 2026-11-01 — D002: LiteLLM scope

- **Decision**: LiteLLM is used only for local models, open-weight subscriptions, and OpenRouter. It is **not** used as a proxy for cloud subscription traffic that would violate provider ToS.
- **Rationale**: Avoid account suspension or request refusal. Native CLIs are driven directly for those providers.

## 2026-11-01 — D003: Operational modes

- **Decision**: Support three modes via CLI flag (MVP) and later via per-prompt front-matter:
  - `local-only` — LiteLLM only.
  - `cloud-only` — native CLIs only.
  - `local-first` — LiteLLM first, native CLI fallback on failure.
- **Rationale**: Explicit control at the entry point; matches user preference for CLI first, front-matter later.

## 2026-11-01 — D004: Dual-path executor and three capacities

- **Decision**: Two backends — `LiteLLMExecutor` and `NativeCLIExecutor`. Support primary agent, specialized agent, and fallback (fallback only in local-first).
- **Rationale**: Clean separation of ToS-safe routing from direct CLI use; covers the three requested capacities.

## 2026-11-01 — D005: LiteLLM ownership and OpenCode sync

- **Decision**: Harness owns LiteLLM endpoint, model groups, and routing policy. When driving OpenCode in a local-capable mode, sync the provider block into the **project-level** OpenCode config (overrides global OpenCode settings for that project only). Global OpenCode config is left alone. `--no-sync` available.
- **Rationale**: Single source of truth; avoids maintaining two routing configs; keeps other tools/manual sessions unaffected.

## 2026-11-01 — D006: Canonical agent format

- **Decision**: Markdown + YAML frontmatter is the canonical format. Sync maps by name into each provider’s expected location (OpenCode, Claude, Gemini, Grok, Codex TOML, Pi Skills, etc.).
- **Rationale**: Matches the de facto standard already used by OpenCode, Claude Code, Gemini CLI, and Grok Build.

## 2026-11-01 — D007: Original MVP scope (superseded below)

- **Decision**: Start with OpenCode for local models + OpenRouter (via LiteLLM) and direct OpenCode runs. CLI `--mode` flag first. Agent sync for OpenCode. Single / sequence / Ralph modes. Pi and other native CLIs later. Other open-source subscription fallbacks stay inside LiteLLM.
- **Rationale**: Smallest useful surface that exercises the dual-path design and the user’s existing LiteLLM instance.

## 2026-11-01 — D008: Rust and binary installation direction

- **Status**: Accepted implementation direction for planning; concrete dependencies remain open.
- **Decision**: Use Rust for the CLI and target prebuilt platform binaries as the primary installation experience. Keep `agent-harness` as the project/repository name and `ah` as the command. Choose a distinct Cargo package name in Phase 1 because the public package name is occupied.
- **Rationale**: The user prioritizes easy installation, prefers compiled distribution, and is willing to learn Rust with AI assistance. Python runtime management and direct ai-queue code reuse are secondary concerns.
- **Validation**: Phase 1 proves the OpenCode integration; Phase 2 produces the first installable binary. Initial and expanded platform support are declared only with build/run evidence.

## 2026-11-01 — D009: First slice before core MVP

- **Decision**: Phase 2 delivers one real project coding run through OpenCode + LiteLLM in local-only mode. Phase 4 closes the core MVP with all operational modes, configured fallback, and named OpenCode agents. Sequences and Ralph are separate later milestones, followed by additional runtimes and optional resource awareness.
- **Supersedes**: D007, the original requirement to include single/sequence/Ralph in the first MVP; no full-product workflow goal is dropped.
- **Rationale**: Start learning through useful execution quickly. Do not wait for every workflow or provider.
- **Validation**: Each usable phase records representative tasks and direct-tool comparisons in PROJECT.md. Goals and exit evidence are in docs/SPECIFICATION.md and docs/IMPLEMENTATION.md.

## 2026-11-01 — D010: Separate model route from runtime transport

- **Decision**: Preserve LiteLLM and native routes as policy boundaries. OpenCode supplies the coding-agent loop on either route; ACP or another supported interface is its transport. `LiteLLMExecutor` / `NativeCLIExecutor` are conceptual paths, not mandatory concrete type names. Raw HTTP completions alone do not satisfy a coding milestone.
- **Clarifies**: The earlier architecture sketch that equated the LiteLLM path with a raw chat request and native execution with any subprocess.
- **Rationale**: The same OpenCode process can use LiteLLM or a native model target. Mode policy must control effective model routing, including inherited settings and subagent choices.
- **Validation**: Phase 1 tests transport/model control; Phases 2–3 test routing isolation. No custom inner tool loop is planned for MVP.

## 2026-11-01 — D011: Decide at the consuming phase

- **Decision**: Plan the complete product but resolve detailed choices just before the phase that needs them. Give each open question an owner phase and evidence trigger. Record rationale, constraints, alternatives, and superseded decisions as choices are made.
- **Rationale**: Avoid blocking first use on Ralph signals, all provider formats, or scheduling storage.
- **Validation**: PROJECT.md owns task status; the implementation plan owns phase acceptance; this log owns decisions. None is a substitute for the others.

## 2026-11-01 — D012: Selective reuse with a narrow integration experiment

- **Decision**: Treat ai-queue as prior work, not the primary architecture or a required dependency. Evaluate Rust ACP and small adapter/process libraries in Phase 1; adopt only after compatibility and license inspection. ACP is the first candidate, not a locked transport.
- **Rationale**: Useful code exists, but framework defaults must not dictate routing, permissions, or a new inner agent loop.
- **Validation**: Record tested releases, model/permission control, streamed events, cancellation, process cleanup, and live limitations before promoting a candidate.

## 2026-11-01 — D013: Feature review dispositions and supporting scope

- **Decision**: Record the upstream comparison and F01–F26 inventory in docs/FEATURE_REVIEW.md. Add input sources, basic diagnostics/preview, dirty-project preservation, attempt outcomes, machine output and explicit verification coverage within G1–G9 and existing phase boundaries.
- **Rationale**: The prior library review did not systematically cover user-facing feature families. These additions make single/workflow operation usable and inspectable without adopting a new agent runtime.
- **Boundary**: Backend skills/MCP/context behavior remains backend-owned and capability-checked. Session continuation/fork, richer history/export, recipes, hooks/plugins and diff summaries remain candidates. No additional runtime, parallel-team scheduler, automatic worktrees, auto-installer or marketplace is approved by this review.
- **Evidence**: Eight upstream project documentation sets were compared on 2026-11-01; this was not a live compatibility benchmark. Revalidate integration behavior per phase.

## 2026-11-01 — D014: Technical contracts before implementation, concrete schemas at consuming phase

- **Decision**: Maintain docs/README.md as the documentation map, with execution, configuration/agents, workflow state, validation, and operations contracts alongside the existing architecture/specification. Finalize flags, serialized schemas, destinations, tested versions and runbook commands at their consuming phase.
- **Rationale**: Technical coverage should be explicit now without presenting speculative interfaces or untested operational instructions as implemented behavior. This extends D011, not a requirement to freeze all later choices before first use.
- **Validation**: Each phase updates its contract and links executable/live evidence from PROJECT.md. Documentation existence alone does not establish operational readiness.

## 2026-11-01 — D015: Rust modular CLI and explicit MVP acceptance

- **Decision**: Rust is the accepted implementation language. Start with a single Cargo package and a thin CLI over domain, policy, application, project/config and runtime-adapter boundaries. No Python scaffold, embedded Python bridge, ai-queue runtime dependency, mandatory daemon or speculative plugin workspace is required.
- **Design status**: docs/DESIGN.md proposes internal modules/types; docs/ARCHITECTURE.md owns system/component, execution, fallback, lifecycle and deployment diagrams. Concrete Rust APIs, dependency versions, edition/MSRV and transport are validated in Phase 1 rather than frozen by diagram labels.
- **Scope**: AC01–AC11 in docs/SPECIFICATION.md make the existing first-slice/core-MVP acceptance explicit. Core MVP remains single runs through OpenCode with all modes, configured fallback and constrained named agents plus supporting installation/diagnostic/automation behavior. Sequences/Ralph and broader runtimes remain later phases.
- **Rationale**: The feature contract was clear but the software design lacked a Rust blueprint and diagrams. Explicit acceptance prevents supporting features being omitted or later workflows delaying first use.
- **Validation**: Check diagram syntax and documentation/task references now; confirm architecture through Phase 1 experiment and phase-owned implementation evidence. No implementation exists yet.

## 2026-11-01 — D016: Clarify LiteLLM configuration and service ownership

- **Clarifies**: D005 and D010; no change to the permitted model routes or the harness-owned source of desired routing policy.
- **Decision**: The harness owns desired endpoint/group selection, route policy and managed project runtime settings; the existing LiteLLM proxy executes internal routing. Phase 2 uses an existing alias. Phase 3 defines group representation, validation and any configuration handoff before claiming proxy configuration synchronization.
- **Boundary**: Ownership of desired routing is not automatic privilege to install, restart or live-reconfigure the proxy service. Project-only OpenCode writes, environment key references and native-route isolation remain mandatory.
- **Rationale**: Earlier shorthand could imply service management or a raw-completion coding runtime. The diagrams distinguish control configuration, runtime model traffic and external service operation.
- **Validation**: P2.3 covers effective project routing; P3.3 records how group configuration is represented and matched to the proxy. Unsupported/unverified effective routing is refused rather than assumed.

## 2026-11-01 — D017: Execution plan and single-source task structure

- **Decision**: Keep mutable task status and current work in PROJECT.md. Store static per-task dependencies, scope, gates and acceptance evidence in tasks/ phase files; docs/PROJECT_PLAN.md owns recommended execution order, milestone dependencies, risk checkpoints and small PR boundaries. No additional tracker service, YAML backend or runtime queue is introduced.
- **Task refinement**: Extract permission policy into P1.6 before the first live transport run; P1.3 remains lifecycle/route validation. Split Pi single-run acceptance P8.3 from workflow parity P8.4, which requires P6.4. These are dependency clarifications of existing scope, not new feature families.
- **Scheduling**: Default to one active implementation task/PR. Additional native adapters require a recorded target selection; optional resource work requires demand selection and only the relevant prerequisite adapter/workflow. Do not require the entire provider portfolio for a quota increment or force scheduling into quota work.
- **Rationale**: A phase checklist alone does not identify a next ready task, consuming decisions or reviewable evidence. Static cards avoid duplicated mutable status while retaining stable P/G/F/AC/D traceability.
- **Validation**: Every remaining implementation task has exactly one card and resolvable dependencies; check acyclicity, conditional gates, links, phase/acceptance coverage and task order. Implementation completion remains gated by evidence and required PR/review/merge workflow.

## 2026-11-01 — D018: Mandatory holistic phase reviews before progression

- **Decision**: Add an explicit phase-review task for every phase (P0.13, P1.7, P2.9, P3.6, P4.9, P5.6, P6.5, P7.7, P8.5, P9.5). Review the entire integrated phase, record findings, address each finding and verify corrections before an accepted pass. Individual PR reviews and use demonstrations remain required but do not replace this gate.
- **Progression**: Rewire cross-phase consumers to accepted review tasks. Preserve independent branches after their common predecessor review; no dependent work proceeds on an unreviewed phase baseline. Phase 0's planning review is required before P1.1 begins.
- **Supersedes**: D017's first-completed-adapter shortcut for Phase 9 quota work; it now waits for P7.7 full portfolio review. Scheduling waits for P5.6; Pi workflow parity waits for P6.5. Phase 9 reviews selected increment snapshots and reopens for newly selected scope, without implementing unselected features.
- **Rationale**: The user explicitly requires holistic review and remediation for each phase before moving on. Existing acceptance/closeout tasks alone did not schedule this complete review or enforce predecessor review dependencies.
- **Evidence**: Use docs/PHASE_REVIEW.md and tasks/PHASE_REVIEW_TEMPLATE.md; store reports in docs/reviews/ with scope, findings, correction and verification links. Status stays in PROJECT.md; use Critical/High/Medium/Low with impact-based mapping of incoming labels. Reopening unchecks the same task, retains prior accepted report links and creates phase-NN-r2.md (then -r3.md, etc.) rather than overwriting history. A pass requires no unresolved finding and completed required review/fix PRs; the Git workflow's review limits still apply per PR.

## 2026-11-01 — D019: Minimal Rust scaffold baseline

- **Decision**: P1.1 uses a single package named `awesomejt-agent-harness` with an explicit `ah` binary and a testable library boundary. Keep version 0.1.0 and `publish = false` during the experiment; retain the repository's Apache-2.0 license. No external Rust dependencies are needed for informational help/version handling.
- **Name evidence**: On 2026-11-01 the crates.io sparse-index path `https://index.crates.io/aw/es/awesomejt-agent-harness` returned HTTP 404 / `NoSuchKey`. This distinguishes the package from occupied `agent-harness`; it does not reserve a name. Recheck before any publication.
- **Toolchain**: Rust edition 2024, `rust-version = "1.85"`, and pinned Rust 1.85.0 with rustfmt/Clippy. [Rust 1.85 introduced edition 2024](https://blog.rust-lang.org/2025/02/20/Rust-1.85.0/); using that floor allows the scaffold's MSRV to be verified directly. Commit Cargo.lock for reproducible application builds. Reassess the pin/MSRV when P1.4 selects real dependencies; this is an experiment baseline, not a permanent toolchain freeze.
- **Platform**: Initial tested development target is `aarch64-apple-darwin` on Apple Silicon macOS with Xcode linker tools. No cross-platform support or distributable release is claimed; those gates remain P2.5/P4.5.
- **Boundary**: Only help/version and rejection of unsupported inputs exist. Exit 2 denotes scaffold usage errors; Phase 2 still owns the coding-run exit contract. No speculative `single`, route, agent or workflow commands, transport, model call, or agent loop is introduced.
- **Evidence**: [P1.1 checks](docs/evidence/p1-1-rust-scaffold.md); no earlier routing or transport decision changes.

## 2026-11-01 — D020: Fail-closed experiment permissions

- **Decision**: Before P1.2 live work, use a headless default-deny policy for all tool actions. Allow only an explicit trusted grant bound to one complete attempt-specific request and an advertised allow-once option. Consume grants on the next request; never persist them or select allow-always. Prompting is unsupported in the experiment and policies requiring it must fail before launch, regardless of TTY availability.
- **Responses**: Select an advertised denial for ungranted actions; otherwise cancel, or stop if the transport cannot represent cancellation. Malformed identities/options fail the attempt. Response delivery failure triggers cleanup and possible uncertainty, never approval or a more permissive retry.
- **Rationale / alternatives**: Blanket project-write or shell grants would widen permission beyond a reviewed action. A TUI/approval timeout is unnecessary for the narrow experiment; default denial is deterministic and works headlessly. Interactive UX and broader declarative policies remain consuming-phase choices, not implicit runtime defaults.
- **Boundary**: [Execution contract](docs/EXECUTION.md#permissions-and-headless-operation) specifies the adapter preflight gate. `src/permission.rs` is a transport-independent experiment with synthetic normalized request tests, not an ACP wire schema or live security claim. No new dependencies, commands, model calls or backend launches. P1.2 must verify actual transport mapping and enforcement before live work; P1.3 proves denied-action and lifecycle behavior. Earlier routing/transport decisions remain unchanged.
- **Evidence**: [P1.6 policy fixtures](docs/evidence/p1-6-permission-policy.md). This resolves the pre-live permission decision only; Phase 1 remains open.

## 2026-11-01 — D021: Keep process policy owned; evaluate SDK wire reuse

- **Decision**: P1.4 retains harness-owned subprocess supervision using direct Rust process APIs. Reject `cli-stream` 0.5.0 and ACP SDK 3.6.0's `AcpAgent` launcher for the current integration: both inherit the parent environment without an environment-clear control; the SDK launcher also lacks project cwd configuration. The leaf wrapper leaves protocol dispatch and an ownership guard to us.
- **Protocol reuse**: Prefer the official ACP SDK 3.6.0 protocol engine over caller-owned I/O as the bounded P1.3 experiment, with no process/stdio/unstable features. This is a conditional candidate, not an adopted dependency or a claim of compatibility. It avoids committing to a custom dispatcher while preserving route/permission control.
- **Toolchain/gates**: Both pinned crates require Rust 1.88, above D019's 1.85 baseline. No toolchain change now. Before adoption, P1.3 must justify/test the MSRV and runtime/I/O fit, protocol-1 OpenCode schemas, callbacks, cancellation and cleanup; P1.5 finalizes transport/dependencies. Reject or reassess reuse if these fail, rather than weakening policy.
- **Evidence**: [Pinned-source comparison, licenses, defaults and lifecycle gaps](docs/evidence/p1-4-dependency-evaluation.md), grounded in [P1.2 live evidence](docs/evidence/p1-2-live-acp.md). Only the existing no-prompt probe and baseline Rust checks ran; neither candidate was compiled or used for a model call. No earlier route, permission or phase-exit gate changes.

## 2026-11-02 — D022: Validate SDK wire reuse in an isolated lifecycle experiment

- **Decision**: P1.3 compiles/runs official ACP SDK 3.6.0 without optional features in a standalone experiment crate. Rust owns process/environment/group cleanup; `ByteStreams` and typed protocol-1 handlers supply wire dispatch over caller-owned Tokio pipes. The existing default-deny Rust permission policy receives actual ACP option kinds; no live grants are introduced.
- **Toolchain**: The experiment alone requires and verifies Rust 1.88.0, satisfying the SDK MSRV, with its own locked dependency graph. The production scaffold stays dependency-free on 1.85.0. P1.5 selects final dependencies/transport and decides any production MSRV change using this evidence, rather than promoting experimental APIs now.
- **Evidence**: [P1.3 lifecycle/route evidence](docs/evidence/p1-3-lifecycle.md): live LiteLLM instruction/stream/denial/cancel behavior, real runtime unavailable-service failure, observed model request payloads, fake protocol failures and descendant cleanup. Automatic project instruction loading is confirmed for OpenCode 1.18.30 on macOS. No public CLI change, other runtime, inner loop, native fallback or new permission grant.
- **Limits**: Process-group cleanup is tested only on macOS and cannot contain deliberately detached descendants. Model-route evidence ends at the configured LiteLLM alias; proxy-internal routing remains external. Production supervision/outcome handling and platform support still require their consuming-phase work.

## 2026-11-02 — D023: Select ACP and the tested Rust integration boundaries

- **Decision**: Select stable ACP protocol 1 over OpenCode stdio, using official `agent-client-protocol =3.6.0` with default features disabled, caller-owned Tokio pipes and `tokio-util` compatibility adapters. Retain harness-owned process launch, environment, deadlines, permissions and cleanup; reject the SDK launcher, `cli-stream` and a custom JSON-RPC dispatcher. OpenCode continues to own the coding loop. Native structured output need not be evaluated because ACP met the experiment requirements.
- **Minimum selected stack**: SDK 3.6.0, Tokio 1.48.0 (`macros`, `rt`, `process`, `io-util`, `time`, `sync`, `signal`), tokio-util 0.7.16 (`compat`), serde_json 1.0.145 and Unix libc 0.2.177. The experiment lockfile (schema 1.13.0) is the tested dependency baseline. These packages enter the production manifest only with their Phase 2 consumers; unused dependencies and experiment-only prompts/recorder are not promoted. No HTTP/CLI/config/release library is selected ahead of its consuming task.
- **Toolchain**: Supersede D019's Rust 1.85 baseline with MSRV/pin 1.88.0, retaining edition 2024 and the Apple Silicon macOS initial target. P1.3 verified the SDK and resolved graph at 1.88; P1.5 verifies the scaffold at that floor. Linux/Windows remain unverified.
- **Validated boundaries**: Transport-independent permission decisions; OpenCode-specific ACP normalization/capability checks; a single supervisor owning child, pipes, connection and cleanup; application-owned attempt outcomes with uncertainty. Keep SDK types out of domain/policy. The experiment's concrete `OwnedChild`, callbacks and Python setup are prototypes, not public APIs or the production adapter.
- **Shutdown reassessment**: Retain bounded cooperative `session/cancel`, followed by group TERM→KILL and direct-child reap; require independent descendant verification. The probe's fixed 300 ms TERM grace proves forced termination only and is unsuitable as an assumed production flush interval. P2.4 must set/test production cancellation, grace, drains and cleanup budgets against a real edit/test run before release. Do not call forced termination graceful or retry uncertain work.
- **Evidence and limits**: [P1.5 acceptance preparation](docs/evidence/p1-5-integration-acceptance.md) consolidates exact versions, live observations, dependency/license inventory and task-owned follow-ups. D020 default-deny experiment behavior remains unchanged; production read/write/shell grants need P2.1/P2.4 enforcement. This prepares acceptance; P1.7 still gates phase exit and Phase 2.

## 2026-11-02 — D024: First-slice JSON inputs, explicit trust and shell outcomes

- **Decision**: Select strict version-1 project `ah.json`, explicit config override and invocation > project > built-in optional defaults. No parent/user/environment harness discovery. Only `local-only` and a single existing LiteLLM alias; credentials remain an environment-name reference. Freeze `single` inline/`--prompt-file PATH|-`, project/config/model/mode/permissions/timeout flags, `--no-sync` and network-free `--preview` semantics in [CONFIGURATION.md](docs/CONFIGURATION.md). The public binary remains informational until P2.2; P2.7 implements preview.
- **Validation**: `src/config.rs` supplies strict duplicate/unknown-field JSON validation, canonical URL and key-name checks, bounded UTF-8 input, prompt conflict handling and resolved request construction. Use serde 1.0.228 (derive) and the previously tested serde_json 1.0.145; url 2.5.8 handles structured URL validation rather than hand-written authority parsing. Unix libc 0.2.177 provides shared nonblocking/no-controlling-terminal config/prompt-file open followed by handle metadata checks, preventing a FIFO path swap from blocking validation. Direct dependencies are MIT/Apache-2.0; URL Unicode handling brings Unicode-3.0 transitives (inventory in evidence), with a locked Rust-1.88-tested graph; no SDK/runtime dependency enters yet. Config/request types deliberately have no Serialize/Debug implementation; parser errors do not echo values. This is input validation, not effective runtime preflight.
- **Permissions**: Default `deny`; project config cannot authorize `trusted`. Only explicit `--permissions trusted` authorizes read/write/shell with host privileges. No scoped-shell containment claim, interactive approval or silent broadening. Runtime tool restrictions plus verified exact allow-once callbacks must be demonstrated by P2.2 before any coding launch; external tools/subagents/inherited auto-allows remain disabled. Keep the D020 experiment policy unchanged; production trusted grants are constructed only by a verified adapter under this explicit policy.
- **Outcomes/deadline**: 0 success, 1 known failure, 2 rejected input/capability, 3 known cancellation/deadline, 4 uncertainty (takes precedence). Default 1800-second active/preflight bound, explicit 1–86400 seconds; prompt acquisition precedes it and remains interruptible. Finite cleanup budgets and actual runtime outcome mapping remain P2.2/P2.4 gates. Never retry uncertain side effects.
- **Boundary/evidence**: P2.1 fixtures and [evidence](docs/evidence/p2-1-config-contract.md) fix inputs without adding a speculative runnable command. P2.3 selects managed-file transaction details; no project config mutation, model call or runtime launch here; supplied environment lookup values are discarded after checking nonemptiness. Phase 1 acceptance is effective because PR #13 merged; P2.3 is the next dependency-ordered task after this PR merges.

## Deferred decision register

| Choice | Owner phase | Decide when / required evidence |
|---|---|---|
| Cargo package name, Rust edition/MSRV, initial development target | 1 | Resolved by D019/P1.1; D023 raises the tested MSRV/pin to 1.88.0. Binary packaging remains Phase 2. |
| OpenCode transport, adapter/process dependencies and concrete Rust interfaces | 1 | Transport/stack and responsibility boundaries selected by D023/P1.5 using P1.2–P1.4 evidence. Concrete production APIs arrive with Phase 2 consumers. |
| ACP permission-request handling (allow/deny/prompt) | 1 | Experiment policy resolved by D020/P1.6; actual denial mapping/lifecycle verified in P1.3. Useful production coding grants remain P2.1/P2.4. |
| Config format, filename/location, precedence, exit codes, prompt-input and preview syntax | 2 | Resolved by D024/P2.1 for the first slice; CLI execution arrives in P2.2 and preview in P2.7. JSON config is distinct from canonical agent YAML frontmatter. |
| Project sync ownership/conflicts and no-sync validation | 2 | Before any managed project writes; prove preservation and effective routing. |
| Release tooling and initial binary target | 2 | Before first usable distribution; validate installation and external prerequisites. |
| Failure eligibility, retries, uncertain tool side effects | 3 | Before automatic native fallback; define refusal/recovery behavior and test it. No blind replay of potentially applied work. |
| Model groups, proxy-config handoff/validation and native-route config isolation | 3 | Before dual routing ships; prove cloud-only cannot inherit the managed LiteLLM route. |
| Canonical agent schema, destination paths, constraints | 4 | Before mapping ships; verify installed backend semantics and reject unsupported restrictions. Markdown + YAML remains canonical. |
| Versioned machine result/events, stdout/stderr and CI contract | 4 | Before automated consumers rely on output; define envelope, terminal semantics, redaction and compatibility tests. |
| MVP platform matrix and packaging polish | 4 | After tested builds/runs; do not imply all targets from Rust portability alone. |
| Sequence ordering/context, metadata, state, retention, concurrency, verification trust and resume | 5 | Before sequence execution; define interrupted/uncertain step behavior. |
| Ralph completion, verification, limits and recovery | 6 | Before loop implementation; test false completion and bounded failure. |
| Additional native CLI order/interface/version support | 7 | One adapter at a time, chosen from actual use; verify supported auth and provider integration. |
| Pi transport and agent/skill mapping | 8 | Before Pi adapter; validate capability and route parity. |
| Quota freshness/ranking, scheduling, storage | 9 | Only as usage justifies each addition; evaluate ai-queue behavior without importing its defaults. |
