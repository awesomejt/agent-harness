# Configuration and agent contract

Status: format-neutral requirements. No example in this document establishes a real configuration filename, precedence table, or provider destination. Phase 2 selects these for the first slice; Phase 3 adds route/model-group details; Phase 4 fixes the canonical-agent schema and backend mapping.

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

## Canonical agents

Markdown body plus YAML frontmatter is canonical. Names map deterministically to backend definitions. The full schema must cover description, primary/specialized applicability, model alias, supported effort, tools and permissions before Phase 4. Exact field names, validation library and output destinations remain deferred.

Name validation must prevent path traversal and ambiguous output names. Validate YAML structures, duplicate names/keys, collisions with user-owned definitions and unsupported restrictions. Preview output and mapping diagnostics before applying. Fixtures compare emitted content and permissions against tested backend versions.

No backend is assumed to have the same subagent semantics or tools. Include a capability/mapping report and refuse unsupported required restrictions. Skills/instruction loading and MCP registration remain backend-owned; mapping an agent into a skill does not prove equivalent permissions.
