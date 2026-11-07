# P8.1 evidence — Pi integration and capability decision

2026-11-07. Entry: merged PR #73, `680eb13`. Task: [P8.1](../../tasks/08-pi.md#p8-1). Decision: [D060](../../DECISIONS.md#2026-11-07--d060-select-pi-rpc-for-litellm-first-feasibility).

## Disposition and baseline

Select caller-owned Pi RPC for the Phase 8 runtime candidate. Pi owns its coding loop; Rust owns routing, process supervision, permission policy and normalized outcomes. P8.1 closes the interface/mapping decision only. Installed feasibility precedes P8.2 production implementation and any model turn. There is no supported Pi runtime/config value yet.

Pi and Gemini are absent from this session's PATH (`command -v pi`, `command -v gemini`). No executable, credential directory, session or model was accessed. Phase 7 Gemini setup remains blocked, Codex/Grok remain paused and Claude remains accepted. Independent Phase 8 decisions consume accepted P4.9, not Phase 7 portfolio acceptance.

The old `badlogic/pi-mono` GitHub API resolves to the current `earendil-works/pi` source. Pin this assessment to **c23b9ec1ef12a63573d739d4c294f81a377b7d57**. Its package manifest and the current npm metadata identify **@earendil-works/pi-coding-agent 1.5.0**, MIT, Node >=22.19.0. The legacy @mariozechner/pi-coding-agent latest metadata is 0.73.1; do not mix its interfaces with this assessment. Neither is an installed support pin, and npm tarball/source equivalence has not been established.

