# Configuration and agent contract

Status: P2.1 fixes the first-slice input contract below and implements library validation. The public binary still supports help/version only until P2.2. P2.3 owns managed OpenCode configuration and effective-route validation; P2.7 implements preview. Phase 3 adds route/model-group details; Phase 4 fixes canonical agents.

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

Strict JSON, no comments. Version, mode, model and both LiteLLM fields are required. Unknown and duplicate fields reject, including literal `api_key`, arbitrary tool policies, agents and fallback configuration. `permissions` defaults to `deny` (absence or JSON null), and project config accepts only `deny`; host-level `trusted` requires an explicit invocation flag. `timeout_secs` defaults to 1800 (absence or JSON null). All other null values reject. Config is UTF-8, at most 1 MiB. Application file loading uses `Config::open`, sharing the prompt-file nonblocking Unix open and opened-handle regular-file check; FIFOs/devices/directories reject before reads. The raw-reader API is for caller-owned readers such as fixtures. Errors never echo raw parse errors, input values, prompt contents or secret-bearing paths.

The model is an existing LiteLLM alias, 1–128 ASCII letters/digits/dot/underscore/hyphen; provider-prefixed models, groups and inline proxy routing are outside this slice. `api_base` is an absolute HTTP(S) URL with host and exactly `/v1`, without trailing slash, credentials, query, fragment, surrounding whitespace or controls. Require canonical URL spelling equal to the structured parser output: reject dot segments, empty userinfo, uppercase scheme/host and explicit default ports instead of retaining an unvalidated raw spelling. URL validation does not establish proxy availability or provider policy. HTTP permits the existing private-network deployment; credential transport security is the operator's responsibility. `api_key_env` is an ASCII environment name (`[A-Za-z_][A-Za-z0-9_]*`). Its value must exist and be nonempty in the launch environment; no interpolation or key lookup fallback. Keep the resolved value out of config, request records, diagnostics and logs. The environment lookup value is checked for nonempty content and immediately dropped; only its name is retained in the resolved request.

Validate the whole config even if invocation flags override fields; malformed/unsupported config cannot be repaired by an override. Then explicit `--mode`, `--model`, `--permissions` and `--timeout-secs` override their corresponding config values. Only explicit `--permissions trusted` may authorize host access; a config requesting it rejects even if a flag overrides it. Built-ins apply only to absent optional fields. No other harness environment settings, prompt metadata, user defaults or inherited runtime defaults participate in harness resolution. Only `local-only` is accepted in Phase 2, including with `--no-sync`. Native routes and automatic fallback are unavailable.

### Selected invocation and preview syntax

```bash
# Contract for P2.2, not a runnable command in P2.1:
ah single "Fix the parser and run tests" --mode local-only --permissions trusted
ah single --prompt-file task.txt --project ./repo --config ./repo/ah.json
cat task.txt | ah single --prompt-file -
ah single "Review this project" --preview --no-sync
```

Exactly one inline positional prompt or `--prompt-file PATH|-` is mandatory. Stdin is read only for explicit `--prompt-file -`; never choose stdin or an interactive session implicitly. Unknown options, repeated options, multiple sources and missing values reject. Options may appear before/after the positional prompt. No short aliases, equals syntax or `--` terminator in the initial parser; use a prompt file for leading-dash text. All arguments must be UTF-8. Preserve prompt whitespace but reject whitespace-only/empty content, invalid UTF-8 or more than 1 MiB. Prompt files must be regular files; stream input uses explicit stdin. Check config/project/key prerequisites before reading stdin. No model work or project writes may precede input validation. File/stdin I/O must stay cancellation-aware in the eventual application; the library reader enforces a byte bound, not a wall-clock deadline.

`--timeout-secs N` is an integer from 1 through 86400, covering preflight and the active attempt after prompt acquisition. An expired bound enters cleanup; cleanup has separate finite budgets fixed/tested in P2.4. Input acquisition can be interrupted without launching work. No hidden retry or timeout extension. `--no-sync` skips managed writes, never effective-routing or permission validation.

`--preview` (P2.7) resolves the same input and managed-change planner, prints a human-readable redacted plan, and exits before writes or child launch. It performs no network checks, remote registry updates, runtime discovery subprocesses or model requests. Show config path, choice sources, route/runtime/model, environment reference presence, permission scope, timeout and required managed changes; omit key values and prompt contents. Availability and capabilities that require runtime/service inspection must be marked unverified. Read-only local binary/version-file discovery is permitted. Preview success means a valid local plan, not readiness to execute. No machine schema is promised until Phase 4.

### Headless permission profiles

