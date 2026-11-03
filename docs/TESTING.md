# Validation and acceptance plan

Status: the local-only Rust CLI, strict config/input validation, project routing transactions, ACP coding adapter, bounded progress/cancellation, read-only preview, dirty-project reporting and Apple Silicon release checks are implemented. The standalone ACP lifecycle experiment remains regression tooling. P3.2 adds isolated native OpenCode cloud-only execution, P3.3 the local-first coordinator with one pre-submission native fallback, P3.4 the three-mode boundary matrix and P3.7 the OpenCode 2.2.5 runtime baseline (D035); named agents, machine output and workflows remain gated. Phase exit criteria in [IMPLEMENTATION.md](IMPLEMENTATION.md) remain authoritative; a passing mock suite does not prove live compatibility.

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
python3 scripts/tests/local_first.py
python3 scripts/tests/modes.py
cargo build --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo fmt --check --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml
cargo clippy --locked --manifest-path scripts/experiments/acp_lifecycle/Cargo.toml -- -D warnings
python3 scripts/experiments/acp_lifecycle.py
```

The root suite covers CLI/config/input/precedence, permission decisions and managed project transactions. The production Python drivers exercise adversarial public-CLI protocol/process behavior, read-only preview and dirty-project preservation. `single_runtime.py` uses installed OpenCode against a deterministic local model stub for actual read/edit/shell operations, independent arithmetic verification and post-edit cancellation. It accepts `--binary /absolute/path/to/ah` to repeat those checks with a release artifact and `--group NAME` to select the stub's proxy group through `litellm.groups`, asserting wire requests carry only the proxy group. `--refuse` first requests the built-in `other`-kind worktree removal, which must be refused; 2.2.5 then ends the turn as cancelled (exit 3) with no project or outside effect. `fake_opencode.py` emulates the recorded 2.2.5 surfaces (sources list, agent rule tails, `path` arguments, the doubled external-directory request, rejection ending the turn). `native.py` traps LiteLLM requests while testing native preflight, grants/denial, deadlines, uncertain failures, preview and project preservation. `native_runtime.py` checks installed native preflight/catalog and ACP session/model for deny/trusted, intercepting the prompt before forwarding it to OpenCode. Its synthetic terminal does not establish inference/authentication success; P3.5 owns live native use. `modes.py` is the P3.4 three-mode boundary matrix. It runs identical scenarios in every mode against reachable and unreachable LiteLLM endpoints and asserts effective behavior: launched route and count, exact runtime environment and routing, endpoint contact, attempt lines, inherited-choice rejection, uncertainty and managed writes. It also covers `--mode` overrides, `--no-sync` and invalid route/fallback configuration. The standalone lifecycle driver retains earlier adversarial child and installed-runtime local-stub/unavailable regressions. Exact observed counts belong in dated evidence and review reports.

Installed-runtime commands require OpenCode 2.2.5 on an absolute PATH entry. The lifecycle experiment's `--runtime` mode is historical 1.18.30 tooling and is no longer a current check. None of the commands above contacts a live model provider. Explicit live commands and observed results are in [P2.2 coding evidence](evidence/p2-2-local-only-run.md), [P2.4 supervision evidence](evidence/p2-4-progress-supervision.md) and [P2.6 published-binary first use](evidence/p2-6-first-use.md). P2.6 distinguishes repeatable commands from the manual direct-OpenCode comparison and unavailable-endpoint trial. Prior [Phase 1 review](reviews/phase-01.md) and [dependency inventory](evidence/p1-5-dependencies.md) remain historical experiment evidence; the production attribution refresh is recorded in [P2.5 release evidence](evidence/p2-5-installable-binary.md). No passing stub suite substitutes for the required live-use gate.

Follow [the release runbook](OPERATIONS.md#maintainer-release-procedure) to package a clean merged source commit and smoke the actual archive with `sh scripts/release/smoke.sh /absolute/path/to/assets 0.1.0-alpha.1`. Published assets require checksum verification and a fresh download/install smoke. Do not overwrite versioned assets during validation.

Each supported release target needs an actual build and installation smoke test; compilation alone does not establish process-tree behavior. Record platform limitations instead of implying Windows parity from Rust portability. Verify checksums and upgrade instructions, and distinguish external CLI prerequisites from harness installation.

## Traceability and closeout

Detailed task acceptance/dependencies are in [tasks/](../tasks/README.md); recommended milestone/PR order is in [PROJECT_PLAN.md](PROJECT_PLAN.md). P1.6 records/tests permission policy before P1.2 live execution; P1.3 validates the complete lifecycle. Pi workflow parity P8.4 runs after accepted Phase 6 review P6.5 even if Pi single-run acceptance happened earlier.

Use G IDs for goals, F IDs for feature dispositions, AC IDs for milestone acceptance, P IDs for tasks, and D IDs for decisions. Validate the Mermaid diagrams and cross-document references when architecture changes; diagram validation is documentation tooling, not a Node.js runtime requirement for ah. Link phase evidence from PROJECT.md with date, task, tested versions, route/model, observed outcome, interventions, direct-tool comparison and limitations. A feature is complete only when its acceptance evidence is linked, docs reflect implemented behavior, and required PR review is complete.

## Holistic phase acceptance

After phase evidence is prepared, execute the explicit phase-review task using [PHASE_REVIEW.md](PHASE_REVIEW.md). Review the accumulated phase and its integration with earlier baselines, not just the final PR. Record every finding, correction and verification; reassess integrated behavior after fixes. The phase remains open until no unresolved finding and all required PR reviews/merges are complete. Successor task dependencies must reference the accepted phase-review gate.
