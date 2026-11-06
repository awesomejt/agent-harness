# Validation and acceptance plan

Status: the local-only Rust CLI, strict config/input validation, project routing transactions, ACP coding adapter, bounded progress/cancellation, read-only preview, dirty-project reporting and Apple Silicon release checks are implemented. The standalone ACP lifecycle experiment remains regression tooling. P3.2 adds isolated native OpenCode cloud-only execution, P3.3 the local-first coordinator with one pre-submission native fallback, P3.4 the three-mode boundary matrix and P3.7 the OpenCode 2.2.5 runtime baseline (D035). Phase 4 adds named-agent parsing, emission and enforcement (D036–D038), version-1 machine output (D039) and the inherited-capability matrix (D040). P5.5 adds trusted verification gates for single runs (D043). P5.2 adds `ah sequence run` (D044) with snapshot, metadata and stop-on-failure tests (`tests/sequence.rs`, `scripts/tests/sequence.py`, installed `sequence_runtime.py`). P5.3 adds durable records, locking, `show` and `resume` with crash-window, competing-writer, cancellation, changed-input, schema and write-failure tests (`tests/state.rs`, `scripts/tests/sequence_state.py`); sequence scripts use a temporary `XDG_STATE_HOME` outside the project. P5.4 adds `offline.py`, the offline-suite runner written during its live sequence use. P6.2 adds `ah ralph run`/`show` (D045). Its tests cover fresh per-iteration runtime state, the header, the prompt snapshot, strict records, both bounds, interruption, cancellation and the lock shared with sequences (`tests/ralph.rs`, `scripts/tests/ralph.py`). P6.3 adds completion verification and `resume`: the completion/stop and resume-plan tables, scripted loop tests (including a signal between iterations), and fake-OpenCode cases for false, stale and DONE-file signals, check outcomes and every resume choice. Phase exit criteria in [IMPLEMENTATION.md](IMPLEMENTATION.md) remain authoritative; a passing mock suite does not prove live compatibility.

## Layers

| Layer | Evidence | First owner |
|---|---|---|
| Pure policy/configuration | Allowed/forbidden routes, resolution, invalid input, alias/agent constraints | 2–4 |
| Adapter fixtures | Versioned captured/synthetic protocol records, lifecycle, permission/model mapping | 1 onward |
| Process integration | Controlled fake child processes, real pipes, deadlines and descendant cleanup | 1–2 |
| Project sync | Temp projects with unrelated/commented config, collisions, concurrent mutation, sentinel keys | 2, 4 |
| CLI/automation | Inline/file/stdin inputs, preview, headless behavior, stdout/stderr and exit contracts | 2, 4 |
| Workflow recovery | Crash windows, changed inputs, competing runs, verification and bounded loops | 5–6 |
| Release smoke | Download/install artifact, version/help, dependencies and one supported runtime scenario | 2, 4 |
| Live use | Representative edit/test task, direct-tool comparison and observed limits | Every usable phase |

Unit and default integration tests use fakes without provider credentials or billable prompts. Live checks are explicit, use a disposable project or intended user task, and record exact harness/runtime/model/proxy versions where available. No automatic account probing that spends a model turn.

## Required boundary cases

- local-only never invokes native cloud fallback; cloud-only never contacts LiteLLM even for discovery; local-first uses only its configured eligible fallback.
- An inherited helper/subagent/default model cannot bypass mode policy. Unsupported restrictions are refused before model work.
- All prompt sources resolve unambiguously; conflicting or empty sources fail before launch. Preview neither sends prompts nor changes files.
- Acceptance/acknowledgement is not completion. Cover malformed/truncated records, partial UTF-8, unexpected EOF, nonzero exit after text, and a terminal backend event before process cleanup.
- Pipe draining handles noisy stderr and slow consumers without deadlock or unbounded memory. Cancellation works while idle, writing input, reading output and waiting for descendants; forced cleanup has a bound.
- Noninteractive permissions cannot hang indefinitely or silently approve. Test explicit grants, denial, unavailable prompt channel and stricter canonical roles.
- Sync preserves unrelated/global content and dirty project files; malformed config, manual edits, concurrent updates, interrupted writes, secret references and no-sync validation are covered.
- Dirty/untracked user changes survive failed and cancelled attempts. Tests do not rely on resetting the user's repository.
- Interrupted side effects yield uncertainty rather than blind retry, with a distinct exit status and explicit stderr diagnostic before machine output is available. Sequence/Ralph resume detects stale state, changed inputs, competing writers, false completion and exhausted limits.
- Reported usage has provenance; missing usage is unknown. No guessed billing balance drives mandatory routing.

## Rust and release checks

The root package pins Rust 1.88.0. Current checks from the repository root (with `~/.cargo/bin` on PATH):

