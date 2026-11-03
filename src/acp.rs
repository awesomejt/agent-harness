//! ACP adapter; OpenCode owns the coding loop and tools.
use crate::permission::{
    OptionKind, PermissionOption as PolicyOption, PermissionPolicy, PermissionRequest,
    PermissionResponse,
};
use crate::{
    config::{Exit, Permissions, Resolved},
    process::OwnedChild,
    runtime::Runtime,
};
use agent_client_protocol::schema::{ProtocolVersion, v1::*};
use agent_client_protocol::{ByteStreams, Client};
use serde_json::Value;
use std::collections::{HashMap, HashSet};
use std::io;
use std::sync::{
    Arc, Mutex,
    atomic::{AtomicBool, AtomicU8, Ordering},
};
use tokio::io::{AsyncRead, ReadBuf};
use tokio_util::compat::{TokioAsyncReadCompatExt, TokioAsyncWriteCompatExt};

// Bound total protocol bytes, independently of frame/notification boundaries.
struct BoundedRead<R> {
    inner: R,
    left: usize,
    violation: Arc<Violation>,
}
impl<R: AsyncRead + Unpin> AsyncRead for BoundedRead<R> {
    fn poll_read(
        mut self: std::pin::Pin<&mut Self>,
        cx: &mut std::task::Context<'_>,
        buf: &mut ReadBuf<'_>,
    ) -> std::task::Poll<io::Result<()>> {
        if self.left == 0 {
            self.violation.fail();
            return std::task::Poll::Ready(Err(io::Error::other("protocol byte limit")));
        }
        let before = buf.filled().len();
        let result = std::pin::Pin::new(&mut self.inner).poll_read(cx, buf);
        let read = buf.filled().len() - before;
        if read > self.left {
            self.violation.fail();
            self.left = 0;
            return std::task::Poll::Ready(Err(io::Error::other("protocol byte limit")));
        }
        self.left -= read;
        result
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
    calls: HashMap<String, Value>,
    granted: usize,
    edit_paths: HashSet<String>,
}

pub(crate) async fn run(runtime: &Runtime, request: &Resolved) -> Exit {
    if runtime.cancelled.is_cancelled() || tokio::time::Instant::now() >= runtime.deadline {
        return Exit::Cancelled;
    }
    let project = &request.project;
    let target = request.runtime_model();
    let prompt = &request.prompt;
    let policy = request.permissions;
    let Some(project_arg) = project.to_str() else {
        return Exit::Invalid;
    };
    let mut command = runtime.command(project, &["acp", "--pure", "--cwd", project_arg]);
    let mut owned = match OwnedChild::spawn(&mut command) {
        Ok(child) => child,
        Err(_) => {
            runtime
                .progress
                .event("attempt=1 launch failed; no prompt submitted");
            return Exit::Failed;
        }
    };
    let input = owned.child.stdin.take().unwrap();
    let output = owned.child.stdout.take().unwrap();
    let violation = Arc::new(Violation::default());
    let transport = ByteStreams::new(
        input.compat_write(),
        BoundedRead {
            inner: output,
            left: 8_000_000,
            violation: violation.clone(),
        }
        .compat(),
    );
    let observed = Arc::new(Mutex::new(Observed::default()));
    let notification_failure = violation.clone();
    let permission_failure = violation.clone();
    let notifications = observed.clone();
    let permissions = observed.clone();
    let foreground = observed.clone();
    let notification_progress = runtime.progress.clone();
    let permission_progress = runtime.progress.clone();
    let permission_cancel = runtime.cancelled.clone();
    let permission_deadline = runtime.deadline;
    let foreground_progress = runtime.progress.clone();
    let active = Arc::new(AtomicBool::new(false));
    let sent = active.clone();
    let terminal = Arc::new(AtomicU8::new(0));
    let finished = terminal.clone();
    let connection = Client
        .builder()
        .on_receive_notification(
            async move |notification: SessionNotification, _cx| {
                let value = serde_json::to_value(notification)?;
                let mut state = notifications.lock().unwrap();
                let kind = value["update"]["sessionUpdate"].as_str();
                if state.session.is_none()
                    && !matches!(
                        kind,
                        Some("agent_message_chunk" | "tool_call" | "tool_call_update")
                    )
                {
                    // Session setup metadata may race the session/new foreground continuation.
                    // It supplies no response text, tool activity or cancellation trigger.
                    return Ok(());
                }
                if value["sessionId"].as_str() != state.session.as_deref() {
                    return Err(notification_failure.fail());
                }
                match kind {
                    Some("usage_update") => notification_progress.usage(&value["update"]),
                    Some("agent_message_chunk") => {
                        state.chunks += 1;
                        if state.chunks == 1 || state.chunks % 128 == 0 {
                            notification_progress.event(format!("attempt=1 assistant activity; chunks={}", state.chunks));
                        }
                        if let Some(text) = value["update"]["content"]["text"].as_str() {
                            if state.text.len() + text.len() > 1_000_000 {
                                return Err(notification_failure.fail());
                            }
                            state.text.push_str(text);
                        }
                    }
                    Some("tool_call" | "tool_call_update") => {
                        state.tools += 1;
                        if state.tools <= 16 || state.tools % 128 == 0 {
                            notification_progress.event(format!("attempt=1 tool activity; events={}", state.tools));
                        }
                        let update = &value["update"];
                        if let Some(id) = update["toolCallId"].as_str() {
                            if (update["status"].is_null()
                                || matches!(
                                    update["status"].as_str(),
                                    Some("pending" | "in_progress")
                                ))
                                && update["rawInput"].is_object()
                                && update["kind"].is_string()
                            {
                                if state.calls.len() >= 4096 {
                                    return Err(notification_failure.fail());
                                }
                                state.calls.insert(id.to_owned(), update.clone());
                            } else if matches!(
                                update["status"].as_str(),
                                Some("completed" | "failed")
                            ) {
                                state.calls.remove(id);
                            }
                        }
                        if policy == Permissions::Deny
                            && matches!(
                                value["update"]["status"].as_str(),
                                Some("in_progress" | "completed")
                            )
                        {
                            return Err(notification_failure.fail());
                        }
                    }
                    _ => {}
                }
                Ok(())
            },
            agent_client_protocol::on_receive_notification!(),
        )
        .on_receive_request(
            async move |request: RequestPermissionRequest, responder, _cx| {
                let value = serde_json::to_value(&request)?;
                let mut state = permissions.lock().unwrap();
                let id = value["toolCall"]["toolCallId"]
                    .as_str()
                    .unwrap_or("")
                    .to_owned();
                if id.trim().is_empty()
                    || value["sessionId"].as_str() != state.session.as_deref()
                    || state.seen.len() >= 4096
                    || !state.seen.insert(value["toolCall"].to_string())
                {
                    return Err(permission_failure.fail());
                }
                let options = request
                    .options
                    .iter()
                    .map(|option| PolicyOption {
                        id: option.option_id.to_string(),
                        kind: match option.kind {
                            PermissionOptionKind::AllowOnce => OptionKind::AllowOnce,
                            PermissionOptionKind::AllowAlways => OptionKind::AllowAlways,
                            PermissionOptionKind::RejectOnce
                            | PermissionOptionKind::RejectAlways => OptionKind::Deny,
                            _ => OptionKind::Unknown,
                        },
                    })
                    .collect();
                // Complete serialized descriptor is bound to a fresh per-request grant, never logged.
                let descriptor = state.calls.get(&id);
                let complete = descriptor.is_some_and(|tool| {
                    tool["rawInput"].as_object().is_some_and(|v| !v.is_empty())
                        && matches!(
                            tool["kind"].as_str(),
                            Some("read" | "search" | "edit" | "execute")
                        )
                });
                let normalized = PermissionRequest {
                    id: format!("{}:{id}", state.seen.len()),
                    action:
                        serde_json::json!({"permission": value["toolCall"], "tool": descriptor})
                            .to_string(),
                    options,
                };
                let supported = descriptor.is_some_and(|tool| {
                    tool["kind"] == value["toolCall"]["kind"]
                        && consistent_metadata(&value["toolCall"]["rawInput"], &tool["rawInput"])
                }) && matches!(
                    value["toolCall"]["kind"].as_str(),
                    Some("read" | "search" | "edit" | "execute")
                );
                // Only external_directory can produce `other` in this verified
                // profile. Pin its exact v1.18.30 metadata shape; never approve
                // arbitrary `other` tools or infer semantics from their titles.
                let external = verified_external(&value["toolCall"], descriptor);
                let described = complete;
                let mut policy =
                    if policy == Permissions::Trusted
                        && !permission_cancel.is_cancelled()
                        && tokio::time::Instant::now() < permission_deadline
                        && (supported || external) && described {
                        PermissionPolicy::grant_next_request(normalized.clone())
                    } else {
                        PermissionPolicy::default()
                    };
                let outcome = match policy.respond(&normalized) {
                    PermissionResponse::Selected(id) => {
                        if request.options.iter().any(|o| {
                            o.option_id.to_string() == id
                                && o.kind == PermissionOptionKind::AllowOnce
                        }) {
                            state.granted += 1;
                            if value["toolCall"]["kind"] == "edit" {
                                let mut paths = Vec::new();
                                for input in [
                                    &value["toolCall"]["rawInput"],
                                    &state
                                        .calls
                                        .get(value["toolCall"]["toolCallId"].as_str().unwrap_or(""))
                                        .unwrap_or(&Value::Null)["rawInput"],
                                ] {
                                    for key in ["filePath", "filepath"] {
                                        if let Some(path) = input[key].as_str() {
                                            paths.push(path.to_owned());
                                        }
                                    }
                                }
                                state.edit_paths.extend(paths);
                            }
                        }
                        RequestPermissionOutcome::Selected(SelectedPermissionOutcome::new(id))
                    }
                    PermissionResponse::Cancelled => RequestPermissionOutcome::Cancelled,
                    PermissionResponse::Refused => return Err(permission_failure.fail()),
                };
                state.permissions += 1;
                if state.permissions <= 16 || state.permissions % 128 == 0 {
                    permission_progress.event(format!("attempt=1 headless permission response; requests={}; grants={}", state.permissions, state.granted));
                }
                responder
                    .respond(RequestPermissionResponse::new(outcome))
                    .map_err(|_| permission_failure.fail())
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                async move |_request: ReadTextFileRequest, _responder, _cx| {
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                let writes = observed.clone();
                async move |request: WriteTextFileRequest, _responder, _cx| {
                    let value = serde_json::to_value(request)?;
                    let mut state = writes.lock().unwrap();
                    if policy == Permissions::Trusted
                        && value["sessionId"].as_str() == state.session.as_deref()
                        && value["path"]
                            .as_str()
                            .is_some_and(|path| state.edit_paths.remove(path))
                    {
                        // v1.18.30 sends this optional editor synchronization even
                        // when fs capability is absent. Refuse client-side I/O;
                        // its built-in edit tool still owns the authorized edit.
                        return Err(agent_client_protocol::Error::internal_error());
                    }
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                async move |_request: CreateTerminalRequest, _responder, _cx| {
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                async move |_request: TerminalOutputRequest, _responder, _cx| {
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                async move |_request: ReleaseTerminalRequest, _responder, _cx| {
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                async move |_request: KillTerminalRequest, _responder, _cx| {
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .on_receive_request(
            {
                let failure = violation.clone();
                async move |_request: WaitForTerminalExitRequest, _responder, _cx| {
                    Err::<(), _>(failure.fail())
                }
            },
            agent_client_protocol::on_receive_request!(),
        )
        .connect_with(transport, async move |cx| {
            let init = cx
                .send_request(InitializeRequest::new(ProtocolVersion::V1))
                .block_task()
                .await?;
            if init.protocol_version != ProtocolVersion::V1 {
                return Err(agent_client_protocol::Error::internal_error());
            }
            let session = cx
                .send_request(NewSessionRequest::new(project.to_owned()))
                .block_task()
                .await?;
            let value = serde_json::to_value(&session)?;
            let models: Vec<&Value> = value["configOptions"]
                .as_array()
                .into_iter()
                .flatten()
                .filter(|x| x["id"] == "model")
                .collect();
            if models.len() != 1 || models[0]["currentValue"] != target {
                return Err(agent_client_protocol::Error::internal_error());
            }
            foreground.lock().unwrap().session = Some(session.session_id.to_string());
            // Session IDs are opaque backend data: JSON escaping and a length
            // bound plus non-ASCII escaping prevent terminal injection and
            // unbounded diagnostics (including C1 controls and bidi overrides).
            foreground_progress.event(format!("attempt=1 session={}", serde_json::to_string(&session.session_id.to_string().chars().take(128).map(|c| if c.is_ascii() { c.to_string() } else { c.escape_unicode().to_string() }).collect::<String>()).unwrap()));
            if runtime.cancelled.is_cancelled() || tokio::time::Instant::now() >= runtime.deadline {
                return Err(agent_client_protocol::Error::internal_error());
            }
            sent.store(true, Ordering::SeqCst);
            foreground_progress.event("attempt=1 prompt submitted");
            let response = cx
                .send_request(PromptRequest::new(
                    session.session_id.clone(),
                    vec![ContentBlock::Text(TextContent::new(prompt.clone()))],
                ))
                .block_task();
            tokio::pin!(response);
            let result = tokio::select! {
                result = &mut response => result?,
                _ = runtime.cancelled.cancelled() => {
                    foreground_progress.event("attempt=1 signal; sending session/cancel (5s response budget)");
                    cx.send_notification(CancelNotification::new(session.session_id.clone()))?;
                    tokio::time::timeout(std::time::Duration::from_secs(5), &mut response).await
                        .map_err(|_| agent_client_protocol::Error::internal_error())??
                },
                _ = tokio::time::sleep_until(runtime.deadline) => {
                    foreground_progress.event("attempt=1 deadline; sending session/cancel (5s response budget)");
                    cx.send_notification(CancelNotification::new(session.session_id.clone()))?;
                    tokio::time::timeout(std::time::Duration::from_secs(5), &mut response).await
                        .map_err(|_| agent_client_protocol::Error::internal_error())??
                },
            };
            let stop = serde_json::to_value(&result)?;
            foreground_progress.event(match stop["stopReason"].as_str() {
                Some("end_turn") => "attempt=1 backend terminal=end_turn",
                Some("cancelled") => "attempt=1 backend terminal=cancelled; project effects may remain",
                _ => "attempt=1 backend terminal=failure (turn limit or refusal)",
            });
            finished.store(match stop["stopReason"].as_str() {
                Some("end_turn") => 1,
                Some("cancelled") => 3,
                _ => 2,
            }, Ordering::SeqCst);
            Ok(())
        });
    tokio::pin!(connection);
    let mut heartbeat = tokio::time::interval(std::time::Duration::from_secs(5));
    heartbeat.tick().await;
    let result = loop {
        tokio::select! {
            value = &mut connection => break value.is_ok(),
            // Once active, the foreground sends session/cancel and awaits a
            // terminal response. Before active, interruption needs no protocol ACK.
            _ = runtime.cancelled.cancelled(), if !active.load(Ordering::SeqCst) => { if !active.load(Ordering::SeqCst) { break false; } },
            _ = tokio::time::sleep_until(runtime.deadline), if !active.load(Ordering::SeqCst) => { if !active.load(Ordering::SeqCst) { break false; } },
            _ = violation.wake.notified() => {
                runtime.progress.event("attempt=1 protocol/callback/output limit failure");
                break false;
            },
            _ = heartbeat.tick() => {
                let state = observed.lock().unwrap();
                runtime.progress.event(format!("attempt=1 active; chunks={}; tools={}; permissions={}", state.chunks, state.tools, state.permissions));
            }
        }
    };
    if !result && !violation.failed.load(Ordering::SeqCst) {
        runtime.progress.event(if active.load(Ordering::SeqCst) {
            "attempt=1 runtime/provider/transport failure or cancellation response timeout; effects unknown"
        } else { "attempt=1 setup stopped before prompt submission" });
    }
    runtime.progress.event("attempt=1 process cleanup started");
    let cleanup = owned.cleanup().await;
    {
        let state = observed.lock().unwrap();
        runtime.progress.event(format!(
            "attempt=1 cleanup={cleanup}; terminal={}; protocol_violation={}; permission requests: {}; grants: {}; tool events: {}; stderr_bytes={} (raw withheld; count capped at 1048577)",
            terminal.load(Ordering::SeqCst), violation.failed.load(Ordering::SeqCst),
            state.permissions, state.granted, state.tools, owned.stderr_bytes()
        ));
    }
    if !cleanup
        || (active.load(Ordering::SeqCst)
            && (terminal.load(Ordering::SeqCst) == 0 || violation.failed.load(Ordering::SeqCst)))
    {
        return Exit::Uncertain;
    }
    if violation.failed.load(Ordering::SeqCst) {
        return Exit::Failed;
    }
    if terminal.load(Ordering::SeqCst) == 3 {
        return Exit::Cancelled;
    }
    if terminal.load(Ordering::SeqCst) == 2 {
        return Exit::Failed;
    }
    if terminal.load(Ordering::SeqCst) == 0 && !result {
        return if runtime.cancelled.is_cancelled()
            || tokio::time::Instant::now() >= runtime.deadline
        {
            Exit::Cancelled
        } else {
            Exit::Failed
        };
    }
    runtime.progress.event(
        "attempt=1 backend end_turn; cleanup confirmed; delivering response (2s output budget)",
    );
    let text = std::mem::take(&mut observed.lock().unwrap().text);
    if !crate::progress::response(text).await {
        runtime.progress.event("attempt=1 final response delivery failed or blocked; backend completed, output may be partial");
        return Exit::Failed;
    }
    Exit::Success
}

fn verified_external(permission: &Value, descriptor: Option<&Value>) -> bool {
    use std::path::Path;
    let Some(tool) = descriptor else {
        return false;
    };
    if permission["kind"] != "other" {
        return false;
    }
    let Some(raw) = permission["rawInput"].as_object() else {
        return false;
    };
    if raw.len() == 2 {
        let (Some(file), Some(parent)) = (
            raw.get("filepath").and_then(Value::as_str),
            raw.get("parentDir").and_then(Value::as_str),
        ) else {
            return false;
        };
        let path = Path::new(file);
        let parent = Path::new(parent);
        return path.is_absolute()
            && parent.is_absolute()
            && (path.parent() == Some(parent) || path == parent)
            && ["filePath", "path", "filepath"]
                .iter()
                .any(|key| tool["rawInput"][key].as_str() == Some(file));
    }
    if raw.len() != 3 || tool["kind"] != "execute" {
        return false;
    }
    let Some(command) = raw.get("command").and_then(Value::as_str) else {
        return false;
    };
    if command.trim().is_empty() || tool["rawInput"]["command"] != command {
        return false;
    }
    let (Some(dirs), Some(patterns)) = (
        raw.get("directories").and_then(Value::as_array),
        raw.get("patterns").and_then(Value::as_array),
    ) else {
        return false;
    };
    !dirs.is_empty()
        && dirs.len() == patterns.len()
        && dirs.iter().zip(patterns).all(|(dir, pattern)| {
            let (Some(dir), Some(pattern)) = (dir.as_str(), pattern.as_str()) else {
                return false;
            };
            Path::new(dir).is_absolute()
                && Path::new(pattern).parent() == Some(Path::new(dir))
                && Path::new(pattern)
                    .file_name()
                    .is_some_and(|name| name == "*")
        })
}

/// Pinned callbacks can add generated metadata (e.g. an edit diff), while read
/// metadata is empty. Shared arguments and normalized path aliases must agree.
fn consistent_metadata(metadata: &Value, arguments: &Value) -> bool {
    if metadata.is_null() {
        return arguments.is_object();
    }
    let (Some(metadata), Some(arguments)) = (metadata.as_object(), arguments.as_object()) else {
        return false;
    };
    metadata.iter().all(|(key, value)| {
        if let Some(argument) = arguments.get(key) {
            return argument == value;
        }
        if key == "filepath" {
            return arguments.get("filePath") == Some(value);
        }
        true
    })
}

#[cfg(test)]
mod tests {
    use super::{consistent_metadata, verified_external};
    use serde_json::json;

    #[test]
    fn permission_metadata_rejects_changed_arguments_and_path_aliases() {
        let args = json!({"filePath":"/tmp/file","command":"true"});
        assert!(consistent_metadata(&json!({}), &args));
        assert!(consistent_metadata(&json!(null), &args));
        assert!(!consistent_metadata(&json!([]), &args));
        assert!(consistent_metadata(
            &json!({"filepath":"/tmp/file","diff":"generated"}),
            &args
        ));
        assert!(!consistent_metadata(
            &json!({"filePath":"/tmp/other"}),
            &args
        ));
        assert!(!consistent_metadata(
            &json!({"filepath":"/tmp/other"}),
            &args
        ));
        assert!(!consistent_metadata(&json!({"command":"false"}), &args));
    }

    #[test]
    fn external_shell_metadata_must_bind_command_and_each_directory_pattern() {
        let tool = json!({"kind":"execute","rawInput":{"command":"cat /tmp/example"}});
        let request = json!({"kind":"other","rawInput":{"command":"cat /tmp/example","directories":["/tmp"],"patterns":["/tmp/*"]}});
        assert!(verified_external(&request, Some(&tool)));
        for (field, value) in [
            ("command", json!("different")),
            ("patterns", json!(["/elsewhere/*"])),
            ("patterns", json!([])),
            ("directories", json!(["relative"])),
        ] {
            let mut malformed = request.clone();
            malformed["rawInput"][field] = value;
            assert!(!verified_external(&malformed, Some(&tool)));
        }
        assert!(!verified_external(&request, None));
        assert!(!verified_external(
            &request,
            Some(&json!({"kind":"read","rawInput":{"command":"cat /tmp/example"}}))
        ));
    }

    #[test]
    fn external_file_metadata_must_match_the_bound_tool_target() {
        let tool = json!({"kind":"read","rawInput":{"filePath":"/tmp/example"}});
        let mut request =
            json!({"kind":"other","rawInput":{"filepath":"/tmp/example","parentDir":"/tmp"}});
        assert!(verified_external(&request, Some(&tool)));
        request["rawInput"]["filepath"] = json!("/tmp/different");
        assert!(!verified_external(&request, Some(&tool)));
        request["rawInput"]["filepath"] = json!("/tmp/example");
        request["rawInput"]["parentDir"] = json!("/elsewhere");
        assert!(!verified_external(&request, Some(&tool)));
    }
}
