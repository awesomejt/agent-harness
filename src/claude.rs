//! Pinned Claude Code native adapter (D046–D048): the official `claude`
//! executable in print mode with stream-json input and output, on the
//! operator's existing official login (D047). The harness owns launch,
//! environment, deadline and cleanup; Claude Code owns the inner loop. This
//! increment runs deny-profile cloud-only single attempts: no tool is offered.
use crate::config::{Invalid, Permissions, Resolved, RuntimeKind};
use serde_json::{Value, json};
use std::ffi::OsString;

pub(crate) const VERSION: &str = "2.1.314";

/// Context categories a deny attempt may use before the prompt: the built-in
/// system prompt (with the appended `AGENTS.md`) and the empty message list.
/// Tools, memory files, skills, MCP tools and custom agents add categories.
const CONTEXT: [&str; 2] = ["system_prompt", "messages"];

/// Capabilities this increment cannot enforce yet are refused before launch,
/// so a later PR widens the surface deliberately (D048).
pub(crate) fn supported(request: &Resolved) -> Result<(), Invalid> {
    if request.runtime != RuntimeKind::Claude {
        return Ok(());
    }
    if request.permissions != Permissions::Deny {
        return Err(Invalid(
            "trusted permissions are not yet supported on the Claude runtime; use deny",
        ));
    }
    if request.agent.is_some() {
        return Err(Invalid(
            "named agents are not yet supported on the Claude runtime",
        ));
    }
    Ok(())
}

/// Launch arguments. Every valued option uses `--name=value`, so a model or
/// path can never be parsed as another option. `--safe-mode` drops CLAUDE.md,
/// skills, hooks, plugins, MCP servers, custom agents and output styles; an
/// empty `--setting-sources` loads no user, project or local settings;
/// `--tools=` offers no tool and `--permission-prompts=none` denies any
/// prompt. The project `AGENTS.md`, when present, is the only instruction
/// source, named by path and read by the runtime (D040).
pub(crate) fn args(request: &Resolved) -> Vec<OsString> {
    let mut args: Vec<OsString> = [
        "-p",
        "--output-format=stream-json",
        "--input-format=stream-json",
        "--verbose",
        "--safe-mode",
        "--setting-sources=",
        "--strict-mcp-config",
        "--disable-slash-commands",
        "--no-session-persistence",
        "--permission-prompts=none",
        "--tools=",
    ]
    .into_iter()
    .map(OsString::from)
    .collect();
    args.push(format!("--model={}", request.model).into());
    if let Some(path) = &request.instructions {
        let mut arg = OsString::from("--append-system-prompt-file=");
        arg.push(path);
        args.push(arg);
    }
    args
}

/// Cleared environment: only what the official login and process need. No
/// `ANTHROPIC_*`, `CLAUDE_*` or provider variable crosses, so the CLI can use
/// only its own login (`apiKeySource: "none"` is checked after submission).
pub(crate) fn environment(
    lookup: impl Fn(&str) -> Option<OsString>,
) -> Result<Vec<(OsString, OsString)>, Invalid> {
    let home = lookup("HOME")
        .filter(|home| !home.is_empty())
        .ok_or(Invalid(
            "HOME is required: the Claude runtime uses the operator's existing login",
        ))?;
    let mut env = vec![
        (OsString::from("HOME"), home),
        (
            "PATH".into(),
            lookup("PATH").unwrap_or_else(|| "/usr/bin:/bin".into()),
        ),
        ("DISABLE_AUTOUPDATER".into(), "1".into()),
    ];
    for name in ["USER", "LOGNAME", "TMPDIR"] {
        if let Some(value) = lookup(name) {
            env.push((name.into(), value));
        }
    }
    Ok(env)
}

/// Control request written to the runtime's stdin.
pub(crate) fn control(id: &str, subtype: &str) -> Value {
    json!({"type": "control_request", "request_id": id, "request": {"subtype": subtype}})
}

/// The user turn: the prompt text only, never other context.
pub(crate) fn prompt(text: &str) -> Value {
    json!({"type": "user", "message": {"role": "user", "content": text}})
}

