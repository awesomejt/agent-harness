# P7.4 evidence — Grok initialization and configuration feasibility

2026-11-07. Baseline: merged P7.1 selection PR #70, `6c6b7a6321810cbe82f8a6843bb44d6f08b6e34c`. Task: [P7.4](../../tasks/07-native-adapters.md#p7-4). Selection: D056. Disposition: [D057](../../DECISIONS.md#2026-11-07--d057-record-grok-initialization-with-the-production-control-gate-unpassed).

## Result and boundary

**Discovery increment complete; the production permission/isolation gate is not passed.** Installed official Grok `1.0.70 (f50904eaee6c)` accepts ACP protocol 1 initialization without a login or model turn. Its reported model distinguishes top-level and agent-level flags. Neither initialization nor inspect establishes a complete effective no-tool boundary. No `native.target: grok`, production adapter, dependency or model work is added; P7.4 remains unchecked.

The committed [probe](../../scripts/experiments/grok_feasibility.py) is repeatable on the D041 Apple Silicon macOS host. It uses disposable synthetic HOME/GROK_HOME/config, a cleared environment, an empty project with a synthetic AGENTS.md, closed stdin for discovery commands, and caller-owned stdio for initialization. It supplies no operator credentials and does not inspect/copy any operator login file. Authentication and account entitlement remain unverified. There are no `authenticate`, `session/new`, `session/prompt`, permission responses or model turns; the send function only permits `initialize`.

This is **not a network sandbox**: official startup may do background work even without inference. It is not proof of production configuration isolation, fresh-process/leader isolation, complete child-tree behavior, or real-login compatibility. Synthetic HOME is used for discovery only, not selected as a production login solution under D047.

## Installed observations

All observations below reproduced with the pinned installed binary, not a source build:

| Check | Observation | Meaning |
|---|---|---|
| Version | `grok 1.0.70 (f50904eaee6c)` | Probe refuses a different pin. |
| Baseline `inspect --json` | Synthetic user permission source (`loaded: 1`) and both user/project MCP entries are reported. | User/project configuration can contribute before a turn; inspection is not an empty-environment guarantee. |
| Inspect with `--tools= --deny '*' --no-subagents --disable-web-search` | Same synthetic permission count and MCP entries remain. | Parser acceptance does not make inspect an effective tool-filter readback. This does **not** demonstrate that ACP executes any forbidden tool or ignores all these flags. |
| Baseline initialization | Protocol 1, agent version 1.0.70, synthetic user-selected `grok-4.5`. | Handshake works; model report comes before any session/prompt. |
| Top-level `-m grok-4.6` plus filters, then `agent --no-leader stdio` | Initialization still reports `grok-4.5`. | Top-level model selection does not set the agent's reported model on this launch path. Do not extrapolate to every flag. |
| `agent --no-leader -m grok-4.6 stdio` with top-level filters | Initialization reports `grok-4.6`. | Agent-level model selection reaches this pre-session report. No inference verifies the eventual request model. |
| Initialization inventory/auth | No `tools` field at result top level or `_meta`; no default authentication method selected. | Available auth methods are not proof of login. Absence of those two fields is not proof that every possible introspection surface is absent. |
| Startup writes | User config receives `[marketplace] default_skills_installs_purged = true`; support docs, logs, metadata and a session-search index appear under synthetic GROK_HOME. | Startup itself can mutate user state before a session. The probe checks the exact observed config migration; production planning must account for it. |
| Project preservation | Synthetic AGENTS.md and the remaining empty `.grok` directory are unchanged. No synthetic auth.json appears. | Bounded scratch preservation only; no project instruction-loading or login-preservation claim. |

The synthetic MCP commands are `/usr/bin/false`. Both MCP configurations are removed **before** ACP initialization, so the committed probe does not start configured MCP servers. The initial configuration bytes are checked after inspect and before that deliberate change. No MCP startup/permission/tool-lifecycle claim follows from the initialization result.

An exploratory scratch run also used inert marker-producing MCP commands before initialization; neither marker appeared within three seconds and initialization reported no MCP entries. This negative, unauthenticated observation does not prove startup cannot launch extensions. It is not part of the repeatable acceptance assertions; the committed probe deliberately removes those configurations first.

Initialization-only runs generate bundled help documentation under synthetic GROK_HOME. The inspected installed files have these SHA-256 fingerprints (exact file bytes):

| Bundled `docs/user-guide/` file | SHA-256 |
|---|---|
| `05-configuration.md` | `ce49c8f08db8c05cb2bc9f040d0955573fbe6b86d5af4381ff2547197a66d433` |
| `15-agent-mode.md` | `b4c4b840392a9b85a356b433b729ea02a89bf2742aa74894bbec56ff369c8fed` |
| `26-config-reference.md` | `ebd97fec98bb00bfdfa37befddf31dd8a14e3f277db887c7b643888867865db7` |
| `02-authentication.md` | `04630e3d30bb74c0a7b1c3df3e50fe42e4285d7aeeacc4ecd7573cfbe34852bb` |

