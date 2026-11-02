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

## Deferred decision register

| Choice | Owner phase | Decide when / required evidence |
|---|---|---|
| Cargo package name, Rust edition/MSRV, initial development target | 1 | Before scaffolding/publishing; verify naming and toolchain availability. |
| OpenCode transport, adapter/process dependencies and concrete Rust interfaces | 1 | After a narrow experiment proves model selection, project instructions, callbacks, streaming, and cancellation. |
| ACP permission-request handling (allow/deny/prompt) | 1 | Before the first live run; document the non-interactive default and prove no implicit permission widening. |
| Config format, filename/location, precedence, exit codes, prompt-input and preview syntax | 2 | Before first-slice configuration/CLI is implemented; use the smallest schema that supports that slice. YAML is an earlier sketch, not a locked harness-config format. |
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
