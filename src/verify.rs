//! Trusted verification gates (D043): operator-configured checks, authorized by
//! name on the invocation, resolved before any launch and run only after a
//! successful backend turn. Never a command taken from prompts or model output.
use crate::config::Invalid;
use serde::Deserialize;
use std::ffi::OsString;
use std::path::{Path, PathBuf};

pub const DEFAULT_TIMEOUT_SECS: u64 = 600;
pub const MAX_CHECKS: usize = 64;
pub const MAX_ARGS: usize = 64;
pub const MAX_ARG_BYTES: usize = 4096;

/// Runtime key names the harness itself passes to children; scrubbed as well.
const RESERVED_KEYS: [&str; 2] = ["AH_RUNTIME_API_KEY", "OPENCODE_API_KEY"];

/// Config entry `checks.NAME`: an argv vector, never a shell string.
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub(crate) struct Definition {
    argv: Vec<String>,
    timeout_secs: Option<u64>,
}

/// A resolved check. Its program is located before launch, so later edits to
/// the config file, PATH or project cannot change what runs.
pub struct Check {
    pub name: String,
    /// Absolute path as found (not canonicalized: multi-call proxies such as
    /// rustup dispatch on the invoked name).
    pub program: PathBuf,
    pub args: Vec<String>,
    pub timeout_secs: u64,
    /// Environment names removed from the check environment.
    pub(crate) scrub: Vec<String>,
}

pub(crate) fn validate_name(name: &str) -> Result<(), Invalid> {
    if name.is_empty()
        || name.len() > 64
        || !name.as_bytes()[0].is_ascii_lowercase()
        || name.ends_with('-')
        || name.contains("--")
        || !name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
    {
        return Err(Invalid(
            "check name requires 1–64 lowercase letters/digits with single hyphens",
        ));
    }
    Ok(())
}

impl Definition {
    pub(crate) fn validate(&self) -> Result<(), Invalid> {
        let Some(program) = self.argv.first() else {
            return Err(Invalid("check argv requires 1–64 arguments"));
        };
        if self.argv.len() > MAX_ARGS
            || self
                .argv
                .iter()
                .any(|a| a.len() > MAX_ARG_BYTES || a.contains('\0'))
        {
            return Err(Invalid(
                "check argv requires 1–64 arguments of at most 4096 bytes without NUL",
            ));
        }
        // A relative path would resolve against the project, which the agent
        // may have changed; require an absolute path or a PATH lookup.
        let relative = !program.starts_with('/') && program.contains('/');
        if program.is_empty() || relative {
            return Err(Invalid(
                "check program must be an absolute path or a bare name resolved on PATH",
            ));
        }
        if !(1..=86400).contains(&self.timeout_secs.unwrap_or(DEFAULT_TIMEOUT_SECS)) {
            return Err(Invalid("check timeout must be 1–86400 seconds"));
        }
        Ok(())
    }

    /// Locate the program on absolute PATH entries only and pin it outside
    /// the project. Local and read-only: nothing is executed.
    pub(crate) fn resolve(
        &self,
        name: &str,
        project: &Path,
        path: Option<OsString>,
        scrub: Vec<String>,
    ) -> Result<Check, Invalid> {
        let program = &self.argv[0];
        let found = if program.starts_with('/') {
            Some(PathBuf::from(program)).filter(|p| executable(p))
        } else {
            path.iter()
                .flat_map(std::env::split_paths)
                .filter(|dir| dir.is_absolute())
                .map(|dir| dir.join(program))
                .find(|p| executable(p))
        }
        .ok_or(Invalid(
            "check program is not an executable file (bare names use absolute PATH entries only)",
        ))?;
        outside(&found, project)?;
        let mut scrub = scrub;
        scrub.extend(RESERVED_KEYS.map(str::to_owned));
        Ok(Check {
            name: name.to_owned(),
            program: found,
            args: self.argv[1..].to_vec(),
            timeout_secs: self.timeout_secs.unwrap_or(DEFAULT_TIMEOUT_SECS),
            scrub,
        })
    }
}