These identify the installed documentation inspected during scratch discovery. The committed probe deletes its temporary home on exit; it does not retain generated docs, logs, identifiers or raw protocol data.

## Supported-control leads and source limits

Official online [headless/ACP](https://docs.x.ai/build/cli/headless-scripting), [settings](https://docs.x.ai/build/settings) and [permissions](https://docs.x.ai/build/features/permissions) pages were checked on 2026-11-07. They document official scripting/stdio integration, configuration discovery and permission rules. These identify candidates to test, not complete enforcement evidence. D047/D056's authentication and routing boundaries remain unchanged.

The bundled configuration guide describes `GROK_CONFIG` / `GROK_CONFIG_PATH` as allowlisted deep-merged overlays, not replacements for user configuration; requirements/MDM can take precedence. Empty overlays are therefore not a blanket config reset. The bundled agent-mode guide describes `--agent-profile`, session metadata profiles and local versus daemon/leader routes with different behavior. Its authentication guide places login state in the Grok home; the config reference also mentions `GROK_AUTH_PATH`. None was exercised with operator login material. A separate official-CLI-owned authentication-path control would need an evidenced D047 isolation decision, not harness credential handling or an assumption that a private home retains login.

Pinned upstream source was inspected at public commit [`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`](https://github.com/xai-org/grok-build/tree/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8). This is a **different public source snapshot**, not verified source for installed build `f50904eaee6c`; resolving that build identifier through the public commits API returned no commit. Source observations are leads, not runtime proof:

- [`xai-grok-pager-bin/src/main.rs`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-pager-bin/src/main.rs#L1226) dispatches the agent command separately and takes its model from agent arguments, consistent with the installed model observations. The launch path must be assessed flag by flag; top-level tool-filter propagation is not established by parser help.
- [`mvp_agent/acp_agent.rs`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/agent/mvp_agent/acp_agent.rs#L130) starts initialization background work and contains extension/catalog setup. Its toolOverrides capability is scoped to named search sub-tools, not a blanket no-tool contract. Do not initialize against uncontrolled real configuration to discover what it starts.
- [`xai-grok-agent/src/config.rs`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-agent/src/config.rs#L1317) distinguishes an optional session allowlist from an agent's own tool list. In the inspected hosted-tool predicate an empty agent list is unrestricted. An empty profile list must not be assumed equivalent to no tools; complete built-in/hosted/MCP enforcement needs its own evidence.

## Next consuming increment

Before production launch or any model work, assess a specific supported control plan against the installed version: agent-profile/toolConfig/disallowed-tool semantics, flag propagation into ACP, and configuration-source controls while the official CLI retains its own login. Use synthetic sentinels first. Do not repeat the same top-level flags as if their acceptance passed the gate. Do not use real credentials or session creation to bypass unknown startup effects.

The plan must establish complete no-tool enforcement and effective model/endpoint/instruction/configuration isolation across built-ins, hosted tools, MCP, hooks/plugins/skills, delegation and managed requirements. Any later trusted/read-only role also needs exact host decisions and canonical narrowing. Unsupported profiles refuse before submission; failure to prove `deny` refuses the runtime entirely. If no supported plan emerges, record a pause and select another target through P7.1. No adapter is activated by this report beyond D056's Grok candidate.

Codex P7.3 remains paused under D055; Gemini is deferred; Claude remains accepted. P7.6/P7.7 still require all four accepted native targets. The Grok control assessment can continue on this host using the Codex development app; no platform switch is required.

## Reproduction and validation

```sh
python3 scripts/experiments/grok_feasibility.py
python3 scripts/tests/grok_feasibility_cases.py
python3 scripts/tests/offline.py grok_feasibility_cases doclinks
python3 -m py_compile scripts/experiments/grok_feasibility.py scripts/tests/grok_feasibility_cases.py scripts/tests/offline.py
```

Each child has a ten-second deadline and a live two-MiB combined stdout/stderr budget. The probe drains both pipes, rejects malformed/error/unexpected RPC messages without printing them, and terminates its process group on both success and failure. The offline suite checks 22 sanitized refusals (malformed inspect/initialization, server requests, invalid JSON, EOF, deadline and stderr flood), successful observations, descendant cleanup after timeout/flood/success and refusal to send authentication/session/permission methods. Fakes do not require installed Grok, credentials or network.

Installed observations and the offline regression suite pass. Syntax, documentation-link and whitespace validation accompany PR review/closeout in PROJECT.md. No production Rust/dependency changes; Rust/runtime suites and billable live tasks are not rerun. This is discovery evidence, not P7.4 adapter acceptance.
