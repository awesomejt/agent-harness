//! Pinned Pi 1.5.0 local-only adapter (D060/D080/D081): caller-owned RPC with
//! harness-owned private state, provider routing, deny or trusted extension UI.

use crate::config::{Invalid, Permissions, Resolved, RuntimeKind};
use crate::permission::{
    OptionKind, PermissionOption, PermissionPolicy, PermissionRequest, PermissionResponse,
};
#[cfg(target_os = "macos")]
use crate::progress::Progress;
#[cfg(target_os = "macos")]
use crate::{config::Exit, process::OwnedChild};
use serde_json::{Value, json};
#[cfg(target_os = "macos")]
use std::{collections::HashSet, io, path::PathBuf, time::Duration};
use std::{ffi::OsString, path::Path};
#[cfg(target_os = "macos")]
use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
#[cfg(target_os = "macos")]
use tokio::sync::mpsc;
#[cfg(target_os = "macos")]
use tokio::time::Instant;
#[cfg(target_os = "macos")]
use tokio_util::sync::CancellationToken;

pub(crate) const VERSION: &str = "1.5.0";
const PROVIDER: &str = "ah-litellm";
const LINE_LIMIT: usize = 1 << 20;
const OUTPUT_LIMIT: usize = 8 << 20;
const UI_TITLE: &str = "ah-permission";
/// Built-in tool names for a full trusted invocation (D081); intersected for roles later.
pub(crate) const TRUSTED_TOOLS: [&str; 6] = ["bash", "edit", "find", "grep", "read", "write"];

/// Map a Pi tool name to the canonical grant kind OpenCode uses (D037).
pub(crate) fn tool_kind(name: &str) -> Option<&'static str> {
    match name {
        "read" => Some("read"),
        "find" | "grep" | "ls" => Some("search"),
        "edit" | "write" => Some("edit"),
        "bash" => Some("execute"),
        _ => None,
    }
}

/// Active Pi tool names for the effective invocation profile.
pub(crate) fn active_tools(request: &Resolved) -> Vec<&'static str> {
    if request.permissions != Permissions::Trusted {
        return Vec::new();
    }
    let grantable = crate::opencode::grantable(request);
    TRUSTED_TOOLS
        .into_iter()
        .filter(|name| tool_kind(name).is_some_and(|k| grantable.contains(&k)))
        .collect()
}

/// Capabilities this increment refuses before launch (D060/D080/D081).
pub(crate) fn supported(request: &Resolved) -> Result<(), Invalid> {
    if request.runtime != RuntimeKind::Pi {
        return Ok(());
    }
    if request.agent.is_some() {
        return Err(Invalid(
            "named agents are not yet supported on the Pi runtime",
        ));
    }
    if request.fallback.is_some() {
        return Err(Invalid(
            "local-first is unsupported with litellm.runtime pi",
        ));
    }
    Ok(())
}

pub(crate) fn args(request: &Resolved, extension: &Path) -> Vec<OsString> {
    let mut args: Vec<OsString> = [
        "--offline",
        "--mode",
        "rpc",
        "--no-session",
        "--no-extensions",
        "--no-mcp",
        "--no-skills",
        "--no-prompt-templates",
        "--no-themes",
        "--no-context-files",
        "--no-approve",
        "--provider",
        PROVIDER,
    ]
    .into_iter()
    .map(OsString::from)
    .collect();
    if request.permissions == Permissions::Deny {
        args.push(OsString::from("--no-tools"));
    } else {
        let mut names: Vec<_> = active_tools(request).into_iter().collect();
        names.sort();
        if names.is_empty() {
            args.push(OsString::from("--no-tools"));
        } else {
            args.push(format!("--tools={}", names.join(",")).into());
        }
    }
    args.push(format!("--model={}", request.model).into());
    let mut ext = OsString::from("-e");
    ext.push(extension);
    args.push(ext);
    args
}

