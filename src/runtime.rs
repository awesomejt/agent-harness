//! Local and native OpenCode 2.3.0 isolation and effective capability preflight.
use crate::{
    config::{Exit, Mode, Resolved},
    process::OwnedChild,
};
use serde_json::Value;
use std::{ffi::OsString, path::Path, time::Duration};
use tokio::{io::AsyncReadExt, process::Command};

pub(crate) struct Runtime {
    config: Value,
    home: PrivateHome,
    pub progress: crate::progress::Progress,
    pub deadline: tokio::time::Instant,
    pub cancelled: tokio_util::sync::CancellationToken,
    env: Vec<(OsString, OsString)>,
    pub executable: std::path::PathBuf,
    #[cfg(test)]
    go_candidate: bool,
}

impl Runtime {
    pub fn new(
        request: &Resolved,
        deadline: tokio::time::Instant,
        cancelled: tokio_util::sync::CancellationToken,
        progress: crate::progress::Progress,
    ) -> Result<Self, Exit> {
        let executable = crate::preview::discover_runtime("opencode").ok_or_else(|| {
            progress.event(format!(
                "OpenCode missing: install {} on an absolute PATH entry",
                crate::opencode::VERSION
            ));
            progress.reason("OpenCode missing on an absolute PATH entry");
            Exit::Invalid
        })?;
        let key = request
            .api_key_env
            .as_ref()
            .and_then(std::env::var_os)
            .filter(|s| !s.is_empty())
            .ok_or_else(|| {
                progress.reject(crate::config::MISSING_KEY);
                Exit::Invalid
            })?;
        let home = PrivateHome::new().map_err(|_| Exit::Failed)?;
        let config = crate::opencode::config(request);
        let mut env: Vec<(OsString, OsString)> = vec![
            ("HOME".into(), home.path().into()),
            (
                "PATH".into(),
                std::env::var_os("PATH").unwrap_or_else(|| "/usr/bin:/bin".into()),
            ),
            ("OPENCODE_CONFIG_CONTENT".into(), config.to_string().into()),
        ];
        for kind in ["CONFIG", "DATA", "CACHE", "STATE"] {
            env.push((
                format!("XDG_{kind}_HOME").into(),
                home.path().join(kind).into(),
            ));
        }
        // 2.3.0 no longer recognizes OPENCODE_DISABLE_DEFAULT_PLUGINS; the
        // `plugins: []` document and the sources check stand in for it.
        for name in [
            "OPENCODE_DISABLE_MODELS_FETCH",
            "OPENCODE_DISABLE_AUTOUPDATE",
            "OPENCODE_DISABLE_PROJECT_CONFIG",
        ] {
            env.push((name.into(), "true".into()));
        }
        // Copy only the value to a reserved name: arbitrary user-selected names
        // such as DYLD_INSERT_LIBRARIES must never become runtime controls.
        // A provider-recognized env key activates a Console integration in 2.3.0,
        // including remote instructions/skills. Supply inference credentials only
        // through the explicit provider setting in our isolated document (D092).
        env.push(("AH_RUNTIME_API_KEY".into(), key));
        Ok(Self {
            config,
            home,
            progress,
            cancelled,
            env,
            executable,
            deadline,
            #[cfg(test)]
            go_candidate: false,
        })
    }

    #[cfg(test)]
    fn new_go_candidate(
        request: &Resolved,
        deadline: tokio::time::Instant,
        cancelled: tokio_util::sync::CancellationToken,
        progress: crate::progress::Progress,
    ) -> Result<Self, Exit> {
        let mut runtime = Self::new(request, deadline, cancelled, progress)?;
        runtime.go_candidate = true;
        runtime.config["model"]["providerID"] = serde_json::json!("opencode-go");
        runtime.config["agents"]["title"]["model"] = runtime.config["model"].clone();
        runtime.config["policies"][1]["resource"] = serde_json::json!("opencode-go");
        runtime.config["providers"] = serde_json::json!({"opencode-go": {
            "settings": {"apiKey": "{env:AH_RUNTIME_API_KEY}"}
        }});
        let entry = runtime
            .env
            .iter_mut()
            .find(|(name, _)| name == "OPENCODE_CONFIG_CONTENT")
            .ok_or(Exit::Invalid)?;
        entry.1 = runtime.config.to_string().into();
        Ok(runtime)
    }

