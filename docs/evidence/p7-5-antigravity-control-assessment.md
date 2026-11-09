# P7.5 evidence — supported Antigravity control assessment

2026-11-08. Baseline: merged PR #76, `4ddd712b3cd093fd0ed50b4e0eb84ff50eafa770`. Scope: [P7.5](../../tasks/07-native-adapters.md#p7-5), consuming [D062 discovery](p7-5-antigravity-feasibility.md). Disposition: [D063](../../DECISIONS.md#2026-11-08--d063-pause-antigravity-implementation-pending-effective-controls).

## Result and boundary

**Assessment complete; production control gate unpassed.** Pause Antigravity implementation against installed official `agy` 1.5.3 on Apple Silicon macOS until specific supported evidence changes. P7.5 remains unchecked. The interfaces examined do not establish complete pre-turn no-tool enforcement and effective source isolation while preserving CLI-owned login. This is a bounded assessment, not a claim that every possible Antigravity integration fails.

No authentication, credential/keychain inspection, session, prompt, model turn or grant occurred. No production Rust, dependencies or public CLI/config changes. Installed observations use the existing probe's copied executable, disposable HOME/project, cleared environment, network/home-read/outside-write containment, ten-second deadline, two-MiB output bound and process-group cleanup. The experimental sandbox is not a complete production credential/IPC boundary. No raw ACP diagnostics or operator configuration is retained.

## Supported-control assessment

The official sources below were checked on 2026-11-08. They are moving documentation, not a version-pinned implementation or installed conformance proof. Conclusions about missing proof are this assessment's inferences.

