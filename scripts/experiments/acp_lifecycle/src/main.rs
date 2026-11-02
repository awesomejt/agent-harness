//! Bounded Unix-only SDK experiment. No public harness command is added.
use agent_client_protocol::schema::{ProtocolVersion, v1::*};
use agent_client_protocol::{ByteStreams, Client};
use awesomejt_agent_harness::permission::{
    OptionKind, PermissionOption as PolicyOption, PermissionPolicy, PermissionRequest,
    PermissionResponse,
};
use serde_json::{Value, json};
use std::collections::HashSet;
use std::io;
use std::process::Stdio;
use std::sync::{
    Arc, Mutex,
    atomic::{AtomicBool, Ordering},
};
use std::time::Duration;
use tokio::io::{AsyncRead, ReadBuf};
use tokio::process::{Child, Command};
use tokio_util::compat::{TokioAsyncReadCompatExt, TokioAsyncWriteCompatExt};

// Bound total protocol bytes, independently of frame/notification boundaries.
struct BoundedRead<R> {
    inner: R,
    left: usize,
}
impl<R: AsyncRead + Unpin> AsyncRead for BoundedRead<R> {
    fn poll_read(
        mut self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &mut ReadBuf<'_>,
    ) -> std::task::Poll<io::Result<()>> {
        if self.left == 0 {
            return std::task::Poll::Ready(Err(io::Error::other("protocol byte limit")));
        }
        let before = buf.filled().len();
        let result = std::pin::Pin::new(&mut self.inner).poll_read(cx, buf);
        let read = buf.filled().len() - before;
        if read > self.left {
            self.left = 0;
            return std::task::Poll::Ready(Err(io::Error::other("protocol byte limit")));
        }
        self.left -= read;
        result
    }
}

struct OwnedChild {
    child: Child,
    group: i32,
}
impl OwnedChild {
    fn signal(&self, signal: i32) {
        // The child creates its own process group before exec. Never signal our group.
        if self.group > 0 {
            unsafe {
                libc::kill(-self.group, signal);
            }
        }
    }
    async fn cleanup(&mut self) -> io::Result<()> {
        self.signal(libc::SIGTERM);
        // Escalate the entire group even when its leader has already exited.
        tokio::time::sleep(Duration::from_millis(300)).await;
        self.signal(libc::SIGKILL);
        tokio::time::timeout(Duration::from_secs(5), self.child.wait())
            .await
            .map_err(|_| io::Error::other("reap deadline"))??;
        self.group = 0;
        Ok(())
    }
}
impl Drop for OwnedChild {
    fn drop(&mut self) {
        self.signal(libc::SIGKILL);
        let _ = self.child.start_kill();
    }
}

// SDK callback errors are peer responses, not necessarily connection failures.
// Keep a sticky attempt-level failure and wake the owner for immediate cleanup.
#[derive(Default)]
struct Violation {
    failed: AtomicBool,
    wake: tokio::sync::Notify,
}
impl Violation {
    fn fail(&self) -> agent_client_protocol::Error {
        self.failed.store(true, Ordering::SeqCst);
        self.wake.notify_one();
        agent_client_protocol::Error::internal_error()
    }
}

#[derive(Default)]
struct Observed {
    chunks: usize,
    text: String,
    permissions: usize,
    tools: usize,
    session: Option<String>,
    seen: HashSet<String>,
}

#[tokio::main(flavor = "current_thread")]
async fn main() {
    if run().await.is_err() {
        // Arbitrary runtime/provider errors may include secrets or prompt text.
        eprintln!("Lifecycle experiment failed; raw error withheld.");
        std::process::exit(1);
    }
}