fn normalize_lexical(path: &Path) -> PathBuf {
    let mut normalized = PathBuf::new();
    for component in path.components() {
        match component {
            std::path::Component::CurDir => {}
            std::path::Component::ParentDir => {
                normalized.pop();
            }
            c => normalized.push(c),
        }
    }
    normalized
}

/// Reject the program when it, or any symlink hop to it, lies inside the
/// project: the agent could replace or retarget that entry during the run.
fn outside(found: &Path, project: &Path) -> Result<(), Invalid> {
    const INSIDE: Invalid = Invalid(
        "check program must resolve outside the project; agent-editable programs are untrusted",
    );
    const UNAVAILABLE: Invalid = Invalid("check program is unavailable");

    if !found.is_absolute() {
        return Err(UNAVAILABLE);
    }

    let mut current = PathBuf::from("/");
    let mut remaining = found
        .strip_prefix("/")
        .map_err(|_| UNAVAILABLE)?
        .to_path_buf();
    let mut hops = 0;

    while !remaining.as_os_str().is_empty() {
        let (first, next_remaining) = {
            let mut components = remaining.components();
            let first = components
                .next()
                .ok_or(UNAVAILABLE)?
                .as_os_str()
                .to_os_string();
            let next_remaining = components.as_path().to_path_buf();
            (first, next_remaining)
        };
        remaining = next_remaining;

        if first == ".." {
            current.pop();
        } else if first != "." {
            current.push(first);
        }

        if current.starts_with(project) {
            return Err(INSIDE);
        }

        let metadata = std::fs::symlink_metadata(&current).map_err(|_| UNAVAILABLE)?;
        if metadata.file_type().is_symlink() {
            hops += 1;
            if hops > 40 {
                return Err(UNAVAILABLE);
            }
            let target = std::fs::read_link(&current).map_err(|_| UNAVAILABLE)?;
            let parent = current.parent().unwrap_or(Path::new("/"));
            let full_target = normalize_lexical(&if target.is_absolute() {
                target
            } else {
                parent.join(target)
            });

            if full_target.starts_with(project) {
                return Err(INSIDE);
            }
            if !full_target.is_absolute() {
                return Err(UNAVAILABLE);
            }

            current = PathBuf::from("/");
            remaining = full_target
                .strip_prefix("/")
                .map_err(|_| UNAVAILABLE)?
                .join(&remaining);
        }
    }

    if current.starts_with(project) {
        return Err(INSIDE);
    }
    let canonical = current.canonicalize().map_err(|_| UNAVAILABLE)?;
    if canonical.starts_with(project) {
        return Err(INSIDE);
    }

    Ok(())
}

fn executable(path: &Path) -> bool {
    path.metadata().is_ok_and(|m| {
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
}

/// Verification status, separate from the backend outcome (D043).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub(crate) enum Status {
    NotRun,
    Passed,
    Failed,
    TimedOut,
    Cancelled,
    Error,
}

impl Status {
    pub(crate) fn name(self) -> &'static str {
        match self {
            Status::NotRun => "not_run",
            Status::Passed => "passed",
            Status::Failed => "failed",
            Status::TimedOut => "timed_out",
            Status::Cancelled => "cancelled",
            Status::Error => "error",
        }
    }
}

/// The verification fields of the result record before any check runs.
pub(crate) fn pending(check: &Check) -> serde_json::Value {
    serde_json::json!({
        "check": check.name,
        "status": Status::NotRun.name(),
        "agent_outcome": null,
        "exit_code": null,
        "signal": null,
        "timeout_secs": check.timeout_secs,
        "duration_ms": null,
        "cleanup_confirmed": null,
    })
}