/// The successful response body of control request `id`, if `line` is it.
pub(crate) fn control_response<'a>(line: &'a Value, id: &str) -> Option<Result<&'a Value, ()>> {
    let response = &line["response"];
    if line["type"] != "control_response" || response["request_id"] != id {
        return None;
    }
    Some(
        if response["subtype"] == "success" && response["response"].is_object() {
            Ok(&response["response"])
        } else {
            Err(())
        },
    )
}

fn empty_array(value: &Value) -> bool {
    value.as_array().is_some_and(Vec::is_empty)
}

/// `initialize`: exact version, default permission mode, no commands and the
/// default output style. Account fields are never read or retained.
pub(crate) fn validate_initialize(response: &Value) -> Result<(), ()> {
    (response["claude_code_version"] == VERSION
        && response["current_permission_mode"] == "default"
        && empty_array(&response["commands"])
        && response["output_style"] == "default")
        .then_some(())
        .ok_or(())
}

/// `get_settings`: no setting source at all, so admin-managed (policy)
/// settings refuse too; returns the resolved model.
pub(crate) fn validate_settings(response: &Value) -> Result<String, ()> {
    if !empty_array(&response["sources"])
        || response["effective"]
            .as_object()
            .is_none_or(|m| !m.is_empty())
    {
        return Err(());
    }
    let model = response["applied"]["model"].as_str().ok_or(())?;
    crate::config::validate_model(model).map_err(|_| ())?;
    Ok(model.to_owned())
}

/// `mcp_status`: no MCP server.
pub(crate) fn validate_mcp(response: &Value) -> Result<(), ()> {
    empty_array(&response["mcpServers"]).then_some(()).ok_or(())
}

/// `get_context_usage`: the resolved model, and nothing in the context but
/// the system prompt and messages: no tool definitions, memory files, MCP
/// tools or agents. This proves the empty tool set before the prompt.
pub(crate) fn validate_context(response: &Value, model: &str) -> Result<(), ()> {
    let categories = response["categories"].as_array().ok_or(())?;
    let only_allowed = categories.iter().all(|category| {
        category["kind"] != "used"
            || category["id"]
                .as_str()
                .is_some_and(|id| CONTEXT.contains(&id))
    });
    (response["model"] == model
        && only_allowed
        && empty_array(&response["memoryFiles"])
        && empty_array(&response["mcpTools"])
        && empty_array(&response["agents"]))
    .then_some(())
    .ok_or(())
}

/// `system/init`, the first record of the turn: the same version, model and
/// project, no tools, MCP servers, slash commands or skills, the default
/// permission mode and output style, only built-in plugins, and no API key
/// (the CLI's own login). Returns the session ID.
pub(crate) fn validate_init<'a>(
    event: &'a Value,
    model: &str,
    project: &std::path::Path,
) -> Result<&'a str, ()> {
    let builtin = event["plugins"].as_array().is_some_and(|plugins| {
        plugins
            .iter()
            .all(|plugin| plugin["path"] == "builtin" && plugin.as_object().is_some())
    });
    let ok = event["type"] == "system"
        && event["subtype"] == "init"
        && event["claude_code_version"] == VERSION
        && event["model"] == model
        && project.to_str().is_some_and(|p| event["cwd"] == p)
        && empty_array(&event["tools"])
        && empty_array(&event["mcp_servers"])
        && empty_array(&event["slash_commands"])
        && empty_array(&event["skills"])
        && event["permissionMode"] == "default"
        && event["output_style"] == "default"
        && event["apiKeySource"] == "none"
        && builtin;
    let session = event["session_id"].as_str().filter(|s| !s.is_empty());
    match session {
        Some(session) if ok => Ok(session),
        _ => Err(()),
    }
}