pub(crate) fn environment(
    agent_dir: &Path,
    key_env: &str,
    lookup: impl Fn(&str) -> Option<OsString>,
) -> Result<Vec<(OsString, OsString)>, Invalid> {
    let home = lookup("HOME")
        .filter(|home| !home.is_empty())
        .ok_or(Invalid(
            "HOME is required: the Pi runtime uses an isolated agent directory",
        ))?;
    let mut env = vec![
        (OsString::from("HOME"), home),
        (
            OsString::from("PATH"),
            lookup("PATH").unwrap_or_else(|| "/usr/bin:/bin".into()),
        ),
        (
            OsString::from("PI_CODING_AGENT_DIR"),
            agent_dir.as_os_str().to_owned(),
        ),
    ];
    if let Some(key) = lookup(key_env) {
        env.push((OsString::from(key_env), key));
    }
    for name in ["USER", "LOGNAME", "TMPDIR"] {
        if let Some(value) = lookup(name) {
            env.push((OsString::from(name), value));
        }
    }
    Ok(env)
}

fn rpc(id: &str, command: &str, extra: Value) -> Value {
    let mut line = json!({"id": id, "type": command});
    if let Some(object) = extra.as_object() {
        for (key, value) in object {
            line[key] = value.clone();
        }
    }
    line
}

pub(crate) fn validate_response(line: &Value, id: &str, command: &str) -> bool {
    line.get("type") == Some(&json!("response"))
        && line.get("id") == Some(&json!(id))
        && line.get("command") == Some(&json!(command))
        && line.get("success") == Some(&json!(true))
        && line.get("error").is_none()
}

pub(crate) fn validate_state(
    data: &Value,
    model: &str,
    api_base: &str,
    request: &Resolved,
) -> bool {
    let Some(state) = data.as_object() else {
        return false;
    };
    if state.get("isStreaming") != Some(&json!(false))
        || state.get("isCompacting") != Some(&json!(false))
        || state.get("autoCompactionEnabled") != Some(&json!(false))
        || state.get("autoRetryEnabled") == Some(&json!(true))
    {
        return false;
    }
    if state
        .get("messageCount")
        .and_then(Value::as_u64)
        .is_none_or(|n| n != 0)
        || state
            .get("pendingMessageCount")
            .and_then(Value::as_u64)
            .is_none_or(|n| n != 0)
    {
        return false;
    }
    if state.contains_key("sessionFile") {
        return false;
    }
    let model_obj = match state.get("model") {
        Some(Value::Object(map)) => map,
        _ => return false,
    };
    model_obj.get("provider") == Some(&json!(PROVIDER))
        && model_obj.get("id") == Some(&json!(model))
        && model_obj.get("baseUrl") == Some(&json!(api_base))
        && model_obj.get("api") == Some(&json!("openai-completions"))
        && tool_names_match(state.get("activeTools"), request)
        && state.get("mcpServers").is_some_and(empty_array)
        && state
            .get("tools")
            .is_some_and(|value| tool_names_match(Some(value), request))
        && state.get("piVersion") == Some(&json!(VERSION))
}

fn tool_names_match(value: Option<&Value>, request: &Resolved) -> bool {
    let Some(names) = value.and_then(Value::as_array) else {
        return false;
    };
    if request.permissions == Permissions::Deny {
        return names.is_empty();
    }
    let mut expected: Vec<_> = active_tools(request).into_iter().collect();
    expected.sort();
    let mut actual: Vec<&str> = names.iter().filter_map(Value::as_str).collect();
    actual.sort();
    actual == expected
}

fn empty_array(value: &Value) -> bool {
    value.as_array().is_some_and(Vec::is_empty)
}

pub(crate) fn record_tool_call(line: &Value) -> bool {
    match line.get("type").and_then(Value::as_str) {
        Some("tool_call") => true,
        Some("event") if line.get("event") == Some(&json!("tool_call")) => true,
        _ => false,
    }
}

/// Answer one Pi RPC `confirm` for `ah-permission` (D081).
pub(crate) fn decide_ui(
    id: &str,
    message: &str,
    grantable: &[&str],
    eligible: bool,
) -> Option<bool> {
    let Ok(action) = serde_json::from_str::<Value>(message) else {
        return None;
    };
    let tool = action.get("toolName").and_then(Value::as_str)?;
    let kind = tool_kind(tool)?;
    let request = PermissionRequest {
        id: id.to_owned(),
        action: message.to_owned(),
        options: vec![
            PermissionOption {
                id: "allow".into(),
                kind: OptionKind::AllowOnce,
            },
            PermissionOption {
                id: "deny".into(),
                kind: OptionKind::Deny,
            },
        ],
    };
    let mut policy = if eligible && grantable.contains(&kind) {
        PermissionPolicy::grant_next_request(request.clone())
    } else {
        PermissionPolicy::default()
    };
    match policy.respond(&request) {
        PermissionResponse::Selected(selected) => Some(selected == "allow"),
        PermissionResponse::Cancelled | PermissionResponse::Refused => None,
    }
}

