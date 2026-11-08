# P7.5 evidence — Antigravity contained startup and initialization

2026-11-07. Entry: merged PR #75, `95e4add5b09fd457f2884350b91bb16a8fb4c924`. Scope: [P7.5](../../tasks/07-native-adapters.md#p7-5), consuming [D061](../../DECISIONS.md#2026-11-07--d061-replace-the-gemini-cli-requirement-with-antigravity-cli). Disposition: [D062](../../DECISIONS.md#2026-11-07--d062-antigravity-initialization-is-not-a-control-gate-pass).

## Result and boundary

**Startup/initialize increment complete; production control gate unpassed.** Installed `agy` 1.5.3 on Apple Silicon macOS responds to an honestly identified generic ACP client with protocol 1. No authentication, session, prompt, model call or permission grant was sent. P7.5 remains unchecked; this is a focused experiment, not adapter acceptance. No production Rust, dependency or public CLI/config change.

The response exposes authentication-method descriptions and transport capabilities, not effective tool, configuration-source, model or endpoint inventory. It cannot establish complete deny or login-preserving isolation. Next is a specific supported-control assessment before any session/model work, rather than repeating initialization as enforcement evidence. No development-platform switch is needed.

## Reproduction and containment

Run `python3 scripts/experiments/antigravity_feasibility.py` explicitly; it never runs as part of offline testing. The installed executable is copied into a disposable directory, without copying any configuration or auth material. Observed executable SHA-256: `5e4b545bff4a83a93354fc50c54631cf3e8cd02e1a469087af00929f3fdc4d51`. This identifies tested bytes; it is not independent provenance verification or a production support pin.

The probe clears inherited environment (fixed system PATH, synthetic HOME/TMPDIR, NO_COLOR, TERM and LANG), uses a disposable nested project and synthetic repository root, and runs every CLI command under macOS `sandbox-exec`. Its profile denies network operations, operator-home file data reads, and filesystem writes outside scratch. A copied executable is necessary: denying operator-home reads while executing the original home-resident binary caused SIGABRT even for help. The final probe does not weaken that deny to run the binary in place.

Before starting ACP, harmless negative checks confirm network bind, reading the original installed executable, and writing to a separate disposable directory all raise permission errors. These are containment checks for this no-login experiment. The profile is **not** a complete credential/keychain/IPC sandbox, a portable production solution, or proof of effective Antigravity configuration isolation. It prevents this experiment's direct network access; it does not measure attempted network destinations. No operator settings or credentials are selected for inspection. CLI-owned login reuse is deliberately untested.

Each subprocess has a ten-second deadline and two-MiB combined live stdout/stderr bound. Stdin is closed without input except for one fixed `initialize` request. No arbitrary method/payload API is exposed. Protocol validation rejects requests, error envelopes, unknown IDs, non-protocol-1 responses, version drift and extra messages; raw protocol/diagnostics are withheld on failure. Cleanup terminates then kills the process group and closes descriptors. macOS can return EPERM after an orphan group disappears; that error is ignored only when bounded `ps -g` confirms no group members remain.

## Installed observations

| Check | Observation | Limit |
| --- | --- | --- |
| Version and ACP help | Version is 1.5.3; ACP help lists Gemini/app-data/default-customization controls and no `--settings` flag. | Help alone does not establish effective behavior. |
| Startup with EOF | `acp --app-data-dir ah-app --gemini-dir <scratch>/gemini --disable-telemetry --include-default-customizations=false` exits 0 with empty stdout/stderr. | No RPC, login or session. EOF may end startup before later discovery. |
| Top-level overlay | Prefixing the startup command with `--settings '{}'` also exits 0 with empty stdout/stderr. | Parser acceptance only. Overlay propagation and merge/replacement semantics remain unknown; no claim it resets inherited settings. |
| State paths | Startup and initialization create only `gemini/ah-app/log/acp-server-*.log` files in the final probe. | State observed before sessions only. A preliminary absolute app-data value was appended under Gemini state, so the final probe uses a simple app-data component. Do not assume independent absolute auth/state roots. |
| Initialize | `protocolVersion=1`, `agentInfo.name=Antigravity ACP Server`, version 1.5.3; advertises session/prompt capabilities. | No session RPC or model resolution. Capability advertisement does not prove enforcement. |
| Authentication | Method IDs: `oauth-personal`, `oauth-business`, `gemini-api-key`, `agent-platform`. | Available methods are not authenticated status or entitlement. No authentication method was invoked. |
| Inert sentinels | Synthetic user/parent/project instructions, a project custom agent and strict settings remain byte-identical. | Preservation is not exclusion or proof of loading. No claim these instructions reached a prompt or settings reached ACP. |
| Tool/model inventory | No top-level `tools` or `models` inventory in initialization. | Effective deny, model/provider endpoint, permission cache and indirect tools remain unknown. |

No executable hook, plugin or MCP sentinel was installed into a discoverable startup source. Such a probe could run before controls are established; inert sentinels were used instead. Tests of hook/plugin/MCP coverage, legacy discovery, model/endpoint inheritance and role precedence remain explicit consuming work, not a passed matrix.

## Supported-control assessment still required

Official [ACP documentation](https://antigravity.google/docs/cli/acp/) describes reuse of cached CLI login. The [client guide](https://antigravity.google/docs/ide/extensions/acp) and [CLI reference](https://antigravity.google/docs/cli/reference/) do not supply an effective-state proof for this installed generic client. The [discovery guide](https://antigravity.google/docs/customization-discovery/) describes standard and legacy sources; manifests add sources rather than replacing them. These moving official docs were checked 2026-11-07 and remain leads, not installed conformance evidence.

The [permission guide](https://antigravity.google/docs/permissions/?tab=cli) documents action-scoped wildcard matching. A list of wildcard action denials does not establish that every tool is removed or intercepted, particularly hosted/indirect tools and delegation. Strict asks before actions; it is not deny. Before production launch or inference:

1. Establish supported source controls and their exact ACP propagation, including user/parent/project settings, rules, agents, legacy skills, plugins, hooks, MCP, model and endpoint. Prove exclusion using effective inventory or safe adversarial observations; unchanged files and initialization alone do not pass.
2. Establish complete pre-turn no-tool enforcement, including web/search, media, scheduling, subagents and indirect/hosted tools. Verify callback bypasses, cached grants and failure/disconnect behavior. Do not submit a prompt merely to discover whether defaults are safe.
3. Establish a D047-compatible login-preserving configuration plan. Private directories here intentionally have no login. Do not read, copy or symlink auth stores, spoof clients or silently switch to API-key access. Any separate auth-path plan needs its own evidenced decision.
4. Trusted/constrained roles additionally require exact request-bound one-use grants, argument integrity, external-path refusal and narrowing. Preserve shared submission, cleanup and no-uncertain-replay contracts. Unsupported profiles refuse before submission.

If a supported plan cannot be established, record a pause with specific resume conditions. Pi P8.2 is an independent path after its executable setup; Codex/Grok remain paused, Claude remains accepted, and P7.6/P7.7 require the complete portfolio.

## Verification

Installed contained startup/initialize probe passes. Offline adversarial checks cover malformed/version-drift responses, extra messages, forbidden RPCs rejected before launch, sanitized failure output, combined output overflow, child timeout and descendants surviving leader exit. The suite joins `offline.py`; selected probe/doclink suites, Python syntax and whitespace checks pass. Production Rust/runtime tests are not rerun because this increment changes no production source or dependencies. Required Grok findings and closeout are recorded in PROJECT.md after review.