Only `deny` and `trusted` are accepted. Prompt/interactive approval, path-scoped shell, arbitrary read-only policies and per-tool user schemas reject. `deny` grants no filesystem, shell, network or external tool actions. `trusted` explicitly authorizes runtime file reads, edits and shell commands with the user's host privileges, including outside the project and network through shell. Project cwd is not a sandbox; this profile must never be advertised as project containment. Use it only for a project/prompt the caller authorizes to act with that scope. No automatic upgrade from denial or from a narrower requested policy. Prompt/config text cannot grant additional privileges; the explicit invocation flag is caller authorization, not backend advice.

Before a production launch, P2.2/P2.3 must isolate effective settings and inspect them for the tested OpenCode version: deny all tool categories by default; enable only the selected profile's verified built-in read/search/edit/shell operations; disable MCP, external tools, task/subagents, other agent definitions, network tools and inherited auto-allows. Primary and helper model selections must both use the chosen LiteLLM alias. All actions in `deny`, and unknown categories in either profile, remain denied. Trusted shell can run arbitrary commands; these runtime restrictions do not contain what an explicitly authorized shell command can do.

P2.2 must prove actual read/edit/shell enforcement, denied-action behavior and effective-route validation before its first coding prompt. Normalize supported ACP action kinds using adapter-verified semantics and complete request identities/arguments, never display labels. For an authorized trusted operation that requires a callback, issue a fresh exact request-bound grant and select an advertised allow-once option through the existing permission policy. Never select allow-always, inherit blanket approval or reuse grants across requests/attempts. Denied requests receive a verified denial/cancellation immediately. Malformed requests, missing support or response-send failure stop the attempt and enter cleanup with possible uncertainty. If the runtime cannot enforce this profile, refuse execution. P1.3 proves denial only; trusted coding enforcement is a P2.2 gate, not a claim made by these validation fixtures.

## Rust representation and LiteLLM boundary

Deserialize into input structures, then validate into route-specific domain values as outlined in [DESIGN.md](DESIGN.md). Canonical YAML frontmatter is separate from the strict JSON harness config selected by D024. Runtime state is not inherited from ai-queue's SQLite schema.

The first slice references an existing LiteLLM alias. The harness owns desired endpoint/group selection and policy; the proxy executes internal routing. Phase 3 defines group representation, validation and any configuration handoff. This does not imply automatic proxy-service installation/restart/reconfiguration privileges.

## Resolution and validation

Define the complete precedence among explicit invocation values, any supported environment settings, project config, optional user defaults, and built-ins before the first CLI ships. Do not add implicit parent-directory discovery without specifying its trust and conflict rules. An explicit invocation-level mode restriction stays authoritative over later prompt metadata.

Validate types, unknown keys, model aliases, paths, missing environment references, target availability, and unsupported features before starting work. Describe which validations contact a service; cloud-only cannot contact LiteLLM, and a local-only availability failure cannot launch a cloud CLI. Configuration errors are actionable and secrets are redacted.

Model aliases/groups refer to harness-owned routing choices; native target aliases remain separate from LiteLLM aliases. Effort settings are capability-dependent. Unsupported mappings cannot silently broaden access or substitute an unapproved route; decide rejection versus documented effort approximation in Phase 4.

## Read-only diagnostics and preview

Basic Phase 2 diagnostics show harness/runtime versions, binary discovery, effective mode/model/project, missing prerequisites, config source, and managed changes required. A preview must not send a prompt, start a model turn, change files, or update remote registries. Phase 2 decides whether it permits any non-spending health checks; report those separately. Never treat unverified availability as confirmed.

Plan preview shows the resolved route/runtime, applicable constraints, proposed project-config changes, and source of each decision. Exact command names remain open; one compact command or flag can satisfy these requirements. Secret values never appear in preview or diagnostic output.

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

`--no-sync` requires all four project values to match exactly, permits matching unowned configuration and never creates a lock/receipt. This still requires adapter-observed effective config validation: exact selected routing values (allowing inactive sibling providers) and no conflicting or malformed `agent` or legacy `mode` model overrides. Global/environment isolation, permissions, agent/tool allowlists and OpenCode-version capability verification are mandatory P2.2 preflight responsibilities. Native execution must use a separate isolated setup and cannot consume this local-only plan; P3.2 verifies that prerequisite. Neither planning nor disk-only validation proves runtime readiness.

## Canonical agents

Markdown body plus YAML frontmatter is canonical. Names map deterministically to backend definitions. The full schema must cover description, primary/specialized applicability, model alias, supported effort, tools and permissions before Phase 4. Exact field names, validation library and output destinations remain deferred.

Name validation must prevent path traversal and ambiguous output names. Validate YAML structures, duplicate names/keys, collisions with user-owned definitions and unsupported restrictions. Preview output and mapping diagnostics before applying. Fixtures compare emitted content and permissions against tested backend versions.

No backend is assumed to have the same subagent semantics or tools. Include a capability/mapping report and refuse unsupported required restrictions. Skills/instruction loading and MCP registration remain backend-owned; mapping an agent into a skill does not prove equivalent permissions.