fn policy_extension(trusted: bool) -> &'static str {
    if trusted {
        r#"export default function(pi) {
  const grantable = new Set((process.env.AH_PI_GRANTABLE || '').split(',').filter(Boolean));
  const kindOf = (name) => ({read:'read',find:'search',grep:'search',ls:'search',edit:'edit',write:'edit',bash:'execute'}[name]);
  pi.on('tool_call', async (event, ctx) => {
    const kind = kindOf(event.toolName);
    if (!kind || !grantable.has(kind)) return {block: true, reason: 'Harness policy'};
    const msg = JSON.stringify({toolName:event.toolName,toolCallId:event.toolCallId,input:event.input});
    const ok = await ctx.ui.confirm('ah-permission', msg);
    if (!ok) return {block: true, reason: 'denied by agent-harness policy'};
  });
}"#
    } else {
        r#"export default function(pi) {
  pi.on('tool_call', () => ({block: true, reason: 'Harness deny profile'}));
}"#
    }
}

pub(crate) fn validate_prompt_response(line: &Value, id: &str) -> bool {
    validate_response(line, id, "prompt")
        && line
            .pointer("/data/disposition")
            .and_then(Value::as_str)
            .is_some_and(|d| d == "handled" || d == "started")
}

#[derive(Debug, PartialEq)]
pub(crate) enum Terminal {
    Success { text: String },
    Cancelled,
    Other,
}

pub(crate) fn classify_event(line: &Value, interrupted: bool) -> Option<Terminal> {
    match line.get("type").and_then(Value::as_str) {
        Some("agent_settled") if interrupted => Some(Terminal::Cancelled),
        Some("agent_settled")
            if line
                .get("error")
                .is_some_and(|e| !e.is_null() && e.as_bool() != Some(false)) =>
        {
            Some(Terminal::Other)
        }
        Some("agent_settled") => {
            let text = line
                .get("assistantText")
                .and_then(Value::as_str)
                .or_else(|| line.pointer("/message/content").and_then(Value::as_str))
                .unwrap_or_default()
                .to_owned();
            Some(Terminal::Success { text })
        }
        Some("tool_call") | Some("extension_error") => None,
        Some("event") if line.get("event") == Some(&json!("tool_call")) => None,
        Some("agent_end") => None,
        _ => None,
    }
}

#[cfg(target_os = "macos")]
struct AgentDir(Option<PathBuf>);

#[cfg(target_os = "macos")]
impl AgentDir {
    fn new() -> io::Result<Self> {
        use std::os::unix::ffi::{OsStrExt, OsStringExt};
        let template = std::env::temp_dir().join("ah-pi-state-XXXXXX");
        let mut bytes =
            std::ffi::CString::new(template.as_os_str().as_bytes())?.into_bytes_with_nul();
        if unsafe { libc::mkdtemp(bytes.as_mut_ptr().cast()) }.is_null() {
            return Err(io::Error::last_os_error());
        }
        bytes.pop();
        Ok(Self(Some(std::ffi::OsString::from_vec(bytes).into())))
    }
    fn path(&self) -> &Path {
        self.0.as_deref().expect("agent dir")
    }
}

#[cfg(target_os = "macos")]
impl Drop for AgentDir {
    fn drop(&mut self) {
        if let Some(path) = self.0.take() {
            let _ = std::fs::remove_dir_all(path);
        }
    }
}

#[cfg(target_os = "macos")]
struct PreparedState {
    agent_dir: AgentDir,
    extension: PathBuf,
}

