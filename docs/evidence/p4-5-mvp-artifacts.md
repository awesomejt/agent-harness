# P4.5 — MVP artifacts and setup polish

Date: 2026-11-03. Entry baseline: `88345e6` (merged P4.4 PR #39).
Task branch: `feature/04/p4-5-mvp-artifacts`. [Card](../../tasks/04-core-mvp.md#p4-5). Decision: D041.
Platform: Apple Silicon macOS 27.0.1 (26A434), Rust/Cargo 1.88.0, Xcode 27.1 (27A9275),
Python 3.14.3 (maintainer only), installed OpenCode 2.2.5 (Homebrew).
Gate: AC09, AC10; R03-REC2. Version: `0.1.0-alpha.2`; target `aarch64-apple-darwin`.
Acceptance takes effect after PR review/merge and publication of the artifact packaged
from the merged commit. P4.6 and P4.9 remain open.

## Declared matrix

One target is declared: the `aarch64-apple-darwin` archive on macOS 27.0.1, with
OpenCode 2.2.5 and per-route prerequisites installed separately. The runbook's
[supported platforms](../OPERATIONS.md#supported-platforms-d041) table lists the
owner of each prerequisite. Intel macOS, other macOS releases, Linux and Windows are
declared unsupported. No artifact was built for them, and coding runs are compiled
for macOS only (`single.rs` refuses other hosts and preview reports
`execution platform: unsupported`). No claim rests on compilation.

## Deliverables

- **Version/R03-REC2:** Cargo version `0.1.0-alpha.2`. The artifact packages current
  source: all three modes, `group:` references, `--agent`, `--output jsonl`, the
  OpenCode 2.2.5 pin, D030 cleanup and D040 instructions/command refusal.
- **Samples:** `examples/ah.{local-only,cloud-only,local-first}.json`, validated by
  `tests/config.rs::packaged_example_configs_validate`. `package.py` bundles them plus
  `agents/*.md` (already parsed and golden-tested by `tests/agents.rs` and
  `tests/agent_emission.rs`) as `examples/` in the archive.
- **Smoke:** `scripts/release/smoke.sh` now installs over an earlier executable,
  checks archive contents, checks preview platform/runtime lines and the
  `--output jsonl --preview` refusal, previews every sample with both sample agents
  (mode/agent lines, redaction of keys, prompt and endpoint, no writes), compares
  sha256 of every HOME and project file before and after (user/global OpenCode
  config, a login-store sentinel, unmanaged project `opencode.json`, `ah.json`) and
  verifies rollback and reinstall.
- **Docs:** [OPERATIONS](../OPERATIONS.md) has the matrix, alpha.2 install, separate
  prerequisites, samples, a setup check (version, runtime version, network-free
  preview, one read-only reviewer turn), the alpha.1 → alpha.2 upgrade, rollback and
  removal, four new diagnostic rows (runtime version preflight, unsupported platform,
  missing key, agent lookup) and a version-generic maintainer procedure. Native and
  local-first sections are no longer source-only. README, docs index, TESTING,
  EXECUTION and CONFIGURATION drop stale alpha.1/source-only wording. CI guidance
  (P4.7) is unchanged and ships in `INSTALL.md`.
- No harness runtime behavior changed and no CLI flag or `doctor` command was added.

## Verification

```sh
cargo fmt --all -- --check
cargo clippy --all-targets --locked -- -D warnings
cargo test --locked                       # 82 tests
cargo build --locked
for t in single preview worktree modes native local_first machine agents_exec; do
  python3 scripts/tests/$t.py; done
python3 scripts/tests/agent_exec_runtime.py
python3 scripts/tests/capabilities_runtime.py
python3 scripts/release/package.py --output dist/candidate
sh scripts/release/smoke.sh dist/candidate 0.1.0-alpha.2
B=/path/to/extracted/ah-v0.1.0-alpha.2-aarch64-apple-darwin/ah
python3 scripts/tests/single_runtime.py --binary "$B"
python3 scripts/tests/single_runtime.py --binary "$B" --cancel
python3 scripts/tests/single_runtime.py --binary "$B" --refuse
python3 scripts/tests/single_runtime.py --binary "$B" --jsonl --cancel
python3 scripts/tests/single_runtime.py --binary "$B" --live --jsonl --model flash
```

All pass. Results:

- **Candidate:** packaged from `b25d745`, archive SHA-256
  `5c3f219f1817c3bca513348276fdfca62a22132c17b25eda472a92dbbfb1a6a9` (13 MB), 130
  registry packages, Mach-O arm64 `minos 14.0`, system dylibs only. Final
  publication repackages the merged commit; its checksum and provenance are
  authoritative in the release's `SHA256SUMS` and `BUILD-INFO.json`.
- **Smoke mutation checks:** three mutated copies fail (exit 1): a HOME config write
  after install, a wrong expected sample mode, and a rollback that does not restore
  the earlier executable.
- **Installed runtime from the archive executable:** a deterministic edit plus an
  independent arithmetic test, post-edit cancellation (human and JSONL), and
  refusal of an unsupported `other`-kind tool with no project or outside effect.
- **Live from the archive executable:** `--live --jsonl` against the user's LiteLLM
  alias `flash` edits `calc.py`, the independent test passes and `verified` is
  touched; exit 0, `result` outcome `succeeded`, 5 grants, 17 tool events, reported
  session cost 0 USD. Wire requests carry only model `flash`.
- **Upgrade of an alpha.1-managed project:** a `v0.1.0-alpha.1` worktree's own
  planner wrote `opencode.json`, `.ah-opencode-owner.json` and the lock. Current
  source previewed it with `planned changes: none`, both with default sync and with
  `--no-sync` (exact disk route validated). The documented setup-check turn
  (`--agent reviewer --permissions trusted`) from the archive executable then ran
  live on that project: exit 0 with a correct summary, managed routing files and
  project source byte-identical, and only `.opencode/agents/reviewer.md` plus
  `.ah-opencode-agents.json` added.
- No `ah-runtime-*` directory or `opencode acp` process remained after the runs.
  Keys were never printed.

## Limits

- Native live use was not repeated from this artifact: `OPENCODE_API_KEY` was not
  available in the packaging session. Native/local-first fallback live evidence
  remains [P3.5](p3-5-dual-route-use.md) and [P4.4](p4-4-primary-reviewer-acceptance.md)
  on source builds of the same route code. The archive smoke previews the
  cloud-only and local-first samples, and `agent_exec_runtime.py` and
  `capabilities_runtime.py` exercise installed native preflight and fallback.
- Browser download, quarantine/Gatekeeper, Developer ID signing and notarization
  are untested and not provided, as in D029.
- The setup check's runtime version step is manual; preview stays network-free
  and subprocess-free by contract, and execution preflight enforces the pin.