```bash
cargo fmt --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked
cargo build --release --locked
./target/release/ah --version
python3 scripts/tests/single.py
python3 scripts/tests/preview.py
python3 scripts/tests/worktree.py
python3 scripts/tests/single_runtime.py
python3 scripts/tests/single_runtime.py --cancel
python3 scripts/tests/single_runtime.py --group=coder
python3 scripts/tests/single_runtime.py --refuse
python3 scripts/tests/native.py
python3 scripts/tests/native_runtime.py
python3 scripts/tests/agents_runtime.py
python3 scripts/tests/agent_emission_runtime.py
python3 scripts/tests/local_first.py
python3 scripts/tests/modes.py
python3 scripts/tests/agents_exec.py
python3 scripts/tests/machine.py
python3 scripts/tests/verify.py
python3 scripts/tests/single_runtime.py --verify
python3 scripts/tests/sequence.py
python3 scripts/tests/sequence_state.py
python3 scripts/tests/sequence_runtime.py
python3 scripts/tests/ralph.py
python3 scripts/tests/agent_exec_runtime.py
python3 scripts/tests/capabilities_runtime.py
python3 scripts/tests/doclinks.py
cargo build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
```

`python3 scripts/tests/offline.py` runs every offline Python suite above in that order against `target/debug/ah` once `cargo build --locked` has produced it, reporting each suite's result and a final pass count; `--list` prints the suites in order, and positional script names such as `preview` run only those suites. The runner excludes `roles_live.py` and the lifecycle experiment because neither is an offline check.

`python3 scripts/tests/doclinks.py [ROOT]` is the documentation link check: no `ah`, no runtime and no network. ROOT defaults to the repository root derived from the script's own location, and a ROOT that is not an existing directory exits 2. It checks the `*.md` files `git ls-files` reports under ROOT, following inline links and images (`[text](target)` and `![alt](target)`, an optional quoted title allowed) while skipping targets that carry a URL scheme (`https:`, `mailto:`, ...) and anything inside a fenced code block or inline code span. Each target path resolves relative to the linking file and must exist as a file or directory; a `#fragment`, alone (the same file) or after a `.md` path, must match an anchor in that Markdown file, either an explicit `<a id="...">` or a heading's GitHub slug (lowercase, punctuation dropped except hyphens and underscores, each space a hyphen, repeated headings suffixed `-1`, `-2`, ...), compared case-sensitively. Each broken link is one stdout line `PATH:LINE: TARGET` (PATH relative to ROOT, LINE 1-based), and the exit is 1; with no broken link the exit is 0. It needs no binary, so it runs alongside the other suites from the repository root.

The root suite covers CLI/config/input/precedence, permission decisions, managed project transactions and the P4.1 canonical-agent parser. `agents_runtime.py` probes installed 2.2.5 agent document/project-file destinations and primary/subagent/all modes with no model prompt; it does not establish enforced named-role execution. `agents_exec.py` drives named roles through the fake runtime (runtime document, per-role grants/completions, deny narrowing, widened/hidden/altered/substituted role refusal, effort refusal and local-first fallback); `agent_exec_runtime.py` runs installed 2.2.5 named preflight and ACP session setup on both routes with the prompt intercepted, plus a direct probe showing a `subagent` default falls back to `build`. Live named-role inference is P4.4 (below). `capabilities_runtime.py` is the P4.8 inherited-capability matrix: it plants instruction, skill, command, plugin, custom-tool and MCP sources (with execution sentinels) and runs installed 2.2.5 through real `ah single` against a recording local model stub, plus direct ACP probes for instruction loading and advertised commands and a shimmed local-first native fallback. The production Python drivers exercise adversarial public-CLI protocol/process behavior, read-only preview and dirty-project preservation. `single_runtime.py` uses installed OpenCode against a deterministic local model stub for actual read/edit/shell operations, independent arithmetic verification and post-edit cancellation. It accepts `--binary /absolute/path/to/ah` to repeat those checks with a release artifact and `--group NAME` to select the stub's proxy group through `litellm.groups`, asserting wire requests carry only the proxy group. `--refuse` first requests the built-in `other`-kind worktree removal, which must be refused; 2.2.5 then ends the turn as cancelled (exit 3) with no project or outside effect. `fake_opencode.py` emulates the recorded 2.2.5 surfaces (sources list, agent rule tails, `path` arguments, the doubled external-directory request, rejection ending the turn). `native.py` traps LiteLLM requests while testing native preflight, grants/denial, deadlines, uncertain failures, preview and project preservation. `native_runtime.py` checks installed native preflight/catalog and ACP session/model for deny/trusted, intercepting the prompt before forwarding it to OpenCode. Its synthetic terminal does not establish inference/authentication success; live native use is recorded in P3.5. `machine.py` is the P4.7 machine-consumer fixture: an independent validator checks every stdout line, envelope order, exactly one final result, outcome/exit mapping, null unknown metrics, redaction and stderr separation across success, usage, grants, failure, cancellation, uncertainty (including the declined R03-REC1 case), rejection, blocked stdout, local-first fallback and an open, unread stdin. `tests/cli.rs` covers rejected machine invocations. `modes.py` is the P3.4 three-mode boundary matrix. It runs identical scenarios in every mode against reachable and unreachable LiteLLM endpoints and asserts effective behavior: launched route and count, exact runtime environment and routing, endpoint contact, attempt lines, inherited-choice rejection, uncertainty and managed writes. It also covers `--mode` overrides, `--no-sync` and invalid route/fallback configuration. The standalone lifecycle driver retains earlier adversarial child and installed-runtime local-stub/unavailable regressions. Exact observed counts belong in dated evidence and review reports.

