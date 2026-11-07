//! Local/native orchestration with at most one local-first fallback; input validation always precedes project writes.
use crate::{
    config::{Config, Exit, Invocation, Mode},
    project_config::Plan,
};
use std::ffi::OsString;

pub fn run(args: Vec<OsString>) -> Exit {
    let progress = crate::progress::Progress::new(crate::config::machine_output(&args));
    progress.emit(
        "run.started",
        serde_json::json!({"harness_version": env!("CARGO_PKG_VERSION")}),
    );
    let exit = execute(args, &progress);
    progress.finish(exit)
}

fn execute(args: Vec<OsString>, progress: &crate::progress::Progress) -> Exit {
    let cwd = match std::env::current_dir() {
        Ok(cwd) => cwd,
        Err(_) => {
            progress.reject("current directory is unavailable");
            return Exit::Invalid;
        }
    };
    let resolved: Result<_, crate::config::Invalid> = (|| {
        let invocation = Invocation::parse(args, &cwd)?;
        let config_path = invocation.config_path();
        let config = Config::open(&config_path)?;
        let request = invocation.resolve(
            config,
            |name| std::env::var_os(name),
            std::io::stdin().lock(),
        )?;
        Ok((request, config_path))
    })();
    let (request, config_path) = match resolved {
        Ok(request) => request,
        Err(error) => {
            progress.event(format!("{}; use --help", error.0));
            progress.reason(error.0);
            if error.0 == crate::config::MISSING_KEY {
                progress.event(
                    "set the environment variable named by the selected route api_key_env before retrying",
                );
            }
            return Exit::Invalid;
        }
    };
    if let Some(check) = &request.verify {
        progress.verification(crate::verify::pending(check));
    }
    if !request.preview
        && let Err(error) = supported(&request)
    {
        progress.reject(error.0);
        return Exit::Invalid;
    }
    if request.preview {
        return match prepare_plan(&request) {
            Ok(plan) => {
                use std::io::Write;
                let report = crate::preview::render(&request, plan.as_ref(), &config_path);
                if std::io::stdout()
                    .lock()
                    .write_all(report.as_bytes())
                    .is_ok()
                {
                    Exit::Success
                } else {
                    Exit::Failed
                }
            }
            Err(error) => {
                progress.reject(error.0);
                Exit::Invalid
            }
        };
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = request;
        progress.reject("coding runs currently support tested macOS only");
        Exit::Invalid
    }
    #[cfg(target_os = "macos")]
    {
        let runtime = match tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
        {
            Ok(runtime) => runtime,
            Err(_) => return Exit::Failed,
        };
        runtime.block_on(async {
            let signals = crate::runtime::Signals::watch();
            launch(&request, signals.token(), progress).await
        })
    }
}

/// Refuse a required capability the runtime cannot enforce (D038) or a
/// command prompt (D040) before any runtime, network check or project write;
/// both attempts share them. Sequences apply it to every step before step 1.
pub(crate) fn supported(request: &crate::config::Resolved) -> Result<(), crate::config::Invalid> {
    crate::claude::supported(request)?;
    // Effort maps on Claude Code (D050); OpenCode still runs only default.
    if let Some(agent) = &request.agent
        && request.runtime == crate::config::RuntimeKind::OpenCode
    {
        crate::opencode::supports(agent)?;
    }
    crate::opencode::prompt_supported(&request.prompt)
}

/// One validated request through route policy, the D034 fallback and the D043
/// gate, under its own deadline. A sequence step is exactly one such call.
#[cfg(target_os = "macos")]
pub(crate) async fn launch(
    request: &crate::config::Resolved,
    cancelled: tokio_util::sync::CancellationToken,
    progress: &crate::progress::Progress,
) -> Exit {
    let deadline =
        tokio::time::Instant::now() + std::time::Duration::from_secs(request.timeout_secs);
    let plan = match prepare_plan(request) {
        Ok(plan) => plan,
        Err(error) => {
            progress.reject(error.0);
            return Exit::Invalid;
        }
    };
    if tokio::time::Instant::now() >= deadline {
        return Exit::Cancelled;
    }
    let exit = match request.fallback.as_deref() {
        None => {
            let label = if request.mode == Mode::LocalOnly {
                "local-only"
            } else {
                "cloud-only"
            };
            attempt(
                request,
                plan,
                1,
                label,
                deadline,
                cancelled.clone(),
                progress,
            )
            .await
        }
        Some(native) => {
            coordinate(request, native, plan, deadline, cancelled.clone(), progress).await
        }
    };
    // D043: the check follows the final backend outcome, whichever attempt
    // produced it, with its own bound.
    match &request.verify {
        Some(check) => {
            crate::verify::gate(check, &request.project, exit, &cancelled, progress).await
        }
        None => exit,
    }
}

