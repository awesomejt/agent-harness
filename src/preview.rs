//! Local-only diagnosis. Never execute a discovered binary or inspect its output.
use crate::{
    config::{Permissions, Resolved, Source},
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
        Source::Config => "config",
        Source::Default => "default",
    }
}

pub(crate) fn render(r: &Resolved, plan: &Plan, config: &Path) -> String {
    // Debug path formatting escapes control characters. No raw configuration,
    // endpoint, key value, prompt, or unmanaged settings are formatted here.
    let runtime = match discover_runtime() {
        Some(path) => format!("discovered {path:?}; version unverified (requires 1.18.30)"),
        None => "missing; install OpenCode 1.18.30 on an absolute PATH entry".into(),
    };
    let scope = match r.permissions {
        Permissions::Deny => "deny: no file/shell grants",
        Permissions::Trusted => "trusted: read/write/shell with host privileges; no OS sandbox",
    };
    let changes = plan.preview_changes();
    let changes = if changes.is_empty() {
        "none".into()
    } else {
        changes.join("; ")
    };
    format!(
        "ah {} preview: valid local plan; execution readiness unverified\n\
         project: {:?}\nconfig: {:?}\n\
         mode: local-only ({}); route: LiteLLM only; fallback: disabled\n\
         runtime: OpenCode ACP; {runtime}\n\
         execution platform: {}\n\
         model: ah-litellm/{} ({}); helper: same alias\n\
         credentials: environment reference present (config); value and endpoint omitted\n\
         permissions: {scope} ({}); external tools/subagents/network tools disabled\n\
         timeout: {} seconds ({})\n\
         sync: {} ({}); planned changes: {changes}\n\
         prompt: validated; contents omitted\n\
         health checks: none; LiteLLM reachability, alias availability, runtime version and effective capabilities unverified\n\
         before execution: ensure configured LiteLLM /v1 service is reachable and selected alias exists; execution preflight verifies runtime routing/permissions\n",
        env!("CARGO_PKG_VERSION"),
        r.project,
        config,
        source(r.sources.mode),
        if cfg!(target_os = "macos") {
            "macOS (supported)"
        } else {
            "unsupported for coding runs; requires tested macOS"
        },
        r.model,
        source(r.sources.model),
        source(r.sources.permissions),
        r.timeout_secs,
        source(r.sources.timeout),
        if r.no_sync {
            "no-sync; exact disk route validated"
        } else {
            "managed project sync"
        },
        if r.no_sync { "invocation" } else { "default" },
    )
}
