# P7.1 evidence — Grok native adapter selection

2026-11-07. Baseline: merged PR #69, `49d05533f819f3ef7372664bb33bdeb20240ed51`. Task: [P7.1](../../tasks/07-native-adapters.md#p7-1). Decision: [D056](../../DECISIONS.md#2026-11-07--d056-select-grok-acp-for-the-next-native-feasibility-increment).

## Selection and scope

Select Grok as the only active next native-adapter candidate. It is already installed and has been used for project reviews (the P7.1 Claude selection records that use). Gemini is not on this session's PATH. Codex P7.3 stays paused under D055 until specific changed control evidence appears; switching the development app does not clear that gate. Claude P7.2 remains accepted.

This increment closes target/interface selection only. P7.4 stays unchecked. No production runtime, CLI flag, config schema, dependency, model turn, authentication attempt, session or ACP handshake is added. The next increment is a bounded, no-inference P7.4 feasibility experiment, before production launch or live coding.

## Installed baseline and reproduction

Observed on the D041 Apple Silicon macOS platform:

- `/opt/homebrew/bin/grok` resolves to the Homebrew Cask `grok-build/1.0.70/grok-1.0.70-macos-aarch64` executable.
- `grok --version` reports `grok 1.0.70 (f50904eaee6c)`.
- All six discovery commands below exited 0. Each ran in an empty temporary working directory with a synthetic HOME, cleared environment except the values shown, closed stdin and a 15-second subprocess deadline. No real user config/login store was inspected. This synthetic environment verifies help discovery only, not login-preserving isolation.

```python
import hashlib, subprocess, tempfile
with tempfile.TemporaryDirectory(prefix="ah-grok-selection-") as root:
    env = {"HOME": root, "PATH": "/opt/homebrew/bin:/usr/bin:/bin",
           "TERM": "dumb", "NO_COLOR": "1"}
    for args in [["--version"], ["--help"], ["agent", "--help"],
                 ["agent", "stdio", "--help"], ["inspect", "--help"],
                 ["login", "--help"]]:
        result = subprocess.run(["/opt/homebrew/bin/grok", *args], cwd=root,
                                env=env, stdin=subprocess.DEVNULL,
                                capture_output=True, timeout=15)
        print(args, result.returncode, hashlib.sha256(result.stdout).hexdigest())
```

SHA-256 of exact stdout bytes:

| Arguments | SHA-256 |
|---|---|
| `--version` | `78fe2fb0396335d7656b804f1417834e264a1c26727d67ab0d809ad8c451b151` |
| `--help` | `90e7432419efc161095f0c5f616b8f11324357136eb81c05dc726579373de5c4` |
| `agent --help` | `c6ab3e30923fc178dc36530ee017d5dd0bc5796fa0f66880d227ef78a2e208e4` |
| `agent stdio --help` | `2f6e6f70961d82ae3b6c281ca14e2d610ea5eb3870fc5dbb954690dc8958cda8` |
| `inspect --help` | `8ccdb91e8c043b65f02a40b87f8ad45ca35909e0e27148952f7b50fba06d15da` |
| `login --help` | `207a86f26924a3d5c1f364308305ee145473398fadfbd6f2846259fae0040e36` |

Top-level help exposes `--tools`, `--disallowed-tools`, `--deny`, `--permission-mode`, `--no-subagents`, `--disable-web-search`, model and reasoning-effort selection. Agent help exposes `--no-leader`, `--agent-profile` and endpoint overrides; stdio help exposes a leader socket. `inspect --json` is advertised. Help recognition does not prove which top-level flags apply to ACP or the semantics of an empty tool list. Neither inspect nor login was executed beyond help.

## Interface and authentication sources

Official pages checked 2026-11-07; online documentation may differ from installed 1.0.70:

- [Headless and scripting](https://docs.x.ai/build/cli/headless-scripting) documents `grok agent stdio` as ACP over stdio JSON-RPC, existing local authentication, `session/update` text chunks and prompt completion metadata. It also documents streaming JSON headless output and disabling auto-update checks. **Select caller-owned ACP stdio as the feasibility candidate**, to reuse the harness's wire boundary without a third-party bridge. Initialization/authentication and version compatibility remain untested here. Prefer a fresh non-leader process if the installed interface can prove that behavior.
- [CLI reference](https://docs.x.ai/build/cli/reference) documents tool filters, model/effort selection and configuration inspection. [Permissions](https://docs.x.ai/build/features/permissions) distinguishes permissions from sandboxing and documents deny-rule precedence. These are candidate controls, not evidence of a complete no-tool profile or exact allow-once host grants.
- [Settings](https://docs.x.ai/build/settings) documents user, project, managed and requirements sources, GROK_HOME and configuration inspection. A temporary home that loses authentication is not an acceptable production isolation solution. P7.4 must establish which sources can be disabled or constrained while retaining CLI-owned login.
- [Getting started](https://docs.x.ai/build/overview) supports headless automation and official browser login. Installed login help advertises browser/device-code authentication. D047 requires the operator to log in beforehand; this selection does not verify current login or account entitlement.
- [Consumer terms](https://x.ai/legal/terms-of-service) (page dated October 27, 2026) govern individual use, incorporate applicable policies and reserve service restrictions. The [Acceptable Use Policy](https://x.ai/legal/acceptable-use-policy) prohibits unauthorized automated access and bypassing service restrictions. The documented official headless/ACP integration is the basis for this personal orchestration candidate, not permission to impersonate clients, share credentials, serve others or bypass plan limits. Account-specific entitlement and any additional applicable terms remain prerequisites for live use. No subscription traffic crosses LiteLLM; no credential handling is introduced.

Alternatives: streaming JSON is a fallback interface to assess only if ACP cannot satisfy the contract; plain/final JSON alone lacks the required interactive host boundary. Shared leaders, remote WebSocket relay/server, third-party bridges, embedded runtime code and a replacement inner coding loop are not selected. No upstream library or source is imported.

## P7.4 consuming questions and gate

The next focused experiment must remain no-inference until effective controls pass:

1. Verify protocol/version, official CLI-owned login compatibility and a fresh caller-owned process. Start with initialization only; do not create a session until its startup/config effects are understood. No model prompt, automatic login or credential-file inspection.
2. Prove complete pre-turn `deny` enforcement, covering built-ins, hosted web tools, MCP, plugins, hooks, skills, delegation and dynamic tools. Establish whether tool filters apply to ACP and whether an empty set removes all tools. Prompt rules, a read-only sandbox and post-hoc event detection do not prove this.
3. Prove effective configuration/model/endpoint and instruction isolation with synthetic sentinels, including user/project/managed requirements, background updates and leader inheritance, while retaining official login. Determine whether `inspect --json` reflects the actual planned ACP runtime rather than an unrelated configuration view.
4. For any later advertised trusted or read-only role, establish exact per-operation host decisions, default-deny behavior and canonical tool-set narrowing. Refuse unsupported roles/profiles before submission. If no-tool denial cannot be proven, refuse the runtime entirely (D047).
5. Subsequent production PRs own launch/config selection, event/terminal and source-attributed usage mapping, model/effort, canonical agents/project AGENTS.md, cancellation/descendant cleanup, workflows and the one pre-submission fallback. Preserve D030/D031/D034/D039; no automatic replay after possible submission. Version pin and fixture/live acceptance remain required before claiming support.

P7.6 requires all four accepted adapters, including the paused Codex target; P7.7 is the later holistic phase gate. This selection does not close either. PROJECT.md alone owns mutable status. The feasibility task can continue in Codex on this host; switching development platforms is not required.

## Validation

Six installed help/version commands passed with the isolation/deadline described above. Relative Markdown links and whitespace checks are required before merge; review/closeout is recorded in PROJECT.md. No production or dependency changes: Rust/runtime suites and billable live runs are not repeated for this selection.
