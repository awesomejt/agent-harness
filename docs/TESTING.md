# Validation and acceptance plan

Status: planned checks; the repository has no Rust implementation yet. Add runnable commands/fixtures with the consuming phase. Phase exit criteria in [IMPLEMENTATION.md](IMPLEMENTATION.md) remain authoritative; a passing mock suite does not prove live compatibility.

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

Once Cargo files exist, adopt formatting, linting and tests appropriate to supported targets (normally cargo fmt, cargo clippy and cargo test), plus dependency/license inspection when selecting reusable code. Freeze precise commands and feature combinations with the implementation; do not claim checks ran before code exists.

Each supported release target needs an actual build and installation smoke test; compilation alone does not establish process-tree behavior. Record platform limitations instead of implying Windows parity from Rust portability. Verify checksums and upgrade instructions, and distinguish external CLI prerequisites from harness installation.

## Traceability and closeout

Detailed task acceptance/dependencies are in [tasks/](../tasks/README.md); recommended milestone/PR order is in [PROJECT_PLAN.md](PROJECT_PLAN.md). P1.6 records/tests permission policy before P1.2 live execution; P1.3 validates the complete lifecycle. Pi workflow parity P8.4 runs after P6.4 even if Pi single-run acceptance happened earlier.

Use G IDs for goals, F IDs for feature dispositions, AC IDs for milestone acceptance, P IDs for tasks, and D IDs for decisions. Validate the Mermaid diagrams and cross-document references when architecture changes; diagram validation is documentation tooling, not a Node.js runtime requirement for ah. Link phase evidence from PROJECT.md with date, task, tested versions, route/model, observed outcome, interventions, direct-tool comparison and limitations. A feature is complete only when its acceptance evidence is linked, docs reflect implemented behavior, and required PR review is complete.
