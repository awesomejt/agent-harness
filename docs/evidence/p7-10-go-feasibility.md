# P7.10 — Dedicated OpenCode Go feasibility assessment

Date: 2026-11-09. Entry: PR #85 merged. Decision: D072.

## Selected assessment and stop condition

Select the unmodified official OpenCode CLI/server 2.2.5 candidate already used
for D069/D070, on D041 Apple Silicon macOS. Select dedicated `opencode-go`,
separately from non-Go `opencode`/Zen (which also includes free models), and assess
`kimi-k3` as a catalog example, not a public
support pin or entitlement claim. Fresh official tagged source is pinned below;
installed executable provenance remains distinct from tagged source.

Plan: review public catalog, provider registration, request headers, configuration
and account-control documentation without executing upstream code or installing
dependencies. Reuse D071's source/state inventory. Stop before installed checks if
the same CLI/server cannot exclude machine/MDM and other uncontrolled sources.
Only after a separately evidenced source-control plan may a contained synthetic
experiment reuse D070's private transport, disposable HOME/XDG/data, cleared
environment, network/home-read/outside-write containment and bounded cleanup.
No real credential inspection/copy, login, authentication, session, inference or
production change is authorized by this assessment.

Result: the stop condition is met. **P7.10 remains unchecked and P7.12 blocked.**
This focused source assessment can close on required PR review/merge; it does not
pass the full feasibility card. No OpenCode executable was launched here. Neither
installed effective routing nor provider request headers nor account state was
observed. The findings below distinguish public-source facts from future proof.

## Fresh official documentation

