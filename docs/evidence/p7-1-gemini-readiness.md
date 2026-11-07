# P7.1 evidence — Gemini selection and readiness

**Superseded for future work by D061:** the operator replaced the Gemini CLI requirement with Antigravity CLI. See the [current assessment](p7-1-antigravity-readiness.md). This report preserves the earlier observations; its Gemini installation/selection steps are no longer the project plan.

2026-11-07. Entry: merged PR #72, `12c4f1b`. Task: [P7.1](../../tasks/07-native-adapters.md#p7-1). Decision: [D059](../../DECISIONS.md#2026-11-07--d059-select-gemini-for-readiness-with-installed-controls-still-gated).

## Disposition and boundary

Select Gemini as the next Phase 7 candidate for readiness and bounded feasibility. It is the remaining committed native target after Claude acceptance and the Codex/Grok control pauses. This is portfolio-driven selection, not evidence of operator account entitlement or current Gemini use. Only this assessment is complete; P7.5 stays unchecked. No production implementation or model work is activated.

The official executable is not on this session's PATH. An installed version, CLI-owned login compatibility, effective controls and runtime protocol are unverified. Published metadata is a candidate baseline only. Do not treat this report as installed or live adapter acceptance. Codex/Grok resume only with D055/D058's changed evidence; selecting Gemini does not clear their gates.

## Reproducible host and package observations

On D041's Darwin arm64 host, `shutil.which("gemini")` and `shutil.which("pi")` returned `None`. This establishes PATH availability only, not absence from every directory or absence of an account. Node and npm are available under the operator's nvm Node v24.14.0 directory. No login/config/credential directories were read.

