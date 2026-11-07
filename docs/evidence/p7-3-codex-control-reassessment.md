# P7.3 evidence — supported Codex control reassessment

2026-11-07. Baseline: merged PR #68, `a17d93293170d9e675d6142a24b44df357ea0ad9`. Scope: [P7.3](../../tasks/07-native-adapters.md#p7-3), consuming D054's interface reassessment. Disposition: [D055](../../DECISIONS.md#2026-11-07--d055-pause-codex-implementation-until-control-evidence-changes).

## Result and boundary

**Reassessment complete; production feasibility remains unproven.** Keep P7.3 unchecked. The installed official executable is still `codex-cli 0.166.0` on Apple Silicon macOS. No alternative examined below establishes both complete pre-turn restrictions and login-preserving isolation. This is a bounded compatibility assessment, not an assertion that Codex can never support the harness.

Pause implementation against this baseline rather than scheduling another identical discovery probe. Reopen only for specific new control/interface evidence satisfying the checklist below. A new version number alone does not pass the gate. No public target, production code, dependency, authentication handling, thread, model turn, tool trial or permission grant is added. Existing Claude/OpenCode behavior is unchanged.

## Alternatives and evidence

Official documentation was fetched on 2026-11-07. Documentation can describe a newer surface than the installed executable; local help/schema observations below are specifically 0.166.0. No SDK package was installed or tested.

| Candidate | Evidence observed | Assessment against D047/D053 |
|---|---|---|
| Stdio app-server | Existing synthetic-config experiment reproduced inheritance, partial overrides and rejection of exec isolation flags. Fresh stable `ThreadStartParams`, `TurnStartParams` and `ThreadStartResponse` schemas expose configuration/sandbox/approval fields, but no typed blanket no-tool switch or complete effective tool inventory. | D054 remains unpassed. A generic `config` object does not prove that no effective control exists; it also supplies no enforcement evidence by itself. |
| `codex exec --json` | Installed help explicitly describes `--ignore-user-config` as skipping the user config while authentication still uses CODEX_HOME. `--ignore-rules` skips user/project execpolicy rules. The [non-interactive guide](https://learn.chatgpt.com/docs/non-interactive-mode) documents JSONL progress and saved CLI authentication. | Useful isolation building blocks. Help recognition does not establish effective isolation of project settings, instructions, skills, plugins, MCP, hooks or endpoints. No demonstrated pre-turn no-tool policy or bidirectional exact host-grant interface. No exec run was submitted. |
| Official SDK wrappers | The [SDK guide](https://learn.chatgpt.com/docs/codex-sdk) describes the Python SDK as controlling local app-server over JSON-RPC and offering its own pinned runtime. It presents TypeScript thread automation and sandbox options. | The inspected guide supplies no independent complete no-tool enforcement contract. A wrapper or its different runtime pin needs its own evidence; neither is an automatic escape from the underlying gate. No SDK adoption or change to the Rust implementation direction. |
| App-server approval and permission callbacks | The [app-server guide](https://learn.chatgpt.com/docs/app-server) describes command/file approval callbacks and subset filesystem/network permission grants. Permission grants can last a turn or session. | These are useful scoped access mechanisms, but the inspected contract does not establish a callback before every possible tool invocation. Turn/session access cannot be silently treated as the harness's exact per-call grant. No callback was exercised. |
| Individual capability filters | The [config reference](https://learn.chatgpt.com/docs/config-file/config-reference) describes shell/image/delegation flags, MCP per-server tool filters and code-mode namespace controls. | These controls have different scopes. No documented complete effective tool-policy/inventory boundary was established by this inspection. Do not infer blanket tool denial from an MCP filter or namespace exclusion. |

The previous [feasibility report](p7-3-codex-feasibility.md) retains the hook limitations and pinned upstream tool-assembly evidence. This increment does not repeat source conclusions as binary runtime proof. An external filesystem sandbox alone would still not establish the no-tool profile, and replacing the inner coding loop or proxying subscription calls is outside the accepted design.

## Installed observations and reproduction

Run only discovery commands:

```sh
codex --version
codex exec --help
codex app-server --help
python3 scripts/experiments/codex_feasibility.py
python3 scripts/tests/codex_feasibility_cases.py
```

The experiment uses disposable synthetic HOME/CODEX_HOME and an empty project; its protocol method allowlist excludes thread/turn creation. It passed again with `GATE NOT PASSED`. All 11 malformed-protocol cases passed. Help and stable schema generation were additionally run in a disposable synthetic environment, with stdin closed and a ten-second subprocess deadline; no operator config or login files were read by that inspection. `--help` exits before any task execution. Schema generation uses `codex app-server generate-json-schema --out DIR`.

SHA-256 fingerprints of stdout (help) or the generated stable `v2/NAME.json` bytes:

| Surface | SHA-256 |
|---|---|
| `exec --help` | `df0d864ca2076f7654288c6a1e3394e3eaa2ea8f15021df2524efdd90c70986c` |
| `app-server --help` | `d2854a3ad9c9733f8be8034feb198ba017ddce07d539d8e777167fc96dffbd10` |
| `ThreadStartParams` | `e9c6d3cc18d049bfbc0249add3808fb8e5a27e1a0b5a423767aafbc3859a9428` |
| `ThreadStartResponse` | `c655daa1616548f6b3b0960acee9dcfefa8aba5965ec4fc636c84ee840a8626a` |
| `TurnStartParams` | `49e53282f327c25e7b39d97afacd038ef10ad5c4fb0431608b354d3a7bf6bcea` |
| `ConfigReadResponse` | `69a32e3d84e16045802dff8abf01770d759ebc758965c3258a30ea4a93159fce` |

The response reports model/provider, cwd, approval policy/reviewer, sandbox, disabled plugin IDs and instruction sources; it does not list all effective tools. No model-dependent exposure was observed because no thread was created. These hashes identify inspected surfaces, not proof of end-to-end enforcement.

## Evidence required to resume

A focused follow-up must identify a supported, versioned mechanism and then prove all of the following before any model work:

1. `deny` prevents every model-accessible tool from executing. A complete effective policy/inventory or equivalently evidenced enforcement boundary must cover built-ins, hosted tools, MCP/apps, plugins, delegation and dynamically supplied tools. Prompt instructions and after-the-fact events are insufficient.
2. Operator CLI authentication remains owned by the official executable, while uncontrolled user/project configuration, rules, instruction sources, skills, plugins, hooks, MCP and endpoint overrides cannot widen the harness plan. Synthetic sentinels must demonstrate the effective boundary without inspecting/copying login stores.
3. Any advertised `trusted` profile obtains an exact host decision for each permitted operation and fails closed on missing/invalid approval. Unsupported profiles/roles refuse before submission. Establish `deny` first; defer trusted support if necessary.
4. Preflight failures occur before submission; later launch work preserves D030 cleanup, D031/D034 no replay and D039 output semantics. Live coding/role/workflow acceptance remains separate subsequent work.

If no such evidence is available, the next useful Phase 7 increment is a recorded Grok or Gemini target selection under P7.1, with Codex explicitly paused. Neither target is activated here. Changing the development app or operating system does not by itself address the control gap. P7.6 still requires all four accepted adapters; P7.7 remains the later holistic phase gate. PROJECT.md alone owns mutable task status.

## Validation

Existing installed feasibility experiment and 11 malformed-protocol cases pass. Relative Markdown links and whitespace checks pass. This increment changes documentation/decisions only; Rust and offline runtime suites are not rerun. Required Grok review and closeout are recorded in PROJECT.md.