async fn run() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = std::env::args().collect();
    if args.len() != 6 {
        return Err("expected executable, project, target, scenario, prompt".into());
    }
    let (executable, project, target, scenario, prompt) =
        (&args[1], &args[2], &args[3], &args[4], &args[5]);
    if !["text", "instruction", "deny", "cancel", "unavailable"].contains(&scenario.as_str()) {
        return Err("unknown scenario".into());
    }
    let deadline = std::env::var("AH_EXPERIMENT_DEADLINE_SECS")
        .ok()
        .map(|v| v.parse::<u64>())
        .transpose()?
        .unwrap_or(180);
    if !(1..=180).contains(&deadline) {
        return Err("invalid deadline".into());
    }
    let mut command = Command::new(executable);
    command
        .args(["acp", "--pure", "--cwd", project])
        .current_dir(project)
        .env_clear();
    for name in [
        "PATH",
        "HOME",
        "XDG_CONFIG_HOME",
        "XDG_DATA_HOME",
        "XDG_CACHE_HOME",
        "XDG_STATE_HOME",
        "OPENCODE_DISABLE_MODELS_FETCH",
        "OPENCODE_DISABLE_DEFAULT_PLUGINS",
        "OPENCODE_DISABLE_AUTOUPDATE",
        "AH_PROBE_API_KEY",
    ] {
        if let Some(value) = std::env::var_os(name) {
            command.env(name, value);
        }
    }
    command
        .stdin(Stdio::piped())
        .stdout(Stdio::piped())
        .stderr(Stdio::null())
        .kill_on_drop(true)
        .process_group(0);
    let child = command.spawn()?;
    let group = child.id().ok_or("no pid")? as i32;
    let mut owned = OwnedChild { child, group };
    let input = owned.child.stdin.take().ok_or("no stdin")?;
    let output = owned.child.stdout.take().ok_or("no stdout")?;
    let transport = ByteStreams::new(
        input.compat_write(),
        BoundedRead {
            inner: output,
            left: 2_000_000,
        }
        .compat(),
    );
    let observed = Arc::new(Mutex::new(Observed::default()));
    let violation = Arc::new(Violation::default());
    let notification_failure = violation.clone();
    let permission_failure = violation.clone();
    let notifications = observed.clone();
    let permissions = observed.clone();
    let foreground = observed.clone();
    let progress = Arc::new(tokio::sync::Notify::new());
    let notify = progress.clone();
    let connection = Client.builder()
        .on_receive_notification(async move |notification: SessionNotification, _cx| {
            let value = serde_json::to_value(notification)?;
            let mut state = notifications.lock().unwrap();
            let kind = value["update"]["sessionUpdate"].as_str();
            if state.session.is_none() && !matches!(kind, Some("agent_message_chunk" | "tool_call" | "tool_call_update")) {
                // Session setup metadata may race the session/new foreground continuation.
                // It supplies no response text, tool activity or cancellation trigger.
                return Ok(());
            }
            if value["sessionId"].as_str() != state.session.as_deref() { return Err(notification_failure.fail()); }
            match kind {
                Some("agent_message_chunk") => {
                    state.chunks += 1;
                    if let Some(text) = value["update"]["content"]["text"].as_str() {
                        if state.text.len() + text.len() > 100_000 { return Err(notification_failure.fail()); }
                        state.text.push_str(text);
                    }
                    notify.notify_one();
                }
                Some("tool_call" | "tool_call_update") => {
                    state.tools += 1;
                    if scenario != "deny" { return Err(notification_failure.fail()); }
                }
                _ => {}
            }
            Ok(())
        }, agent_client_protocol::on_receive_notification!())
        .on_receive_request(async move |request: RequestPermissionRequest, responder, _cx| {
            let value = serde_json::to_value(&request)?;
            let mut state = permissions.lock().unwrap();
            let id = value["toolCall"]["toolCallId"].as_str().unwrap_or("").to_owned();
            if scenario != "deny" || value["sessionId"].as_str() != state.session.as_deref() || !state.seen.insert(id.clone()) {
                return Err(permission_failure.fail());
            }
            let options = request.options.iter().map(|option| PolicyOption {
                id: option.option_id.to_string(),
                kind: match option.kind {
                    PermissionOptionKind::AllowOnce => OptionKind::AllowOnce,
                    PermissionOptionKind::AllowAlways => OptionKind::AllowAlways,
                    PermissionOptionKind::RejectOnce | PermissionOptionKind::RejectAlways => OptionKind::Deny,
                    _ => OptionKind::Unknown,
                },
            }).collect();
            // No grants: complete raw arguments are unnecessary for denial, and are never logged.
            let normalized = PermissionRequest { id, action: value["toolCall"].to_string(), options };
            let outcome = match PermissionPolicy::default().respond(&normalized) {
                PermissionResponse::Selected(id) => RequestPermissionOutcome::Selected(SelectedPermissionOutcome::new(id)),
                PermissionResponse::Cancelled => RequestPermissionOutcome::Cancelled,
                PermissionResponse::Refused => return Err(permission_failure.fail()),
            };
            state.permissions += 1;
            responder.respond(RequestPermissionResponse::new(outcome)).map_err(|_| permission_failure.fail())
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: ReadTextFileRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: WriteTextFileRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: CreateTerminalRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: TerminalOutputRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: ReleaseTerminalRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: KillTerminalRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .on_receive_request({
            let failure = violation.clone();
            async move |_request: WaitForTerminalExitRequest, _responder, _cx| {
                Err::<(), _>(failure.fail())
            }
        }, agent_client_protocol::on_receive_request!())
        .connect_with(transport, async move |cx| {
            let init = cx.send_request(InitializeRequest::new(ProtocolVersion::V1)).block_task().await?;
            if init.protocol_version != ProtocolVersion::V1 { return Err(agent_client_protocol::Error::internal_error()); }
            let session = cx.send_request(NewSessionRequest::new(std::path::PathBuf::from(project))).block_task().await?;
            let value = serde_json::to_value(&session)?;
            let models: Vec<&Value> = value["configOptions"].as_array().into_iter().flatten().filter(|x| x["id"] == "model").collect();
            if models.len() != 1 || models[0]["currentValue"] != *target { return Err(agent_client_protocol::Error::internal_error()); }
            foreground.lock().unwrap().session = Some(session.session_id.to_string());
            println!("{}", json!({"promptSent": true}));
            let request = cx.send_request(PromptRequest::new(session.session_id.clone(), vec![ContentBlock::Text(TextContent::new(prompt.clone()))]));
            let response = request.block_task();
            tokio::pin!(response);
            let result = if scenario == "cancel" {
                tokio::select! {
                    result = &mut response => { let _ = result?; return Err(agent_client_protocol::Error::internal_error()); },
                    _ = progress.notified() => {},
                }
                cx.send_notification(CancelNotification::new(session.session_id))?;
                tokio::time::timeout(Duration::from_secs(15), response).await.map_err(|_| agent_client_protocol::Error::internal_error())??
            } else {
                match response.await {
                    Ok(value) => value,
                    Err(error) => {
                        println!("{}", json!({"promptError": true}));
                        return Err(error);
                    }
                }
            };
            let stop = serde_json::to_value(&result)?;
            let expected = if scenario == "cancel" { "cancelled" } else { "end_turn" };
            if stop["stopReason"] != expected || scenario == "unavailable" { return Err(agent_client_protocol::Error::internal_error()); }
            println!("{}", json!({"stopReason": expected}));
            Ok(())
        });
    let result = tokio::select! {
        value = tokio::time::timeout(Duration::from_secs(deadline), connection) => Some(value),
        _ = tokio::signal::ctrl_c() => None,
        _ = violation.wake.notified() => None,
    };
    let cleanup = owned.cleanup().await;
    // Successful cleanup never implies successful protocol completion.
    cleanup?;
    println!(
        "{}",
        json!({"directChildReaped": true, "groupEscalated": true, "processGroup": group})
    );
    {
        let state = observed.lock().unwrap();
        println!(
            "{}",
            json!({"observedChunks": state.chunks,
            "observedPermissionDenials": state.permissions, "observedToolEvents": state.tools})
        );
    }
    if violation.failed.load(Ordering::SeqCst) {
        println!("{}", json!({"protocolViolation": true}));
        return Err("protocol violation".into());
    }
    result.ok_or("interrupted")???;
    let state = observed.lock().unwrap();
    if scenario == "deny" && state.permissions == 0 {
        return Err("no permission request".into());
    }
    if scenario != "deny" && state.tools != 0 {
        return Err("unexpected tool activity".into());
    }
    let marker = if scenario == "instruction" {
        "AH_PROJECT_INSTRUCTIONS_OK"
    } else {
        "AH_ACP_LIFECYCLE_OK"
    };
    if ["text", "instruction"].contains(&scenario.as_str()) && state.text.trim() != marker {
        return Err("marker mismatch".into());
    }
    println!(
        "{}",
        json!({"chunks": state.chunks, "permissionDenials": state.permissions, "toolEvents": state.tools, "markerMatched": state.text.trim() == marker})
    );
    Ok(())
}
