//! Network-free diagnosis of the selected route. Never execute a discovered binary or inspect its output.
use crate::{
    config::{Mode, Permissions, Resolved, Source},
    project_config::Plan,
};
use std::path::{Path, PathBuf};

/// Shared with execution: relative PATH entries are deliberately excluded.
pub(crate) fn discover_runtime() -> Option<PathBuf> {
    std::env::var_os("PATH")
        .into_iter()
        .flat_map(|p| std::env::split_paths(&p).collect::<Vec<_>>())
        .filter(|p| p.is_absolute())
        .map(|p| p.join("opencode"))
        .find(|p| {
            p.metadata().is_ok_and(|m| {
                #[cfg(unix)]
                {
                    use std::os::unix::fs::PermissionsExt;
                    m.is_file() && m.permissions().mode() & 0o111 != 0
                }
                #[cfg(not(unix))]
                {
                    m.is_file()
                }
            })
        })
        .and_then(|p| p.canonicalize().ok())
}

fn source(source: Source) -> &'static str {
    match source {
        Source::Invocation => "invocation",
        Source::Agent => "agent",
        Source::Config => "config",
        Source::Default => "default",
    }
}

pub(crate) fn render(r: &Resolved, plan: Option<&Plan>, config: &Path) -> String {
    // Debug path formatting escapes control characters. No raw configuration,
    // endpoint, key value, prompt, or unmanaged settings are formatted here.
    let runtime = match discover_runtime() {
        Some(path) => format!(
            "discovered {path:?}; version unverified (requires {})",
            crate::opencode::VERSION
        ),
        None => format!(
            "missing; install OpenCode {} on an absolute PATH entry",
            crate::opencode::VERSION
        ),
    };
    // A named role can narrow a trusted invocation (D038); report the
    // effective scope from the same mapping the runtime enforces.
    let kinds = crate::opencode::grantable(r);
    let scope = match r.permissions {
        Permissions::Deny => "deny: no file/shell grants".to_owned(),
        Permissions::Trusted
            if crate::opencode::effective(r) == crate::opencode::profile(r.permissions) =>
        {
            "trusted: read/write/shell with host privileges; no OS sandbox".to_owned()
        }
        Permissions::Trusted if kinds.is_empty() => {
            "trusted narrowed by agent to no file/shell grants".to_owned()
        }
        Permissions::Trusted => format!(
            "trusted narrowed by agent to {} grants{}",
            kinds.join(", "),
            if kinds.contains(&"execute") {
                "; shell with host privileges; no OS sandbox"
            } else {
                ""
            }
        ),
    };
    let changes = plan.map(Plan::preview_changes).unwrap_or_default();
    let changes = if changes.is_empty() {
        "none".into()
    } else {
        changes.join("; ")
    };
    let local = r.mode == Mode::LocalOnly;
    let mode = match (local, &r.fallback) {
        (true, Some(_)) => "local-first",
        (true, None) => "local-only",
        _ => "cloud-only",
    };
    let route = if r.fallback.is_some() {
        "LiteLLM primary; configured native OpenCode fallback"
    } else if local {
        "LiteLLM only"
    } else {
        "native OpenCode built-in opencode API-key provider"
    };
    let before = if local {
        "ensure configured LiteLLM /v1 service is reachable and selected alias exists"
    } else {
        "ensure the native API key and built-in model are available; login stores are not consumed"
    };
    // Identifier grammar excludes quotes/controls, so group names print safely.
    let quoted = |names: &[String]| {
        names
            .iter()
            .map(|n| format!("\"{n}\""))
            .collect::<Vec<_>>()
            .join(", ")
    };
    let selection = match &r.group {
        Some(group) => format!(
            "harness group \"{group}\" -> proxy model group \"{}\"",
            r.model
        ),
        None => format!("direct proxy model group \"{}\"", r.model),
    };
    let handoff = if !local {
        "not applicable (native route)".to_owned()
    } else if r.proxy_groups.is_empty() {
        format!(
            "{selection}; no litellm.groups configured; proxy configuration operator-owned and unchanged; existence unverified"
        )
    } else {
        format!(
            "{selection}; litellm.groups require proxy model groups {}; proxy configuration operator-owned and unchanged; existence unverified",
            quoted(&r.proxy_groups)
        )
    };
    let fallback = match &r.fallback {
        Some(native) => format!(
            "configured native {} ({}; key reference present), at most once and only when execution's TCP reachability check finds LiteLLM unreachable before launch; no fallback after the local attempt starts",
            native.runtime_model(),
            // D037 precedence: the agent's native model, else native.model.
            match native.sources.model {
                Source::Agent => "agent models.native",
                _ => "native.model",
            }
        ),
        None => "disabled".to_owned(),
    };
    let agent = match &r.agent {
        None => "none".to_owned(),
        Some(agent) => {
            use crate::agents::{Capacity, Effort, Permissions, Tool};
            let tools = agent
                .tools()
                .iter()
                .map(|t| match t {
                    Tool::Read => "read",
                    Tool::Search => "search",
                    Tool::Edit => "edit",
                    Tool::Execute => "execute",
                })
                .collect::<Vec<_>>();
            let emission = if !local {
                "not applicable (native route)"
            } else if r.no_sync {
                "skipped (no-sync)"
            } else {
                "managed project file (see planned changes)"
            };
            // Name grammar excludes quotes/controls; description/body omitted.
            format!(
                "\"{}\" (capacity {}; ceiling {}; tools [{}]; effort {}); OpenCode emission: {emission}; runtime: default agent with effective permissions {}{}",
                agent.name(),
                match agent.capacity() {
                    Capacity::Primary => "primary",
                    Capacity::Specialized => "specialized",
                    Capacity::Both => "both",
                },
                match agent.permissions() {
                    Permissions::Deny => "deny",
                    Permissions::ReadOnly => "read-only",
                    Permissions::Trusted => "trusted",
                },
                tools.join(", "),
                match agent.effort() {
                    Effort::Default => "default",
                    Effort::Low => "low",
                    Effort::Medium => "medium",
                    Effort::High => "high",
                    Effort::Max => "max",
                },
                if r.permissions == crate::config::Permissions::Deny {
                    "deny (invocation)".to_owned()
                } else {
                    format!("{:?}", crate::opencode::grantable(r))
                },
                match crate::opencode::supports(agent) {
                    Ok(()) => String::new(),
                    Err(error) => format!("; execution refused: {}", error.0),
                },
            )
        }
    };
    let prompt = match crate::opencode::prompt_supported(&r.prompt) {
        Ok(()) => String::new(),
        Err(error) => format!("; execution refused: {}", error.0),
    };
    // D040: path omitted; the runtime, not the harness, reads the file.
    let instructions = if r.instructions.is_some() {
        "project AGENTS.md (runtime-loaded)"
    } else {
        "none (no project AGENTS.md)"
    };
    // D043: arguments omitted; the program path is the pinned identity.
    let verification = match &r.verify {
        None => "none (no --verify)".to_owned(),
        Some(check) => format!(
            "check \"{}\": program {:?} pinned outside the project; {} arguments omitted; timeout {} seconds; runs after backend success only, never by preview; host privileges in the project directory",
            check.name,
            check.program,
            check.args.len(),
            check.timeout_secs
        ),
    };
    let health = if local {
        "LiteLLM reachability, alias availability"
    } else {
        "native provider reachability, model availability, authentication"
    };
    format!(
        "ah {} preview: valid resolved request; execution readiness unverified\n\
         project: {:?}\nconfig: {:?}\n\
         mode: {mode} ({}); route: {route}; fallback: {fallback}\n\
         runtime: OpenCode ACP; {runtime}\n\
         execution platform: {}\n\
         model: {} ({}); helper: same model\n\
         agent: {agent}\n\
         project instructions: {instructions}; skills/MCP/plugins/project config not inherited\n\
         proxy handoff: {handoff}\n\
         credentials: environment reference present (config); value and endpoint omitted\n\
         permissions: {scope} ({}); external tools/subagents/network tools disabled\n\
         timeout: {} seconds ({})\n\
         sync: {} ({}); planned changes: {changes}\n\
         prompt: validated; contents omitted{prompt}\n\
         verification: {verification}\n\
         health checks: none; {health}, runtime version and effective capabilities unverified\n\
         before execution: {before}; execution preflight verifies runtime routing/permissions\n",
        env!("CARGO_PKG_VERSION"),
        r.project,
        config,
        source(r.sources.mode),
        if cfg!(target_os = "macos") {
            "macOS (supported)"
        } else {
            "unsupported for coding runs; requires tested macOS"
        },
        r.runtime_model(),
        source(r.sources.model),
        source(r.sources.permissions),
        r.timeout_secs,
        source(r.sources.timeout),
        if !local {
            "native isolation; managed project config untouched"
        } else if r.no_sync {
            "no-sync; exact disk route validated"
        } else {
            "managed project sync"
        },
        if r.no_sync { "invocation" } else { "default" },
    )
}