/// Local-first (D031/D034): the only eligible evidence is a pre-submission
/// LiteLLM transport failure, established before any runtime, private state or
/// project write exists. Once the local attempt starts, every outcome is final.
#[cfg(target_os = "macos")]
async fn coordinate(
    request: &crate::config::Resolved,
    native: &crate::config::Resolved,
    plan: Option<Plan>,
    deadline: tokio::time::Instant,
    cancelled: tokio_util::sync::CancellationToken,
    progress: &crate::progress::Progress,
) -> Exit {
    use crate::probe::Reachability;
    use crate::recovery::{Decision, Evidence, Failure, Submission};
    let first = progress.attempt(1);
    first.start(describe(request, "local-first"));
    first.event(
        "local-first LiteLLM reachability check (TCP connect only; no request or credential sent)",
    );
    let Some(api_base) = request.api_base.as_deref() else {
        progress.reject("local-first requires a LiteLLM endpoint");
        return Exit::Invalid;
    };
    let failure = match crate::probe::litellm(api_base, deadline, &cancelled).await {
        Reachability::Reachable => {
            first.event("LiteLLM endpoint reachable; later failures stop without fallback");
            progress
                .recovery("no automatic retry; fallback not eligible after the reachability check");
            return attempt(
                request,
                plan,
                1,
                "local-first",
                deadline,
                cancelled,
                progress,
            )
            .await;
        }
        Reachability::Unreachable => Failure::Transport,
        Reachability::Unknown => Failure::Unknown,
        Reachability::Stopped if cancelled.is_cancelled() => Failure::Cancelled,
        Reachability::Stopped => Failure::Deadline,
    };
    // Cancellation or deadline arriving after classification still takes
    // precedence (D031), for both the decision and the exit code.
    let stopped = cancelled.is_cancelled() || tokio::time::Instant::now() >= deadline;
    let failure = match failure {
        _ if cancelled.is_cancelled() => Failure::Cancelled,
        _ if stopped => Failure::Deadline,
        failure => failure,
    };
    let decision = crate::recovery::decide(&Evidence {
        mode: crate::recovery::Mode::LocalFirst,
        failure,
        // No runtime was launched, so nothing was submitted and no created
        // resource awaits cleanup; no project write has occurred.
        submission: Submission::NotAttempted,
        cleanup_confirmed: true,
        cancelled_or_expired: stopped,
        // Static target validation and key presence precede launch; attempt 2
        // still runs the full native preflight before any prompt.
        configured_target_validated: native.mode == Mode::CloudOnly && native.fallback.is_none(),
        constraints_preserved: native.project == request.project
            && native.permissions == request.permissions
            && native.agent.as_ref().map(crate::agents::Agent::name)
                == request.agent.as_ref().map(crate::agents::Agent::name)
            && crate::opencode::effective(native) == crate::opencode::effective(request)
            && native.instructions == request.instructions
            && native.timeout_secs == request.timeout_secs
            && native.prompt == request.prompt,
        prior_fallbacks: 0,
    });
    if decision == Decision::Stop {
        first.event(match failure {
            Failure::Cancelled | Failure::Deadline => {
                "stopped during reachability check; no prompt submitted"
            }
            _ => "reachability check inconclusive; no prompt submitted; no fallback",
        });
        progress.recovery("no automatic retry or fallback");
        return match failure {
            Failure::Cancelled | Failure::Deadline => Exit::Cancelled,
            _ => Exit::Failed,
        };
    }
    first.event(
        "LiteLLM endpoint unreachable before submission; no runtime launched; no project changes",
    );
    progress.recovery("fallback=attempt 2 (native) after pre-submission LiteLLM transport failure; no further retry");
    progress.fallback();
    progress
        .attempt(2)
        .event("fallback from attempt=1; fresh runtime state and grants; shared deadline");
    attempt(
        native,
        None,
        2,
        "local-first fallback",
        deadline,
        cancelled,
        progress,
    )
    .await
}

