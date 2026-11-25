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
  establish the effective endpoint of a configured runtime. The same pinned
  snapshot includes `opencode-go/beam-free`, whose chat-completions base URL is
  `https://opencode.ai/inference/go/openai/v1`.
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
refusal tests did not assert which guard refused. `2428104` corrected the
fixture. At the operator's request, `d0fb2b3` then changed the live helper model
from `kimi-k3` to `beam-free`. A follow-up review found zero blockers, one
concern about the stale setup record and missing Beam Free source observation,
and one portability nit. The follow-up reviewed the model change; this record
corrects its requested model and endpoint evidence, and the portability nit is
fixed. Neither finding requires another setup review under the workflow. The
third review covered the live result and found zero blockers, zero concerns and
two documentation nits, corrected here; no further review is required.

The separately ignored `runtime::go_candidate_fixture::live_acp` entry requires
setup review and a fresh same-session Go account/Extra-Usage-off attestation
before each live run.
It requires `AH_P710_LIVE=operator-attested` and `P710_KEY` in its environment,
refuses the fixture sentinel, and requires the executable to resolve to the
Homebrew OpenCode path. It uses a newly created private disposable project,
the operator-selected `opencode-go/beam-free` model, deny permissions, one fixed no-tool prompt
(`Reply with OK.`), a 90-second deadline, normal process cleanup and no retry.
It requires a nonempty response for success and refuses observed tool activity;
interrupts use the normal cancellation watcher.
Beam Free was selected by the operator. A successful request to this free model
does not demonstrate paid Go allowance consumption, subscription entitlement,
or live Go-limit behavior; those remain limitations of that observation.
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
performed before setup review.

## Bounded live observation

On 2026-11-24 at approximately 22:45 CST, the operator confirmed Extra Usage
was still off for the existing Personal Go account and directed the use of Beam
Free. Earlier in the session the operator supplied screenshots of the active Go
subscription, the disabled Extra Usage setting and a Personal API-key entry,
then configured the key used here. The operator stated the existing account was
active. These account observations are not an independent API verification of
workspace/key association or billing state.

One run used source revision `c2e840d70b40d6cf2b808f4a6b1df3eb0e2766a2`
(its Rust sources match reviewed revision `d0fb2b3`; subsequent changes before
the run affected documentation and the test runner),
the prebuilt test executable SHA-256
`d9cc3e4f4e63feef0b335f3dbe7d9377d8ed943c47c9d66716a9a2b391ce12f9`,
and installed OpenCode 2.3.2 on macOS arm64. The reviewed preflight passed the
isolated source, Go-only catalog, effective-agent/title and version checks; ACP
session selection matched `opencode-go/beam-free`. The fixed prompt produced
`OK`, terminal `end_turn` and result 0 in approximately 2.3 seconds, with zero
permission requests, grants or tool events, zero recorded stderr bytes and
confirmed process and private-runtime cleanup. The disposable project removal
also succeeded. No retry or deliberate limit exhaustion occurred. The key was
supplied to the test via its environment, remapped to the private runtime child,
and was not recorded in the evidence.

This observation establishes the selected effective OpenCode Go model and a
successful no-tool ACP response. It is not a captured wire trace, paid allowance
or entitlement proof, live usage-limit test, billing guarantee, or production
Go adapter. P7.12 still owns its own schema, route implementation and live
acceptance, including a fresh account check. P7.10 acceptance is effective on
PR #132 merge after the completed result review.

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
