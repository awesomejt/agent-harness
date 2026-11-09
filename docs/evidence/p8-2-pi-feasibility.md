# P8.2 evidence — installed Pi no-inference discovery

2026-11-08 (America/Denver). Entry: merged PR #77, `f0f7d67` (see Git history for full identity). Task: [P8.2](../../tasks/08-pi.md#p8-2). Consumes [D060](../../DECISIONS.md#2026-11-07--d060-select-pi-rpc-for-litellm-first-feasibility); discovery disposition: D064.

## Result and boundary

Installed Pi 1.5.0 starts in bounded disposable macOS containment, loads only the explicit observer extension among the tested extension sources, reports empty active/all-tool, MCP and skill/template command inventories, omits seeded context text from its system prompt, and returns correlated idle state for an explicit synthetic model. Retry and compaction disable commands succeed; no session file is reported or created in the private session directory. No prompt, model request, login, real credential/config read, production Rust change or dependency adoption occurs.

This closes **discovery only**, effective on PR review/merge. P8.2 remains unchecked. Empty tool inventories and a block hook before any model turn do not prove adversarial tool enforcement, effective complete resource/settings isolation, credential precedence or HTTP route fidelity. No production Pi runtime/config/flag is introduced. This experiment's OS containment is a safety fence, not a selected production sandbox.

## Installed distribution and matching release

`/Users/jason/bin/pi` is a symlink to `/Users/jason/.pi/agent/bin/pi`, a managed shell launcher. Read-only inspection finds its release selection in `install/current-version` (`1.5.0`) and launch target `install/releases/1.5.0/node_modules/.bin/pi`. The wrapper also exports `PI_MANAGED_INSTALL_ROOT` and can amend PATH. The probe deliberately bypasses the wrapper: it copies only the release's `node_modules` and Node into scratch and executes the bundled CLI directly with private state and a cleared environment. It does not copy operator state or the managed-install root.

Installed package: **@earendil-works/pi-coding-agent 1.5.0**, MIT, Node >=22.19.0. Installed Node: **v24.14.0**, macOS arm64. The managed `metadata.json` records source **f9a26365568127461c47a07a37dcb42c140a3ac5**. This differs from the moving-source snapshot in P8.1; source references below use the release metadata's commit. Metadata alone does not prove a build correspondence.

