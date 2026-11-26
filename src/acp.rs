//! ACP adapter; OpenCode owns the coding loop and tools.
use crate::permission::{
    OptionKind, PermissionOption as PolicyOption, PermissionPolicy, PermissionRequest,
    PermissionResponse,
};
use crate::{
    config::{Exit, Resolved},
    process::OwnedChild,
    runtime::Runtime,
};
use agent_client_protocol::schema::{ProtocolVersion, v1::*};
use agent_client_protocol::{ByteStreams, Client};
use serde_json::{Value, json};
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
    /// Announced kind per tool call, for checking completions of a named role.
    kinds: HashMap<String, String>,
    granted: usize,
}
impl Observed {
    /// Cumulative counters, so a dropped activity record loses nothing.
    fn counters(&self) -> Value {
        json!({"assistant_chunks": self.chunks, "tool_events": self.tools,
               "permission_requests": self.permissions, "grants": self.granted})
    }
}

/// Closed post-submission ACP error label (D107). Call-site values are never
/// returned by [`classify_acp_error`].
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AcpError {
    ParseError,
    InvalidRequest,
    MethodNotFound,
    InvalidParams,
    InternalError,
    RequestCancelled,
    AuthRequired,
    ResourceNotFound,
    Other,
    ResponseTimeout,
    Unknown,
}

impl AcpError {
    fn as_str(self) -> &'static str {
        match self {
            Self::ParseError => "parse_error",
            Self::InvalidRequest => "invalid_request",
            Self::MethodNotFound => "method_not_found",
            Self::InvalidParams => "invalid_params",
            Self::InternalError => "internal_error",
            Self::RequestCancelled => "request_cancelled",
            Self::AuthRequired => "auth_required",
            Self::ResourceNotFound => "resource_not_found",
            Self::Other => "other",
            Self::ResponseTimeout => "response_timeout",
            Self::Unknown => "unknown",
        }
    }
}

/// Closed post-submission ACP data label (D107).
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
enum AcpData {
    Absent,
    Unclassified,
    GoLimit,
}

impl AcpData {
    fn as_str(self) -> &'static str {
        match self {
            Self::Absent => "absent",
            Self::Unclassified => "unclassified",
            Self::GoLimit => "go_limit",
        }
    }
}

/// Pure classifier of a peer ACP `Error`. Drops `message` and all non-allowlisted
/// `data`; never returns `response_timeout` or `unknown`.
fn classify_acp_error(error: &agent_client_protocol::Error) -> (AcpError, AcpData) {
    let acp_error = match error.code {
        ErrorCode::ParseError => AcpError::ParseError,
        ErrorCode::InvalidRequest => AcpError::InvalidRequest,
        ErrorCode::MethodNotFound => AcpError::MethodNotFound,
        ErrorCode::InvalidParams => AcpError::InvalidParams,
        ErrorCode::InternalError => AcpError::InternalError,
        ErrorCode::RequestCancelled => AcpError::RequestCancelled,
        ErrorCode::AuthRequired => AcpError::AuthRequired,
        ErrorCode::ResourceNotFound => AcpError::ResourceNotFound,
        // Non-exhaustive: any future code is retained as the closed `other` label.
        ErrorCode::Other(_) | _ => AcpError::Other,
    };
    let acp_data = match (&acp_error, error.data.as_ref()) {
        (_, None) | (_, Some(Value::Null)) => AcpData::Absent,
        (AcpError::InternalError, Some(Value::Object(obj)))
            if obj.get("service").and_then(Value::as_str) == Some("session")
                && obj.get("errorName").and_then(Value::as_str) == Some("provider.go-limit") =>
        {
            AcpData::GoLimit
        }
        _ => AcpData::Unclassified,
    };
    (acp_error, acp_data)
}