#[cfg(target_os = "macos")]
async fn attempt(
    request: &crate::config::Resolved,
    plan: Option<Plan>,
    number: u8,
    label: &str,
    deadline: tokio::time::Instant,
    cancelled: tokio_util::sync::CancellationToken,
    progress: &crate::progress::Progress,
) -> Exit {
    let progress = &progress.attempt(number);
    progress.start(describe(request, label));
    if request.runtime == crate::config::RuntimeKind::Claude {
        return crate::claude::attempt(request, label, deadline, cancelled, progress).await;
    }
    let mut adapter =
        match crate::runtime::Runtime::new(request, deadline, cancelled, progress.clone()) {
            Ok(adapter) => adapter,
            Err(exit) => return exit,
        };
    let exit = async {
        if let Err(exit) = crate::worktree::report(&request.project, deadline, progress).await {
            return exit;
        }
        if adapter.cancelled.is_cancelled() || tokio::time::Instant::now() >= deadline {
            return Exit::Cancelled;
        }
        // Preflight consumes an isolated routing snapshot; no project code or
        // plugins execute. Only then persist the already validated plan.
        if let Err(exit) = adapter.preflight(request).await {
            progress.event(format!(
                "preflight failed (requires OpenCode {} and exact isolated routing/permissions)",
                crate::opencode::VERSION
            ));
            if exit == Exit::Invalid {
                progress.reason(
                    "preflight failed: OpenCode version, isolated routing, permissions or agent did not match",
                );
            }
            return exit;
        }
        if tokio::time::Instant::now() >= adapter.deadline {
            return Exit::Cancelled;
        }
        if let Some(plan) = plan
            && let Err(error) = plan.apply()
        {
            progress.reject(error.0);
            return Exit::Invalid;
        }
        tokio::task::yield_now().await;
        if adapter.cancelled.is_cancelled() || tokio::time::Instant::now() >= adapter.deadline {
            return Exit::Cancelled;
        }
        progress.event(format!(
            "{label} via OpenCode {}; model {}{}; permissions {:?}{}",
            crate::opencode::VERSION,
            request.runtime_model(),
            request
                .group
                .as_ref()
                .map(|g| format!(" (group {g})"))
                .unwrap_or_default(),
            request.permissions,
            request
                .agent
                .as_ref()
                .map(|a| format!(
                    "; agent {} (capacity {}; tools {:?}; enforced kinds {:?})",
                    a.name(),
                    match a.capacity() {
                        crate::agents::Capacity::Primary => "primary",
                        crate::agents::Capacity::Specialized => "specialized",
                        crate::agents::Capacity::Both => "both",
                    },
                    a.tools(),
                    crate::opencode::grantable(request)
                ))
                .unwrap_or_default()
        ));
        crate::acp::run(&adapter, request).await
    }
    .await;
    let removed = adapter.cleanup_private_home().await;
    progress.note(serde_json::json!({"runtime_state_removed": removed}));
    if !removed {
        progress.event(
            "uncertain private runtime cleanup; inspect ah-runtime-* under the system temporary directory before manual removal",
        );
        Exit::Uncertain
    } else {
        exit
    }
}

/// Public attempt description (D039); fixed harness names, never paths,
/// endpoints, prompts or credential references.
#[cfg(target_os = "macos")]
fn describe(request: &crate::config::Resolved, label: &str) -> serde_json::Value {
    serde_json::json!({
        "route": label,
        "runtime": match request.runtime {
            crate::config::RuntimeKind::OpenCode => "opencode",
            crate::config::RuntimeKind::Claude => "claude",
        },
        "runtime_version": match request.runtime {
            crate::config::RuntimeKind::OpenCode => crate::opencode::VERSION,
            crate::config::RuntimeKind::Claude => crate::claude::VERSION,
        },
        "model": request.runtime_model(),
        "group": request.group,
        "permissions": match request.permissions {
            crate::config::Permissions::Deny => "deny",
            crate::config::Permissions::Trusted => "trusted",
        },
        "agent": request.agent.as_ref().map(|a| serde_json::json!({
            "name": a.name(),
            "capacity": match a.capacity() {
                crate::agents::Capacity::Primary => "primary",
                crate::agents::Capacity::Specialized => "specialized",
                crate::agents::Capacity::Both => "both",
            },
        })),
    })
}

pub(crate) fn prepare_plan(
    request: &crate::config::Resolved,
) -> Result<Option<Plan>, crate::config::Invalid> {
    match request.mode {
        Mode::LocalOnly => Plan::prepare(request).map(Some),
        Mode::CloudOnly => Ok(None),
    }
}