Installed-runtime commands require OpenCode 2.2.5 on an absolute PATH entry. The lifecycle experiment's `--runtime` mode is historical 1.18.30 tooling and is no longer a current check. None of the commands above contacts a live model provider. Explicit live commands and observed results are in [P2.2 coding evidence](evidence/p2-2-local-only-run.md), [P2.4 supervision evidence](evidence/p2-4-progress-supervision.md), [P2.6 published-binary first use](evidence/p2-6-first-use.md) and [P3.5 dual-route use](evidence/p3-5-dual-route-use.md) (all three modes and the eligible fallback on OpenCode 2.2.5). `python3 scripts/tests/roles_live.py` is the explicit P4.4 live gate for AC05/AC07/AC08/AC11: it requires `LITELLM_API_KEY` and `OPENCODE_API_KEY`, contacts the live LiteLLM proxy and the native OpenCode provider, and runs the example coder and reviewer on LiteLLM through a recording forwarder (offered tools, `AGENTS.md` and role text per request), on the native route and through a local-first fallback, plus prohibited-operation, deny-invocation, unsupported-effort and dirty-work cases, all through `--output jsonl`; results are in [P4.4 evidence](evidence/p4-4-primary-reviewer-acceptance.md). Each live row reports `elapsed_secs`. Run live acceptance passes serially, never alongside another session on the same alias: P4.6's only cancellation coincided with such overlap. `--binary` selects a published executable, and [P4.6](evidence/p4-6-core-mvp-acceptance.md) records five passes from `v0.1.0-alpha.2`. P2.6 distinguishes repeatable commands from the manual direct-OpenCode comparison and unavailable-endpoint trial. Prior [Phase 1 review](reviews/phase-01.md) and [dependency inventory](evidence/p1-5-dependencies.md) remain historical experiment evidence; the production attribution refresh is recorded in [P2.5 release evidence](evidence/p2-5-installable-binary.md). No passing stub suite substitutes for the required live-use gate.

Follow [the release runbook](OPERATIONS.md#maintainer-release-procedure) to package a clean merged source commit and smoke the actual archive with `sh scripts/release/smoke.sh /absolute/path/to/assets VERSION`. The smoke covers upgrade over an earlier executable, every packaged sample config with both sample agents, configuration/login-store preservation and rollback, with no OpenCode or service on PATH. Repeat `single_runtime.py --binary` (deterministic, `--cancel`, `--refuse` and `--live --jsonl`) against the extracted archive executable for installed-runtime and live evidence ([P4.5](evidence/p4-5-mvp-artifacts.md)). Published assets require checksum verification and a fresh download/install smoke. Do not overwrite versioned assets during validation.

Each supported release target needs an actual build and installation smoke test; compilation alone does not establish process-tree behavior. Record platform limitations instead of implying Windows parity from Rust portability. Verify checksums and upgrade instructions, and distinguish external CLI prerequisites from harness installation.

## Traceability and closeout

Detailed task acceptance/dependencies are in [tasks/](../tasks/README.md); recommended milestone/PR order is in [PROJECT_PLAN.md](PROJECT_PLAN.md). P1.6 records/tests permission policy before P1.2 live execution; P1.3 validates the complete lifecycle. Pi workflow parity P8.4 runs after accepted Phase 6 review P6.5 even if Pi single-run acceptance happened earlier.

Use G IDs for goals, F IDs for feature dispositions, AC IDs for milestone acceptance, P IDs for tasks, and D IDs for decisions. Validate the Mermaid diagrams and cross-document references when architecture changes; diagram validation is documentation tooling, not a Node.js runtime requirement for ah. Link phase evidence from PROJECT.md with date, task, tested versions, route/model, observed outcome, interventions, direct-tool comparison and limitations. A feature is complete only when its acceptance evidence is linked, docs reflect implemented behavior, and required PR review is complete.

## Holistic phase acceptance

After phase evidence is prepared, execute the explicit phase-review task using [PHASE_REVIEW.md](PHASE_REVIEW.md). Review the accumulated phase and its integration with earlier baselines, not just the final PR. Record every finding, correction and verification; reassess integrated behavior after fixes. The phase remains open until no unresolved finding and all required PR reviews/merges are complete. Successor task dependencies must reference the accepted phase-review gate.
