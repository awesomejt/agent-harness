# P3.3 (part 1 of 2) — LiteLLM model groups and proxy handoff

Date: 2026-11-02. Entry: `b5724cc` (merged P3.2 / PR #26). Task branch: `feature/03/p3-3-model-groups`. This is the first of the two PRs the [P3.3 card](../../tasks/03-routing.md#p3-3) allows: group references and proxy handoff/validation. The configured local-first fallback coordinator (attempt identity, eligible-failure evidence, native target guards) is the second PR; P3.3 stays open until it merges. [D033](../../DECISIONS.md#2026-11-02--d033-harness-model-groups-as-explicit-single-proxy-group-references) and the [configuration contract](../CONFIGURATION.md#litellm-model-groups-p33--d033) define the behavior.

## Delivered behavior

- Optional `litellm.groups` maps 1–64 harness group names to exactly one existing proxy model group each. Duplicate keys (rejected by a dedicated map visitor, since serde maps otherwise keep the last value), empty/null/array/object values, invalid identifiers and nested references reject with fixed, non-echoing messages.
- `model` and `--model` accept a bare proxy model group (unchanged) or `group:NAME`. Only the explicit prefix consults groups, so harness names never shadow proxy names. Undefined references reject before key lookup and stdin.
- Groups are LiteLLM-only: `group:` with cloud-only rejects; native model grammar excludes references. A cloud-only config may carry a valid inactive local group default, used by `--mode local-only`.
- Resolution replaces the reference before planning. Managed `opencode.json`, the ownership receipt, effective-route validation, ACP session model and wire requests contain only `ah-litellm/PROXY_GROUP`; harness names and unselected groups never leave `ah`. D025 transaction semantics are unchanged.
- Read-only handoff: `--preview` adds `proxy handoff:` with the selected harness/proxy group and all distinct proxy groups the config requires, explicitly unverified and operator-owned; native preview reports "not applicable". The `attempt=1` progress line names the group. Help lists `--model MODEL|group:NAME`.
- No proxy writes, admin/discovery requests, restarts, new dependency, flag or command. No allocation-ranked pool: LiteLLM keeps intra-group load balancing/fallback.

## Validation

Tested on macOS 27.0.1 arm64, Rust/Cargo 1.88.0, OpenCode 1.18.30. All commands are non-spending; fixture keys are synthetic.

| Command | Observed result |
|---|---|
| `cargo test --locked` | 49 tests pass (44 prior plus 4 group config tests and 1 managed-transaction group test): resolution from config/invocation, bare-name non-shadowing, distinct handoff list, undefined/native references rejecting before key lookup, malformed `--model` references, inactive native-config defaults, schema bounds/duplicates, and managed config/receipt containing only the resolved proxy group with effective validation rejecting a different group. |
| `cargo fmt --check`, `cargo clippy --all-targets --locked -- -D warnings`, `cargo build --release --locked` | Pass. |
| `python3 scripts/tests/preview.py` | Prior preview fixtures plus group handoff lines for config default, `--model group:review`, direct override, no-groups config and an undefined reference (exit 2); no launch, writes or secret/endpoint leakage. |
| `python3 scripts/tests/single.py` | 59 cases pass: the prior 57 plus fake-runtime grouped deny and trusted-read runs whose progress names the group and whose preflight routing is the resolved proxy group. |
| `python3 scripts/tests/native.py` | 32 cases pass; native preview reports the handoff as not applicable; zero LiteLLM discovery/model requests. |
| `python3 scripts/tests/single_runtime.py [--group coder]` | Installed OpenCode with deterministic stub: actual edit and independent test pass, exit 0. With `--group coder`, all six wire requests carry only proxy group `fixture`. |
| `python3 scripts/tests/single_runtime.py --cancel --group coder` | Actual edit/test then confirmed cancellation, exit 3, no replay. |
| `python3 scripts/tests/native_runtime.py`, `python3 scripts/tests/worktree.py` | Pass unchanged. |

## Limits and next step

Proxy group existence is not verified before use; preview says so and a missing group stops without fallback. No live LiteLLM request was made for this PR; live dual-route use remains P3.5. The second P3.3 PR must add the configured local-first coordinator: new linked attempt identity, D031 guards, a validated native target with identical constraints, and a decision on whether a bounded pre-submission discovery check supplies trustworthy unavailable-model evidence.