    pub fn target(&self, request: &Resolved) -> String {
        #[cfg(test)]
        if self.go_candidate {
            return format!("opencode-go/{}", request.model);
        }
        request.runtime_model()
    }

    #[cfg(test)]
    pub fn is_go_candidate(&self) -> bool {
        self.go_candidate
    }
    pub fn command(&self, project: &Path, args: &[&str]) -> Command {
        let mut command = Command::new(&self.executable);
        command
            .args(args)
            .current_dir(project)
            .env_clear()
            .envs(self.env.iter().cloned());
        command
    }
    async fn inspect(&self, project: &Path, args: &[&str]) -> Result<Vec<u8>, Exit> {
        self.progress.event("preflight check started");
        let mut owned =
            OwnedChild::spawn(&mut self.command(project, args)).map_err(|_| Exit::Failed)?;
        let mut bytes = Vec::new();
        let mut stdout = owned.child.stdout.take().unwrap();
        let result = tokio::select! {
            value = tokio::time::timeout_at(self.deadline.min(tokio::time::Instant::now() + Duration::from_secs(30)), async {
                (&mut stdout).take(1_048_577).read_to_end(&mut bytes).await.map_err(|_| Exit::Failed)?;
                if bytes.len() > 1_048_576 { return Err(Exit::Invalid); }
                let status = owned.child.wait().await.map_err(|_| Exit::Failed)?;
                if !status.success() { return Err(Exit::Invalid); }
                Ok(())
            }) => value.unwrap_or(Err(Exit::Cancelled)),
            _ = self.cancelled.cancelled() => Err(Exit::Cancelled),
        };
        if !owned.cleanup().await {
            return Err(Exit::Uncertain);
        }
        result?;
        Ok(bytes)
    }
    /// Every inspection runs `--standalone`: without it 2.x attaches to the
    /// user's shared background service and its configuration.
    pub async fn preflight(&self, request: &Resolved) -> Result<String, Exit> {
        let version = self
            .inspect(&request.project, &["--version", "--standalone"])
            .await?;
        let detected_version = crate::opencode::parse_supported_version(&version)
            .ok_or(Exit::Invalid)?
            .to_owned();
        let parse =
            |bytes: Vec<u8>| serde_json::from_slice::<Value>(&bytes).map_err(|_| Exit::Invalid);
        let sources = parse(
            self.inspect(&request.project, &["debug", "config", "--standalone"])
                .await?,
        )?;
        crate::opencode::validate_sources(&self.config, &sources, self.home.path())
            .map_err(|_| Exit::Invalid)?;
        if request.mode == Mode::CloudOnly {
            let bytes = self
                .inspect(&request.project, &["models", "--standalone"])
                .await?;
            let models = std::str::from_utf8(&bytes).map_err(|_| Exit::Invalid)?;
            #[cfg(test)]
            if self.go_candidate {
                crate::opencode::validate_catalog_for(&self.target(request), "opencode-go", models)
                    .map_err(|_| Exit::Invalid)?;
            } else {
                crate::opencode::validate_catalog(request, models).map_err(|_| Exit::Invalid)?;
            }
            #[cfg(not(test))]
            crate::opencode::validate_catalog(request, models).map_err(|_| Exit::Invalid)?;
        }
        let agents = parse(
            self.inspect(&request.project, &["debug", "agents", "--standalone"])
                .await?,
        )?;
        #[cfg(test)]
        if self.go_candidate {
            crate::opencode::validate_agents_for(request, &agents, "opencode-go", true)
                .map_err(|_| Exit::Invalid)?;
        } else {
            crate::opencode::validate_agents(request, &agents).map_err(|_| Exit::Invalid)?;
        }
        #[cfg(not(test))]
        crate::opencode::validate_agents(request, &agents).map_err(|_| Exit::Invalid)?;
        Ok(detected_version)
    }