#[cfg(target_os = "macos")]
impl PreparedState {
    fn prepare(request: &Resolved) -> io::Result<Self> {
        let trusted = request.permissions == Permissions::Trusted;
        let agent_dir = AgentDir::new()?;
        let root = agent_dir.path();
        let key_name = request
            .api_key_env
            .as_deref()
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "missing api_key_env"))?;
        let api_base = request
            .api_base
            .as_deref()
            .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "missing api_base"))?;
        let models = json!({
            "providers": {
                PROVIDER: {
                    "baseUrl": api_base,
                    "api": "openai-completions",
                    "apiKey": format!("${{{key_name}}}"),
                    "models": [{"id": request.model, "name": request.model}],
                }
            }
        });
        std::fs::write(
            root.join("models.json"),
            serde_json::to_vec(&models).map_err(io::Error::other)?,
        )?;
        std::fs::write(
            root.join("settings.json"),
            br#"{"compaction":{"enabled":false},"retry":{"enabled":false}}"#,
        )?;
        let extension = root.join("ah-policy.mjs");
        std::fs::write(&extension, policy_extension(trusted))?;
        Ok(Self {
            agent_dir,
            extension,
        })
    }

    fn agent_path(&self) -> &Path {
        self.agent_dir.path()
    }
}

#[cfg(target_os = "macos")]
struct Channel {
    records: mpsc::Receiver<Result<Value, ()>>,
    stdin: Option<tokio::process::ChildStdin>,
}

#[cfg(target_os = "macos")]
impl Channel {
    async fn send(&mut self, value: &Value, deadline: Instant) -> bool {
        let Some(stdin) = self.stdin.as_mut() else {
            return false;
        };
        let mut line = value.to_string();
        line.push('\n');
        let write = async {
            stdin.write_all(line.as_bytes()).await?;
            stdin.flush().await
        };
        let bound = deadline.min(Instant::now() + Duration::from_secs(5));
        matches!(tokio::time::timeout_at(bound, write).await, Ok(Ok(())))
    }
}

#[cfg(target_os = "macos")]
fn reader(stdout: tokio::process::ChildStdout) -> mpsc::Receiver<Result<Value, ()>> {
    let (send, receive) = mpsc::channel(64);
    tokio::spawn(async move {
        let mut stdout = BufReader::new(stdout);
        let mut left = OUTPUT_LIMIT;
        loop {
            let mut line = Vec::new();
            let limit = left.min(LINE_LIMIT) as u64;
            let read = (&mut stdout).take(limit).read_until(b'\n', &mut line).await;
            let record = match read {
                Ok(0) if left == 0 => Err(()),
                Ok(0) => return,
                Ok(n) if line.ends_with(b"\n") => {
                    left -= n;
                    serde_json::from_slice::<Value>(&line)
                        .ok()
                        .filter(Value::is_object)
                        .ok_or(())
                }
                _ => Err(()),
            };
            let failed = record.is_err();
            if send.send(record).await.is_err() || failed {
                return;
            }
        }
    });
    receive
}

#[cfg(target_os = "macos")]
#[derive(Default)]
struct Observed {
    submitted: bool,
    violation: bool,
    tools: u32,
    permissions: u32,
    grants: u32,
    answered_ui: HashSet<String>,
}

#[cfg(target_os = "macos")]
enum Outcome {
    Terminal(Terminal),
    Refused,
    Stopped,
    Failed,
}

#[cfg(target_os = "macos")]
fn deny_tool_violation(request: &Resolved, line: &Value) -> bool {
    request.permissions == Permissions::Deny && record_tool_call(line)
}

