# P7.10 — ACP source and limit-error increment

Date: 2026-11-24. Preliminary source and offline fixture evidence; P7.10 is
**not accepted**. This increment does not authorize inference or implement a Go
route. The account screenshot and direct interactive Go use in PROJECT.md are
operator-provided observations, not an ACP-path acceptance run.

## Pinned source observations

Reviewed the official OpenCode v2.3.0 tag at commit
[`a6b15d33daf6ab7d35569f6d711fdb630b9f04e7`](https://github.com/anomalyco/opencode/tree/a6b15d33daf6ab7d35569f6d711fdb630b9f04e7).
The official v2.3.2 tag resolves to `c0ad18b402eb2827fc1ee71c171b1177b3fc02d1`.
Of the ten files fingerprinted below, seven are byte-identical. In the other
three, the examined diff adds video-model resolution (`model-resolver.ts`),
background-shell tracking and changes inbox event folding (`acp/translate.ts`),
and passes location into tool snapshot selection (`session/context.ts`). The
relevant error serialization and the credential-setting merge remain unchanged
in those file diffs. This targeted comparison is not complete behavioral
equivalence or proof of installed-binary provenance; D104's version policy does
not itself establish either.

- `packages/core/src/models-dev/snapshot.txt` contains separate `opencode` and
  `opencode-go` providers, both advertising `OPENCODE_API_KEY`. For `kimi-k3`,
  their chat-completions base URLs are respectively
  `https://opencode.ai/inference/openai/v1` and
  `https://opencode.ai/inference/go/openai/v1`. This catalog observation does not
  establish the effective endpoint of a configured runtime.
- `packages/core/src/plugin/models-dev.ts` registers provider and integration IDs
  from the catalog, with key and environment methods. `model-resolver.ts` merges
  settings and credentials; a connection credential can affect precedence. D092's
  private HOME/XDG and settings-only key boundary therefore still matters.
- `session/runner/model.ts` looks up an explicit session model by provider and
  model ID; without one it can select an agent/default. `session/context.ts` and
  the helper paths require separate effective-control proof. The harness currently
  pins a title model, validates agent overrides and checks the ACP session option,
  but its native config, provider check and catalog validator are hard-coded to
  `opencode`. They cannot be assumed to validate `opencode-go` as implemented.
- `session/model-request.ts` derives the User-Agent from `App.useragent(app)` and
  sets session affinity headers. `app.ts` formats the OpenCode identity. This is a
  source observation, not a captured Go wire request or proof for every helper.
- `session/to-session-error.ts` maps a `GoUsageLimitError` body to
  `provider.go-limit` only within its `QuotaExceeded` branch. The ACP event fold
  retains step/execution errors (`cli/src/acp/translate.ts`); for a started turn
  its failure translation creates a session service failure with that error name.
  `cli/src/acp/error.ts` serializes this as an internal JSON-RPC error carrying
  `data.service` and `data.errorName`. Other upstream error categories or turn
  paths must not be assumed to have that shape.

## Local fixture and limitations

`scripts/tests/native.py` uses the fake runtime to send that error shape after a
prompt on the **existing** native route. It checks exit 4 (uncertain), one native
launch, no secret sentinel in output, unchanged project sentinels and no LiteLLM
traffic, with and without `--no-sync`. The 48-case native suite passes. This
checks conservative handling, not Go routing, quota classification, or a safe
fallback transition. P7.14 owns any future classifier and chain policy.

Rust fixtures exercise the actual validators with a synthetic Go-shaped
document: source validation rejects provider, title model and base URL changes;
agent validation rejects a foreign provider, different model, widened permission
and request override under deny and trusted profiles. A stricter experimental
agent check also requires exactly one title entry with the exact model; the
existing production validator does not require a title entry and accepts its
model as null. Catalog validation rejects a missing exact Go model and foreign
providers. Validators are factored to accept an explicit provider internally for
these fixtures; the production wrappers retain their existing behavior. These
fixtures do not prove an installed runtime's effective configuration.

## Candidate and live setup

The candidate is compiled only in Rust's test configuration. It starts with the
production `Runtime` and ACP adapter, replacing the native provider with
`opencode-go` in the isolated document, policy and expected catalog/session
model. It retains `AH_RUNTIME_API_KEY`, private HOME/XDG, no provider environment
key, source validation, deny permission profile, session model check, process
supervision and cleanup. The candidate additionally requires the effective title
agent to have the exact provider/model. The regular CLI cannot select this path.

`scripts/tests/go_acp_candidate.py` runs the actual preflight and ACP adapter
through the fake executable, with a fixed sentinel key. It checks success,
foreign/changed source, endpoint, helper, catalog and session refusals, and Go
limit behavior, as well as refusal of an otherwise successful turn with tool
activity. The fake-only test entry verifies the executable resolves to the
repository fake and requires the sentinel. Separate refusal tests exercise the
live entry without its gate, with the sentinel, and with a fake executable.
The focused runner passes 13 candidate cases and three live-entry refusals. The
offline runner completed 52/52 suites; after the later no-tool guard was added,
the focused runner was rerun. `cargo test --locked`, locked Clippy and doc-link
checks pass.

Setup review on [PR #132](https://github.com/awesomejt/agent-harness/pull/132)
of `f25d236` reported zero blockers and concerns, and one nit: the live-entry
refusal tests did not assert which guard refused. The fixture now checks each
specific refusal diagnostic; the live helper bytes are unchanged. The focused
runner passes again. The repository workflow does not require re-review for this
nit. The live result and its separate result review remain pending.

The separately ignored `runtime::go_candidate_fixture::live_acp` entry is
**not authorized to run until setup review completes and the operator provides
a fresh same-session Go workspace/active-plan/Extra-Usage-off attestation**.
It requires `AH_P710_LIVE=operator-attested` and `P710_KEY` in its environment,
refuses the fixture sentinel, and requires the executable to resolve to the
Homebrew OpenCode path. It uses a newly created private disposable project,
the fixed `opencode-go/kimi-k3` model, deny permissions, one fixed no-tool prompt
(`Reply with OK.`), a 90-second deadline, normal process cleanup and no retry.
It requires a nonempty response for success and refuses observed tool activity;
interrupts use the normal cancellation watcher.
The production preflight verifies the accepted 2.3.x version, sources, catalog,
agents and session model; no provider request is made before that preflight and
session selection succeed. The operator's key must be supplied privately through
`P710_KEY`; do not place it in a command argument, project file or evidence.
Build the test executable from the reviewed revision **before** supplying the
key, identify and fingerprint that executable, and launch it directly with only
the exact ignored test name; do not run Cargo or a compiler with the key in their
environment. Record the reviewed revision and executable digest without recording
the key. Do not persist the gate environment variable. A failed or uncertain run is a
stop, not permission to retry. User-provided interactive Go use is not a pass for
this candidate. No forced exhaustion, authenticated request, or model turn was
performed by this increment.

## Reproduce source identity

```sh
git clone --depth 1 --branch v2.3.0 https://github.com/anomalyco/opencode.git /tmp/ah-p710-source
git -C /tmp/ah-p710-source rev-parse HEAD
cd /tmp/ah-p710-source
shasum -a 256 packages/core/src/models-dev/snapshot.txt \
  packages/core/src/plugin/models-dev.ts packages/core/src/model-resolver.ts \
  packages/core/src/session/to-session-error.ts packages/core/src/session/model-request.ts \
  packages/core/src/app.ts packages/cli/src/acp/translate.ts packages/cli/src/acp/error.ts \
  packages/core/src/session/context.ts packages/core/src/session/runner/model.ts
```

Expected SHA-256 values, in command order:

```text
5d5740c70071aa628d1efe317f6885faf1f20b32a9fcb502553f57cce15cf9f1
5b456026359976407f2be11456d1974ee795ce3cc2a6ec41b0d0d0ac6a96ef74
65424cc372f85ff0de66c974dec8024692a7f389bbf663ef32982061273f0fa3
d40892d1ee6b46676c08c385126045776ee38b9910d0f502d692ce8101533328
2a7b1730cb7b222347bec4b3bfbd7143574f1960ccec68ca3dff736ab36321ab
fcd2450b44544b4a9bf83f2613d2d5b2a16f7079e108e2e48476705153235cfb
24bb0b85434a90834e9fc9214f69ebd11d06657dd3bafb54410eb810a814e2f2
bb1ec0aca37fe7e97698567ad705af24c6a5b3d2040d63753e73e88e84368e44
4b02e439fe766018c78c292b1530d45ee641c413333b758a5c6e51641567f0b8
d60af414540a66e52e0f918a2bed2809fe77d59f7b3b1b7ca7ae5afb48e790c8
```

The corresponding v2.3.2 hashes for the three changed files are:

```text
1e8bfc94f9a33a32963af92dd276b09fe1ddc9f7b4796a575a38f7c1b418f7b7  packages/core/src/model-resolver.ts
a1d44399d2052020e356db07dec8e2150be28a2108b153c5695ede46f420a025  packages/cli/src/acp/translate.ts
9e294e9ce2f1fbf7fcda7cce6fb9a2b49306560a39e327aed52ad8da11de012e  packages/core/src/session/context.ts
```
