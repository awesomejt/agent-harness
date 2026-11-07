# P7.4 evidence — supported Grok control assessment

2026-11-07. Baseline: merged PR #71, `fa9d77ad4ec4b1ca7c53f45ac121c14be5614315`. Scope: [P7.4](../../tasks/07-native-adapters.md#p7-4), consuming D057. Disposition: [D058](../../DECISIONS.md#2026-11-07--d058-pause-grok-implementation-until-control-evidence-changes).

## Result and boundary

**Assessment complete; production permission/isolation remains unproven.** Pause Grok implementation against installed official `grok 1.0.70 (f50904eaee6c)` on Apple Silicon macOS. Keep P7.4 unchecked. No supported plan examined here establishes both complete pre-turn no-tool enforcement and effective configuration isolation with CLI-owned login. This is a bounded assessment, not a claim that Grok cannot support the harness.

No production target, Rust/dependency change, authentication, session, prompt, model turn or permission grant is added. All installed commands use disposable synthetic HOME/GROK_HOME and an empty scratch project, cleared environment, the existing probe's ten-second/two-MiB subprocess limits and process-group cleanup. No operator configuration, credential store or keychain is inspected or copied. Initialization may do background networking; this experiment is not a network sandbox.

## Supported-control assessment

Official [CLI reference](https://docs.x.ai/build/cli/reference), [headless/ACP](https://docs.x.ai/build/cli/headless-scripting), [settings](https://docs.x.ai/build/settings), [permissions](https://docs.x.ai/build/features/permissions) and [subagents](https://docs.x.ai/build/features/subagents) documentation were checked on 2026-11-07. Online documentation may describe a different build. The installed bundled guides retain the four byte fingerprints in [D057 evidence](p7-4-grok-feasibility.md); configuration, agent-mode and config-reference fingerprints were reproduced here.

| Candidate | Observation | Assessment |
| --- | --- | --- |
| ACP profile file | Installed `agent --help` exposes `--agent-profile PATH` and `--no-leader`. An explicit JSON profile with empty `toolConfig.tools`, `injectDefaultTools: false`, `tools: []`, `disallowedTools: ["*"]`, `agentsMd: false`, `discoverSkills: false` and `skills: []` permits initialization. A missing profile produces a sanitized initialization refusal. | File recognition and initialization are useful, but neither establishes effective session tools. No session was created, so the empty profile is not an accepted deny mapping. |
| Profile allowlist/denylist | The distinct pinned public source described below defaults omitted `toolConfig` to built-ins, treats empty `tools` as inheritance, injects optional tools by default, and has separate function/hosted-tool filtering. | Empty `tools` is not a no-tool contract. A wildcard-looking profile deny entry is not interchangeable with CLI permission-rule grammar. Complete function, hosted, MCP and delegation coverage remains unproven. |
| Curated toolConfig | The inspected public builder rejects an empty curated tool list when `injectDefaultTools` is false. | This source lead explains why initialization acceptance cannot establish eventual agent-build success. It does not prove that the installed build rejects the same session or that every alternative profile fails. No source build or replacement loop is proposed. |
| Top-level tool flags | Installed top-level help describes `--tools` and `--disallowed-tools` as built-in filters. Agent help exposes profile/model/leader controls. D057 already demonstrated different model-flag behavior by command level. | No complete ACP propagation/enforcement evidence follows from global parser acceptance. `--deny '*'` permission rules, built-in filters and profile fields are different mechanisms; they cannot substitute for each other's evidence. |
| Configuration overlays | Bundled configuration guide describes allowlisted deep merging above user/managed settings and below requirements/MDM. Synthetic `GROK_CONFIG={}` and an overlay with empty MCP and permission tables both retain the synthetic user permission count and user/project MCP names in `inspect --json`. | Empty overlays cannot reset inherited sources. Unsupported overlay tables are documented as discarded. Inspect is configuration discovery, not ACP tool enforcement; these MCP entries were removed before initialization. |
| Real HOME plus overrides | Settings include user/project configuration, managed settings, requirements/MDM, model endpoints, instruction/extension sources and startup writes. The documented overlay excludes arbitrary endpoint, auth and discovery-source replacement. | No evidenced fail-closed plan isolates all those sources while retaining login. Merely choosing a model ID does not prove its effective endpoint or instruction provenance. Do not initialize against uncontrolled real configuration to discover its effects. |
| Private HOME plus auth-path control | Bundled config reference mentions `GROK_AUTH_PATH`; authentication docs place login in Grok home. | A possible separate CLI-owned path deserves future assessment, but has not been exercised. It needs an evidenced D047 isolation decision, including official login/refresh behavior and startup writes. The harness must never read/copy credentials; a symlink/copy of the login store is not selected. This path alone would not prove tool denial, project-source or system-managed isolation. |
| Leader/daemon or headless alternative | Bundled agent guide documents profile behavior differing on daemon routes; the official headless guide offers structured output. | `--no-leader` is necessary candidate isolation, not full proof. Changing transport does not establish config/tool enforcement or exact host approvals. No shared leader, headless prompt or alternative model probe was run. |
| Permissions/trusted roles | Official permissions docs describe ask/auto/always-approve modes and rule precedence. | No exact per-operation host-grant mapping was demonstrated. Do not advertise trusted/read-only roles or use always-approve. Prove deny first, and refuse unsupported profiles before submission. |

## Pinned source leads, distinct from the installed binary

Public source commit [`2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8`](https://github.com/xai-org/grok-build/tree/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8) remains different from installed build `f50904eaee6c`. These are inspection leads, not installed runtime proof:

- [`AgentDefinition`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-agent/src/config.rs#L693) uses camelCase fields, defaults `toolConfig`, discovery and injection, and describes empty `tools` as inheritance. At lines 1215–1221 and 1317–1341, hosted/session matching compares full IDs or short names for equality; `"*"` does not establish blanket hosted-tool denial there. This is separate from permission-rule patterns and the function-filter helper.
- [`AgentBuilder`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-agent/src/builder.rs#L753) rejects an empty curated toolset, injects optional tools when enabled, then applies definition and session filters around lines 991–1032. No complete installed effective-tool inventory is established by inspecting this builder.
- [`run_agent_command`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-pager-bin/src/main.rs#L1226) loads effective configuration and sets the agent profile path/model from agent arguments. [`CliAgentOverrides`](https://github.com/xai-org/grok-build/blob/2bdd1d6a6369de0e8c68132ea4539e9abd9e14a8/crates/codegen/xai-grok-shell/src/agent/config.rs#L1002) distinguishes main-definition overrides from subagent session clamps. These do not prove global flags reach every ACP path.

## Reproduction and installed observations

Run from the repository root. The existing probe and fake suite remain unchanged:

```sh
python3 scripts/experiments/grok_feasibility.py
python3 scripts/tests/grok_feasibility_cases.py
python3 scripts/tests/doclinks.py
```

The additional bounded synthetic checks can be reproduced with the existing probe helpers:

```sh
python3 - <<'PY'
import json, pathlib, shutil, sys, tempfile
sys.path.insert(0, 'scripts/experiments')
import grok_feasibility as g
exe = str(pathlib.Path(shutil.which('grok')).resolve())
with tempfile.TemporaryDirectory(prefix='ah-grok-controls-') as directory:
    root = pathlib.Path(directory)
    home, project = root / 'home', root / 'project'
    grok_home = home / '.grok'
    grok_home.mkdir(parents=True)
    (project / '.grok').mkdir(parents=True)
    env = {'HOME': str(home), 'GROK_HOME': str(grok_home), 'TMPDIR': str(root),
           'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'NO_COLOR': '1',
           'TERM': 'dumb', 'RUST_LOG': 'off'}
    g.check(g.capture(exe, ['--version'], project, env).decode().strip() == g.PIN)
    user, local = grok_home / 'config.toml', project / '.grok/config.toml'
    user.write_text('[cli]\nauto_update=false\n[permission]\n'
                    'rules=[{action="allow",tool="read"}]\n'
                    '[mcp_servers.ah_user]\ncommand="/usr/bin/false"\nenabled=true\n')
    local.write_text('[mcp_servers.ah_project]\ncommand="/usr/bin/false"\nenabled=true\n')
    for overlay in [{}, {'mcp_servers': {}, 'permission': {'rules': []}}]:
        g.inspect(exe, project, dict(env, GROK_CONFIG=json.dumps(overlay)), [])
        print('PASS: overlay retains synthetic permission and MCP sources')
    # Never initialize with the synthetic MCP sources present.
    user.write_text('[cli]\nauto_update=false\n')
    local.unlink()
    profile = root / 'empty.json'
    profile.write_text(json.dumps({
        'name': 'ah-deny', 'description': 'synthetic probe',
        'toolConfig': {'tools': []}, 'injectDefaultTools': False,
        'tools': [], 'disallowedTools': ['*'], 'agentsMd': False,
        'discoverSkills': False, 'skills': []}))
    result = g.initialize(exe, project, env, [], ['--agent-profile', str(profile)])
    g.check('tools' not in result and 'tools' not in result['_meta'])
    print('PASS: profile initialization; no complete tool inventory; GATE NOT PASSED')
PY
```

Both overlay checks and the empty-profile initialization reproduced twice, including the exact snippet above. The missing-profile refusal was a separate exploratory check; it does not establish which internal validation step failed. No raw diagnostics or protocol are retained. The existing feasibility probe passes with `GATE NOT PASSED`; its 23 sanitized fake refusals and lifecycle/environment/method-allowlist checks pass. Relative Markdown links and whitespace checks pass. No runtime code changes, so Rust/runtime/model suites are not rerun.

Fresh synthetic discovery stdout fingerprints:

| Command | SHA-256 |
| --- | --- |
| `--help` | `90e7432419efc161095f0c5f616b8f11324357136eb81c05dc726579373de5c4` |
| `agent --help` | `c6ab3e30923fc178dc36530ee017d5dd0bc5796fa0f66880d227ef78a2e208e4` |
| `agent stdio --help` | `2f6e6f70961d82ae3b6c281ca14e2d610ea5eb3870fc5dbb954690dc8958cda8` |

## Resume and next selection boundary

Resume Grok only for specific new supported control/interface evidence, with installed-version synthetic proof of: (1) complete no-tool enforcement across built-ins, hosted tools, MCP, plugins and delegation before any prompt; (2) effective model/endpoint/instruction/configuration isolation, including project and managed sources, while the official CLI owns login and refresh; (3) exact host grants for any advertised trusted role, otherwise refusal; and (4) pre-submission refusal plus D030/D031/D034 cleanup/no-replay behavior. A version bump, accepted profile, repeated initialization, prompt instruction or read-only sandbox alone is insufficient. New source leads may justify a focused reassessment; they do not authorize production consumption without installed evidence.

Grok remains the last selected candidate, now paused; Codex remains paused under D055, Claude accepted and Gemini deferred. Next is a new P7.1 selection/readiness assessment for Gemini (not installed at D056 selection), or P8.1's independent Pi integration decision after accepted P4.9/P6.5 gates. Neither candidate is activated here. P7.6/P7.7 remain blocked on the complete four-adapter portfolio; this increment is not a phase review or P7.4 acceptance. No development-platform switch is required to assess readiness; another development app alone does not resolve either adapter's controls. A fresh context is efficient for that new target selection, using PROJECT.md and this report as the handoff.