#[cfg(target_os = "macos")]
async fn answer_extension_ui(
    channel: &mut Channel,
    line: &Value,
    request: &Resolved,
    deadline: Instant,
    cancelled: &CancellationToken,
    progress: &Progress,
    observed: &mut Observed,
) -> Result<bool, Outcome> {
    if line.get("type") != Some(&json!("extension_ui_request")) {
        return Ok(false);
    }
    if line.get("method") != Some(&json!("confirm")) || line.get("title") != Some(&json!(UI_TITLE))
    {
        return Err(Outcome::Failed);
    }
    let id = line
        .get("id")
        .and_then(Value::as_str)
        .filter(|s| !s.is_empty())
        .ok_or(Outcome::Failed)?;
    if !observed.answered_ui.insert(id.to_owned()) {
        observed.violation = true;
        return Err(Outcome::Failed);
    }
    let message = line.get("message").and_then(Value::as_str).unwrap_or("");
    let eligible = !cancelled.is_cancelled() && Instant::now() < deadline;
    let grantable = crate::opencode::grantable(request);
    let Some(allow) = decide_ui(id, message, &grantable, eligible) else {
        observed.violation = true;
        return Err(Outcome::Failed);
    };
    observed.permissions += 1;
    if allow {
        observed.grants += 1;
        observed.tools += 1;
    }
    let response = json!({
        "type": "extension_ui_response",
        "id": id,
        "confirmed": allow,
    });
    if !channel.send(&response, deadline).await {
        return Err(Outcome::Failed);
    }
    if observed.permissions <= 16 || observed.permissions % 128 == 0 {
        progress.event(format!(
            "Pi extension UI response; requests={}; grants={}",
            observed.permissions, observed.grants
        ));
    }
    Ok(true)
}

#[cfg(target_os = "macos")]
async fn expect(
    channel: &mut Channel,
    id: &str,
    command: &str,
    deadline: Instant,
    cancelled: &CancellationToken,
) -> Result<Value, Outcome> {
    let bound = deadline.min(Instant::now() + Duration::from_secs(30));
    tokio::select! {
        record = tokio::time::timeout_at(bound, channel.records.recv()) => match record {
            Ok(Some(Ok(line))) if validate_response(&line, id, command) => Ok(line),
            Ok(Some(Ok(line)))
                if line.get("type") == Some(&json!("response"))
                    && line.get("id") == Some(&json!(id))
                    && line.get("command") == Some(&json!(command)) =>
            {
                Err(Outcome::Refused)
            }
            Ok(Some(Ok(_))) => Err(Outcome::Failed),
            Ok(Some(Err(()))) => Err(Outcome::Failed),
            Ok(None) => Err(Outcome::Failed),
            Err(_) if Instant::now() >= deadline => Err(Outcome::Stopped),
            Err(_) => Err(Outcome::Failed),
        },
        _ = cancelled.cancelled() => Err(Outcome::Stopped),
    }
}

