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
use std::collections::HashMap;
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
    seen: HashMap<String, u8>,
    calls: HashMap<String, Value>,
    granted: usize,
}

pub(crate) async fn run(runtime: &Runtime, request: &Resolved) -> Exit {
    if runtime.cancelled.is_cancelled() || tokio::time::Instant::now() >= runtime.deadline {
        return Exit::Cancelled;
    }
    let project = &request.project;
    let target = request.runtime_model();
    let prompt = &request.prompt;
    let policy = request.permissions;
    // 2.2.5 `acp` takes no project flags: the working directory and
    // session/new cwd select the project, and it spawns its own private
    // `serve --stdio` child inside the owned process group.
    let mut command = runtime.command(project, &["acp"]);
    let mut owned = match OwnedChild::spawn(&mut command) {
        Ok(child) => child,
        Err(_) => {
            runtime.progress.event("launch failed; no prompt submitted");
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
                            notification_progress.event(format!("assistant activity; chunks={}", state.chunks));
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
                            notification_progress.event(format!("tool activity; events={}", state.tools));
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
                        // 2.2.5 reports `in_progress` while parsing arguments, before
                        // availability is checked; only completion proves execution.
                        if policy == Permissions::Deny
                            && value["update"]["status"].as_str() == Some("completed")
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
                // External-directory and tool checks each raise a byte-identical
                // request for one call; a third copy is a replay.
                let repeats = state.seen.len();
                let copies = {
                    let copies = state.seen.entry(value["toolCall"].to_string()).or_default();
                    *copies += 1;
                    *copies
                };
                if id.trim().is_empty()
                    || value["sessionId"].as_str() != state.session.as_deref()
                    || repeats >= 4096
                    || copies > 2
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
                let normalized = PermissionRequest {
                    id: format!("{}:{copies}:{id}", state.seen.len()),
                    action:
                        serde_json::json!({"permission": value["toolCall"], "tool": descriptor})
                            .to_string(),
                    options,
                };
                let mut policy =
                    if policy == Permissions::Trusted
                        && !permission_cancel.is_cancelled()
                        && tokio::time::Instant::now() < permission_deadline
                        && bound(&value["toolCall"], descriptor) {
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
                        }
                        RequestPermissionOutcome::Selected(SelectedPermissionOutcome::new(id))
                    }
                    PermissionResponse::Cancelled => RequestPermissionOutcome::Cancelled,
                    PermissionResponse::Refused => return Err(permission_failure.fail()),
                };
                state.permissions += 1;
                if state.permissions <= 16 || state.permissions % 128 == 0 {
                    permission_progress.event(format!("headless permission response; requests={}; grants={}", state.permissions, state.granted));
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
                // 2.2.5 sends no editor synchronization; client-side I/O is never offered.
                let failure = violation.clone();
                async move |_request: WriteTextFileRequest, _responder, _cx| {
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
            foreground_progress.event(format!("session={}", serde_json::to_string(&session.session_id.to_string().chars().take(128).map(|c| if c.is_ascii() { c.to_string() } else { c.escape_unicode().to_string() }).collect::<String>()).unwrap()));
            if runtime.cancelled.is_cancelled() || tokio::time::Instant::now() >= runtime.deadline {
                return Err(agent_client_protocol::Error::internal_error());
            }
            sent.store(true, Ordering::SeqCst);
            foreground_progress.event("prompt submitted");
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
                    foreground_progress.event("signal; sending session/cancel (5s response budget)");
                    cx.send_notification(CancelNotification::new(session.session_id.clone()))?;
                    tokio::time::timeout(std::time::Duration::from_secs(5), &mut response).await
                        .map_err(|_| agent_client_protocol::Error::internal_error())??
                },
                _ = tokio::time::sleep_until(runtime.deadline) => {
                    foreground_progress.event("deadline; sending session/cancel (5s response budget)");
                    cx.send_notification(CancelNotification::new(session.session_id.clone()))?;
                    tokio::time::timeout(std::time::Duration::from_secs(5), &mut response).await
                        .map_err(|_| agent_client_protocol::Error::internal_error())??
                },
            };
            let stop = serde_json::to_value(&result)?;
            foreground_progress.event(match stop["stopReason"].as_str() {
                Some("end_turn") => "backend terminal=end_turn",
                Some("cancelled") => "backend terminal=cancelled; project effects may remain",
                _ => "backend terminal=failure (turn limit or refusal)",
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
                runtime.progress.event("protocol/callback/output limit failure");
                break false;
            },
            _ = heartbeat.tick() => {
                let state = observed.lock().unwrap();
                runtime.progress.event(format!("active; chunks={}; tools={}; permissions={}", state.chunks, state.tools, state.permissions));
            }
        }
    };
    if !result && !violation.failed.load(Ordering::SeqCst) {
        runtime.progress.event(if active.load(Ordering::SeqCst) {
            "runtime/provider/transport failure or cancellation response timeout; effects unknown"
        } else {
            "setup stopped before prompt submission"
        });
    }
    runtime.progress.event("process cleanup started");
    let cleanup = owned.cleanup().await;
    {
        let state = observed.lock().unwrap();
        runtime.progress.event(format!(
            "cleanup={cleanup}; terminal={}; protocol_violation={}; permission requests: {}; grants: {}; tool events: {}; stderr_bytes={} (raw withheld; count capped at 1048577)",
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
    runtime
        .progress
        .event("backend end_turn; cleanup confirmed; delivering response (2s output budget)");
    let text = std::mem::take(&mut observed.lock().unwrap().text);
    if !crate::progress::response(text).await {
        runtime.progress.event(
            "final response delivery failed or blocked; backend completed, output may be partial",
        );
        return Exit::Failed;
    }
    Exit::Success
}

/// A grant binds one request to the latest announced arguments of the same
/// tool call. Only the verified 2.2.5 built-in kinds qualify; `other` (for
/// example worktree removal) is always refused. Titles are never interpreted.
fn bound(permission: &Value, descriptor: Option<&Value>) -> bool {
    descriptor.is_some_and(|tool| {
        tool["kind"] == permission["kind"]
            && matches!(
                permission["kind"].as_str(),
                Some("read" | "search" | "edit" | "execute")
            )
            && permission["rawInput"]
                .as_object()
                .is_some_and(|raw| !raw.is_empty())
            && tool["rawInput"] == permission["rawInput"]
    })
}

#[cfg(test)]
mod tests {
    use super::bound;
    use serde_json::json;

    #[test]
    fn grants_bind_exact_arguments_of_a_supported_kind() {
        let tool =
            json!({"kind":"edit","rawInput":{"path":"/tmp/file","oldString":"a","newString":"b"}});
        let request = json!({"kind":"edit","title":"/tmp/file","rawInput":{"path":"/tmp/file","oldString":"a","newString":"b"},
                             "content":[{"type":"diff","path":"/tmp/file"}]});
        assert!(bound(&request, Some(&tool)));
        assert!(!bound(&request, None));
        for (field, value) in [
            ("kind", json!("execute")),
            (
                "rawInput",
                json!({"path":"/tmp/other","oldString":"a","newString":"b"}),
            ),
            ("rawInput", json!({"path":"/tmp/file"})),
            ("rawInput", json!({})),
            ("rawInput", json!(null)),
        ] {
            let mut changed = request.clone();
            changed[field] = value;
            assert!(!bound(&changed, Some(&tool)), "{field}");
        }
        // A pending announcement without arguments never authorizes a request.
        assert!(!bound(
            &request,
            Some(&json!({"kind":"edit","rawInput":{}}))
        ));
    }

    #[test]
    fn other_kinds_are_never_granted() {
        let raw = json!({"directory":"/tmp/worktree"});
        let tool = json!({"kind":"other","rawInput":raw});
        assert!(!bound(&json!({"kind":"other","rawInput":raw}), Some(&tool)));
    }
}