Read-only metadata sources: [current package](https://registry.npmjs.org/@earendil-works/pi-coding-agent/1.5.0), [legacy package](https://registry.npmjs.org/@mariozechner/pi-coding-agent/0.73.1). Current distribution integrity:

```text
sha512-xNDZ5kqowO6Z03FS2gwAkPEGk1ssxVcYKQ6qZId84mFEvwACvvyc2l0vAMOS+c5zvxLRMLBE9r4y44IGYkMJaQ==
```

No package installation or tarball execution occurred. Read-only raw source copies live outside the repository; installed discovery must compare matching release sources and record its own fingerprints.

## Selected route and authentication boundary

The first Pi candidate is **local-only through the existing LiteLLM proxy**, using an explicit compatible provider/model and only the existing route key in an allowlisted environment. Preserve resolved aliases/model groups, endpoint and no-sync validation. Do not inherit Pi's default provider, stored login, ambient keys, credential commands or direct local/OpenRouter endpoints. OpenRouter stays behind LiteLLM. This is a runtime change, not a new route.

Pi documents subscription logins and custom providers, but its third-party provider clients are not the official Claude/Codex/Grok/Gemini executables selected by D001/D047. **Do not select Pi's subscription clients for cloud-only or native fallback.** Keep native work in existing official CLI executors. Pi cloud-only is unsupported by this decision; local-first Pi primary plus an existing native fallback is deferred to a separately evidenced coordinator increment with D034's one pre-submission fallback and no replay. P8.2 must explicitly refuse unimplemented combinations.

A private Pi state/HOME is the selected isolation candidate for the LiteLLM form because it requires no Pi-owned subscription login. It must not import or read real auth storage. The existing harness LiteLLM key handoff remains the only credential input, as on the accepted OpenCode LiteLLM path; never write it literally to configuration or output. Confirm installed auth precedence cannot override that input before submission. This decision adds no Pi login form or subscription policy exception.

## Canonical mapping and capability limits

| Harness concept | Selected mapping / refusal | Required feasibility evidence |
|---|---|---|
| Primary or specialized named agent | Resolve canonical name/frontmatter in Rust; one direct Pi process per request, append canonical body and explicitly selected project instructions. No Pi subagent package or role-file sync. | Disable automatic context discovery; prove only planned instructions reach the model, without duplicate global/ancestor/project context. |
| Skills / prompt templates | Disable discovery/loading initially; skill activation and external packages are unsupported. Agent prose is instruction text, never a permission control. | Synthetic user/project/package sentinels stay unloaded; explicit policy extension is the only loaded extension. |
| Model | Explicit provider plus resolved LiteLLM alias; validate effective provider, model, endpoint and API transport before prompt. No default/model cycling/automatic provider substitution. | Synthetic proxy captures exact alias/endpoint/key source; trap every alternate endpoint, including startup/background traffic. |
| Effort | Model-default initially; explicit non-default effort refuses until exact model-specific thinking-level equivalence is proven. | Pi can clamp thinking levels; matching names alone do not prove canonical effort. |
| `deny` | No executable tools, MCP, codemode, custom/hosted tools or delegation. | Installed no-tool flags plus effective tool/resource inventory from the policy extension, validated before prompt; adversarial attempts must have zero tool effects. |
| `trusted` / narrowed roles | A harness-owned explicit extension gates each tool operation before execution, intersects canonical tools with the permission profile and defaults to refusal. | Exact tool name/arguments/path/grant binding, unique one-use request IDs, fail-closed disconnect/timeout, external paths and parallel-call handling. Until proven, refuse trusted and every unsupported constraint. |
| Usage / completion | Normalize provider-reported usage with Pi attribution, otherwise unknown. Settled idle is necessary, not sufficient for success. | Associate one submitted prompt with final assistant stop reason, no pending work, no errors/abort and `agent_settled`; validate malformed/duplicate/out-of-order records and usage scopes. |

Read-only is a constraint, not a no-tool profile. Pi tools run with host privileges; no OS sandbox is claimed. Trusted bash may execute arbitrary project code under the existing trusted contract. A blocked tool cannot be treated as successfully completed work. Shared steering, follow-ups, resumed Pi sessions and in-process SDK embedding are not selected.

## Supported control and terminal plan

The pinned sources establish a testable candidate, not runtime proof:

- [CLI reference](https://github.com/earendil-works/pi/blob/c23b9ec1ef12a63573d739d4c294f81a377b7d57/packages/coding-agent/docs/cli.md) documents `--mode rpc --no-session`, `--no-tools`, `--no-extensions`, `--no-mcp`, `--no-skills`, `--no-prompt-templates`, `--no-themes` and `--no-context-files`. `--no-tools` starts every tool source disabled; a plain `--tools` allowlist alone can leave MCP reachable. Explicit `-e` still loads with extension discovery disabled. Use only a harness-owned, pinned explicit policy extension, loaded outside the project; no installed/user packages. Prove startup/model-catalog/telemetry/cache-warming behavior and suppress unintended traffic before a model request.
- [Extension reference](https://github.com/earendil-works/pi/blob/c23b9ec1ef12a63573d739d4c294f81a377b7d57/packages/coding-agent/docs/extensions.md) provides active/all-tool inventory and a pre-execution `tool_call` block hook. Use a controlled extension to report effective state before accepting a prompt, then enforce exact one-shot grants through RPC extension UI. Inventory must account for inactive/indirect tool reach and provider registrations, not just model-visible tools. The documented ability to mutate tool inputs and load dynamic tools makes exclusive extension ownership necessary. No advisory prompt, post-hoc event or unverified empty list substitutes for enforcement.
- [RPC reference](https://github.com/earendil-works/pi/blob/c23b9ec1ef12a63573d739d4c294f81a377b7d57/packages/coding-agent/docs/rpc.md) defines LF-delimited JSON records, correlated command IDs, asynchronous responses and continuous pipe draining. RPC is Pi's own protocol, **not ACP/JSON-RPC 2.0**. A successful prompt response acknowledges handling, not completion; even `agent_end` can precede automatic work. [Event reference](https://github.com/earendil-works/pi/blob/c23b9ec1ef12a63573d739d4c294f81a377b7d57/packages/coding-agent/docs/json.md) makes `agent_settled` the idle boundary; still inspect the final assistant stop reason/errors and abort flag. A prompt disposition of `handled` starts no run and cannot count as model success.
- [Command reference](https://github.com/earendil-works/pi/blob/c23b9ec1ef12a63573d739d4c294f81a377b7d57/packages/coding-agent/docs/rpc-commands.md) supplies `get_state`, model/thinking selection, abort and automatic-retry/compaction controls. Preflight must disable automatic agent retry, provider retries, compaction and cache warming where supported; prove no hidden resubmission/background inference remains. `get_state` alone lacks a complete effective tool/source inventory. The planned extension must supply and bind missing state to the same process/session.
- Shutdown: mark submission before writing prompt bytes. Abort on cancellation, then close stdin and allow bounded cooperative exit before process-group cleanup under D030. Missing terminal, descriptor leak, timeout or malformed protocol after submission means uncertainty; no replay or fallback. No session resume/fork/bash/steer/follow-up RPCs are authorized in the first slice.

A minimal no-inference feasibility allowlist may inspect `get_state` and disable retry/compaction after startup isolation is established; it must not send `prompt`, `bash`, session switch/fork or provider-auth commands. An explicit extension can execute during startup, so first inspect matching release source and run synthetic isolated startup-effect checks. Preflight reports must be strict, bounded, uniquely correlated and tied to the exact requested profile/model rather than arbitrary extension text.

## Next increment and acceptance gates

1. Operator supplies the official Pi executable on PATH; no login is needed for the selected LiteLLM-only form. Record exact version/distribution, Node compatibility and matching release sources. Do not silently install a legacy package or reuse its flags.
2. Open a focused P8.2 feasibility PR before production adapter work: isolated synthetic HOME/state/project/settings/model/extension/context sentinels, environment allowlist, trapped networking, no model turn, bounded output/deadlines and descendant/pipe cleanup. Verify private-state isolation and full pre-turn deny inventory. Record a pause if effective controls cannot be established.
3. Only after those controls pass, implement narrow deny-profile launch/events plus fake protocol/lifecycle/refusal regressions. Prove the trusted policy bridge separately before advertising it. Finalize public runtime/config syntax at that consuming increment, without speculative flags here.
4. P8.3 still requires live primary/specialized coding use against LiteLLM and a direct-tool comparison. P8.4 owns sequence/Ralph parity/recovery; P8.5 remains the holistic phase gate. P7.6/P7.7 and optional Phase 9 gates are unaffected.

No development-platform switch is required. Gemini setup or new Codex/Grok control evidence can reopen Phase 7 work, but switching development apps alone supplies neither. With Pi and Gemini absent, the next consuming tasks require setup; another documentation-only selection is not a substitute for installed proof.

## Validation and reproducibility

Read-only GitHub API/raw source and versioned npm metadata requests, plus PATH observations. Reproduce source lookup with `https://api.github.com/repos/badlogic/pi-mono/commits/main`, then fetch raw files from the recorded commit rather than moving main. Selected SHA-256 fingerprints:

| Pinned path | SHA-256 |
|---|---|
| `packages/coding-agent/package.json` | `e9c967b05f1135093ae1475813ffcc87ac8d33a01f4b49c4744c364d8b4314b3` |
| `packages/coding-agent/docs/rpc.md` | `54e29df00e080c962df4fbb516dc441a9ce6805287bea61d45f3c99f92078446` |
| `packages/coding-agent/docs/extensions.md` | `d59f4ded8e49275120c8379dbeabb847267efd36e15fc21f6189026d0fbf8f22` |
| `packages/coding-agent/src/cli/args.ts` | `7db79597928e0ae100fdcaf41d6fbd9c5b841744a9f87c4745e3ad0863435e29` |

Relative Markdown links and whitespace checks are required before PR closeout. No production Rust/dependency changes; Rust/runtime suites and billable model calls are not needed for this decision task. Installed/live claims remain explicitly unverified. PR review/merge results belong in PROJECT.md.