#[cfg(target_os = "macos")]
async fn turn(
    channel: &mut Channel,
    request: &Resolved,
    label: &str,
    deadline: Instant,
    cancelled: &CancellationToken,
    progress: &Progress,
    observed: &mut Observed,
) -> Outcome {
    let api_base = request.api_base.as_deref().unwrap_or_default();
    progress.event("preflight check started (Pi RPC; no prompt)");
    for (id, command, extra) in [
        (
            "ah-compaction",
            "set_auto_compaction",
            json!({"enabled": false}),
        ),
        ("ah-retry", "set_auto_retry", json!({"enabled": false})),
        ("ah-state", "get_state", json!({})),
    ] {
        if !channel.send(&rpc(id, command, extra), deadline).await {
            return Outcome::Failed;
        }
        let line = match expect(channel, id, command, deadline, cancelled).await {
            Ok(line) => line,
            Err(outcome) => return outcome,
        };
        if command == "get_state" {
            let Some(data) = line.get("data") else {
                return Outcome::Refused;
            };
            if !validate_state(data, &request.model, api_base, request) {
                return Outcome::Refused;
            }
        }
    }
    if cancelled.is_cancelled() || Instant::now() >= deadline {
        return Outcome::Stopped;
    }
    let profile = match request.permissions {
        Permissions::Deny => "deny (no tools offered)",
        Permissions::Trusted => "trusted (extension UI grants)",
    };
    progress.event(format!(
        "{label} via Pi {VERSION}; model pi/{}; permissions {profile}",
        request.model
    ));
    let prompt_id = "ah-prompt";
    if !channel
        .send(
            &rpc(prompt_id, "prompt", json!({"message": request.prompt})),
            deadline,
        )
        .await
    {
        return Outcome::Failed;
    }
    observed.submitted = true;
    progress.emit("attempt.prompt_submitted", json!({}));
    progress.note(json!({"prompt_submitted": true}));
    let bound = deadline.min(Instant::now() + Duration::from_secs(30));
    let mut prompt_ok = false;
    let mut attempts = 0;
    while !prompt_ok && attempts < 16 {
        let record = tokio::select! {
            value = tokio::time::timeout_at(bound, channel.records.recv()) => value,
            _ = cancelled.cancelled() => return Outcome::Stopped,
        };
        attempts += 1;
        match record {
            Ok(Some(Ok(line))) => {
                match answer_extension_ui(
                    channel, &line, request, deadline, cancelled, progress, observed,
                )
                .await
                {
                    Err(outcome) => return outcome,
                    Ok(true) => continue,
                    Ok(false) if validate_prompt_response(&line, prompt_id) => {
                        prompt_ok = true;
                    }
                    Ok(false) if deny_tool_violation(request, &line) => {
                        observed.tools += 1;
                        observed.violation = true;
                        return Outcome::Failed;
                    }
                    Ok(false) => {}
                }
            }
            Ok(Some(Err(()))) => return Outcome::Failed,
            Ok(None) => return Outcome::Failed,
            Err(_) if Instant::now() >= deadline => return Outcome::Stopped,
            Err(_) => return Outcome::Failed,
        }
    }
    if !prompt_ok {
        return Outcome::Failed;
    }
    let mut interrupted = cancelled.is_cancelled();
    let mut terminal = None;
    while terminal.is_none() {
        if cancelled.is_cancelled() && !interrupted {
            interrupted = true;
            let _ = channel
                .send(&rpc("ah-abort", "abort", json!({})), deadline)
                .await;
        }
        if Instant::now() >= deadline {
            interrupted = true;
            let _ = channel
                .send(&rpc("ah-abort", "abort", json!({})), deadline)
                .await;
        }
        let bound = deadline.min(Instant::now() + Duration::from_secs(30));
        let record = if interrupted {
            tokio::time::timeout_at(bound, channel.records.recv()).await
        } else {
            tokio::select! {
                biased;
                value = tokio::time::timeout_at(bound, channel.records.recv()) => value,
                _ = cancelled.cancelled() => {
                    interrupted = true;
                    let _ = channel.send(&rpc("ah-abort", "abort", json!({})), deadline).await;
                    continue;
                }
            }
        };
        match record {
            Ok(Some(Ok(line))) => {
                match answer_extension_ui(
                    channel, &line, request, deadline, cancelled, progress, observed,
                )
                .await
                {
                    Err(outcome) => return outcome,
                    Ok(true) => continue,
                    Ok(false) => {}
                }
                if deny_tool_violation(request, &line) {
                    observed.tools += 1;
                    observed.violation = true;
                    return Outcome::Failed;
                }
                if let Some(found) = classify_event(&line, interrupted) {
                    terminal = Some(found);
                }
            }
            Ok(Some(Err(()))) => return Outcome::Failed,
            Ok(None) => return Outcome::Failed,
            Err(_) if Instant::now() >= deadline => return Outcome::Stopped,
            Err(_) => return Outcome::Failed,
        }
    }
    Outcome::Terminal(terminal.unwrap())
}

