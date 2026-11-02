//! First-slice OpenCode 1.18.30 isolation and effective capability preflight.
use crate::{
    config::{Exit, Permissions, Resolved},
    process::OwnedChild,
    project_config::Plan,
};
use serde_json::{Value, json};
use std::{ffi::OsString, path::Path, time::Duration};
use tokio::{io::AsyncReadExt, process::Command};

pub(crate) struct Runtime {
    _home: PrivateHome,
    pub progress: crate::progress::Progress,
    pub deadline: tokio::time::Instant,
    pub cancelled: tokio_util::sync::CancellationToken,
    signals: tokio::task::JoinHandle<()>,
    env: Vec<(OsString, OsString)>,
    pub executable: std::path::PathBuf,
}

pub(crate) fn profile(policy: Permissions, home: &Path) -> (Value, Value) {
    let mut permissions = json!({"*":"deny", "external_directory": {
        "*":"deny", home.join("DATA/opencode/tool-output/*").to_string_lossy().as_ref():"deny"
    }});
    let mut tools = json!({"*":false});
    if policy == Permissions::Trusted {
        for name in ["read", "glob", "grep", "edit", "apply_patch", "bash"] {
            permissions[name] = json!("ask");
        }
        for name in [
            "read",
            "glob",
            "grep",
            "edit",
            "write",
            "apply_patch",
            "bash",
        ] {
            tools[name] = json!(true);
        }
    }
    if policy == Permissions::Trusted {
        permissions["external_directory"]["*"] = json!("ask");
    }
    (permissions, tools)
}
impl Runtime {
    pub fn new(
        request: &Resolved,
        plan: &Plan,
        deadline: tokio::time::Instant,
        progress: crate::progress::Progress,
    ) -> Result<Self, Exit> {
        let executable = std::env::var_os("PATH")
            .into_iter()
            .flat_map(|p| std::env::split_paths(&p).collect::<Vec<_>>())
            .filter(|p| p.is_absolute())
            .map(|p| p.join("opencode"))
            .find(|p| {
                use std::os::unix::fs::PermissionsExt;
                p.metadata()
                    .is_ok_and(|m| m.is_file() && m.permissions().mode() & 0o111 != 0)
            })
            .and_then(|p| p.canonicalize().ok())
            .ok_or(Exit::Invalid)?;
        let home = PrivateHome::new().map_err(|_| Exit::Failed)?;
        let mut config = plan.runtime_routing();
        config["provider"]["ah-litellm"]["options"]["apiKey"] = json!("{env:AH_RUNTIME_API_KEY}");
        let (permissions, tools) = profile(request.permissions, home.path());
        for (key, value) in [
            ("permission", permissions),
            ("tools", tools),
            ("autoupdate", json!(false)),
            ("share", json!("disabled")),
            ("plugin", json!([])),
            ("mcp", json!({})),
            ("default_agent", json!("build")),
        ] {
            config[key] = value;
        }
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
        for name in [
            "OPENCODE_DISABLE_MODELS_FETCH",
            "OPENCODE_DISABLE_DEFAULT_PLUGINS",
            "OPENCODE_DISABLE_AUTOUPDATE",
            "OPENCODE_DISABLE_PROJECT_CONFIG",
        ] {
            env.push((name.into(), "true".into()));
        }
        let key = std::env::var_os(&request.api_key_env)
            .filter(|s| !s.is_empty())
            .ok_or(Exit::Invalid)?;
        // Copy only the value to a reserved name: arbitrary user-selected names
        // such as DYLD_INSERT_LIBRARIES must never become runtime controls.
        env.push(("AH_RUNTIME_API_KEY".into(), key));
        let cancelled = tokio_util::sync::CancellationToken::new();
        let signal_cancel = cancelled.clone();
        let signals = tokio::spawn(async move {
            tokio::select! { _ = tokio::signal::ctrl_c() => {}, _ = terminate() => {} }
            signal_cancel.cancel();
        });
        Ok(Self {
            _home: home,
            progress,
            cancelled,
            signals,
            env,
            executable,
            deadline,
        })
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
    pub async fn preflight(&self, request: &Resolved, plan: &Plan) -> Result<(), Exit> {
        if self
            .inspect(&request.project, &["--version"])
            .await?
            .trim_ascii()
            != b"1.18.30"
        {
            return Err(Exit::Invalid);
        }
        let bytes = self
            .inspect(&request.project, &["debug", "config", "--pure"])
            .await?;
        let mut effective: Value = serde_json::from_slice(&bytes).map_err(|_| Exit::Invalid)?;
        // OpenCode resolves env references in debug output. Compare privately then
        // restore the reference for the transaction's exact routing validator.
        let actual = effective["provider"]["ah-litellm"]["options"]["apiKey"]
            .as_str()
            .ok_or(Exit::Invalid)?;
        let key = std::env::var(&request.api_key_env).map_err(|_| Exit::Invalid)?;
        if actual != key {
            return Err(Exit::Invalid);
        }
        effective["provider"]["ah-litellm"]["options"]["apiKey"] =
            json!(format!("{{env:{}}}", request.api_key_env));
        plan.validate_effective(&effective)
            .map_err(|_| Exit::Invalid)?;
        let (permissions, tools) = profile(request.permissions, self._home.path());
        if effective["permission"] != permissions
            || effective["tools"] != tools
            || effective["autoupdate"] != false
            || effective["share"] != "disabled"
            || effective["plugin"] != json!([])
            || effective["mcp"] != json!({})
            || effective["default_agent"] != "build"
            || effective["agent"] != json!({})
            || effective["mode"] != json!({})
        {
            return Err(Exit::Invalid);
        }
        let bytes = self
            .inspect(&request.project, &["debug", "agent", "build", "--pure"])
            .await?;
        let agent: Value = serde_json::from_slice(&bytes).map_err(|_| Exit::Invalid)?;
        let rules = agent["permission"].as_array().ok_or(Exit::Invalid)?;
        // Runtime defaults may precede our catch-all deny, but nothing may follow
        // except the exact ask rules in the selected profile.
        let start = rules
            .iter()
            .rposition(|r| r == &json!({"permission":"*","pattern":"*","action":"deny"}))
            .ok_or(Exit::Invalid)?;
        let mut expected = Vec::new();
        for name in [
            "*",
            "read",
            "glob",
            "grep",
            "edit",
            "apply_patch",
            "bash",
            "external_directory",
        ] {
            let Some(value) = permissions.get(name) else {
                continue;
            };
            if let Some(action) = value.as_str() {
                expected.push(json!({"permission":name,"pattern":"*","action":action}));
            } else {
                for (pattern, action) in value.as_object().unwrap() {
                    expected.push(json!({"permission":name,"pattern":pattern,"action":action}));
                }
            }
        }
        if rules[start..] != expected || agent["name"] != "build" {
            return Err(Exit::Invalid);
        }
        Ok(())
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
struct PrivateHome(std::path::PathBuf);
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
        Ok(Self(OsString::from_vec(bytes).into()))
    }
    fn path(&self) -> &Path {
        &self.0
    }
}
impl Drop for PrivateHome {
    fn drop(&mut self) {
        let _ = std::fs::remove_dir_all(&self.0);
    }
}

impl Drop for Runtime {
    fn drop(&mut self) {
        self.signals.abort();
    }
}