Read-only [versioned npm metadata](https://registry.npmjs.org/@earendil-works/pi-coding-agent/1.5.0) supplies the published tarball and SHA-512 integrity. A Python `urllib.request` download verified that integrity and compared every regular tar member beneath `package/` byte-for-byte with the installed package: **1,286 files matched**. Integrity is the same `sha512-xNDZ5kqowO6Z03FS2gwAkPEGk1ssxVcYKQ6qZId84mFEvwACvvyc2l0vAMOS+c5zvxLRMLBE9r4y44IGYkMJaQ==` recorded in P8.1. This is package-file equivalence, not independent verification of all transitive packages or Node provenance. No installation/update or downloaded-code execution occurred; execution uses the installed copy under containment.

The probe pins the copied runtime tree (15,162 files/symlinks), bundled CLI and Node before executing them; drift refuses. Tree SHA-256 hashes relative paths sorted by Python `Path` components (not lexically by the full path string), plus NUL, then each regular file's SHA-256 or `link:` plus symlink target, then LF. Directory metadata is excluded. This is a host fixture fingerprint, not a portable support promise.

| Installed/copied input | SHA-256 |
|---|---|
| Full `node_modules` tree | `2af836467c982ecb6dc38764d4d192585d5893e096354255c8028af19aa5b159` |
| `dist/bundle/cli.js` | `e79626f2dd6f94aa45d30f3fa63cd84319a6eefcd150b353cfaf274366926774` |
| `dist/bundle/rpc-entry.js` | `73565777eb24113bdf076d6d54e47be00351dfaa3277ab747b9920e7c32590f2` |
| Node executable | `20a18709f0154d668f1bd6f6ea8c2a7ae001447b4b2c339732f22e57a8767a55` |
| `dist/main.js` | `dec83f4f151de1351c9a39ed8ad6752cb5e5d91798daede5780fa401d0e6ec06` |
| `dist/core/resource-loader.js` | `57ece4ebd0ef6429bf45e1a22a7c581813251a988afa67bf2d3158eb752cdecc` |
| `dist/core/settings-manager.js` | `66edb495ff9767e7f2ce0d2f4e2d102532e4b396ad7bc7c3c648c7c12c0fe71d` |

Release [main](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/src/main.ts), [CLI args](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/src/cli/args.ts), [resources](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/src/core/resource-loader.ts) and [RPC docs](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/docs/rpc.md) inform the installed checks. Installed published JS/docs were inspected directly for flags, state paths, model configuration, cache warming and extension inventory APIs. `--offline`/`PI_OFFLINE` suppress catalog network updates; OS network denial contains any other traffic, without proving there were zero attempted connections. Extension stdout is redirected to stderr in RPC mode; the observer is validated there separately from command responses on stdout.

## Reproduction and observations

On this tested macOS host, with `/usr/bin/sandbox-exec` and Command Line Tools system Python available:

```sh
python3 -B scripts/experiments/pi_feasibility.py \
  --release /Users/jason/.pi/agent/install/releases/1.5.0 \
  --node /Users/jason/.nvm/versions/node/v24.14.0/bin/node
python3 -B scripts/tests/pi_feasibility_cases.py
python3 -B scripts/tests/doclinks.py
git diff --check
```

The opt-in probe has no network download or model-call path. Missing installation, different tree/Node bytes, protocol shape/order or changed observations refuse with sanitized diagnostics. It creates scratch state plus one synthetic operator-home read sentinel; it never reads real auth/configuration. Child processes receive only explicit HOME/TMPDIR/PATH/state/offline/terminal settings and a synthetic key. Scratch is removed after bounded process-group cleanup. Ten-second child deadlines and a two-MiB combined pipe limit apply during reads; no raw runtime output is printed on failure.

1. Verify OS network-bind denial, synthetic operator-home data-read denial and outside-scratch write denial before launching Pi. Runtime code is copied so all operator-home data reads can remain denied. The containment self-check uses Command Line Tools Python directly, avoiding the `/usr/bin/python3` launcher cache attempt.
2. Verify copied tree/Node fingerprints and contained Node/Pi version output. State is separate from synthetic HOME, cwd is a disposable Git-shaped nested project, and no managed-install environment variable is inherited.
3. Seed inert home/state/ancestor/project instructions, project SYSTEM text, a skill whose description contains the sentinel, and an inert prompt-template file. The observer reports loaded skill/template commands using `pi.getCommands()`; file preservation alone cannot establish that they stayed unloaded. Seed safe executable auto-extension canaries in private state and project; they would create an observable scratch marker if loaded. No package, hook or MCP server installation is performed.
4. Supply private settings: cache warming `off`, agent retry disabled, provider retry maximum zero, compaction disabled. Supply a dedicated synthetic provider/model with `openai-completions`, `http://127.0.0.1:9/v1`, and an environment interpolation for a fake key. This is no HTTP/key-use proof: networking remains denied and no model is requested.
5. Launch `--offline --mode rpc --no-session --no-tools --no-extensions --no-mcp --no-skills --no-prompt-templates --no-themes --no-context-files --provider ah-feasibility --model ah-no-inference -e <scratch observer>`. The observer blocks `tool_call` and reports active/all-tool names, MCP registrations, skill/template command names and whether unplanned sentinel text appears in the current system prompt.
6. Send only fixed correlated `set_auto_compaction(false)`, `set_auto_retry(false)` and `get_state` records, then EOF. Validate one observer record, three ordered successful responses, exact synthetic model/provider/base URL/API, no streaming/compaction/pending messages and zero message count. Observed inventories are all empty, sentinel text is absent and executable canaries stay unloaded. A second contained no-inference process omits only `--no-skills` and `--no-prompt-templates` as a positive detector control: `getCommands()` must report exactly `skill:inert` and template `inert`. With no read/bash tool available, Pi does not advertise loaded skills in its system prompt, so even a skill-description sentinel alone would not detect loading here. No private session JSONL file appears. Source settings and remaining startup-created files are not a complete effective-settings/resource inventory.

## Verification and next boundary

The offline suite never launches Pi. It covers malformed/duplicate/out-of-order records, duplicate JSON keys, inventory/resource and model-route mismatches, streaming/session/queued work refusal, forbidden input before child launch, sanitized failure, combined output limits, nonzero child exit, deadlines and descendant cleanup (including leader exit with inherited pipes). Tree hash tests detect changed file bytes and symlink targets. The installed positive control verifies that the command inventory can actually observe loaded skills and templates. The suite joins `offline.py`; selected offline suites, document links and whitespace checks pass. No Rust checks or inference are necessary for this isolated experimental addition.

Next is a focused **P8.2 effective-control proof** on this same platform: private/project settings precedence and effective retry/cache controls; full loaded resource/provider inventory; synthetic credential precedence without real auth; a trapped synthetic endpoint capture; and adversarial pre-execution denial before any production/model turn. Trusted one-use grants remain separate. Refuse unsupported profiles/routes throughout. Do not mark P8.2 complete or start P8.3 until its adapter/lifecycle evidence exists. P7.6/P7.7 and P8.5 remain unready; no development-platform switch is needed. A fresh context is efficient before that distinct control experiment.

Grok PR #78 review of `dc4b927` (posted as `awesomejt`): 0 blockers, 1 concern, 1 nit. The concern identified insufficient skill/template load detection; corrected with explicit loaded command inventories and an installed positive control, retaining the skill-description marker. The nit corrected the tree-hash ordering description to Python Path components. Both fixes, installed positive control, offline cases, links and whitespace pass. No critical/high fixes or re-review required.