#[cfg(target_os = "macos")]
pub(crate) async fn attempt(
    request: &Resolved,
    label: &str,
    deadline: Instant,
    cancelled: CancellationToken,
    progress: &Progress,
) -> Exit {
    let Some(executable) = crate::preview::discover_runtime("pi") else {
        progress.event(format!(
            "Pi missing: install {VERSION} on an absolute PATH entry"
        ));
        progress.reason("Pi missing on an absolute PATH entry");
        return Exit::Invalid;
    };
    let key_env = match request.api_key_env.as_deref() {
        Some(name) => name,
        None => {
            progress.reject("selected route requires a LiteLLM API key environment reference");
            return Exit::Invalid;
        }
    };
    let prepared = match PreparedState::prepare(request) {
        Ok(prepared) => prepared,
        Err(_) => {
            progress.event("private Pi state setup failed");
            return Exit::Failed;
        }
    };
    let mut env = match environment(prepared.agent_path(), key_env, |name| {
        std::env::var_os(name)
    }) {
        Ok(env) => env,
        Err(error) => {
            progress.reject(error.0);
            return Exit::Invalid;
        }
    };
    if request.permissions == Permissions::Trusted {
        let kinds = crate::opencode::grantable(request);
        env.push((OsString::from("AH_PI_GRANTABLE"), kinds.join(",").into()));
    }
    if let Err(exit) = crate::worktree::report(&request.project, deadline, progress).await {
        return exit;
    }
    if cancelled.is_cancelled() || Instant::now() >= deadline {
        return Exit::Cancelled;
    }
    let mut command = tokio::process::Command::new(&executable);
    command
        .args(args(request, &prepared.extension))
        .current_dir(&request.project)
        .env_clear()
        .envs(env);
    let mut owned = match OwnedChild::spawn(&mut command) {
        Ok(child) => child,
        Err(_) => {
            progress.event("launch failed; no prompt submitted");
            return Exit::Failed;
        }
    };
    progress.note(json!({"launched": true}));
    let mut channel = Channel {
        records: reader(owned.child.stdout.take().unwrap()),
        stdin: owned.child.stdin.take(),
    };
    let mut observed = Observed::default();
    let outcome = turn(
        &mut channel,
        request,
        label,
        deadline,
        &cancelled,
        progress,
        &mut observed,
    )
    .await;
    channel.stdin = None;
    if matches!(outcome, Outcome::Terminal(_)) {
        let _ = tokio::time::timeout(Duration::from_secs(2), owned.child.wait()).await;
    }
    progress.event("process cleanup started");
    let cleanup = owned.cleanup().await;
    let summary = json!({
        "cleanup_confirmed": cleanup,
        "tool_events": observed.tools,
        "protocol_violation": observed.violation,
        "permission_requests": observed.permissions,
        "permission_grants": observed.grants,
    });
    progress.event(format!(
        "cleanup={cleanup}; protocol_violation={}; tool events: {}; stderr_bytes={}",
        observed.violation,
        observed.tools,
        owned.stderr_bytes()
    ));
    progress.note(summary.clone());
    progress.emit("attempt.cleanup", summary);
    let terminal = match outcome {
        Outcome::Refused => {
            progress.event(format!(
                "preflight failed (requires Pi {VERSION}, deny profile, empty tools and exact model route)"
            ));
            progress
                .reason("preflight failed: Pi version, tools, MCP or model route did not match");
            return Exit::Invalid;
        }
        Outcome::Stopped if cancelled.is_cancelled() || Instant::now() >= deadline => {
            return Exit::Cancelled;
        }
        Outcome::Terminal(terminal) if !observed.violation => terminal,
        _ if !cleanup || observed.submitted => return Exit::Uncertain,
        _ => return Exit::Failed,
    };
    if !cleanup {
        return Exit::Uncertain;
    }
    match terminal {
        Terminal::Success { text } => {
            progress.note(json!({"backend_stop": "agent_settled"}));
            progress.emit(
                "attempt.backend_stop",
                json!({"stop": "agent_settled", "usage_unknown": true}),
            );
            progress.event(
                "backend agent_settled; cleanup confirmed; delivering response (2s output budget)",
            );
            if progress.deliver(text).await {
                Exit::Success
            } else {
                progress.event(
                    "final response delivery failed or blocked; backend completed, output may be partial",
                );
                Exit::Failed
            }
        }
        Terminal::Cancelled => {
            progress.note(json!({"backend_stop": "cancelled"}));
            Exit::Cancelled
        }
        Terminal::Other => Exit::Failed,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::config::{Mode, Permissions, Resolved, RuntimeKind, Source, Sources};
    use serde_json::json;
    use std::path::PathBuf;

    fn request(permissions: Permissions) -> Resolved {
        Resolved {
            mode: Mode::LocalOnly,
            sources: Sources {
                mode: Source::Invocation,
                model: Source::Invocation,
                permissions: Source::Invocation,
                timeout: Source::Invocation,
            },
            project: PathBuf::from("."),
            model: "fixture".into(),
            group: None,
            proxy_groups: Vec::new(),
            api_base: Some("http://127.0.0.1:9/v1".into()),
            api_key_env: Some("LOCAL_KEY".into()),
            runtime: RuntimeKind::Pi,
            permissions,
            timeout_secs: 30,
            no_sync: false,
            preview: false,
            prompt: String::new(),
            instructions: None,
            agent: None,
            fallback: None,
            verify: None,
        }
    }

    #[test]
    fn preflight_state_accepts_idle_deny_route() {
        let data = json!({
            "isStreaming": false,
            "isCompacting": false,
            "autoCompactionEnabled": false,
            "messageCount": 0,
            "pendingMessageCount": 0,
            "piVersion": VERSION,
            "model": {
                "provider": PROVIDER,
                "id": "fixture",
                "baseUrl": "http://127.0.0.1:9/v1",
                "api": "openai-completions",
            },
            "activeTools": [],
            "mcpServers": [],
            "tools": [],
        });
        assert!(validate_state(
            &data,
            "fixture",
            "http://127.0.0.1:9/v1",
            &request(Permissions::Deny)
        ));
    }

    #[test]
    fn preflight_state_accepts_trusted_toolset() {
        let data = json!({
            "isStreaming": false,
            "isCompacting": false,
            "autoCompactionEnabled": false,
            "messageCount": 0,
            "pendingMessageCount": 0,
            "piVersion": VERSION,
            "model": {
                "provider": PROVIDER,
                "id": "fixture",
                "baseUrl": "http://127.0.0.1:9/v1",
                "api": "openai-completions",
            },
            "activeTools": ["bash","edit","find","grep","read","write"],
            "mcpServers": [],
            "tools": ["bash","edit","find","grep","read","write"],
        });
        assert!(validate_state(
            &data,
            "fixture",
            "http://127.0.0.1:9/v1",
            &request(Permissions::Trusted)
        ));
    }

    #[test]
    fn preflight_state_refuses_missing_version() {
        let data = json!({
            "isStreaming": false,
            "isCompacting": false,
            "autoCompactionEnabled": false,
            "messageCount": 0,
            "pendingMessageCount": 0,
            "model": {
                "provider": PROVIDER,
                "id": "fixture",
                "baseUrl": "http://127.0.0.1:9/v1",
                "api": "openai-completions",
            },
            "activeTools": [],
            "mcpServers": [],
            "tools": [],
        });
        assert!(!validate_state(
            &data,
            "fixture",
            "http://127.0.0.1:9/v1",
            &request(Permissions::Deny)
        ));
    }

    #[test]
    fn preflight_state_refuses_tooling() {
        let data = json!({
            "isStreaming": false,
            "isCompacting": false,
            "autoCompactionEnabled": false,
            "messageCount": 0,
            "pendingMessageCount": 0,
            "piVersion": VERSION,
            "model": {
                "provider": PROVIDER,
                "id": "fixture",
                "baseUrl": "http://127.0.0.1:9/v1",
                "api": "openai-completions",
            },
            "activeTools": ["bash"],
            "mcpServers": [],
            "tools": [],
        });
        assert!(!validate_state(
            &data,
            "fixture",
            "http://127.0.0.1:9/v1",
            &request(Permissions::Deny)
        ));
    }

    #[test]
    fn ui_grant_accepts_matching_tool_kind() {
        let message = r#"{"toolName":"read","toolCallId":"t1","input":{"path":"x"}}"#;
        assert_eq!(
            decide_ui("ui-1", message, &["read", "edit"], true),
            Some(true)
        );
        assert_eq!(decide_ui("ui-1", message, &["edit"], true), Some(false));
        assert_eq!(decide_ui("ui-1", message, &["read"], false), Some(false));
        assert_eq!(decide_ui("ui-1", "not-json", &["read"], true), None);
        assert_eq!(
            decide_ui(
                "ui-1",
                r#"{"toolName":"find","toolCallId":"t1","input":{}}"#,
                &["search"],
                true
            ),
            Some(true)
        );
    }

    #[test]
    fn settled_error_after_interrupt_maps_cancelled() {
        let line = json!({"type": "agent_settled", "error": true});
        assert_eq!(classify_event(&line, true), Some(Terminal::Cancelled));
    }

    #[test]
    fn settled_event_maps_success() {
        let line = json!({"type": "agent_settled", "assistantText": "ok\n"});
        assert_eq!(
            classify_event(&line, false),
            Some(Terminal::Success {
                text: "ok\n".into()
            })
        );
    }
}
