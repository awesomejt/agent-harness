# Design rationale

[Specification](SPECIFICATION.md) defines goals; [DECISIONS.md](../DECISIONS.md) records decisions and [ARCHITECTURE.md](ARCHITECTURE.md) defines boundaries.

## Learn through use

The first milestone must perform a real coding task. A single local-only OpenCode run through LiteLLM exercises the most important integration without waiting for multi-provider mapping or autonomous workflows. Usable phases provide evidence about setup friction, routing clarity, permissions, output, and recovery.

The core MVP then adds the complete mode policy and named agents. Sequences and Ralph remain product goals but do not delay first use or core MVP. Later choices receive an owner phase and a decision trigger so planning stays complete without guessing every implementation detail now.

## Rust and distribution

Rust is the planned implementation language, reflecting the user's preference for binary installation and willingness to learn it. Select a nonconflicting Cargo package name separately from repository/CLI naming. Prebuilt binaries are the primary user installation experience; Cargo installation can remain an optional developer path.

The integration experiment determines libraries and transport. AI assistance does not remove the need to understand ownership, cancellation, process lifetime, or platform differences. Test those boundaries directly.

## Existing runtimes supply coding behavior

The product orchestrates installed tools. OpenCode owns its inner model/tool loop; the harness owns route selection, configuration, definition mapping, and outer workflows. Raw LiteLLM completions do not replace a coding runtime. This avoids taking on an agent framework solely to issue HTTP calls.

Model route and runtime transport are orthogonal. Both LiteLLM-backed and native-model OpenCode runs may use the same executable and transport. Enforce policy on the effective route, including inherited configuration and tool/subagent model choices.

## Explicit policy and recoverable work

Mode restrictions are stronger than availability, quota ranking, or fallback convenience. Provider credentials stay in native tools; no subscription-token extraction or prohibited proxying.

Coding attempts have side effects. Timeouts and interrupted streams may leave applied changes; a naive retry can duplicate work. Classify failure and expose uncertainty before adding automatic fallback or resume. Durable workflows must record enough evidence to distinguish completed, failed, and uncertain work without promising exactly-once execution.

## Configuration and portable definitions

Project-level sync provides one source of truth while preserving user/global settings. Validate effective routing even when writes are skipped. Canonical Markdown + YAML agents map by name, but actual destinations and enforceable permissions are verified per backend. Portability includes an honest capability report and refusal of unsupported restrictions.

## Selective reuse

Use ai-queue's HTTP/error handling, test patterns, and later usage readers as behavioral references. Do not import its allocation-first routing, tools-disabled temporary execution, TOML agent schema, or SQLite queue as the default architecture.

Evaluate Rust ACP/adapter/process libraries behind our boundaries. Borrow Ralph and configuration-sync patterns where useful. Avoid adopting a whole framework when a leaf component satisfies the requirement. Preserve required attribution when code is reused.