/// Run the gate after the backend outcome is final. Only a backend success
/// starts the check; the harness never repairs, retries or re-prompts.
#[cfg(target_os = "macos")]
pub(crate) async fn gate(
    check: &Check,
    project: &Path,
    exit: crate::config::Exit,
    cancelled: &tokio_util::sync::CancellationToken,
    progress: &crate::progress::Progress,
) -> crate::config::Exit {
    use crate::config::Exit;
    progress.verification(serde_json::json!({"agent_outcome": crate::progress::outcome(exit)}));
    if exit != Exit::Success {
        progress.event(format!(
            "verification check {} not run: backend turn did not succeed",
            check.name
        ));
        return exit;
    }
    if cancelled.is_cancelled() {
        progress.event(format!(
            "verification check {} not run: cancelled",
            check.name
        ));
        return Exit::Cancelled;
    }
    progress.emit(
        "verification.started",
        serde_json::json!({"check": check.name, "timeout_secs": check.timeout_secs}),
    );
    progress.event(format!(
        "verification check {} started (timeout {}s; configured program in the project directory with host privileges; output follows on stderr)",
        check.name, check.timeout_secs
    ));
    let started = std::time::Instant::now();
    let (status, code, signal, confirmed) = run(check, project, cancelled).await;
    let fields = serde_json::json!({
        "check": check.name,
        "status": status.name(),
        "exit_code": code,
        "signal": signal,
        "duration_ms": started.elapsed().as_millis() as u64,
        "cleanup_confirmed": confirmed,
    });
    progress.verification(fields.clone());
    progress.emit("verification.finished", fields);
    progress.event(format!(
        "verification check {} {}{}",
        check.name,
        status.name(),
        match (code, signal) {
            (Some(code), _) => format!(" (exit {code})"),
            (_, Some(signal)) => format!(" (signal {signal})"),
            _ => String::new(),
        }
    ));
    if status != Status::Passed {
        progress.recovery("no automatic retry, repair or fallback after verification");
    }
    if confirmed == Some(false) {
        progress.event(
            "uncertain verification cleanup; check processes may still be running in the project",
        );
        return Exit::Uncertain;
    }
    match status {
        Status::Passed => Exit::Success,
        Status::Cancelled => Exit::Cancelled,
        _ => Exit::Failed,
    }
}

/// Spawn without a shell in its own process group: stdin closed, stdout and
/// stderr both to the harness stderr (stdout stays machine-only). Timeout or
/// cancellation terminates the group; every exit confirms group absence.
#[cfg(target_os = "macos")]
async fn run(
    check: &Check,
    project: &Path,
    cancelled: &tokio_util::sync::CancellationToken,
) -> (Status, Option<i32>, Option<i32>, Option<bool>) {
    use std::os::fd::AsFd;
    use std::os::unix::process::ExitStatusExt;
    let output = || {
        std::io::stderr()
            .as_fd()
            .try_clone_to_owned()
            .map(std::process::Stdio::from)
    };
    let (Ok(stdout), Ok(stderr)) = (output(), output()) else {
        return (Status::Error, None, None, None);
    };
    let mut command = tokio::process::Command::new(&check.program);
    command.args(&check.args).current_dir(project);
    for name in &check.scrub {
        command.env_remove(name);
    }
    let Ok(mut child) = crate::process::OwnedChild::spawn_output(&mut command, stdout, stderr)
    else {
        return (Status::Error, None, None, None);
    };
    // Biased toward the exit: a check that finished as the bound expired keeps
    // its real status.
    let mut waited = tokio::select! {
        biased;
        status = child.child.wait() => Some(status),
        () = tokio::time::sleep(std::time::Duration::from_secs(check.timeout_secs)) => None,
        () = cancelled.cancelled() => None,
    };
    if waited.is_none()
        && let Ok(Some(status)) = child.child.try_wait()
    {
        waited = Some(Ok(status));
    }
    let stopped_by_signal = cancelled.is_cancelled();
    // Lingering descendants are terminated even after a normal exit.
    let confirmed = child.cleanup().await;
    let (status, code, signal) = match waited {
        Some(Ok(status)) => (
            if status.success() {
                Status::Passed
            } else {
                Status::Failed
            },
            status.code(),
            status.signal(),
        ),
        Some(Err(_)) => (Status::Error, None, None),
        None if stopped_by_signal => (Status::Cancelled, None, None),
        None => (Status::TimedOut, None, None),
    };
    (status, code, signal, Some(confirmed))
}