/// What a turn record means for the attempt.
#[derive(Debug, PartialEq)]
pub(crate) enum Event {
    /// Assistant text blocks in one message.
    Assistant(usize),
    /// A tool call or tool result: never permitted under deny.
    Tool,
    /// The runtime asked the host something; never expected under deny.
    Request,
    RateLimit(&'static str),
    Result(Terminal),
    Other,
}

#[derive(Debug, PartialEq)]
pub(crate) enum Terminal {
    Success {
        text: String,
        cost: Option<f64>,
    },
    /// A known stop after the harness's own interrupt.
    Cancelled {
        cost: Option<f64>,
    },
    Other {
        cost: Option<f64>,
    },
}

/// Classify one turn record. Only `result` with `subtype: "success"`,
/// `is_error: false` and `stop_reason: "end_turn"` is success (D046); an
/// aborted result counts as cancelled only after the harness interrupted.
pub(crate) fn classify(event: &Value, interrupted: bool) -> Event {
    match event["type"].as_str() {
        Some("assistant") => {
            let blocks = event["message"]["content"].as_array();
            let tool = blocks.into_iter().flatten().any(|block| {
                !matches!(
                    block["type"].as_str(),
                    Some("text" | "thinking" | "redacted_thinking")
                )
            });
            if tool {
                return Event::Tool;
            }
            Event::Assistant(
                blocks
                    .into_iter()
                    .flatten()
                    .filter(|block| block["type"] == "text")
                    .count(),
            )
        }
        Some("user") => {
            let tool = event["message"]["content"]
                .as_array()
                .into_iter()
                .flatten()
                .any(|block| block["type"] == "tool_result");
            if tool { Event::Tool } else { Event::Other }
        }
        Some("control_request") => Event::Request,
        Some("rate_limit_event") => {
            Event::RateLimit(match event["rate_limit_info"]["status"].as_str() {
                Some("allowed") => "allowed",
                Some("allowed_warning") => "allowed_warning",
                Some("rejected") => "rejected",
                _ => "unknown",
            })
        }
        Some("result") => {
            let cost = event["total_cost_usd"]
                .as_f64()
                .filter(|cost| cost.is_finite() && *cost >= 0.0);
            let success = event["subtype"] == "success"
                && event["is_error"] == false
                && event["stop_reason"] == "end_turn";
            Event::Result(match event["result"].as_str() {
                Some(text) if success => Terminal::Success {
                    text: text.to_owned(),
                    cost,
                },
                _ if interrupted
                    && event["is_error"] == true
                    && event["terminal_reason"]
                        .as_str()
                        .is_some_and(|r| r.starts_with("aborted")) =>
                {
                    Terminal::Cancelled { cost }
                }
                _ => Terminal::Other { cost },
            })
        }
        _ => Event::Other,
    }
}

/// Backend IDs are opaque: bounded, JSON-escaped, non-ASCII escaped.
fn escape(session: &str) -> String {
    let escaped: String = session
        .chars()
        .take(128)
        .map(|c| {
            if c.is_ascii() {
                c.to_string()
            } else {
                c.escape_unicode().to_string()
            }
        })
        .collect();
    escaped
}

#[cfg(target_os = "macos")]
pub(crate) use supervise::attempt;

#[cfg(target_os = "macos")]
mod supervise {
    use super::*;
    use crate::{config::Exit, process::OwnedChild, progress::Progress};
    use std::time::Duration;
    use tokio::io::{AsyncBufReadExt, AsyncReadExt, AsyncWriteExt, BufReader};
    use tokio::process::ChildStdin;
    use tokio::sync::mpsc;
    use tokio::time::Instant;
    use tokio_util::sync::CancellationToken;

    /// Total stdout bytes and bytes per record.
    const OUTPUT_LIMIT: usize = 64 << 20;
    const LINE_LIMIT: usize = 8 << 20;
    const RESPONSE_LIMIT: usize = 1_000_000;

    #[derive(Default)]
    struct Observed {
        chunks: usize,
        tools: usize,
        submitted: bool,
        interrupted: bool,
        violation: bool,
    }
    impl Observed {
        fn counters(&self) -> Value {
            json!({"assistant_chunks": self.chunks, "tool_events": self.tools,
                   "permission_requests": 0, "grants": 0})
        }
    }

    enum Outcome {
        /// Effective configuration did not match before the prompt.
        Refused,
        /// Setup ended before the prompt, without a configuration mismatch.
        Failed,
        /// Stopped by signal or deadline, or ended without a terminal record.
        Stopped,
        Terminal(Terminal),
    }

    struct Channel {
        records: mpsc::Receiver<Result<Value, ()>>,
        stdin: Option<ChildStdin>,
    }
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

    /// One bounded JSON object per line; a read error, oversize, partial
    /// final line or non-object is a protocol violation (`Err`).
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
                    // An exhausted budget reads nothing, which is not EOF.
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