    /// Remove runtime-owned state before reporting the final outcome. A plain
    /// worker thread keeps recursive filesystem cleanup outside Tokio's worker
    /// pool; dropping its handle after the timeout does not make runtime
    /// shutdown wait for an unbounded filesystem operation.
    pub async fn cleanup_private_home(&mut self) -> bool {
        let Some(path) = self.home.take() else {
            return true;
        };
        let (send, receive) = tokio::sync::oneshot::channel();
        let worker = std::thread::Builder::new()
            .name("ah-private-home-cleanup".into())
            .spawn(move || {
                fn confirm_absent(path: &Path) -> std::io::Result<()> {
                    match std::fs::symlink_metadata(path) {
                        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(()),
                        Ok(_) => Err(std::io::Error::new(
                            std::io::ErrorKind::AlreadyExists,
                            "private runtime directory remains",
                        )),
                        Err(error) => Err(error),
                    }
                }
                let result = match std::fs::remove_dir_all(&path) {
                    Ok(()) => confirm_absent(&path),
                    Err(error) if error.kind() == std::io::ErrorKind::NotFound => {
                        confirm_absent(&path)
                    }
                    Err(error) => Err(error),
                };
                let _ = send.send(result);
            });
        if worker.is_err() {
            // No removal was attempted. Do not fall back to recursive I/O on
            // the supervisor: it has no wall-clock bound. The caller reports
            // uncertainty and directs the user to inspect retained state.
            return false;
        }
        matches!(
            tokio::time::timeout(Duration::from_secs(2), receive).await,
            Ok(Ok(Ok(())))
        )
    }
}
/// One invocation-wide SIGINT/SIGTERM watcher shared by every linked attempt,
/// so a signal between attempts cannot be lost.
pub(crate) struct Signals(
    tokio::task::JoinHandle<()>,
    tokio_util::sync::CancellationToken,
);
impl Signals {
    pub fn watch() -> Self {
        let cancelled = tokio_util::sync::CancellationToken::new();
        let signal_cancel = cancelled.clone();
        Self(
            tokio::spawn(async move {
                tokio::select! { _ = tokio::signal::ctrl_c() => {}, _ = terminate() => {} }
                signal_cancel.cancel();
            }),
            cancelled,
        )
    }
    pub fn token(&self) -> tokio_util::sync::CancellationToken {
        self.1.clone()
    }
}
impl Drop for Signals {
    fn drop(&mut self) {
        self.0.abort();
    }
}

pub(crate) async fn terminate() {
    if let Ok(mut signal) =
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
    {
        signal.recv().await;
    } else {
        std::future::pending::<()>().await;
    }
}

/// mkdtemp creates a fresh mode-0700 directory without predictable-name races.
struct PrivateHome(Option<std::path::PathBuf>);
impl PrivateHome {
    fn new() -> std::io::Result<Self> {
        use std::os::unix::ffi::{OsStrExt, OsStringExt};
        let template = std::env::temp_dir().join("ah-runtime-XXXXXX");
        let mut bytes =
            std::ffi::CString::new(template.as_os_str().as_bytes())?.into_bytes_with_nul();
        if unsafe { libc::mkdtemp(bytes.as_mut_ptr().cast()) }.is_null() {
            return Err(std::io::Error::last_os_error());
        }
        bytes.pop();
        Ok(Self(Some(OsString::from_vec(bytes).into())))
    }
    fn path(&self) -> &Path {
        self.0.as_deref().expect("private home is active")
    }
    fn take(&mut self) -> Option<std::path::PathBuf> {
        self.0.take()
    }
}
impl Drop for PrivateHome {
    fn drop(&mut self) {
        if let Some(path) = self.0.take() {
            // Constructor failures still get best-effort RAII cleanup. Active
            // runs use Runtime::cleanup_private_home so failure affects outcome.
            let _ = std::fs::remove_dir_all(path);
        }
    }
}

#[cfg(test)]
mod go_candidate_fixture {
    use super::*;
    use crate::config::{Config, Invocation};