| Candidate | Documented or installed observation | Assessment |
| --- | --- | --- |
| Source manifests | [Customization discovery](https://antigravity.google/docs/customization-discovery/) loads user/workspace/parent sources through the repository root, including legacy folder spellings. Manifests add sources. Manifest patterns do not support wildcards; legacy CLI skills in `~/.gemini/antigravity-cli/skills/` and `~/.gemini/skills/` outrank other skills and bypass manifest excludes. Rules accumulate. | An empty manifest or `exclude: ["*"]` is not a complete source-exclusion plan. Enumerating current names does not establish fail-closed behavior for future files. Settings, hooks, plugins, MCP and model/endpoint sources also need coverage. |
| Default-customization flag | Installed ACP help exposes `--include-default-customizations`, enabled by default. D062 initializes with it false and preserves inert sentinels. | Neither the flag name nor unchanged sentinels establishes exclusion of user/project/parent/legacy sources. No effective inventory or installed enforcement evidence was found. Do not equate default customizations with all customizations. |
| Settings overlay | Installed top-level help describes `--settings` as a session-only JSON object or file. ACP help does not list it. [Settings](https://antigravity.google/docs/settings?tab=cli) documents separate hooks/MCP/plugin files, startup normalization of valid settings, retention of ignored unknown keys, and Global permissions combined with Project/Shared rules. | D062 proves only top-level overlay parser/startup acceptance. Exact ACP propagation and merge/replacement semantics remain unknown. Empty settings cannot be assumed to reset these independent sources. No executable sentinel was seeded to test this before exclusion was proven. |
| Complete deny | The CLI section of [Permissions](https://antigravity.google/docs/permissions/?tab=cli) documents `read_file`, `write_file`, `read_url`, `execute_url`, `command`, `unsandboxed`, and `mcp`; wildcard targets cover their own action namespace. Deny outranks Ask/Allow. | Denying all listed actions is a candidate, not proof that every tool passes through those checks. Coverage for search, hosted/media tools, scheduling, delegation and indirect operations remains unproven. No installed tool inventory or safe pre-turn enforcement trace was established. |
| Strict policy / OS sandbox | [Settings](https://antigravity.google/docs/settings?tab=cli) describes strict policy as prompting for every tool action; the terminal sandbox restricts terminal commands. | Asking is not denial. A terminal sandbox is not evidence that model-hosted tools or delegation are intercepted. No prompt is submitted merely to discover whether unverified defaults are safe. |
| Custom agent tools | [Custom subagents](https://antigravity.google/docs/subagents) documents a `tools` list, direct primary selection, inherited permissions and a known hang for unmapped tool names. CLI agents are discovered from workspace/global Markdown. Installed ACP exposes `--agent`. | A named role is a promising lead, but an empty/default `tools: []` has no proven deny-all semantics here. Complete primary/descendant tool coverage, tool-name validation and source precedence require installed proof before this can become the permission mapping. No role/session was exercised. |
| Cached login with real home | [ACP](https://antigravity.google/docs/cli/acp/) reuses cached CLI credentials and CLI settings. Installed ACP has `--gemini-dir`, `--app-data-dir`, `--cli_dir_name` and an endpoint override. | D062 private directories contain no login; changing state roots does not prove login preservation. Keeping real home reintroduces uncontrolled settings/discovery/startup effects. No supported independently isolated CLI-owned auth/refresh plan was established. Never read/copy/symlink auth stores or silently switch to API-key access. |
| Host permissions / alternative transport | The [ACP client guide](https://antigravity.google/docs/ide/extensions/acp) says existing allow/deny rules bypass permission prompts; cancellation abandons pending requests. It exposes per-session workers, sandbox and IDE-MCP flags. | Denying callbacks alone cannot constrain actions that never request approval. Exact request-bound one-use grants, argument integrity, external-path refusal, disconnect handling and role narrowing remain unverified. Per-session workers/headless output do not independently establish these controls. Client identity spoofing and shared/remote control are not selected. |

No matched public source revision for the installed binary was established in this increment. We do not infer implementation semantics from embedded strings or borrow Gemini CLI/SDK controls for Antigravity. The SDK is a separate integration, not authorization to replace the chosen coding runtime or loop.

## Installed evidence and reproduction

The existing installed probe and offline cases pass unchanged:

```sh
python3 scripts/experiments/antigravity_feasibility.py
python3 scripts/tests/antigravity_feasibility_cases.py
python3 scripts/tests/doclinks.py
```

The installed executable retains SHA-256 `5e4b545bff4a83a93354fc50c54631cf3e8cd02e1a469087af00929f3fdc4d51`. Containment negatives pass; startup with and without the top-level empty settings object exits cleanly; initialize returns protocol 1/version 1.5.3 without effective tool/model inventory; inert sentinels remain unchanged and only synthetic ACP logs appear. No session or authentication request is sent. This rerun confirms discovery, not any missing control guarantee.

Fresh help fingerprints (UTF-8 bytes as emitted; both commands exit 0, stdout empty):

| Command | stderr SHA-256 |
| --- | --- |
| `--help` | `e92946f85cec63eca61f93014ca49f53b1e84277eac7954e7fac7d8d712940fd` |
| `acp --help` | `08cedbbc6d63dc2dbd9f3c108d949e048ee3a6696c31e41914384c2057d27747` |

Reproduce only the synthetic help observations with the existing capture/profile helpers:

```sh
python3 - <<'PY'
import hashlib, pathlib, shutil, sys, tempfile
sys.path.insert(0, 'scripts/experiments')
import antigravity_feasibility as a
with tempfile.TemporaryDirectory(prefix='ah-agy-assess-') as directory:
    root = pathlib.Path(directory).resolve()
    exe = root / 'agy'
    shutil.copy2(shutil.which('agy'), exe)  # executable only; no settings/auth
    home, project = root / 'home', root / 'project'
    home.mkdir()
    project.mkdir()
    env = {'HOME': str(home), 'TMPDIR': str(root),
           'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'NO_COLOR': '1',
           'TERM': 'dumb', 'LANG': 'C'}
    sandbox = ['/usr/bin/sandbox-exec', '-p', a.profile(root, pathlib.Path.home())]
    for args in [['--help'], ['acp', '--help']]:
        out, err = a.capture([*sandbox, str(exe), *args], project, env)
        a.check(not out)
        print(' '.join(args), hashlib.sha256(err).hexdigest())
PY
```

The fresh help commands use the same profile as the separately verified containment probe. Offline cases verify malformed protocol/version drift, forbidden RPC refusal, sanitized errors, output/deadline bounds and descendant/descriptor cleanup. Documentation links and whitespace checks pass. Rust/runtime/model suites are not rerun because production source/dependencies are unchanged. Direct coding comparison remains gated on production/live acceptance.

## Resume and next task

Resume Antigravity only on specific supported control/interface evidence, followed by installed-version synthetic proof of:

1. Complete no-tool enforcement before submission across built-in, hosted, MCP, plugin, delegation and indirect operations; cached permissions and callback bypasses cannot widen it.
2. Effective user/parent/project/legacy/managed source isolation for instructions, roles, settings, hooks, plugins, MCP and model/endpoint, with CLI-owned login/refresh preserved and startup writes bounded.
3. Exact request-bound one-use host grants and narrowing for any advertised trusted/constrained roles, otherwise explicit pre-submission refusal.
4. Shared lifecycle/terminal/cancellation and no-uncertain-replay contracts (D030/D031/D034).

A version bump, settings parser acceptance, repeated initialization, prompt instruction or terminal-only sandbox is insufficient. A focused new source/control lead may reopen assessment; it does not by itself authorize production or inference.

Antigravity is the last selected native candidate, now paused. Codex/Grok remain paused under D055/D058; Claude stays accepted. P7.6/P7.7 require the full four-target portfolio and are not ready. Independent P8.2 is the next available assessment: `command -v pi` now resolves `/Users/jason/bin/pi`, a symlink to `../.pi/agent/bin/pi`; executable presence alone proves no version, provenance, RPC, isolation or permission capability. No Pi command or login/model access was performed here. Verify those in a separate bounded no-inference installed-feasibility task under D060 before production work. P8.3 live acceptance, P8.4 workflow parity and P8.5 holistic review remain open. No development-platform switch is needed; a fresh context is efficient at this different-runtime boundary.