    pub(crate) async fn attempt(
        request: &Resolved,
        label: &str,
        deadline: Instant,
        cancelled: CancellationToken,
        progress: &Progress,
    ) -> Exit {
        progress.claude_usage(None);
        let Some(executable) = crate::preview::discover_runtime("claude") else {
            progress.event(format!(
                "Claude Code missing: install {VERSION} on an absolute PATH entry and log in with it"
            ));
            progress.reason("Claude Code missing on an absolute PATH entry");
            return Exit::Invalid;
        };
        let env = match environment(|name| std::env::var_os(name)) {
            Ok(env) => env,
            Err(error) => {
                progress.reject(error.0);
                return Exit::Invalid;
            }
        };
        if let Err(exit) = crate::worktree::report(&request.project, deadline, progress).await {
            return exit;
        }
        if cancelled.is_cancelled() || Instant::now() >= deadline {
            return Exit::Cancelled;
        }
        let mut command = tokio::process::Command::new(&executable);
        command
            .args(args(request))
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
        // Closing stdin ends the stream-json session; allow a short natural
        // exit before group escalation.
        channel.stdin = None;
        if matches!(outcome, Outcome::Terminal(_)) {
            let _ = tokio::time::timeout(Duration::from_secs(2), owned.child.wait()).await;
        }
        progress.event("process cleanup started");
        let cleanup = owned.cleanup().await;
        let summary = json!({
            "cleanup_confirmed": cleanup,
            "permission_requests": 0,
            "grants": 0,
            "tool_events": observed.tools,
            "protocol_violation": observed.violation,
        });
        progress.event(format!(
            "cleanup={cleanup}; protocol_violation={}; tool events: {}; stderr_bytes={} (raw withheld; count capped at 1048577)",
            observed.violation,
            observed.tools,
            owned.stderr_bytes()
        ));
        progress.note(summary.clone());
        progress.emit("attempt.cleanup", summary);
        let terminal = match outcome {
            Outcome::Terminal(terminal) if !observed.violation => terminal,
            _ if !cleanup || observed.submitted => return Exit::Uncertain,
            Outcome::Refused => {
                progress.event(format!(
                    "preflight failed (requires Claude Code {VERSION}, no settings sources, tools, MCP servers, memory or agents)"
                ));
                progress.reason(
                    "preflight failed: Claude Code version, settings, tools or model did not match",
                );
                return Exit::Invalid;
            }
            Outcome::Stopped if cancelled.is_cancelled() || Instant::now() >= deadline => {
                return Exit::Cancelled;
            }
            _ => return Exit::Failed,
        };
        if !cleanup {
            return Exit::Uncertain;
        }
        match terminal {
            Terminal::Success { text, .. } => {
                progress.event(
                    "backend end_turn; cleanup confirmed; delivering response (2s output budget)",
                );
                if progress.deliver(text).await {
                    Exit::Success
                } else {
                    progress.event("final response delivery failed or blocked; backend completed, output may be partial");
                    Exit::Failed
                }
            }
            Terminal::Cancelled { .. } => Exit::Cancelled,
            Terminal::Other { .. } => Exit::Failed,
        }
    }

    /// Bounded wait for control request `id`'s response. Anything else
    /// before the prompt is unexpected.
    async fn expect(
        channel: &mut Channel,
        id: &str,
        deadline: Instant,
        cancelled: &CancellationToken,
    ) -> Result<Value, Outcome> {
        let bound = deadline.min(Instant::now() + Duration::from_secs(30));
        tokio::select! {
            record = tokio::time::timeout_at(bound, channel.records.recv()) => match record {
                Ok(Some(Ok(line))) => match control_response(&line, id) {
                    Some(Ok(response)) => Ok(response.clone()),
                    Some(Err(())) => Err(Outcome::Refused),
                    None => Err(Outcome::Failed),
                },
                Err(_) if Instant::now() >= deadline => Err(Outcome::Stopped),
                _ => Err(Outcome::Failed),
            },
            _ = cancelled.cancelled() => Err(Outcome::Stopped),
        }
    }