    // This entry point is deliberately fake-only. It cannot be used for the
    // reviewed live gate: both executable identity and credential are fixed.
    #[test]
    #[ignore = "invoked only by the disposable Go candidate fixture runner"]
    fn synthetic_acp() {
        let project = std::path::PathBuf::from(std::env::var_os("AH_P710_PROJECT").unwrap());
        assert_eq!(std::env::var("P710_KEY").as_deref(), Ok("SECRET_SENTINEL"));
        let executable = crate::preview::discover_runtime("opencode").unwrap();
        let fake = Path::new(env!("CARGO_MANIFEST_DIR")).join("scripts/tests/fake_opencode.py");
        assert_eq!(
            executable.canonicalize().unwrap(),
            fake.canonicalize().unwrap()
        );
        let input = br#"{"version":1,"mode":"cloud-only","native":{"target":"opencode","model":"fixture","api_key_env":"P710_KEY"}}"#;
        let request = Invocation::parse(
            vec![
                "single".into(),
                "fixture prompt".into(),
                "--project".into(),
                project.into_os_string(),
            ],
            Path::new("/"),
        )
        .unwrap()
        .resolve(
            Config::read(&input[..]).unwrap(),
            |name| std::env::var_os(name),
            &b""[..],
        )
        .unwrap();
        let executor = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        executor.block_on(async {
            let deadline = tokio::time::Instant::now() + Duration::from_secs(20);
            let mut runtime = Runtime::new_go_candidate(
                &request,
                deadline,
                tokio_util::sync::CancellationToken::new(),
                crate::progress::Progress::new(false),
            )
            .unwrap();
            let outcome = match runtime.preflight(&request).await {
                Ok(_) => crate::acp::run(&runtime, &request).await,
                Err(exit) => exit,
            };
            assert!(runtime.cleanup_private_home().await);
            println!("P710_RESULT={}", outcome as u8);
        });
    }

    // Not run by the fixture suite. Execute only after setup review and the
    // operator's fresh account attestation; never force allowance exhaustion.
    #[test]
    #[ignore = "operator-gated Go live acceptance; see P7.10 setup evidence"]
    fn live_acp() {
        assert_eq!(
            std::env::var("AH_P710_LIVE").as_deref(),
            Ok("operator-attested")
        );
        let key = std::env::var_os("P710_KEY")
            .filter(|s| !s.is_empty())
            .expect("P710_KEY is required");
        assert_ne!(key, "SECRET_SENTINEL");
        let executable = crate::preview::discover_runtime("opencode").unwrap();
        let installed = Path::new("/opt/homebrew/bin/opencode");
        assert_eq!(
            executable.canonicalize().unwrap(),
            installed.canonicalize().unwrap()
        );
        let mut project = PrivateHome::new().unwrap();
        let input = br#"{"version":1,"mode":"cloud-only","native":{"target":"opencode","model":"beam-free","api_key_env":"P710_KEY"}}"#;
        let request = Invocation::parse(
            vec![
                "single".into(),
                "Reply with OK.".into(),
                "--project".into(),
                project.path().into(),
            ],
            Path::new("/"),
        )
        .unwrap()
        .resolve(
            Config::read(&input[..]).unwrap(),
            |name| std::env::var_os(name),
            &b""[..],
        )
        .unwrap();
        let executor = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap();
        executor.block_on(async {
            let deadline = tokio::time::Instant::now() + Duration::from_secs(90);
            let signals = Signals::watch();
            let mut runtime = Runtime::new_go_candidate(&request, deadline, signals.token(), crate::progress::Progress::new(false)).unwrap();
            let outcome = match runtime.preflight(&request).await {
                Ok(version) => {
                    eprintln!("Go candidate preflight passed: OpenCode {version}, opencode-go/beam-free, deny");
                    crate::acp::run(&runtime, &request).await
                }
                Err(exit) => exit,
            };
            let outcome = if outcome == Exit::Success && runtime.progress.final_line().is_none() {
                eprintln!("Go candidate returned an empty response; acceptance not met");
                Exit::Failed
            } else {
                outcome
            };
            assert!(runtime.cleanup_private_home().await);
            let path = project.take().unwrap();
            std::fs::remove_dir_all(path).expect("remove disposable project");
            println!("P710_LIVE_RESULT={}", outcome as u8);
        });
    }
}