/// First write wins, except a peer classification replaces `response_timeout`.
fn record_acp_labels(
    slot: &Mutex<Option<(AcpError, AcpData)>>,
    next: (AcpError, AcpData),
    peer: bool,
) {
    let mut guard = slot.lock().unwrap();
    match *guard {
        None => *guard = Some(next),
        Some((AcpError::ResponseTimeout, _)) if peer => *guard = Some(next),
        Some(_) => {}
    }
}

pub(crate) async fn run(runtime: &Runtime, request: &Resolved) -> Exit {
    if runtime.cancelled.is_cancelled() || tokio::time::Instant::now() >= runtime.deadline {
        return Exit::Cancelled;
    }
    let project = &request.project;
    let target = runtime.target(request);
    let prompt = &request.prompt;
    // Kinds the effective rules may grant; a named role also fails on a
    // completed call of any other kind, independently of backend rules.
    let grantable = crate::opencode::grantable(request);
    let restricted = request.agent.is_some();
    let permission_kinds = grantable.clone();
    let agent = request.agent.as_ref().map(|a| a.name().to_owned());
    // 2.3.0 `acp` takes no project flags: the working directory and
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
    runtime.progress.note(json!({"launched": true}));
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
    let labels = Arc::new(Mutex::new(None::<(AcpError, AcpData)>));
    let prompt_labels = labels.clone();
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
                            notification_progress.emit("attempt.activity", state.counters());
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
                            notification_progress.emit("attempt.activity", state.counters());
                        }
                        let update = &value["update"];
                        let mut completed_kind = None;
                        if let Some(id) = update["toolCallId"].as_str() {
                            if let Some(kind) = update["kind"].as_str() {
                                if state.kinds.len() >= 4096 && !state.kinds.contains_key(id) {
                                    return Err(notification_failure.fail());
                                }
                                state.kinds.insert(id.to_owned(), kind.to_owned());
                            }
                            match update["status"].as_str() {
                                Some("completed") => completed_kind = state.kinds.remove(id),
                                Some("failed") => {
                                    state.kinds.remove(id);
                                }
                                _ => {}
                            }
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
                        // 2.3.0 reports `in_progress` while parsing arguments, before
                        // availability is checked; only completion proves execution.
                        // An unknown kind under a named role fails closed.
                        if value["update"]["status"].as_str() == Some("completed")
                            && (grantable.is_empty()
                                || (restricted
                                    && !completed_kind
                                        .is_some_and(|kind| grantable.contains(&kind.as_str()))))
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
                    if value["toolCall"]["kind"]
                        .as_str()
                        .is_some_and(|kind| permission_kinds.contains(&kind))
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
                    permission_progress.emit("attempt.activity", state.counters());
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
                // 2.3.0 sends no editor synchronization; client-side I/O is never offered.
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
            // 2.3.0 silently falls back to `build` when the default agent is
            // unusable; a named role must be the session's selected mode.
            if let Some(agent) = &agent {
                let modes: Vec<&Value> = value["configOptions"]
                    .as_array()
                    .into_iter()
                    .flatten()
                    .filter(|x| x["id"] == "mode")
                    .collect();
                if modes.len() != 1 || modes[0]["currentValue"] != agent.as_str() {
                    return Err(agent_client_protocol::Error::internal_error());
                }
            }
            foreground.lock().unwrap().session = Some(session.session_id.to_string());
            // Session IDs are opaque backend data: JSON escaping and a length
            // bound plus non-ASCII escaping prevent terminal injection and
            // unbounded diagnostics (including C1 controls and bidi overrides).
            let escaped = session.session_id.to_string().chars().take(128).map(|c| if c.is_ascii() { c.to_string() } else { c.escape_unicode().to_string() }).collect::<String>();
            foreground_progress.event(format!("session={}", serde_json::to_string(&escaped).unwrap()));
            foreground_progress.note(json!({"session": escaped}));
            foreground_progress.emit("attempt.session", json!({"session": escaped}));
            if runtime.cancelled.is_cancelled() || tokio::time::Instant::now() >= runtime.deadline {
                return Err(agent_client_protocol::Error::internal_error());
            }
            sent.store(true, Ordering::SeqCst);
            foreground_progress.event("prompt submitted");
            foreground_progress.note(json!({"prompt_submitted": true}));
            foreground_progress.emit("attempt.prompt_submitted", json!({}));
            let response = cx
                .send_request(PromptRequest::new(
                    session.session_id.clone(),
                    vec![ContentBlock::Text(TextContent::new(prompt.clone()))],
                ))
                .block_task();
            tokio::pin!(response);
            // Capture peer ACP errors before `is_ok()` drops them (D107). Elapsed
            // cancel/deadline budgets record response_timeout at the arm and do
            // not classify the synthetic InternalError.
            let result = tokio::select! {
                result = &mut response => match result {
                    Ok(ok) => ok,
                    Err(err) => {
                        record_acp_labels(&prompt_labels, classify_acp_error(&err), true);
                        return Err(err);
                    }
                },
                _ = runtime.cancelled.cancelled() => {
                    foreground_progress.event("signal; sending session/cancel (5s response budget)");
                    cx.send_notification(CancelNotification::new(session.session_id.clone()))?;
                    match tokio::time::timeout(std::time::Duration::from_secs(5), &mut response)
                        .await
                    {
                        Ok(Ok(ok)) => ok,
                        Ok(Err(err)) => {
                            record_acp_labels(&prompt_labels, classify_acp_error(&err), true);
                            return Err(err);
                        }
                        Err(_) => {
                            record_acp_labels(
                                &prompt_labels,
                                (AcpError::ResponseTimeout, AcpData::Absent),
                                false,
                            );
                            return Err(agent_client_protocol::Error::internal_error());
                        }
                    }
                },
                _ = tokio::time::sleep_until(runtime.deadline) => {
                    foreground_progress.event("deadline; sending session/cancel (5s response budget)");
                    cx.send_notification(CancelNotification::new(session.session_id.clone()))?;
                    match tokio::time::timeout(std::time::Duration::from_secs(5), &mut response)
                        .await
                    {
                        Ok(Ok(ok)) => ok,
                        Ok(Err(err)) => {
                            record_acp_labels(&prompt_labels, classify_acp_error(&err), true);
                            return Err(err);
                        }
                        Err(_) => {
                            record_acp_labels(
                                &prompt_labels,
                                (AcpError::ResponseTimeout, AcpData::Absent),
                                false,
                            );
                            return Err(agent_client_protocol::Error::internal_error());
                        }
                    }
                },
            };
            let stop = serde_json::to_value(&result)?;
            foreground_progress.event(match stop["stopReason"].as_str() {
                Some("end_turn") => "backend terminal=end_turn",
                Some("cancelled") => "backend terminal=cancelled; project effects may remain",
                _ => "backend terminal=failure (turn limit or refusal)",
            });
            let backend_stop = match stop["stopReason"].as_str() {
                Some("end_turn") => "end_turn",
                Some("cancelled") => "cancelled",
                _ => "other",
            };
            foreground_progress.note(json!({"backend_stop": backend_stop}));
            foreground_progress.emit("attempt.backend_stop", json!({"backend_stop": backend_stop}));
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
                runtime.progress.emit("attempt.activity", state.counters());
            }
        }
    };
    if !result && !violation.failed.load(Ordering::SeqCst) {
        if active.load(Ordering::SeqCst) {
            let mut slot = labels.lock().unwrap();
            let (acp_error, acp_data) =
                *slot.get_or_insert((AcpError::Unknown, AcpData::Absent));
            drop(slot);
            runtime.progress.event(format!(
                "runtime/provider/transport failure or cancellation response timeout; effects unknown; acp_error={}; acp_data={}",
                acp_error.as_str(),
                acp_data.as_str()
            ));
            let fields = json!({
                "acp_error": acp_error.as_str(),
                "acp_data": acp_data.as_str(),
            });
            runtime.progress.note(fields.clone());
            runtime.progress.emit("attempt.acp_error", fields);
        } else {
            runtime.progress.event("setup stopped before prompt submission");
        }
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
        let summary = json!({
            "cleanup_confirmed": cleanup,
            "permission_requests": state.permissions,
            "grants": state.granted,
            "tool_events": state.tools,
            "protocol_violation": violation.failed.load(Ordering::SeqCst),
        });
        runtime.progress.note(summary.clone());
        runtime.progress.emit("attempt.cleanup", summary);
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
    #[cfg(test)]
    if runtime.is_go_candidate() {
        let state = observed.lock().unwrap();
        if state.permissions != 0 || state.tools != 0 {
            runtime
                .progress
                .event("Go candidate observed tool activity; no-tool acceptance not met");
            return Exit::Failed;
        }
    }
    runtime
        .progress
        .event("backend end_turn; cleanup confirmed; delivering response (2s output budget)");
    let text = std::mem::take(&mut observed.lock().unwrap().text);
    if !runtime.progress.deliver(text).await {
        runtime.progress.event(
            "final response delivery failed or blocked; backend completed, output may be partial",
        );
        return Exit::Failed;
    }
    Exit::Success
}