    async fn turn(
        channel: &mut Channel,
        request: &Resolved,
        label: &str,
        deadline: Instant,
        cancelled: &CancellationToken,
        progress: &Progress,
        observed: &mut Observed,
    ) -> Outcome {
        progress.event("preflight check started (stream-json control requests; no prompt)");
        let mut model = String::new();
        for (id, subtype) in [
            ("ah-initialize", "initialize"),
            ("ah-settings", "get_settings"),
            ("ah-mcp", "mcp_status"),
            ("ah-context", "get_context_usage"),
        ] {
            if !channel.send(&control(id, subtype), deadline).await {
                return Outcome::Failed;
            }
            let response = match expect(channel, id, deadline, cancelled).await {
                Ok(response) => response,
                Err(outcome) => return outcome,
            };
            let checked = match subtype {
                "initialize" => validate_initialize(&response),
                "get_settings" => validate_settings(&response).map(|m| model = m),
                "mcp_status" => validate_mcp(&response),
                _ => validate_context(&response, &model),
            };
            if checked.is_err() {
                return Outcome::Refused;
            }
        }
        if cancelled.is_cancelled() || Instant::now() >= deadline {
            return Outcome::Stopped;
        }
        progress.event(format!(
            "{label} via Claude Code {VERSION}; model {} (resolved {model}); permissions deny (no tools offered)",
            request.model
        ));
        // The submission boundary precedes the write: a failed send can
        // still deliver (D031).
        observed.submitted = true;
        progress.event("prompt submitted");
        progress.note(json!({"prompt_submitted": true}));
        progress.emit("attempt.prompt_submitted", json!({}));
        if !channel
            .send(&super::prompt(&request.prompt), deadline)
            .await
        {
            return Outcome::Stopped;
        }
        let mut session = false;
        let mut limit = None;
        let mut heartbeat = tokio::time::interval(Duration::from_secs(5));
        heartbeat.tick().await;
        let mut stop_by: Option<Instant> = None;
        loop {
            let wake = stop_by.unwrap_or(deadline);
            let record = tokio::select! {
                record = channel.records.recv() => record,
                _ = cancelled.cancelled(), if stop_by.is_none() => {
                    progress.event("signal; sending interrupt (5s response budget)");
                    if !interrupt(channel, observed, deadline).await { return Outcome::Stopped; }
                    stop_by = Some(Instant::now() + Duration::from_secs(5));
                    continue;
                }
                _ = tokio::time::sleep_until(wake) => {
                    if stop_by.is_some() { return Outcome::Stopped; }
                    progress.event("deadline; sending interrupt (5s response budget)");
                    if !interrupt(channel, observed, Instant::now() + Duration::from_secs(5)).await { return Outcome::Stopped; }
                    stop_by = Some(Instant::now() + Duration::from_secs(5));
                    continue;
                }
                _ = heartbeat.tick() => {
                    progress.event(format!("active; chunks={}; tools={}; permissions=0", observed.chunks, observed.tools));
                    progress.emit("attempt.activity", observed.counters());
                    continue;
                }
            };
            let Some(Ok(record)) = record else {
                if matches!(record, Some(Err(()))) {
                    observed.violation = true;
                    progress.event("protocol/output limit failure");
                }
                return Outcome::Stopped;
            };
            if !session {
                if record["type"] == "system" && record["subtype"] == "init" {
                    let Ok(id) = validate_init(&record, &model, &request.project) else {
                        observed.violation = true;
                        progress.event("system/init did not match the preflight configuration");
                        return Outcome::Stopped;
                    };
                    session = true;
                    let id = escape(id);
                    progress.event(format!("session={}", serde_json::to_string(&id).unwrap()));
                    progress.note(json!({"session": id}));
                    progress.emit("attempt.session", json!({"session": id}));
                    continue;
                }
                if record["type"] != "result" && record["type"] != "control_response" {
                    observed.violation = true;
                    progress.event("turn record before system/init");
                    return Outcome::Stopped;
                }
            }
            match classify(&record, observed.interrupted) {
                Event::Assistant(blocks) => {
                    observed.chunks += blocks;
                    if blocks > 0 {
                        progress.event(format!("assistant activity; chunks={}", observed.chunks));
                        progress.emit("attempt.activity", observed.counters());
                    }
                }
                Event::Tool | Event::Request => {
                    observed.tools += 1;
                    observed.violation = true;
                    progress.event("tool or host request under deny; stopping");
                    return Outcome::Stopped;
                }
                Event::RateLimit(status) => {
                    if limit != Some(status) {
                        limit = Some(status);
                        progress.event(format!("backend rate limit status={status}"));
                    }
                }
                Event::Result(terminal) => {
                    if !session && matches!(terminal, Terminal::Success { .. }) {
                        observed.violation = true;
                        progress.event("success result without system/init");
                        return Outcome::Stopped;
                    }
                    let (stop, cost) = match &terminal {
                        Terminal::Success { text, cost } => {
                            if text.len() > RESPONSE_LIMIT {
                                observed.violation = true;
                                return Outcome::Stopped;
                            }
                            ("end_turn", cost)
                        }
                        Terminal::Cancelled { cost } => ("cancelled", cost),
                        Terminal::Other { cost } => ("other", cost),
                    };
                    progress.claude_usage(*cost);
                    progress.event(match stop {
                        "end_turn" => "backend terminal=end_turn",
                        "cancelled" => "backend terminal=cancelled",
                        _ => "backend terminal=failure (error, refusal or limit)",
                    });
                    progress.note(json!({"backend_stop": stop}));
                    progress.emit("attempt.backend_stop", json!({"backend_stop": stop}));
                    return Outcome::Terminal(terminal);
                }
                Event::Other => {}
            }
        }
    }