A read-only HTTPS request to [the npm package metadata](https://registry.npmjs.org/@google/gemini-cli/0.67.0) observed `@google/gemini-cli` version **0.67.0** at `latest`, Node `>=20`, Apache-2.0, and the official `google-gemini/gemini-cli` repository. Recorded distribution integrity:

```text
sha512-lDJfCcYem6/6QZdwZFiGfOu1ZxJJ+j4wsr4HlmcYBfqUHTDXLKDv1MPUXYL2Ok1ygdfMve0F5KrW/ORNZRSHIg==
```

Reproduce without executing or installing the package:

```python
import json, shutil, urllib.request
for name in ("gemini", "pi", "node", "npm"):
    print(name, shutil.which(name))
with urllib.request.urlopen(
    "https://registry.npmjs.org/@google/gemini-cli/0.67.0", timeout=20
) as response:
    package = json.load(response)
print({key: package.get(key) for key in
       ("name", "version", "engines", "license", "repository")})
print(package["dist"]["integrity"])
```

The initial discovery used `/latest`; the versioned URL above makes the candidate reproducible. No tarball was downloaded, signature independently verified, package installed, CLI launched, ACP handshake/session created or prompt submitted. A future installed release must be identified and pinned on its own evidence; website documentation is not proof of 0.67.0 behavior.

## Official interface, authentication and service boundary

Sources checked 2026-11-07:

- [ACP mode](https://geminicli.com/docs/cli/acp-mode/) documents `gemini --acp`, caller-owned stdio JSON-RPC, session control and cancellation. Choose this as the feasibility candidate, reusing harness protocol/process ownership while Gemini owns the coding loop. Verify installed wire names, protocol version, notifications and terminal semantics rather than copying the documentation's conceptual method names. A documented model-change method is unstable; model/effort support needs separate proof.
- [Authentication](https://geminicli.com/docs/get-started/authentication/) documents Google-account sign-in and existing cached authentication in headless mode. D047 selects the operator's official CLI login; account eligibility and ACP login reuse remain untested. API-key/Vertex alternatives are not selected by this increment.
- [Terms/privacy notice](https://geminicli.com/docs/resources/tos-privacy/) identifies service terms by authentication method and prohibits direct third-party access to the backing services. The selected candidate launches the official CLI through its documented integration, with all service and credential handling inside it. No extracted OAuth, custom service client, endpoint impersonation, shared-login service or LiteLLM subscription route is allowed. This is an integration-boundary assessment, not account-specific legal/entitlement approval.
- [Installation](https://geminicli.com/docs/get-started/installation/) documents npm/Homebrew and stable releases. D047 requires official installation and login by the operator before harness use. If Gemini exists outside PATH, exposing that executable is sufficient to start installed discovery; otherwise install through the official guide and sign in directly. Do not substitute an API key or auto-login to bypass this prerequisite.

Headless stream output remains an alternative if installed ACP is unsuitable. Third-party ACP bridges, embedded SDK/replacement loops, shared daemons and direct backend HTTP are not selected.

## Supported-control leads and consuming evidence

These are documentation leads, not proven launch arguments or an accepted permission mapping.

| Question | Official lead | Required evidence before consumption |
|---|---|---|
| Complete no-tool `deny` | [Policy engine](https://geminicli.com/docs/reference/policy-engine/) documents wildcard tool rules, deny decisions, priorities and exclusion of globally denied tools from model context. | Prove installed ACP honors a complete deny policy before submission, including built-ins, MCP, discovered/hosted tools and subagents; account for higher-priority inherited policies. Validate effective state. Empty lists, read-only mode and rejected approval callbacks alone are insufficient. |
| Configuration isolation with login | [Configuration reference](https://geminicli.com/docs/reference/configuration/) describes user/project/system layers and a system-settings path override. | Use synthetic sentinels to establish actual precedence, merge/array semantics and isolation of model, endpoints, instructions, policies, extensions, hooks, skills, MCP, environment files and delegation. Preserve CLI-owned login; a settings overlay or private HOME alone is not proof. |
| Trusted and constrained roles | Policy engine distinguishes allow/deny/ask-user; headless ask-user becomes denial. | Prove exact per-operation host decisions on ACP, including reads that might otherwise execute without approval, raw arguments, external paths, one-use grants and default deny. Refuse profiles/roles lacking enforcement. |
| Model and events | ACP offers session model/mode controls and streamed updates. | Prove exact native model/provider selection and refusal of alternate endpoints; decide effort mapping only if enforceable. Record source-attributed usage or unknown, strict terminals, bounded output and malformed/duplicate-message refusal. |
| Lifecycle and project instructions | ACP documents cancellation and client file-system capabilities. | Determine startup/session effects before expanding an initialize-only allowlist; prove bounded descendant cleanup, explicit AGENTS.md mapping and no inherited prompt sources beyond the planned request. Retain D030/D031/D034/D039 submission and no-replay boundaries. |

The configuration reference's `tools.core` is a built-in allowlist; `tools.allowed`/`--allowed-tools` bypass confirmation. They are different controls. An empty `tools.core`, tool exclusions or disabled extensions cannot be assumed to cover every tool source. No complete no-tool/isolation plan is proven here.

## Next task and gates

1. Obtain an official executable on PATH and operator-owned login per D047; report its exact version and distribution without inspecting credential material. Missing PATH is the observed setup blocker; login state is unknown.
2. Start a focused P7.5 no-inference feasibility PR. First inspect bounded isolated help/version and matching release sources. Prove startup effects before initialization; keep an explicit no-session/no-prompt allowlist until effective isolation permits expanding it. Use synthetic config and bounded output/deadline/process-group cleanup. Any login-preserving isolation alternative needs an evidenced decision; never copy credentials into a private home.
3. Only after complete pre-turn deny/isolation proof, implement narrow launch/events, trusted roles, workflows/fallback and live acceptance increments as warranted. If proof fails, record the specific pause/resume evidence instead of repeating the same probe or submitting a model turn.

No development-app/platform switch is required for discovery or feasibility. A switch alone does not provide the executable/login or prove controls. Independent P8.1 Pi decisions remain available if Gemini setup is unavailable; Pi is also absent from PATH here, so live Pi acceptance would need its own setup. P7.6/P7.7 remain full-portfolio gates; no holistic phase review is ready. Phase 9 remains demand-gated.

## Validation

Read-only PATH/package observations and official-source assessment above; relative Markdown links and `git diff --check` pass. No source/dependency behavior changed, so Rust/runtime suites and billable model runs are not required for this documentation increment. PR review/merge closeout is recorded in PROJECT.md.