/// A grant binds one request to the latest announced arguments of the same
/// tool call. Only the verified 2.3.0 built-in kinds qualify; `other` (for
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
    use super::{
        AcpData, AcpError, bound, classify_acp_error, record_acp_labels,
    };
    use agent_client_protocol::{Error, ErrorCode};
    use serde_json::{Value, json};
    use std::sync::Mutex;

    const SECRET: &str = "SECRET_SENTINEL";

    fn assert_labels(error: &Error, expected: (AcpError, AcpData)) {
        let got = classify_acp_error(error);
        assert_eq!(got, expected);
        let rendered = format!("acp_error={}; acp_data={}", got.0.as_str(), got.1.as_str());
        assert!(!rendered.contains(SECRET), "{rendered}");
        assert!(!format!("{got:?}").contains(SECRET));
        assert_ne!(got.0, AcpError::ResponseTimeout);
        assert_ne!(got.0, AcpError::Unknown);
    }

    #[test]
    fn classify_known_codes_drop_canary_message_and_data() {
        let canary = json!({SECRET: true, "nested": SECRET});
        for (code, label) in [
            (ErrorCode::ParseError, AcpError::ParseError),
            (ErrorCode::InvalidRequest, AcpError::InvalidRequest),
            (ErrorCode::MethodNotFound, AcpError::MethodNotFound),
            (ErrorCode::InvalidParams, AcpError::InvalidParams),
            (ErrorCode::InternalError, AcpError::InternalError),
            (ErrorCode::RequestCancelled, AcpError::RequestCancelled),
            (ErrorCode::AuthRequired, AcpError::AuthRequired),
            (ErrorCode::ResourceNotFound, AcpError::ResourceNotFound),
        ] {
            // Present non-null data is unclassified except the go_limit allowlist.
            assert_labels(
                &Error::from(code).data(canary.clone()),
                (label, AcpData::Unclassified),
            );
        }
    }

    #[test]
    fn classify_other_codes_without_emitting_integer() {
        for code in [-32099, 0, 1, i32::MIN, i32::MAX] {
            let error = Error::new(code, SECRET);
            let (label, data) = classify_acp_error(&error);
            assert_eq!((label, data), (AcpError::Other, AcpData::Absent));
            assert_eq!(label.as_str(), "other");
            let out = format!("{}{}", label.as_str(), data.as_str());
            assert!(!out.contains(&code.to_string()), "{code} leaked into {out}");
            assert!(!out.contains(SECRET));
        }
    }

    #[test]
    fn classify_go_limit_allowlist() {
        let error = Error::internal_error().data(json!({
            "service": "session",
            "errorName": "provider.go-limit",
            SECRET: true,
        }));
        assert_labels(&error, (AcpError::InternalError, AcpData::GoLimit));
    }

    #[test]
    fn classify_go_limit_near_misses_and_absent_data() {
        let exact = json!({"service": "session", "errorName": "provider.go-limit"});
        for data in [
            json!({"service": "session", "errorName": "provider.go-limit "}),
            json!({"service": "session", "errorName": "Provider.go-limit"}),
            json!({"service": "session", "errorName": "provider.go-limit.extra"}),
            json!({"service": "session", "errorName": SECRET}),
            json!({"service": "other", "errorName": "provider.go-limit"}),
            json!({"service": "session", "errorName": {"nested": true}}),
            json!({"service": "session", "errorName": ["provider.go-limit"]}),
            json!({"service": "session", "errorName": 1}),
            json!(SECRET),
            json!([exact]),
        ] {
            assert_labels(
                &Error::internal_error().data(data),
                (AcpError::InternalError, AcpData::Unclassified),
            );
        }
        assert_labels(
            &Error::internal_error(),
            (AcpError::InternalError, AcpData::Absent),
        );
        let mut null_data = Error::internal_error();
        null_data.data = Some(Value::Null);
        assert_labels(&null_data, (AcpError::InternalError, AcpData::Absent));
    }

    #[test]
    fn classify_non_internal_data_is_unclassified_without_go_limit() {
        assert_labels(
            &Error::resource_not_found(Some(SECRET.into())),
            (AcpError::ResourceNotFound, AcpData::Unclassified),
        );
        assert_labels(
            &Error::auth_required().data(json!({SECRET: true})),
            (AcpError::AuthRequired, AcpData::Unclassified),
        );
        // into_internal_error stuffs the message into data as a string.
        assert_labels(
            &Error::into_internal_error(std::io::Error::other(SECRET)),
            (AcpError::InternalError, AcpData::Unclassified),
        );
    }

    #[test]
    fn classify_large_hostile_message_does_not_enter_labels() {
        let mut message = String::new();
        message.push_str(SECRET);
        message.push('\n');
        message.push_str("\u{1b}[31m");
        message.push_str("\u{202e}");
        message.extend(std::iter::repeat_n('x', 3_000_000));
        let error = Error::new(-32603, message);
        let got = classify_acp_error(&error);
        assert_eq!(got, (AcpError::InternalError, AcpData::Absent));
        assert_eq!(std::mem::size_of_val(&got), std::mem::size_of::<(AcpError, AcpData)>());
        assert!(!got.0.as_str().contains(SECRET));
    }

    #[test]
    fn unknown_fallback_only_when_no_label_stored() {
        let mut slot = None;
        let (error, data) = *slot.get_or_insert((AcpError::Unknown, AcpData::Absent));
        assert_eq!((error, data), (AcpError::Unknown, AcpData::Absent));
        assert_eq!(error.as_str(), "unknown");
        assert_eq!(data.as_str(), "absent");
    }

    #[test]
    fn label_store_first_write_wins_except_peer_replaces_timeout() {
        let slot = Mutex::new(None);
        record_acp_labels(&slot, (AcpError::ResponseTimeout, AcpData::Absent), false);
        record_acp_labels(&slot, (AcpError::InternalError, AcpData::GoLimit), true);
        assert_eq!(
            *slot.lock().unwrap(),
            Some((AcpError::InternalError, AcpData::GoLimit))
        );
        record_acp_labels(&slot, (AcpError::Unknown, AcpData::Absent), false);
        assert_eq!(
            *slot.lock().unwrap(),
            Some((AcpError::InternalError, AcpData::GoLimit))
        );
        let fresh = Mutex::new(None);
        record_acp_labels(&fresh, (AcpError::AuthRequired, AcpData::Absent), true);
        record_acp_labels(&fresh, (AcpError::ResponseTimeout, AcpData::Absent), false);
        assert_eq!(
            *fresh.lock().unwrap(),
            Some((AcpError::AuthRequired, AcpData::Absent))
        );
    }

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