    async fn interrupt(channel: &mut Channel, observed: &mut Observed, deadline: Instant) -> bool {
        observed.interrupted = true;
        channel
            .send(&control("ah-interrupt", "interrupt"), deadline)
            .await
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::Path;

    fn init() -> Value {
        json!({"type": "system", "subtype": "init", "cwd": "/project", "session_id": "s-1",
               "tools": [], "mcp_servers": [], "model": "claude-sonnet-5-5",
               "permissionMode": "default", "slash_commands": [], "apiKeySource": "none",
               "claude_code_version": VERSION, "output_style": "default",
               "agents": ["claude", "Explore"], "skills": [],
               "plugins": [{"name": "x", "path": "builtin", "source": "x@builtin"}]})
    }

    #[test]
    fn init_must_match_preflight_exactly() {
        let project = Path::new("/project");
        assert_eq!(
            validate_init(&init(), "claude-sonnet-5-5", project),
            Ok("s-1")
        );
        assert!(validate_init(&init(), "claude-opus-5-5", project).is_err());
        assert!(validate_init(&init(), "claude-sonnet-5-5", Path::new("/other")).is_err());
        for (field, value) in [
            ("tools", json!(["Read"])),
            ("mcp_servers", json!([{"name": "m"}])),
            ("slash_commands", json!(["review"])),
            ("skills", json!(["s"])),
            ("permissionMode", json!("bypassPermissions")),
            ("apiKeySource", json!("ANTHROPIC_API_KEY")),
            ("claude_code_version", json!("2.1.315")),
            ("output_style", json!("Explanatory")),
            ("plugins", json!([{"name": "p", "path": "/home/p"}])),
            ("session_id", json!("")),
            ("tools", json!(null)),
        ] {
            let mut event = init();
            event[field] = value;
            assert!(
                validate_init(&event, "claude-sonnet-5-5", project).is_err(),
                "{field}"
            );
        }
    }

    #[test]
    fn control_preflight_refuses_settings_tools_and_versions() {
        let initialize = json!({"claude_code_version": VERSION, "current_permission_mode": "default",
                                "commands": [], "output_style": "default",
                                "account": {"email": "never-read"}});
        assert!(validate_initialize(&initialize).is_ok());
        for (field, value) in [
            ("claude_code_version", json!("2.1.313")),
            ("current_permission_mode", json!("acceptEdits")),
            ("commands", json!([{"name": "review"}])),
            ("output_style", json!("Learning")),
        ] {
            let mut changed = initialize.clone();
            changed[field] = value;
            assert!(validate_initialize(&changed).is_err(), "{field}");
        }
        let settings =
            json!({"effective": {}, "sources": [], "applied": {"model": "claude-sonnet-5-5"}});
        assert_eq!(
            validate_settings(&settings).as_deref(),
            Ok("claude-sonnet-5-5")
        );
        for (field, value) in [
            ("sources", json!([{"source": "policySettings"}])),
            ("effective", json!({"permissions": {"allow": ["Bash"]}})),
            ("applied", json!({"model": "bad model"})),
            ("applied", json!({})),
        ] {
            let mut changed = settings.clone();
            changed[field] = value;
            assert!(validate_settings(&changed).is_err(), "{field}");
        }
        assert!(validate_mcp(&json!({"mcpServers": []})).is_ok());
        assert!(validate_mcp(&json!({"mcpServers": [{"name": "m"}]})).is_err());
        let context = json!({"model": "claude-sonnet-5-5", "memoryFiles": [], "mcpTools": [], "agents": [],
            "categories": [{"id": "system_prompt", "kind": "used"}, {"id": "messages", "kind": "used"},
                           {"id": "free_space", "kind": "free"}]});
        assert!(validate_context(&context, "claude-sonnet-5-5").is_ok());
        assert!(validate_context(&context, "claude-opus-5-5").is_err());
        let mut tools = context.clone();
        tools["categories"]
            .as_array_mut()
            .unwrap()
            .push(json!({"id": "system_tools", "kind": "used"}));
        assert!(validate_context(&tools, "claude-sonnet-5-5").is_err());
        for field in ["memoryFiles", "mcpTools", "agents"] {
            let mut changed = context.clone();
            changed[field] = json!([{"name": "x"}]);
            assert!(
                validate_context(&changed, "claude-sonnet-5-5").is_err(),
                "{field}"
            );
        }
        let line = json!({"type": "control_response", "response": {"subtype": "error", "request_id": "a", "error": "x"}});
        assert_eq!(control_response(&line, "a"), Some(Err(())));
        assert_eq!(control_response(&line, "b"), None);
    }

    #[test]
    fn only_end_turn_success_succeeds_and_aborts_need_an_interrupt() {
        let success = json!({"type": "result", "subtype": "success", "is_error": false,
                             "stop_reason": "end_turn", "result": "ok", "total_cost_usd": 0.01});
        assert_eq!(
            classify(&success, false),
            Event::Result(Terminal::Success {
                text: "ok".into(),
                cost: Some(0.01)
            })
        );
        for (field, value) in [
            ("subtype", json!("error_max_turns")),
            ("is_error", json!(true)),
            ("stop_reason", json!("max_tokens")),
            ("result", json!(null)),
        ] {
            let mut changed = success.clone();
            changed[field] = value;
            assert_eq!(
                classify(&changed, false),
                Event::Result(Terminal::Other { cost: Some(0.01) }),
                "{field}"
            );
        }
        let aborted = json!({"type": "result", "subtype": "error_during_execution", "is_error": true,
                             "terminal_reason": "aborted_streaming", "total_cost_usd": -1});
        assert_eq!(
            classify(&aborted, true),
            Event::Result(Terminal::Cancelled { cost: None })
        );
        assert_eq!(
            classify(&aborted, false),
            Event::Result(Terminal::Other { cost: None })
        );
    }

    #[test]
    fn tool_blocks_and_host_requests_are_never_ordinary_activity() {
        let text = json!({"type": "assistant", "message": {"content": [{"type": "text", "text": "a"}, {"type": "thinking"}]}});
        assert_eq!(classify(&text, false), Event::Assistant(1));
        for block in ["tool_use", "server_tool_use", "unknown"] {
            let tool = json!({"type": "assistant", "message": {"content": [{"type": block}]}});
            assert_eq!(classify(&tool, false), Event::Tool, "{block}");
        }
        let result = json!({"type": "user", "message": {"content": [{"type": "tool_result"}]}});
        assert_eq!(classify(&result, false), Event::Tool);
        assert_eq!(
            classify(&json!({"type": "control_request"}), false),
            Event::Request
        );
        assert_eq!(
            classify(
                &json!({"type": "rate_limit_event", "rate_limit_info": {"status": "x\u{1b}"}}),
                false
            ),
            Event::RateLimit("unknown")
        );
    }

    #[test]
    fn environment_is_cleared_and_needs_home() {
        let lookup = |name: &str| match name {
            "HOME" => Some(OsString::from("/home/u")),
            "ANTHROPIC_API_KEY" => Some("secret".into()),
            _ => None,
        };
        let env = environment(lookup).unwrap();
        assert!(env.iter().all(|(name, _)| name != "ANTHROPIC_API_KEY"));
        assert!(env.contains(&("PATH".into(), "/usr/bin:/bin".into())));
        assert!(environment(|_| None).is_err());
        assert_eq!(escape("a\u{202e}b"), "a\\u{202e}b");
    }
}