The [Go documentation](https://opencode.ai/docs/console/go/), re-read 2026-11-09,
allows coding-agent clients, requires their own user agent and stable conversation
session attribution, and documents `opencode-go/<model-id>` plus Go-specific
inference endpoints. Extra Usage can charge a Console balance after allowance
exhaustion; Teams starts with it enabled. The documented control is on the Go
page in Console. These are service documentation observations, not account checks.
No pricing, model availability or default setting proves this operator's state.

## Pinned source findings

Table paths are relative to `packages/core/src/`, except `server/` denotes
`packages/server/src/`, in the official
[v2.2.5 commit](https://github.com/anomalyco/opencode/tree/9bbb8ce18c80f099e0e448775f59d965ead40a21).
A fresh shallow checkout resolves to `9bbb8ce18c80f099e0e448775f59d965ead40a21`.

| Control | Source observation and consequence |
|---|---|
| Provider distinction | `models-dev/snapshot.txt` has separate `opencode` and `opencode-go` records. For `kimi-k3`, the former uses `https://opencode.ai/inference/openai/v1`, the latter `https://opencode.ai/inference/go/openai/v1`. Both expose `OPENCODE_API_KEY`. A key name or shared host does not distinguish Go from metered traffic. |
| Registration and secret ownership | `plugin/models-dev.ts` registers separate provider/integration IDs and key/environment methods. `model-resolver.ts` resolves the selected integration connection and maps runtime-owned key credentials to provider settings. This is a source lead for official-client-owned secret handling, not installed auth precedence or permission to read/copy the operator's store. |
| Explicit model | `session/runner/model.ts` looks up explicit session provider/model identity and errors when unavailable. Without explicit session selection it may use agent/default resolution. Every future main/helper selection must be pinned or disabled; the default path is not a Go-only guarantee. |
| Mutable endpoint | `config/plugin/provider.ts` lets configured provider baseURL replace catalog per-model endpoints; per-model settings can win later. `model-resolver.ts` merges settings/headers. Therefore catalog Go identity is necessary but insufficient effective endpoint proof. |
| Client identification | `app.ts` formats the user agent as `opencode/<channel>/<version>/<name>`. `session/model-request.ts` places `App.useragent(app)` in request headers. Select honest official OpenCode identity; do not spoof a different validated client. Final wire headers remain unproven. |
| Session attribution | `session/model-request.ts` sets `x-opencode-session` to `SessionAffinity.get(session)`, as well as session/client/project headers. `session/affinity.ts` chooses parent ID, else fork source, else current ID. Continuation, child and fork attribution needs installed trapped-request proof, not a header-presence assertion. |
| Hooks | The same request path triggers `session/model.request`, which can replace baseURL and headers, and then optional HTTP hooks. Uncontrolled plugins can alter the proposed route and identity before delivery. |
| Helpers | `session/context.ts` selects an explicit title-agent model, otherwise a small model in the primary provider via `model.ts`; `session/title.ts` can attempt selected and primary models. `generate.ts` has a separate stateless text path creating a new session header. Main-turn header code does not prove all auxiliary traffic shares the conversation or stays on Go. The consuming experiment must inventory title/compaction/summary/other generation paths and disable or prove each enabled path. |
| Limit reporting | `session/to-session-error.ts` maps `GoUsageLimitError` to `provider.go-limit`, with a message suggesting free models or Extra Usage. This is error classification, not proof of refusal without another paid request, disabled overage, or safe harness output. Preserve D034; no new fallback or automatic free-model switch is selected. |
| Shared source blocker | `server/options.ts` exposes project/claude/file/content but no global/system controls; `server/routes.ts` forwards that subset. `config/discovery.ts` has core-only controls for machine directory/MDM discovery. D071's source/state blocker therefore applies to Go independently of credential type. |

The `kimi-k3` catalog example lists `none` among its advertised tool choices
(`auto`, `none`, `required`); other Go models need separate capability checks. That metadata is not complete runtime no-tool denial.
No installed `deny`, exact trusted grant, named-role constraint or helper isolation
is claimed. No public schema, model default, route target or CLI flag is added.

## Reproduction without runtime or account access

Use a fresh absent destination, then inspect public files only:

```sh
git clone --depth 1 --branch v2.2.5 https://github.com/anomalyco/opencode.git /tmp/ah-go-source-review
git -C /tmp/ah-go-source-review rev-parse HEAD
cd /tmp/ah-go-source-review
python3 - <<'PYCODE'
import json
from pathlib import Path
catalog = json.loads(Path("packages/core/src/models-dev/snapshot.txt").read_text())
for provider in ("opencode", "opencode-go"):
    item = catalog[provider]
    model = item["models"]["kimi-k3"]
    print(provider, item["env"], model["api"]["chat-completions"]["base_url"])
PYCODE
shasum -a 256 packages/core/src/models-dev/snapshot.txt \
  packages/core/src/plugin/models-dev.ts \
  packages/core/src/config/plugin/provider.ts \
  packages/core/src/model-resolver.ts \
  packages/core/src/session/runner/model.ts \
  packages/core/src/session/model-request.ts \
  packages/core/src/session/affinity.ts \
  packages/core/src/app.ts \
  packages/core/src/generate.ts \
  packages/core/src/session/title.ts \
  packages/core/src/session/to-session-error.ts \
  packages/core/src/config/discovery.ts \
  packages/server/src/options.ts \
  packages/server/src/routes.ts \
  packages/cli/src/server-process.ts \
  packages/core/src/usage-limits.ts \
  packages/core/src/session/context.ts \
  packages/core/src/model.ts
```

Linux can use `sha256sum` with the same file arguments, without `-a 256`.
The JSON extraction reads a bundled public catalog, not an effective runtime
configuration. No synthetic runtime controls were exercised because the stop
condition was met. D071 remains the complete shared discovery/state inventory.

## Extra Usage verification plan and limits

Immediately before each later live-acceptance run, in the same operator session,
the operator must verify the intended Console workspace/account, active Go plan
and Extra Usage **off** on its Go page. Record the timestamp (with timezone),
workspace/plan match and off result in the P7.12 live-acceptance evidence under
`docs/evidence/`, linked from PROJECT.md, without keys, balance details or personal
data. Recheck after workspace/plan changes and after any interruption between
verification and the run; an earlier day/session attestation is insufficient. Unknown, enabled
or wrong-workspace state blocks the run; do not infer off from individual-plan
defaults or a zero balance. The operator owns account changes.

`usage-limits.ts` reads Go allowance percentages, limit status and reset times,
not Extra Usage. Its query requires an active `opencode` Console connection with
workspace metadata; the separate catalog `opencode-go` key integration alone
does not supply that path. Even a successful usage query cannot attest overage off.
No supported programmatic read of that setting has been established by the
inspected documentation/source. This assessment did not call Console, inspect
private account endpoints or authenticate. An operator attestation is a point-in-time
account check, not continuous harness enforcement or a guaranteed hard cap.
Future implementation must state this limitation explicitly and must not substitute
metered Zen, another paid provider or automatic Extra Usage when limits refuse.
A synthetic limit response and later bounded live acceptance must separately
verify refusal/output/no-replay; deliberately exhausting allowance is unnecessary.
D067's included-allowance spend rule remains binding.

## Resume boundary and next task

The next portfolio work is a **separate shared source-control design assessment**
under P7.9/D071, consumed by P7.10 as well: identify supported official CLI/server
exclusions, or design a narrowly justified source-read/refusal boundary for
machine/MDM resources and changes. Record and independently review that plan
before installed expansion. Do not repeat config diagnostics on this unchanged
uncontrolled baseline, rebuild/embed core implicitly, seed machine-wide files or
waive the gate. A newer interface must provide specific changed control evidence.

After that boundary passes, a separate Go continuation must prove synthetic
resource/persistent-state exclusion, runtime-owned exclusive-state credential
setup under a separate D047 decision, exact effective provider/model/endpoint,
main/helper headers and permissions. D070 only supplies an experimental diagnostic
transport; it is not production containment. Real operator state is never imported
for synthetic proof. P7.11/P7.12 and P7.13/P7.6/P7.7 remain gated. Independent
P8.2 Pi continuation is available under D060/D065; no implicit placement switch.

No platform switch is required. A fresh context is efficient for the shared
control-design task. No Rust/dependency/runtime changes, installation, auth/model
traffic or direct-tool coding comparison occurred in this static assessment.

## Source fingerprints and validation

SHA-256 of public tagged source; these do not certify installed build equivalence.

| File | SHA-256 |
|---|---|
| [packages/core/src/models-dev/snapshot.txt](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/models-dev/snapshot.txt) | `5d5740c70071aa628d1efe317f6885faf1f20b32a9fcb502553f57cce15cf9f1` |
| [packages/core/src/plugin/models-dev.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/plugin/models-dev.ts) | `5b456026359976407f2be11456d1974ee795ce3cc2a6ec41b0d0d0ac6a96ef74` |
| [packages/core/src/config/plugin/provider.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/plugin/provider.ts) | `61f9ab3d689c792d4dbaaf42efe2c6c1c902b24da3a91c5745578ebcd93c77f0` |
| [packages/core/src/model-resolver.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/model-resolver.ts) | `521cd590c715c6ba26e1af9b3c0f7fbd88dce6db670306b22378bc4cc71d40b8` |
| [packages/core/src/session/runner/model.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/runner/model.ts) | `4da9f4cb5c0d785d07bb5168aa4086fa398002c0382f5d0c4d42658b9e29641a` |
| [packages/core/src/session/model-request.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/model-request.ts) | `9b295efe14e64105d99f7edda87ce6205e722954f3a133c38f9db630d6b6886c` |
| [packages/core/src/session/affinity.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/affinity.ts) | `06187f3eb40c5f39386316abf1079327089af3c4f154737606a02ed5d8d3be22` |
| [packages/core/src/app.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/app.ts) | `c11731f94606f7c4cffc11822ee93de5849283f35b9ff12ee1fc1b753a92e3f9` |
| [packages/core/src/generate.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/generate.ts) | `319ce03989abb58af2dbf045af97fa72382762aa5f1e3a7a6bc9f330cd2d120a` |
| [packages/core/src/session/title.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/title.ts) | `72c5b35e54ff70dd63627acd4b65b0b053ea970d729c662ce1ea5f7661ac847b` |
| [packages/core/src/session/to-session-error.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/to-session-error.ts) | `444a47da0ae7c9f80415c83d8f00085ef13b84cd19f50161bcc16f21ac178ad4` |
| [packages/core/src/config/discovery.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/config/discovery.ts) | `48118dafc1ba0ec03112e98cdd616f339262a08a42b4ae75e9014575d863434d` |
| [packages/server/src/options.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/server/src/options.ts) | `131335c86cf30eba4ec47bc3ccf6632f35b3e94b4c3ac2e7685784bf42a1c8af` |
| [packages/server/src/routes.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/server/src/routes.ts) | `284510fcdba864c46bfb382cf40acc3d473e61176b5e8999da7dc52efe5599c9` |
| [packages/cli/src/server-process.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/cli/src/server-process.ts) | `37e89b2eed32bc9324f4cdf0a639387dfe6fc0ef8e6f37fc33c43987869b4bc2` |
| [packages/core/src/usage-limits.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/usage-limits.ts) | `6891419fe21a037f5ed42fd282533db1692cb8797b01b6398c1dd758e6280145` |
| [packages/core/src/session/context.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/session/context.ts) | `6e6567d148166fb581e6a1c6337b0675685d06e36f84463409240f38ea9708d0` |
| [packages/core/src/model.ts](https://github.com/anomalyco/opencode/blob/9bbb8ce18c80f099e0e448775f59d965ead40a21/packages/core/src/model.ts) | `4727e56aaa53d5e128c836002895695e1bba95a1382dac64a19bcc9f12500525` |

Independent read-only security/spend review confirms both high-risk gates are
preserved: missing source exclusions prevent installed expansion, and the usage
query cannot verify Extra Usage. The assessment records them as blockers rather
than introducing runtime work. The exact extraction/hash command and all 18 fingerprints pass against the fresh
checkout. Documentation links/anchors and Git whitespace checks pass. No Rust tests
are required for unchanged production code/dependencies.

Grok reviewed `acd7cdc` in [PR #86](https://github.com/awesomejt/agent-harness/pull/86)
under the operator account: 0 blockers, 0 concerns, 2 nits. Both addressed: table
path bases are explicit, and the Extra Usage check now requires the same operator
session immediately before each run, with timestamp/timezone and a linked P7.12
evidence location. Independent review's two wording refinements also clarify
catalog tool choices and non-Go Zen's inclusion of free models. Documentation
links/anchors, exact reproduction/fingerprints and whitespace pass. No critical/high
finding and no re-review requested. Bounded assessment closeout is effective on
merge; full P7.10 remains open.
