# Configuration and agent contract

Status: P2.1 fixes the first-slice input contract below and implements library validation. P2.2 exposes `ah single` on tested macOS; P3.7 moves the runtime pin to OpenCode 2.2.5 (D035). P2.3 owns managed OpenCode configuration and effective-route validation; P2.7 exposes read-only `ah single ... --preview` diagnostics. P3.2 adds isolated native OpenCode cloud-only execution (D032); P3.3 adds LiteLLM model-group references and the read-only proxy handoff (D033) and the configured local-first fallback (D034); P3.7 moves both routes to OpenCode 2.2.5. Phase 3 passed P3.6. P4.1 fixes the canonical schema below; P4.2 adds `--agent` selection, model precedence, read-only preview and conflict-aware project emission (D037); P4.3 enforces named execution with intersected runtime rules and refuses unsupported effort (D038). P4.5 adds one validated sample config per mode under `examples/`, packaged with `agents/*.md` in the release archive (D041). P7.2 adds the Claude runtime as `native.target: "claude"` for cloud-only single runs ([D048](../DECISIONS.md#2026-11-06--d048-claude-runtime-launch-preflight-and-deny-profile-single-runs)), with trusted host prompts (D049) and named roles with effort ([D050](../DECISIONS.md#2026-11-06--d050-claude-named-roles-as-a-narrowed-tool-set-appended-body-and-verified-effort)).

## Version 1 first-slice configuration (D024)

The selected project directory contains `ah.json`. Read exactly that file, or the file selected by `--config PATH`; a missing, malformed or unreadable file is an error. Do not search parents, HOME, XDG directories or environment for harness defaults. Resolve `--project`, `--config` and prompt-file paths against invocation cwd; default project is cwd. Canonicalize the project and require an existing directory. Prompt paths may be outside the project because they are explicitly selected by the caller. Symlinks are followed. Config and prompt files are trusted caller-selected inputs, not an authorization boundary against another process changing them.

```json
{
  "version": 1,
  "mode": "local-only",
  "model": "macmini-qwen3-coder-30b",
  "litellm": {
    "api_base": "http://litellm:4000/v1",
    "api_key_env": "LITELLM_API_KEY"
  },
  "permissions": "deny",
  "timeout_secs": 1800
}
```

Strict JSON, no comments. Version and mode are required. Local-only requires top-level `model` and both `litellm` fields. Cloud-only requires the `native` block below. Local-first requires top-level `model` and both blocks. Present route blocks must validate even when inactive; absent blocks are allowed for the other route, but explicit null blocks reject. Unknown and duplicate fields reject, including literal `api_key`, arbitrary tool policies, agents and fallback configuration. The optional `checks` block (below) declares verification commands but never runs them. `permissions` defaults to `deny` (absence or JSON null), and project config accepts only `deny`; host-level `trusted` requires an explicit invocation flag. `timeout_secs` defaults to 1800 (absence or JSON null). All other null values reject. Config is UTF-8, at most 1 MiB. Application file loading uses `Config::open`, sharing the prompt-file nonblocking Unix open and opened-handle regular-file check; FIFOs/devices/directories reject before reads. The raw-reader API is for caller-owned readers such as fixtures. Errors never echo raw parse errors, input values, prompt contents or secret-bearing paths.

The model is an existing LiteLLM alias (proxy model group), 1–128 ASCII letters/digits/dot/underscore/hyphen, or an explicit `group:NAME` reference to a harness model group (below). Provider-prefixed models and inline proxy routing are unsupported. `api_base` is an absolute HTTP(S) URL with host and exactly `/v1`, without trailing slash, credentials, query, fragment, surrounding whitespace or controls. Require canonical URL spelling equal to the structured parser output: reject dot segments, empty userinfo, uppercase scheme/host and explicit default ports instead of retaining an unvalidated raw spelling. URL validation does not establish proxy availability or provider policy. HTTP permits the existing private-network deployment; credential transport security is the operator's responsibility. `api_key_env` is an ASCII environment name (`[A-Za-z_][A-Za-z0-9_]*`). Its value must exist and be nonempty in the launch environment; no interpolation or key lookup fallback. Keep the resolved value out of config, request records, diagnostics and logs. The environment lookup value is checked for nonempty content and immediately dropped; only its name is retained in the resolved request.

Optional `litellm.runtime` is `opencode` when absent (default) or `pi` ([D080](../DECISIONS.md#2026-11-10--d080-optional-litellmruntime-selects-opencode-or-pi-locally)). `pi` is valid only with `mode: "local-only"`; `local-first`, `cloud-only` and unknown values reject during config validation. The Pi route keeps `api_base`, `api_key_env`, `model` and optional `groups`; it does not sync project `opencode.json`.

Validate the whole config even if invocation flags override fields; malformed/unsupported config cannot be repaired by an override. Then explicit `--mode`, `--model`, `--permissions` and `--timeout-secs` override their corresponding config values. Only explicit `--permissions trusted` may authorize host access; a config requesting it rejects even if a flag overrides it. Built-ins apply only to absent optional fields. No other harness environment settings, prompt metadata, user defaults or inherited runtime defaults participate in harness resolution. `local-only` and `cloud-only` are accepted after P3.2; P3.3 adds `local-first` with one configured native fallback (below). A mode override requires its explicitly configured route and never inherits the other route's model or credentials. A cloud-only config may include `litellm` without a top-level local model; switching it to local-only then requires explicit `--model`. A config whose own mode is local-only still requires its local model default before any overrides.

### Native OpenCode route (P3.2 / D032)

```json
{
  "version": 1,
  "mode": "cloud-only",
  "native": {
    "target": "opencode",
    "model": "gpt-5.4",
    "api_key_env": "OPENCODE_API_KEY"
  },
  "permissions": "deny",
  "timeout_secs": 1800
}
```

`native.target: "opencode"` selects the official OpenCode executable using its built-in `opencode` API-key provider. This target uses OpenCode; the separate `claude` target below uses the official Claude runtime. The caller supplies an OpenCode Console/Zen API key in the named environment variable; the harness passes it only to OpenCode as `OPENCODE_API_KEY`. The built-in provider owns endpoint/authentication handling. No custom endpoint, SDK, provider override, literal credential, OAuth token or login-store path is supported. No subscription credentials are proxied, and the harness neither reads nor copies official login stores. An existing TUI `/connect` login alone is insufficient in the private runtime HOME. Other official provider/CLI integrations remain separately gated.

`native.model` is required and uses the same 1–128 ASCII identifier grammar as a local alias; it excludes provider prefixes. Both primary and helper become `opencode/MODEL`. The pinned runtime's embedded catalog must contain that model before ACP launch; fetching/updating the catalog is disabled. Catalog presence does not prove valid credentials, account balance, model access or service availability. `--model` overrides only the selected route's model. Top-level `model` remains the LiteLLM default and is optional in cloud-only config; it is never reinterpreted as a native model. Both route blocks can coexist so `--mode` selects an explicit route/model/key independently. Only the selected key environment reference is checked; an absent inactive key cannot block cloud-only or trigger LiteLLM discovery.

Cloud-only bypasses the project transaction planner entirely, including with `--no-sync`; it neither reads nor rewrites `opencode.json`, `opencode.jsonc`, ownership receipts, locks or staging files. Its generated in-memory routing has an empty `providers` object, a `provider.use` policy allowing only `opencode`, and the selected model for both the primary and the title helper. Private HOME/XDG, cleared environment, project-config discovery disabling, exact source/agent/catalog checks and ACP session-model checks still apply. Unmanaged project/global runtime settings and auth/endpoint/catalog environment overrides are excluded. Project instruction loading remains enabled under the existing trust scope. The tested runtime/platform is OpenCode **2.2.5 on macOS arm64** (D035).

Native preview uses the same input resolver, reports native selection and no managed changes, and performs no child launch, catalog read or network check. `--no-sync` has no additional effect on this route: effective runtime checks are always mandatory. No harness retry or fallback is added; unknown post-submission outcomes remain uncertain.

### Native Claude runtime (P7.2 / D048)

```json
{
  "version": 1,
  "mode": "cloud-only",
  "native": {
    "target": "claude",
    "model": "sonnet"
  }
}
```

`native.target: "claude"` runs the native route through the official Claude Code CLI, pinned to **2.1.314 on macOS arm64**, instead of OpenCode. The prerequisite is the operator's existing official login: install `claude` on an absolute PATH entry and log in with it before using the harness ([D047](../DECISIONS.md#2026-11-06--d047-native-adapters-use-the-operators-existing-official-cli-login)). The harness never reads, copies or proxies that login, and it passes no `ANTHROPIC_*` or `CLAUDE_*` variable. `native.api_key_env` is rejected for this target; no API-key form is offered. `native.model` is a Claude alias (such as `sonnet` or `opus`) or a full model name under the identifier grammar above; `--model` overrides it, and `group:NAME` rejects. Plan use draws on the operator's own plan limits or usage credits, as Anthropic applies them; the harness makes no claim about either.

`ah single` runs with `deny` (no tool offered) or, with `--permissions trusted`, the fixed built-in set `Bash`, `Edit`, `Glob`, `Grep`, `Read` and `Write`. Under `trusted` the harness answers each host permission prompt with one exact allow-once grant ([D049](../DECISIONS.md#2026-11-06--d049-claude-trusted-permissions-through-the-host-prompt-path)), with host privileges and no OS sandbox. `--agent NAME` runs the role with its body appended to the system prompt and its tools intersected with the invocation, and a non-default `effort` passes `--effort` and is verified before the prompt ([D050](../DECISIONS.md#2026-11-06--d050-claude-named-roles-as-a-narrowed-tool-set-appended-body-and-verified-effort)). `ah sequence` and `ah ralph` run each step or iteration as one such single run, and records name the model `claude/MODEL` ([D051](../DECISIONS.md#2026-11-06--d051-claude-sequences-and-ralph-as-fresh-single-runs-with-runtime-named-records)). `local-first` also accepts a `claude` target ([D052](../DECISIONS.md#2026-11-06--d052-claude-as-the-configured-pre-submission-native-fallback)): OpenCode remains the LiteLLM primary, and Claude runs only after the existing pre-submission unreachable-endpoint check. Both runtimes must support the selected role: non-default effort is still refused by the OpenCode primary, and the Claude body limit is checked before probing. `--mode local-only` with a `litellm` block still runs OpenCode on the LiteLLM route. Preview reports the Claude runtime and the login prerequisite without launching it. See [execution](EXECUTION.md#p72-claude-runtime-d048-d049) for the preflight and outcome mapping.

### LiteLLM model groups (P3.3 / D033)

```json
{
  "version": 1,
  "mode": "local-only",
  "model": "group:coder",
  "litellm": {
    "api_base": "http://litellm:4000/v1",
    "api_key_env": "LITELLM_API_KEY",
    "groups": {
      "coder": "macmini-qwen3-coder-30b",
      "review": "macmini-qwen3-coder-30b"
    }
  }
}
```

`litellm.groups` is optional. When present it is an object of 1–64 entries; explicit null, empty objects, duplicate keys and non-string targets reject. Each key is a harness group name and each value names exactly one existing LiteLLM proxy model group (the `model_name` clients request). Both use the model identifier grammar, so a value cannot itself be a reference or provider-prefixed model. Several harness groups may name the same proxy group.

Top-level `model` and `--model` accept either a bare proxy model group (unchanged) or `group:NAME`. Only the explicit prefix consults `litellm.groups`; a bare name equal to a harness group name is still sent directly, so harness names cannot shadow proxy names. An undefined reference rejects during config validation (config default) or resolution (`--model`), before credential lookup or stdin. Groups belong to the LiteLLM route: `--mode cloud-only --model group:NAME` rejects, and `native.model` cannot be a reference. A cloud-only config may still hold a valid local group default for an explicit `--mode local-only` switch.

A harness group is a stable name for one proxy group, not a pool. The harness does not list deployments, rank or order alternatives; LiteLLM keeps load balancing, retries and fallbacks within its group. Resolution replaces the reference with its proxy group before planning: managed `opencode.json`, the ownership receipt, effective-route checks, runtime/session model and wire requests use only `ah-litellm/PROXY_GROUP`. Harness group names and unselected groups never reach the runtime or project files. Switching between a direct alias and a group that resolves to the same proxy name changes no managed values; changing a group's target updates owned routing like any model change, and `--no-sync` requires the resolved values on disk.

**Proxy handoff.** LiteLLM configuration is operator-owned; the harness never writes it, calls admin/model-management APIs, or installs/restarts/reloads the proxy. `--preview` prints a `proxy handoff:` line: the selected harness group (or direct selection), its proxy model group, and every distinct proxy model group that `litellm.groups` requires, marked existence unverified. Operators ensure those `model_name` entries (or LiteLLM aliases) exist at the configured endpoint. The command remains network-free. Before execution, validation is static (schema, references, route) plus the existing exact effective-routing preflight; proxy group existence is established only by actual use. A missing proxy group surfaces as a runtime failure that stops without retry or fallback. The `attempt=1` progress line names the harness group when one was used.

### Local-first route (P3.3 / D034)

```json
{
  "version": 1,
  "mode": "local-first",
  "model": "group:coder",
  "litellm": {
    "api_base": "http://litellm:4000/v1",
    "api_key_env": "LITELLM_API_KEY",
    "groups": { "coder": "macmini-qwen3-coder-30b" }
  },
  "native": {
    "target": "opencode",
    "model": "gpt-5.4",
    "api_key_env": "OPENCODE_API_KEY"
  }
}
```

`local-first` (config or `--mode`) requires both route blocks. Whole-config validation runs first, so a config whose own `mode` is `local-first` (or `local-only`) must declare top-level `model` even when `--model` is given. `--model` can supply the local model only when `--mode local-first` switches a config whose own mode is `cloud-only`, which needs no top-level `model`. Before prompt input is read, the LiteLLM key must be present and nonempty, as must the native key for an `opencode` target; a `claude` target uses its official CLI login without any native key lookup. The LiteLLM attempt is primary and uses the local model/group exactly as local-only does; `--model` selects only that primary. The fallback model is `agent.models.native` when selected, else `native.model`, with the same project, permissions, timeout, deadline and prompt; there is no fallback-specific override.

Before constructing the local runtime, creating private state, running preflight or applying the project plan, execution performs one bounded TCP connect to the `api_base` host and port (five seconds at most, within the overall deadline). It sends no bytes, credential or HTTP request. Only when no address connects and name resolution fails, or a resolved address refuses, is unreachable or times out, does exactly one native attempt run (`attempt=2`, same `run=`), with a fresh private runtime, fresh grants and the full native preflight. Its outcome is final. A reachable endpoint runs the unchanged local attempt; any later failure, including a missing proxy group, rate limit, authentication or runtime error, stops without fallback. An inconclusive check exits 1 and a cancelled/expired one exits 3, both without fallback. Static validation errors exit 2 before any network contact. The final progress line states whether fallback ran.

Reachability is not model availability, and a mistyped host resolves as unreachable and falls back. Preview stays network-free and reports the configured fallback target; local-only and cloud-only perform no reachability check.

### Verification checks (P5.5 / D043)

```json
{
  "checks": {
    "test": { "argv": ["cargo", "test", "--locked"], "timeout_secs": 900 },
    "lint": { "argv": ["/usr/bin/make", "lint"] }
  }
}
```

`checks` is optional; when present it holds 1–64 named entries (agent-name grammar; duplicate names reject). Each entry has `argv`: 1–64 strings of at most 4096 bytes, no NUL, executed without a shell. Its program is an absolute path or a bare name looked up on absolute PATH entries; relative paths such as `./scripts/check.sh` reject. Run a project script through an interpreter outside the project instead, for example `["/bin/sh", "scripts/check.sh"]`. `timeout_secs` is 1–86400 seconds, default 600. Unknown fields reject.

Declaring a check never runs it. `--verify NAME` selects one declared check for this run; an undeclared name exits 2 before any runtime, network check or write. Resolution pins the program before launch. The found entry and every symlink hop must lie outside the canonical project, so a program the agent could replace exits 2 as untrusted. The check runs only after a successful backend turn and confirmed runtime cleanup. It runs in the project directory with host privileges, closed stdin, both output streams on the harness stderr, configured route key names removed from its environment and its own timeout. Outcomes and exits are in [EXECUTION](EXECUTION.md#p55-verification-gates-d043).

### Selected invocation and preview syntax

```bash
# Runnable with the P2.2 development binary:
ah single "Fix the parser and run tests" --mode local-only --permissions trusted
ah single "Review the change" --model group:review --preview
ah single --prompt-file task.txt --project ./repo --config ./repo/ah.json
cat task.txt | ah single --prompt-file -
ah single "Review this project" --preview --no-sync
ah single --prompt-file task.txt --output jsonl </dev/null   # P4.7 machine records
ah single "Fix the failing test" --permissions trusted --verify test   # P5.5 gate
```

`--output human|jsonl` (default `human`) selects the [machine record contract](EXECUTION.md#p47-machine-output-d039) for coding runs; it changes stdout only.

Exactly one inline positional prompt or `--prompt-file PATH|-` is mandatory. Stdin is read only for explicit `--prompt-file -`; never choose stdin or an interactive session implicitly. Unknown options, repeated options, multiple sources and missing values reject. Options may appear before/after the positional prompt. No short aliases, equals syntax or `--` terminator in the initial parser; use a prompt file for leading-dash text. All arguments must be UTF-8. Preserve prompt whitespace but reject whitespace-only/empty content, invalid UTF-8 or more than 1 MiB. A coding run also rejects a prompt whose first word is `/NAME` (no further `/`), which the runtime would run as a slash command (D040); preview reports the refusal. Prompt files must be regular files; stream input uses explicit stdin. Check config/project/key prerequisites before reading stdin. No model work or project writes may precede input validation. File/stdin I/O must stay cancellation-aware in the eventual application; the library reader enforces a byte bound, not a wall-clock deadline.

`--timeout-secs N` is an integer from 1 through 86400, covering preflight and the active attempt after prompt acquisition. An expired bound enters cleanup; cleanup has separate finite budgets fixed/tested in P2.4. Input acquisition can be interrupted without launching work. No hidden retry or timeout extension. `--no-sync` skips managed writes, never effective-routing or permission validation.

`--preview` resolves the same input and managed-change planner, prints a human-readable redacted plan, and exits before writes or child launch. It performs no network checks, remote registry updates, runtime discovery subprocesses or model requests. Show config path, choice sources, route/runtime/model, environment reference presence, project `AGENTS.md` presence (D040), permission scope, timeout, the selected verification check (pinned program path and argument count, never run; D043) and required managed changes; omit key values and prompt contents. Availability and capabilities that require runtime/service inspection must be marked unverified. Read-only local binary/version-file discovery is permitted. Preview success means a valid local plan, not readiness to execute. Preview stays human-only; `--output jsonl --preview` rejects ([D039](../DECISIONS.md#2026-11-03--d039-opt-in-version-1-machine-records-with-unchanged-exits)).

### Headless permission profiles

Only `deny` and `trusted` are accepted. Prompt/interactive approval, path-scoped shell, arbitrary read-only policies and per-tool user schemas reject. `deny` grants no filesystem, shell, network or external tool actions. `trusted` explicitly authorizes runtime file reads, edits and shell commands with the user's host privileges, including outside the project and network through shell. Project cwd is not a sandbox; this profile must never be advertised as project containment. Use it only for a project/prompt the caller authorizes to act with that scope. No automatic upgrade from denial or from a narrower requested policy. Prompt/config text cannot grant additional privileges; the explicit invocation flag is caller authorization, not backend advice.

Before a production launch, the adapter must isolate effective settings and inspect them for the tested OpenCode version: deny all tool categories by default; enable only the selected profile's verified built-in read/search/edit/shell operations; disable MCP, external tools, task/subagents, other agent definitions, network tools and inherited auto-allows. Primary and helper model selections must both use the selected route's model. All actions in `deny`, and unknown categories in either profile, remain denied. Trusted shell can run arbitrary commands; these runtime restrictions do not contain what an explicitly authorized shell command can do.

P2.2 must prove actual read/edit/shell enforcement, denied-action behavior and effective-route validation before its first coding prompt. Normalize supported ACP action kinds using adapter-verified semantics and complete request identities/arguments, never display labels. For an authorized trusted operation that requires a callback, issue a fresh exact request-bound grant and select an advertised allow-once option through the existing permission policy. Never select allow-always, inherit blanket approval or reuse grants across requests/attempts. Denied requests receive a verified denial/cancellation immediately. Malformed requests, missing support or response-send failure stop the attempt and enter cleanup with possible uncertainty. If the runtime cannot enforce this profile, refuse execution. P1.3 proves denial only; trusted coding enforcement is a P2.2 gate, not a claim made by these validation fixtures.

## Rust representation and LiteLLM boundary

Deserialize into input structures, then validate into route-specific domain values as outlined in [DESIGN.md](DESIGN.md). Canonical YAML frontmatter is separate from the strict JSON harness config selected by D024. Runtime state is not inherited from ai-queue's SQLite schema.

The first slice references an existing LiteLLM alias. The harness owns desired endpoint/group selection and policy; the proxy executes internal routing. P3.3 defines group representation, validation and the read-only handoff below (D033). This does not imply automatic proxy-service installation/restart/reconfiguration privileges.

## Resolution and validation

Define the complete precedence among explicit invocation values, any supported environment settings, project config, optional user defaults, and built-ins before the first CLI ships. Do not add implicit parent-directory discovery without specifying its trust and conflict rules. An explicit invocation-level mode restriction stays authoritative over later prompt metadata.

Validate types, unknown keys, model aliases, paths, missing environment references, target availability, and unsupported features before starting work. Describe which validations contact a service; cloud-only cannot contact LiteLLM, and a local-only availability failure cannot launch a cloud CLI. Configuration errors are actionable and secrets are redacted.

Model aliases/groups refer to harness-owned routing choices; native target aliases remain separate from LiteLLM aliases. Effort settings are capability-dependent. Unsupported mappings cannot silently broaden access or substitute an unapproved route; decide rejection versus documented effort approximation in Phase 4.

## Read-only diagnostics and preview

Basic Phase 2 diagnostics show harness/runtime versions, binary discovery, effective mode/model/project, missing prerequisites, config source, and managed changes required. A preview must not send a prompt, start a model turn, change files, or update remote registries. Phase 2 decides whether it permits any non-spending health checks; report those separately. Never treat unverified availability as confirmed.

Plan preview shows the resolved route/runtime, applicable constraints, proposed project-config changes, and source of each decision. `ah single PROMPT --preview` is the selected diagnostic command; normal input/config flags also apply. Missing or empty key references and invalid model/config inputs return exit 2 before planning. Missing OpenCode is reported with installation guidance; a valid local plan still returns 0 because discovery is not an execution readiness check. Runtime version, remote alias availability and reachability remain explicitly unverified. No health checks, including non-spending network requests, are permitted in this command. Config/project/runtime paths are quoted with control escaping; endpoint, credential values, prompt contents and unmanaged settings are omitted. Sources identify invocation/config/default choices; managed-change output lists affected files and routing fields without dumping old/new values. Secret values never appear in preview or diagnostic output.

## Managed configuration transaction

Identify the project destination and managed fields before mutation. Preserve unrelated settings and supported user formatting/comments; if preservation is not reliable, refuse the write and explain the supported alternative. Detect an existing user-owned conflicting field rather than overwrite it blindly.

Plan changes first, validate resulting effective routing, and write atomically. Detect a concurrent change between read and replace, using a hash/version check, lock or equivalent mechanism selected in Phase 2. Fail visibly without replacing newer user content. Track ownership sufficiently to distinguish generated values from later manual edits. Cleanup, if implemented, removes only still-owned content; no general destructive reset.

A LiteLLM key stays in an environment reference that the backend resolves at runtime. Never resolve it into project config, previews, logs, events, fixtures or workflow records. Test this with a sentinel secret. Native credentials stay with official tools; the harness neither copies login stores nor asks a proxy to impersonate subscription authentication.

`--no-sync` skips writes but not effective-route validation. Cloud-only/native runs do not rewrite the provider block and must not inherit the generated LiteLLM selection. Document how runtime defaults, agents, helper models, and project/global settings are accounted for; reject a route that cannot be proven from supported configuration.

### P2.3 selected transaction (D025)

`project_config::Plan` reads only project `opencode.json` and `.ah-opencode-owner.json`. It reserves `provider.ah-litellm`, `enabled_providers`, `model` and `small_model` values. Provider `ah-litellm` uses `@ai-sdk/openai-compatible`, the requested API base, `{env:NAME}` key reference and the existing alias. Both model selections are `ah-litellm/ALIAS`. Permissions and runtime isolation remain P2.2 gates.

Support strict UTF-8 JSON objects up to 1 MiB without duplicate keys at any depth. Unrelated fields and their formatting remain byte-for-byte unchanged. JSONC/comments, symlink/nonregular files, existing `opencode.jsonc`, and unowned routing fields refuse sync: manually migrate comments/alternate config and move conflicting routing settings before retrying. Inactive sibling provider definitions and their formatting remain untouched. No automatic adoption, config deletion, rollback or global writes occur. New transaction files use mode 0600; replacement preserves the existing project config permission mode.

The receipt contains exactly the four last-generated values. Updates require their semantic equality with the current managed fields, preserving unrelated edits. Apply uses a retained `.ah-opencode.lock` with nonblocking advisory locking, exact read/replace snapshot checks, exclusive same-directory staging, file flush, atomic rename per file, then directory sync. Cooperating writers serialize and stale plans refuse; external editors must avoid racing apply because advisory locks do not provide atomic compare-and-swap against noncooperating writers. Config and receipt are separate renames. An interrupted update can leave a mismatch or unowned fields: inspect both files and reconcile deliberately; the harness refuses rather than restoring over user work. Abandoned `.ah-write-*` files are inert. Write support is currently Unix, tested on macOS arm64.

When versioning managed configuration, commit `opencode.json` and `.ah-opencode-owner.json` together so clones inherit the intended ownership record. The receipt contains environment names, never resolved keys, and is trusted project input rather than proof of authorship. If configuration is intentionally local, keep both files local; committing only the config leaves clones with unowned routing fields, requiring exact `--no-sync` or deliberate manual reconciliation. Add `/.ah-opencode.lock` and `/.ah-write-*` to the project's ignore rules (or local `.git/info/exclude`). The harness does not edit ignore rules or create commits. Lock/staging files must remain untracked. Treat both config and receipt changes as project changes during dirty-worktree reporting.

`--no-sync` requires all four project values to match exactly, permits matching unowned configuration and never creates a lock/receipt. That disk check only covers the managed file. The runtime still goes through every effective check described below (sources, agent rule tails, catalog and version; D035), which validate the generated in-memory document, not the project file. Native execution must use a separate isolated setup and cannot consume this local-only plan; P3.2 verifies that prerequisite. Neither planning nor disk-only validation proves runtime readiness.

## Canonical agents

D036 fixes version 1. `agents/NAME.md` is the canonical project source. P4.1 supplies the parser and examples. P4.2 adds `--agent NAME` selection, preview and project emission ([below](#p42-selection-and-emission-d037)); P4.3 runs the selected role with enforced constraints ([below](#p43-enforced-named-execution-d038)).

```yaml
---
version: 1
name: reviewer
description: Review a change for correctness and regressions.
capacity: specialized
permissions: read-only
tools: [read, search]
---
Inspect the change and report concrete defects. Do not edit or run commands.
```

Required fields are `version`, `name`, `description`, `capacity`, `permissions` and `tools`. Unknown/duplicate fields, invalid types and unknown enum values reject. Explicit null rejects, including optional fields. Names use 1–64 ASCII lowercase letters/digits with single internal hyphens, begin with a letter and match the filename exactly. No dot, slash, backslash, underscore, case folding, traversal or hidden name. OpenCode built-ins `build`, `plan`, `general`, `explore`, `compaction`, `title` and `summary` are reserved; backend conflicts beyond this set remain a P4.2 check. A catalog has at most 64 unique names, sorted by name; duplicate definitions never override.

`description` is 1–512 UTF-8 bytes, single-line and trimmed, without controls or Unicode line/paragraph separators (U+2028/U+2029). `capacity` is `primary`, `specialized` or `both`; specialized means a separate harness-invoked role, not permission to create backend subagents. `tools` is an explicit, duplicate-free list from `read`, `search`, `edit`, `execute`; an empty list is valid. These are harness capabilities, not arbitrary backend tool names. `permissions` is a ceiling: `deny` requires no tools, `read-only` permits only read/search, and `trusted` permits any of the four. The runtime mapping intersects this ceiling and list with invocation authorization (D038); project metadata cannot grant host trust. Shell/execute cannot satisfy read-only, even for a command described as a test. No path globs, auto-allow or prompt-only restrictions are accepted.

Optional `models` has only `local` and/or `native`, at least one present. For example `models: {local: 'group:code', native: gpt-5.4}`. Each is a string scalar: local uses the existing LiteLLM alias or `group:NAME` grammar; native uses the existing unprefixed model identifier grammar. No endpoints, keys, provider prefixes or native group references. An omitted route inherits its resolved invocation/config model. Group existence and active-route compatibility are checked when resolving selection in P4.2/P4.3, not by this standalone parser. Fallback must resolve its own native model under the same agent restrictions and may never broaden them. P4.2 fixes precedence: explicit `--model`, then the agent's route model, then config (D037).

Optional `effort` is `default` (also the omission default), `low`, `medium`, `high` or `max`. Non-default values are required capabilities, not a tested mapping or approximation. P4.3 refuses every non-default effort on OpenCode 2.2.5 before model work (D038). The Claude runtime maps each non-default value to `--effort` and checks the applied level before the prompt ([D050](../DECISIONS.md#2026-11-06--d050-claude-named-roles-as-a-narrowed-tool-set-appended-body-and-verified-effort)). The parser does not claim that OpenCode can enforce every syntactically valid definition.

Files are UTF-8, at most 1 MiB, with an exact opening `---` line and closing `---` line. LF and CRLF delimiters are accepted; BOM, missing delimiters, whitespace-only bodies and body controls other than tab/CR/LF reject. Frontmatter is at most 16 KiB, parsed as one YAML mapping by pinned `serde_yaml_ng` 0.10.0. A bounded value pass rejects custom tags, then direct strict-struct decoding retains duplicate-field rejection. String fields must be YAML strings, with no null/number/boolean coercion; quote numeric-only model names. YAML merge keys and custom tags are unsupported. Ordinary string anchors/aliases may resolve within the mapping; unresolved/recursive/type-incompatible aliases reject. Body text is preserved exactly, including trailing newline. File loading requires a regular file, rejects parent traversal and a final symlink, and uses nonblocking/no-follow Unix opening. Parent-directory containment and transaction races belong to the P4.2 project planner; the parser is not a filesystem sandbox. Errors contain only static messages, with no file content, raw YAML diagnostics or private paths.

**OpenCode destinations (tested 2.2.5).** Project emission is `.opencode/agents/NAME.md`, with native frontmatter and the Markdown body as `system`. Canonical frontmatter must be translated, never copied unchanged: OpenCode does not understand harness version, capacity, tools or permission ceilings. Map capacity `primary`/`specialized`/`both` to native `mode: primary`/`subagent`/`all`. Native `description`, structured `model: {providerID, model}` and ordered `permissions` use their 2.x fields. Isolated harness execution uses a generated `agents.NAME` entry in `OPENCODE_CONFIG_CONTENT`, with body as `system`, rather than enabling project-config discovery or loading the emitted file. Preflight checks the selected definition before execution: a named request requires that agent as the visible primary with the exact model, description and system text, and `build` alone no longer satisfies it (D038). No global agent destination, other provider format, backend delegation or non-default effort mapping is guaranteed. The [destination probe](../scripts/tests/agents_runtime.py) verifies both destinations and three modes with no model prompt; [P4.1 evidence](evidence/p4-1-agent-schema.md) records limits.

P4.1 implements the validation rules above; P4.3 adds the runtime capability checks and enforced constraints below.

### P4.2 selection and emission (D037)

`ah single ... --agent NAME` validates the name, then loads only `PROJECT/agents/NAME.md`. `agents` must be a real directory whose listing contains exactly `NAME.md`; a case-variant filename refuses and other definitions are never parsed. Global/user agent locations are not consulted.

| Route | Model precedence |
| --- | --- |
| LiteLLM (local-only, local-first primary) | `--model` → agent `models.local` → config `model` |
| Native (cloud-only) | `--model` → agent `models.native` → `native.model` |
| Local-first fallback | agent `models.native` → `native.model` (`--model` never applies) |

An agent `group:NAME` resolves through `litellm.groups` only on the active LiteLLM route and is ignored on the native route. Preview shows the model source as `agent`, plus an `agent:` line with name, capacity, ceiling, tools, effort and emission status; description/body are omitted.

P4.2 refused named execution; P4.3 enables it with the enforced mapping below.

On the managed local route (not `--no-sync`; never native, D032), the project transaction emits only the selected agent to `.opencode/agents/NAME.md` for direct OpenCode use:

```text
---
{"description":"…","mode":"subagent","model":{"providerID":"ah-litellm","model":"proxy"},"permissions":[{"action":"*","resource":"*","effect":"deny"},{"action":"read","resource":"*","effect":"ask"},…]}
---
<canonical body, byte-for-byte>
```

The frontmatter is one JSON flow mapping (valid YAML). `model` is the resolved route model. Permissions come only from the canonical ceiling and tools: deny all, then `ask` for each listed tool (`read`→`read`, `search`→`glob`+`grep`, `edit`→`edit`, `execute`→`shell`), and `external_directory` is `ask` only under a trusted ceiling, otherwise `deny`. No rule allows. The isolated runtime never loads this file, and it is not the enforced runtime entry. [Golden fixtures](../tests/fixtures/opencode-agents/) pin the bytes.

`.ah-opencode-agents.json` records the exact content last emitted for each owned name. Only an unchanged owned file is replaced. A manually edited owned file, or an existing file absent from the receipt (even if identical), refuses. A missing file is (re)created; other owned files are untouched and never deleted. The planner refuses, case-insensitively, any other OpenCode 2.2.5 project source of the same name: another spelling in `.opencode/agents/`, legacy `.opencode/agent/`, or `agent`/`agents` keys in `opencode.json` or `.opencode/opencode.json`. `.opencode/opencode.jsonc`, symlinked `.opencode`/`.opencode/agents`/destination and an invalid receipt also refuse. Nested IDs such as `.opencode/agents/sub/NAME.md` (`sub/NAME`) are distinct. Writes use the existing lock, re-checked snapshots and collisions, atomic replacement and directory fsync. A crash between the agent file and receipt is a visible ownership conflict. Preview lists the planned file and receipt by path and writes nothing.

### P4.3 enforced named execution (D038)

A named run invokes the role directly as the session's default agent, whatever its capacity; `capacity` is reported as the role. The generated runtime document adds `agents.NAME` (`mode: primary`, resolved route model, effective rules, body as `system`) and `default_agent: NAME`. Installed 2.2.5 silently replaces a `subagent` default with `build`, so the entry is never a subagent and the ACP session `mode` must equal NAME before the prompt.

| Invocation `--permissions` | Effective rules (global and agent) | Grantable ACP kinds |
| --- | --- | --- |
| `deny` (default) | deny profile, any role | none; any completed tool fails |
| `trusted`, no agent | trusted profile (unchanged) | read, search, edit, execute |
| `trusted`, agent | D037 ceiling rules of the agent | the agent's listed tools only |

Built-in helpers and subagents receive the same global rules, so they never exceed the role. Under a named role, a completed tool call of an unlisted or unknown kind is a violation (exit 4 after submission). Preview reports `runtime: default agent with effective permissions …`.

Effort on OpenCode: only `default` runs (the Claude runtime maps every value, D050). 2.2.5's ACP `effort` session option has no verified provider mapping, so `low`, `medium`, `high` and `max` exit 2 before any runtime, network check or project write; preview appends `execution refused: …`. The local-first fallback carries the same agent and must preserve the same name and effective rules.

No backend is assumed to have the same subagent semantics or tools. Include a capability/mapping report and refuse unsupported required restrictions. Skills/instruction loading and MCP registration remain backend-owned; mapping an agent into a skill does not prove equivalent permissions.

## P2.2 isolated OpenCode launch (D026)

Under D035 there are two deliberate generators. The planner writes the managed project `opencode.json` in legacy keys for direct OpenCode use, and 2.2.5 translates them into the equivalent routing. The runtime document passed in `OPENCODE_CONFIG_CONTENT` is generated separately in the native 2.x schema from the same resolved request. Only that document is executed and validated. Native execution uses the same generator with its own route and never touches the project file (D032). It disables OpenCode project-config discovery, uses a private mode-0700 temporary HOME/XDG tree, clears inherited environment variables and passes a generated `OPENCODE_CONFIG_CONTENT`. Unmanaged project/global config, plugins, MCP, skills, commands and custom agents are not loaded; their files remain untouched. Because 2.2.5 disables project instruction discovery with project config, the document names the project-root `AGENTS.md` by absolute path as its only instruction source (D040, [P4.8](EXECUTION.md#p48-inherited-capabilities-d040)). D030 requires attempted worker-backed removal and verified absence of its private tree after each prepared-runtime outcome, including rejection/cancellation. A separate worker gets a two-second wait; failed/unconfirmed removal returns exit 4 with a retained-state warning. If the worker cannot start, removal is unattempted; no unbounded synchronous fallback is used. Abrupt termination, detached writers and constructor failure are outside that removal guarantee. The published `v0.1.0-alpha.1` artifact predates this correction and removes private state only on a best-effort basis; `v0.1.0-alpha.2` includes it. Only PATH and the selected key value under reserved `AH_RUNTIME_API_KEY` (LiteLLM) or `OPENCODE_API_KEY` (native) cross the environment boundary; no provider login stores or inherited OpenCode overrides participate. Authorized shell commands inherit this restricted environment and may access host resources; this is not containment.

Before applying the managed plan or launching ACP, bounded `--standalone` subprocess checks require `opencode v2.2.5` and exactly two configuration sources: the private config directory, and a document equal to the generated native-schema routing with only the resolved key masked. Every agent, including built-in helpers and subagents, must end with the exact ordered permission profile followed only by built-in denials, use no other model and carry no request overrides. The runtime document is generated in memory; the managed project `opencode.json` keeps legacy keys for direct OpenCode use, which 2.x translates (D035). `--no-sync` still goes through every effective check. Unsupported versions/capabilities refuse, without a model turn.

Trusted grants join the same-session ACP permission request to its tool call's latest announcement. OpenCode 2.2.5 announces a `pending` call with empty `rawInput`, then sends the complete arguments in an `in_progress` update before asking; completed/failed updates retire that descriptor. A grant requires a kind of `read`, `search`, `edit` or `execute` matching the announcement, and a non-empty request `rawInput` exactly equal to the announced `rawInput`. Empty, omitted or changed request arguments fail closed, and generated diff content outside `rawInput` is not interpreted. An `other` kind (for example the built-in `opencode_worktree_remove`) is always refused. An outside-project read raises two byte-identical requests (external directory, then the tool); each copy gets its own one-shot grant, and a third copy fails the attempt. Grant only advertised allow-once, bind the complete joined descriptor, and never reuse a grant. Unsupported requests receive denial, which ends the 2.2.5 turn as cancelled (exit 3). Malformed, wrong-session or replayed requests fail the attempt, and any client filesystem or terminal callback fails closed (D035).

`--preview` returns the local plan before runtime creation, preflight or project apply. The adapter buffers at most 1 MB of assistant text and bounds total protocol traffic at 8 MB; P2.4 drains and counts child stderr without exposing it and supplies bounded progress/cancellation. The active/preflight deadline starts after input acquisition. Synchronous filesystem transaction operations depend on OS completion; deadline/cancellation are checked again after apply and before launch. Cancellation during blocking input uses normal process signals before the async supervisor starts.
