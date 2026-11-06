//! Pinned Claude Code native adapter (D046–D048): the official `claude`
//! executable in print mode with stream-json input and output, on the
//! operator's existing official login (D047). The harness owns launch,
//! environment, deadline and cleanup; Claude Code owns the inner loop. It runs
//! cloud-only single attempts: `deny` offers no tool (D048); `trusted` offers
//! a fixed built-in set and answers each host permission prompt with one
//! request-bound allow-once grant (D049). A named role narrows that set to
//! its own tools, appends its body to the system prompt and maps its effort
//! to `--effort` (D050).
use crate::agents::{self, Agent, Effort, Tool};
use crate::config::{Invalid, Permissions, Resolved, RuntimeKind};
use crate::permission::{
    OptionKind, PermissionOption, PermissionPolicy, PermissionRequest, PermissionResponse,
};
use serde_json::{Value, json};
use std::ffi::OsString;

pub(crate) const VERSION: &str = "2.1.314";

/// Context categories an attempt may use before the prompt: the built-in
/// system prompt (with the appended `AGENTS.md`) and the empty message list.
/// Memory files, skills, MCP tools and custom agents add categories.
const CONTEXT: [&str; 2] = ["system_prompt", "messages"];
/// The built-in tool definitions, present only when tools are offered.
const TOOL_CONTEXT: &str = "system_tools";

/// The trusted built-in tool set (D049): read, search, edit and shell, in the
/// order `system/init` lists them. Agent/Task, Skill, web, MCP, notebook,
/// background-task and planning tools are never offered.
pub(crate) const TRUSTED_TOOLS: [&str; 6] = ["Bash", "Edit", "Glob", "Grep", "Read", "Write"];

/// Built-in tools for each canonical tool (D050), within the trusted set.
fn builtins(tool: Tool) -> &'static [&'static str] {
    match tool {
        Tool::Read => &["Read"],
        Tool::Search => &["Glob", "Grep"],
        Tool::Edit => &["Edit", "Write"],
        Tool::Execute => &["Bash"],
    }
}

/// Tools offered to the runtime: the invocation profile intersected with a
/// selected role's tools (D038/D050). A deny invocation offers none for every
/// role; a trusted one offers the role's mapped tools, never more than the
/// trusted set. Listed in `TRUSTED_TOOLS` order.
pub(crate) fn tools(request: &Resolved) -> Vec<&'static str> {
    match (request.permissions, &request.agent) {
        (Permissions::Deny, _) => Vec::new(),
        (Permissions::Trusted, None) => TRUSTED_TOOLS.to_vec(),
        (Permissions::Trusted, Some(agent)) => {
            let mapped: Vec<&str> = agent
                .tools()
                .iter()
                .flat_map(|t| builtins(*t))
                .copied()
                .collect();
            TRUSTED_TOOLS
                .into_iter()
                .filter(|tool| mapped.contains(tool))
                .collect()
        }
    }
}

/// Whether a host prompt may be granted at all. Claude Code prompts for
/// project-local reads and searches never (observed), and for any path
/// outside the project; a role whose ceiling is below `trusted` is denied
/// every prompt, as OpenCode denies its `external_directory` (D037/D050).
/// An empty offered set launches as deny, so it grants nothing either.
pub(crate) fn grants(request: &Resolved) -> bool {
    request.permissions == Permissions::Trusted
        && !tools(request).is_empty()
        && request
            .agent
            .as_ref()
            .is_none_or(|agent| agent.permissions() == agents::Permissions::Trusted)
}

/// `--effort` value for a role's canonical effort; `default` passes none and
/// leaves the model's own default (D050).
pub(crate) fn effort(request: &Resolved) -> Option<&'static str> {
    match request.agent.as_ref().map(Agent::effort)? {
        Effort::Default => None,
        Effort::Low => Some("low"),
        Effort::Medium => Some("medium"),
        Effort::High => Some("high"),
        Effort::Max => Some("max"),
    }
}

/// The role body travels as one launch argument; it stays well inside the
/// macOS argument limit, so launch cannot fail on its size (D050).
pub(crate) const BODY_LIMIT: usize = 128 << 10;

/// Capabilities this increment cannot enforce are refused before launch, so a
/// later PR widens the surface deliberately (D048–D050).
pub(crate) fn supported(request: &Resolved) -> Result<(), Invalid> {
    if request.runtime != RuntimeKind::Claude {
        return Ok(());
    }
    if request
        .agent
        .as_ref()
        .is_some_and(|agent| agent.body().len() > BODY_LIMIT)
    {
        return Err(Invalid(
            "agent body exceeds 128 KiB, the Claude runtime's launch-argument bound",
        ));
    }
    Ok(())
}

/// Launch arguments. Every valued option uses `--name=value`, so a model or
/// path can never be parsed as another option. `--safe-mode` drops CLAUDE.md,
/// skills, hooks, plugins, MCP servers, custom agents and output styles; an
/// empty `--setting-sources` loads no user, project or local settings. Under
/// deny, `--tools=` offers no tool and `--permission-prompts=none` denies any
/// prompt; under trusted, `--tools` names the fixed set and prompts go to the
/// harness over stdin (`--permission-prompt-tool=stdio`). The project
/// `AGENTS.md`, when present, is named by path and read by the runtime
/// (D040); a selected role's body follows it as `--append-system-prompt`
/// (only the last `--append-system-prompt-file` applies, so the body cannot
/// be a second file). A non-default role effort adds `--effort` (D050).
/// An empty offered set (deny, or a role with no tools) launches as deny.
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
    ]
    .into_iter()
    .map(OsString::from)
    .collect();
    let offered = tools(request);
    if offered.is_empty() {
        args.push("--permission-prompts=none".into());
    } else {
        args.push("--permission-prompts=host".into());
        args.push("--permission-prompt-tool=stdio".into());
    }
    args.push(format!("--tools={}", offered.join(",")).into());
    args.push(format!("--model={}", request.model).into());
    if let Some(effort) = effort(request) {
        args.push(format!("--effort={effort}").into());
    }
    if let Some(path) = &request.instructions {
        let mut arg = OsString::from("--append-system-prompt-file=");
        arg.push(path);
        args.push(arg);
    }
    if let Some(agent) = &request.agent {
        args.push(format!("--append-system-prompt={}", agent.body()).into());
    }
    args
}

/// Cleared environment: only what the official login and process need. No
/// `ANTHROPIC_*`, `CLAUDE_*` or provider variable crosses, so the CLI can use
/// only its own login (`apiKeySource: "none"` is checked after submission).
/// The harness sets two fixed values: no auto-update, and no background
/// tasks, so a shell command runs inside the turn rather than detached from
/// it with only a promise to report later (D049).
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
        ("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS".into(), "1".into()),
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
/// settings refuse too, and a requested effort applied exactly; returns the
/// resolved model. With no requested effort the model default stands.
pub(crate) fn validate_settings(response: &Value, effort: Option<&str>) -> Result<String, ()> {
    if !empty_array(&response["sources"])
        || response["effective"]
            .as_object()
            .is_none_or(|m| !m.is_empty())
        || effort.is_some_and(|effort| response["applied"]["effort"] != effort)
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
/// the system prompt and messages, plus built-in tool definitions only when
/// tools are offered: no memory files, MCP tools or agents. Under deny this
/// proves the empty tool set before the prompt.
pub(crate) fn validate_context(response: &Value, model: &str, tools: bool) -> Result<(), ()> {
    let categories = response["categories"].as_array().ok_or(())?;
    let only_allowed = categories.iter().all(|category| {
        category["kind"] != "used"
            || category["id"]
                .as_str()
                .is_some_and(|id| CONTEXT.contains(&id) || (tools && id == TOOL_CONTEXT))
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
/// project, exactly the offered tools, no MCP servers, slash commands or
/// skills, the default permission mode and output style, only built-in
/// plugins, and no API key (the CLI's own login). Returns the session ID.
pub(crate) fn validate_init<'a>(
    event: &'a Value,
    model: &str,
    project: &std::path::Path,
    tools: &[&str],
) -> Result<&'a str, ()> {
    let mut listed: Vec<&str> = event["tools"]
        .as_array()
        .into_iter()
        .flatten()
        .map(|tool| tool.as_str().unwrap_or_default())
        .collect();
    listed.sort_unstable();
    let mut expected = tools.to_vec();
    expected.sort_unstable();
    let exact_tools = event["tools"].is_array() && listed == expected;
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
        && exact_tools
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

/// One announced tool call: its ID, built-in tool name and complete input.
#[derive(Debug, PartialEq, Clone)]
pub(crate) struct Call {
    pub id: String,
    pub name: String,
    pub input: Value,
}

/// A host permission prompt (`can_use_tool`) for one announced call.
#[derive(Debug, PartialEq)]
pub(crate) struct Prompt {
    pub request_id: String,
    pub call: Call,
}

/// What a turn record means for the attempt.
#[derive(Debug, PartialEq)]
pub(crate) enum Event {
    /// Assistant text blocks and tool calls in one message.
    Assistant {
        text: usize,
        calls: Vec<Call>,
    },
    /// Tool results in one user record, by tool call ID.
    ToolResults(Vec<String>),
    /// A host permission prompt; never expected under deny.
    Permission(Prompt),
    /// Any other host request, a subagent record or a malformed tool block:
    /// always a protocol violation.
    Unsupported,
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

fn call(value: &Value) -> Option<Call> {
    let id = value["id"].as_str().filter(|id| !id.is_empty())?;
    let name = value["name"].as_str().filter(|name| !name.is_empty())?;
    value["input"].is_object().then(|| Call {
        id: id.to_owned(),
        name: name.to_owned(),
        input: value["input"].clone(),
    })
}

fn prompt_request(event: &Value) -> Option<Prompt> {
    let request = &event["request"];
    if request["subtype"] != "can_use_tool" {
        return None;
    }
    let request_id = event["request_id"].as_str().filter(|id| !id.is_empty())?;
    let call = call(
        &json!({"id": request["tool_use_id"], "name": request["tool_name"],
                            "input": request["input"]}),
    )?;
    Some(Prompt {
        request_id: request_id.to_owned(),
        call,
    })
}

/// Classify one turn record. Only `result` with `subtype: "success"`,
/// `is_error: false` and `stop_reason: "end_turn"` is success (D046); an
/// aborted result counts as cancelled only after the harness interrupted.
/// A record from a subagent (`parent_tool_use_id` set) is unsupported: no
/// delegation tool is offered.
pub(crate) fn classify(event: &Value, interrupted: bool) -> Event {
    let nested = !event["parent_tool_use_id"].is_null();
    match event["type"].as_str() {
        Some("assistant") => {
            let mut text = 0;
            let mut calls = Vec::new();
            for block in event["message"]["content"].as_array().into_iter().flatten() {
                match block["type"].as_str() {
                    Some("text") => text += 1,
                    Some("thinking" | "redacted_thinking") => {}
                    Some("tool_use") => match call(block) {
                        Some(call) => calls.push(call),
                        None => return Event::Unsupported,
                    },
                    _ => return Event::Unsupported,
                }
            }
            if nested {
                return Event::Unsupported;
            }
            Event::Assistant { text, calls }
        }
        Some("user") => {
            let mut results = Vec::new();
            for block in event["message"]["content"].as_array().into_iter().flatten() {
                if block["type"] == "tool_result" {
                    match block["tool_use_id"].as_str().filter(|id| !id.is_empty()) {
                        Some(id) => results.push(id.to_owned()),
                        None => return Event::Unsupported,
                    }
                }
            }
            if nested {
                Event::Unsupported
            } else if results.is_empty() {
                Event::Other
            } else {
                Event::ToolResults(results)
            }
        }
        Some("control_request") => {
            prompt_request(event).map_or(Event::Unsupported, Event::Permission)
        }
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
        _ if nested => Event::Unsupported,
        _ => Event::Other,
    }
}

/// The harness's answer to one host permission prompt: `Some(true)` grants
/// it once, `Some(false)` denies it, `None` is a malformed prompt (protocol
/// violation). A grant needs the trusted set to name the tool, `eligible`
/// (the prompt repeats a pending, not yet prompted call exactly, before any
/// interrupt or deadline) and the shared policy's request-bound allow-once
/// (D020/D026). Nothing is ever granted beyond this one request.
pub(crate) fn decide(prompt: &Prompt, offered: &[&str], eligible: bool) -> Option<bool> {
    let request = PermissionRequest {
        id: prompt.request_id.clone(),
        action: json!({"tool": prompt.call.name, "call": prompt.call.id,
                       "input": prompt.call.input})
        .to_string(),
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
    let mut policy = if eligible && offered.contains(&prompt.call.name.as_str()) {
        PermissionPolicy::grant_next_request(request.clone())
    } else {
        PermissionPolicy::default()
    };
    match policy.respond(&request) {
        PermissionResponse::Selected(id) => Some(id == "allow"),
        PermissionResponse::Cancelled | PermissionResponse::Refused => None,
    }
}

/// Control response to a host permission prompt. A grant returns the
/// prompted input unchanged and never the runtime's suggested rules or mode
/// changes, so nothing persists beyond this call.
pub(crate) fn permission_response(prompt: &Prompt, allow: bool) -> Value {
    let response = if allow {
        json!({"behavior": "allow", "updatedInput": prompt.call.input})
    } else {
        json!({"behavior": "deny", "message": "denied by agent-harness policy"})
    };
    json!({"type": "control_response", "response": {"subtype": "success",
           "request_id": prompt.request_id, "response": response}})
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
    use std::collections::HashMap;
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
    /// Announced calls awaiting a result.
    const PENDING_LIMIT: usize = 4096;

    #[derive(Default)]
    struct Observed {
        chunks: usize,
        tools: usize,
        permissions: usize,
        granted: usize,
        submitted: bool,
        interrupted: bool,
        violation: bool,
        /// Announced calls without a result yet, by ID, with whether the
        /// host has already been prompted for them.
        pending: HashMap<String, (Call, bool)>,
    }
    impl Observed {
        /// Cumulative counters, so a dropped activity record loses nothing.
        fn counters(&self) -> Value {
            json!({"assistant_chunks": self.chunks, "tool_events": self.tools,
                   "permission_requests": self.permissions, "grants": self.granted})
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
            "permission_requests": observed.permissions,
            "grants": observed.granted,
            "tool_events": observed.tools,
            "protocol_violation": observed.violation,
        });
        progress.event(format!(
            "cleanup={cleanup}; protocol_violation={}; permission requests: {}; grants: {}; tool events: {}; stderr_bytes={} (raw withheld; count capped at 1048577)",
            observed.violation,
            observed.permissions,
            observed.granted,
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
                "get_settings" => validate_settings(&response, effort(request)).map(|m| model = m),
                "mcp_status" => validate_mcp(&response),
                _ => validate_context(&response, &model, !tools(request).is_empty()),
            };
            if checked.is_err() {
                return Outcome::Refused;
            }
        }
        if cancelled.is_cancelled() || Instant::now() >= deadline {
            return Outcome::Stopped;
        }
        let offered = tools(request);
        let grants = grants(request);
        progress.event(format!(
            "{label} via Claude Code {VERSION}; model {} (resolved {model}); effort {}; {}{}",
            request.model,
            effort(request).map_or("model default", |e| e),
            match (request.permissions, offered.is_empty()) {
                (Permissions::Deny, _) => "permissions deny (no tools offered)".to_owned(),
                (Permissions::Trusted, true) => "permissions trusted narrowed by agent to no tools".to_owned(),
                (Permissions::Trusted, false) => format!(
                    "permissions trusted{} (tools {}; host prompts {}; host privileges, no OS sandbox)",
                    if offered.len() < TRUSTED_TOOLS.len() || !grants {
                        " narrowed by agent"
                    } else {
                        ""
                    },
                    offered.join(", "),
                    if grants { "granted once each" } else { "denied (ceiling below trusted)" }
                ),
            },
            request
                .agent
                .as_ref()
                .map(|a| format!("; agent {} (body appended to the system prompt)", a.name()))
                .unwrap_or_default()
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
                    progress.event(format!("active; chunks={}; tools={}; permissions={}", observed.chunks, observed.tools, observed.permissions));
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
                    let Ok(id) = validate_init(&record, &model, &request.project, &offered) else {
                        observed.violation = true;
                        progress.event("system/init did not match the preflight configuration");
                        violation_interrupt(channel, observed).await;
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
            let event = classify(&record, observed.interrupted);
            if let Err(reason) = tool_event(&event, &offered, observed) {
                observed.violation = true;
                progress.event(format!("{reason}; stopping"));
                violation_interrupt(channel, observed).await;
                return Outcome::Stopped;
            }
            match event {
                Event::Assistant { text, calls } => {
                    observed.chunks += text;
                    if text > 0 || !calls.is_empty() {
                        progress.event(format!(
                            "assistant activity; chunks={}; tools={}",
                            observed.chunks, observed.tools
                        ));
                        progress.emit("attempt.activity", observed.counters());
                    }
                }
                Event::ToolResults(_) => {
                    progress.emit("attempt.activity", observed.counters());
                }
                Event::Permission(prompt) => {
                    // The pending entry is marked prompted whatever the
                    // answer, so a repeat is never granted.
                    let first_exact = observed.pending.get_mut(&prompt.call.id).is_some_and(
                        |(call, prompted)| {
                            let first = !*prompted;
                            *prompted = true;
                            first && *call == prompt.call
                        },
                    );
                    let eligible = first_exact
                        && grants
                        && !observed.interrupted
                        && !cancelled.is_cancelled()
                        && Instant::now() < deadline;
                    let Some(allow) = decide(&prompt, &offered, eligible) else {
                        observed.violation = true;
                        progress.event("malformed permission prompt; stopping");
                        violation_interrupt(channel, observed).await;
                        return Outcome::Stopped;
                    };
                    observed.permissions += 1;
                    observed.granted += usize::from(allow);
                    if observed.permissions <= 16 || observed.permissions % 128 == 0 {
                        progress.event(format!(
                            "headless permission response; requests={}; grants={}",
                            observed.permissions, observed.granted
                        ));
                        progress.emit("attempt.activity", observed.counters());
                    }
                    if !channel
                        .send(
                            &permission_response(&prompt, allow),
                            deadline.max(Instant::now() + Duration::from_secs(1)),
                        )
                        .await
                    {
                        return Outcome::Stopped;
                    }
                }
                Event::Unsupported => unreachable!("rejected by tool_event"),
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

    /// Track announced calls and their results; refuses (with a reason) any
    /// tool activity the offered set does not permit: every tool event under
    /// deny, a call to a tool outside the set, a repeated call ID, a result
    /// for no announced call, an unsupported host request or subagent record,
    /// and a prompt under deny.
    fn tool_event(
        event: &Event,
        offered: &[&str],
        observed: &mut Observed,
    ) -> Result<(), &'static str> {
        match event {
            Event::Unsupported => Err("unsupported host request or tool record"),
            Event::Assistant { calls, .. } if !calls.is_empty() => {
                if offered.is_empty() {
                    return Err("tool call under deny");
                }
                for call in calls {
                    if !offered.contains(&call.name.as_str()) {
                        return Err("tool call outside the offered tool set");
                    }
                    if call.input["run_in_background"] == true {
                        return Err("background tool call");
                    }
                    if observed.pending.len() >= PENDING_LIMIT
                        || observed.pending.contains_key(&call.id)
                    {
                        return Err("repeated or unbounded tool call");
                    }
                    observed
                        .pending
                        .insert(call.id.clone(), (call.clone(), false));
                    observed.tools += 1;
                }
                Ok(())
            }
            Event::ToolResults(ids) => {
                if offered.is_empty() {
                    return Err("tool result under deny");
                }
                for id in ids {
                    if observed.pending.remove(id).is_none() {
                        return Err("tool result without an announced call");
                    }
                    observed.tools += 1;
                }
                Ok(())
            }
            Event::Permission(_) if offered.is_empty() => Err("host request under deny"),
            _ => Ok(()),
        }
    }

    /// Best-effort stop on a protocol violation, as on signal or deadline; the
    /// attempt stays uncertain whatever follows, and group cleanup still runs.
    /// Waits up to two seconds for any result, which is not trusted: the
    /// attempt is uncertain either way.
    async fn violation_interrupt(channel: &mut Channel, observed: &mut Observed) {
        let stop_by = Instant::now() + Duration::from_secs(2);
        if !interrupt(channel, observed, stop_by).await {
            return;
        }
        while let Ok(Some(Ok(record))) =
            tokio::time::timeout_at(stop_by, channel.records.recv()).await
        {
            if record["type"] == "result" {
                return;
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
            validate_init(&init(), "claude-sonnet-5-5", project, &[]),
            Ok("s-1")
        );
        assert!(validate_init(&init(), "claude-opus-5-5", project, &[]).is_err());
        assert!(validate_init(&init(), "claude-sonnet-5-5", Path::new("/other"), &[]).is_err());
        // Trusted: exactly the fixed set, in any order, nothing more or less.
        let mut trusted = init();
        trusted["tools"] = json!(["Write", "Read", "Grep", "Glob", "Edit", "Bash"]);
        assert!(validate_init(&trusted, "claude-sonnet-5-5", project, &TRUSTED_TOOLS).is_ok());
        assert!(validate_init(&trusted, "claude-sonnet-5-5", project, &[]).is_err());
        assert!(validate_init(&init(), "claude-sonnet-5-5", project, &TRUSTED_TOOLS).is_err());
        for tools in [
            json!(["Bash", "Edit", "Glob", "Grep", "Read", "Write", "Agent"]),
            json!(["Bash", "Edit", "Glob", "Grep", "Read"]),
            json!(["Bash", "Edit", "Glob", "Grep", "Read", "Read"]),
            json!(["Bash", "Edit", "Glob", "Grep", "Read", 1]),
        ] {
            trusted["tools"] = tools;
            assert!(validate_init(&trusted, "claude-sonnet-5-5", project, &TRUSTED_TOOLS).is_err());
        }
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
                validate_init(&event, "claude-sonnet-5-5", project, &[]).is_err(),
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
            validate_settings(&settings, None).as_deref(),
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
            assert!(validate_settings(&changed, None).is_err(), "{field}");
        }
        // A requested effort must apply exactly; none leaves the model default.
        let mut high = settings.clone();
        high["applied"]["effort"] = json!("high");
        assert!(validate_settings(&high, Some("high")).is_ok());
        assert!(validate_settings(&high, None).is_ok());
        assert!(validate_settings(&high, Some("max")).is_err());
        assert!(validate_settings(&settings, Some("high")).is_err());
        assert!(validate_mcp(&json!({"mcpServers": []})).is_ok());
        assert!(validate_mcp(&json!({"mcpServers": [{"name": "m"}]})).is_err());
        let context = json!({"model": "claude-sonnet-5-5", "memoryFiles": [], "mcpTools": [], "agents": [],
            "categories": [{"id": "system_prompt", "kind": "used"}, {"id": "messages", "kind": "used"},
                           {"id": "free_space", "kind": "free"}]});
        assert!(validate_context(&context, "claude-sonnet-5-5", false).is_ok());
        assert!(validate_context(&context, "claude-opus-5-5", false).is_err());
        let mut tools = context.clone();
        tools["categories"]
            .as_array_mut()
            .unwrap()
            .push(json!({"id": "system_tools", "kind": "used"}));
        assert!(validate_context(&tools, "claude-sonnet-5-5", false).is_err());
        assert!(validate_context(&tools, "claude-sonnet-5-5", true).is_ok());
        let mut skills = context.clone();
        skills["categories"]
            .as_array_mut()
            .unwrap()
            .push(json!({"id": "skills", "kind": "used"}));
        assert!(validate_context(&skills, "claude-sonnet-5-5", true).is_err());
        for field in ["memoryFiles", "mcpTools", "agents"] {
            let mut changed = context.clone();
            changed[field] = json!([{"name": "x"}]);
            assert!(
                validate_context(&changed, "claude-sonnet-5-5", true).is_err(),
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
        assert_eq!(
            classify(&text, false),
            Event::Assistant {
                text: 1,
                calls: vec![]
            }
        );
        let tool = json!({"type": "assistant", "parent_tool_use_id": null, "message": {"content": [
            {"type": "text", "text": "a"},
            {"type": "tool_use", "id": "t1", "name": "Bash", "input": {"command": "ls"}}]}});
        assert_eq!(
            classify(&tool, false),
            Event::Assistant {
                text: 1,
                calls: vec![Call {
                    id: "t1".into(),
                    name: "Bash".into(),
                    input: json!({"command": "ls"})
                }]
            }
        );
        let mut nested = tool.clone();
        nested["parent_tool_use_id"] = json!("t0");
        assert_eq!(classify(&nested, false), Event::Unsupported);
        for block in [
            json!({"type": "server_tool_use", "id": "s", "name": "web_search", "input": {}}),
            json!({"type": "unknown"}),
            json!({"type": "tool_use", "id": "", "name": "Bash", "input": {}}),
            json!({"type": "tool_use", "id": "t", "name": "Bash", "input": "ls"}),
        ] {
            let tool = json!({"type": "assistant", "message": {"content": [block]}});
            assert_eq!(classify(&tool, false), Event::Unsupported, "{tool}");
        }
        let result = json!({"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1"}]}});
        assert_eq!(
            classify(&result, false),
            Event::ToolResults(vec!["t1".into()])
        );
        let result = json!({"type": "user", "message": {"content": [{"type": "tool_result"}]}});
        assert_eq!(classify(&result, false), Event::Unsupported);
        for request in [
            json!({"type": "control_request"}),
            json!({"type": "control_request", "request_id": "q", "request": {"subtype": "hook_callback"}}),
            json!({"type": "control_request", "request_id": "q", "request": {
                "subtype": "can_use_tool", "tool_name": "Bash", "input": {}}}),
        ] {
            assert_eq!(classify(&request, false), Event::Unsupported, "{request}");
        }
        assert_eq!(
            classify(
                &json!({"type": "rate_limit_event", "rate_limit_info": {"status": "x\u{1b}"}}),
                false
            ),
            Event::RateLimit("unknown")
        );
    }

    fn prompt_for(name: &str) -> Prompt {
        Prompt {
            request_id: "q1".into(),
            call: Call {
                id: "t1".into(),
                name: name.into(),
                input: json!({"file_path": "/project/a.py", "content": "x"}),
            },
        }
    }

    #[test]
    fn prompts_are_granted_once_only_for_eligible_offered_tools() {
        let request = json!({"type": "control_request", "request_id": "q1", "request": {
            "subtype": "can_use_tool", "tool_name": "Write", "tool_use_id": "t1",
            "input": {"file_path": "/project/a.py", "content": "x"},
            "permission_suggestions": [{"type": "setMode", "mode": "acceptEdits"}]}});
        let Event::Permission(prompt) = classify(&request, false) else {
            panic!("permission prompt")
        };
        assert_eq!(prompt, prompt_for("Write"));
        assert_eq!(decide(&prompt, &TRUSTED_TOOLS, true), Some(true));
        assert_eq!(decide(&prompt, &TRUSTED_TOOLS, false), Some(false));
        assert_eq!(decide(&prompt, &[], true), Some(false));
        assert_eq!(
            decide(&prompt_for("NotebookEdit"), &TRUSTED_TOOLS, true),
            Some(false)
        );
        let mut empty = prompt_for("Write");
        empty.request_id = " ".into();
        assert_eq!(decide(&empty, &TRUSTED_TOOLS, true), None);
        // A grant echoes the prompted input and carries no rule or mode change.
        let allow = permission_response(&prompt, true);
        assert_eq!(allow["response"]["request_id"], "q1");
        assert_eq!(
            allow["response"]["response"],
            json!({"behavior": "allow", "updatedInput": prompt.call.input})
        );
        let deny = permission_response(&prompt, false);
        assert_eq!(deny["response"]["response"]["behavior"], "deny");
        assert!(!allow.to_string().contains("updatedPermissions"));
    }

    fn request(permissions: &str, agent: Option<(&str, &str, &str)>) -> Resolved {
        let config =
            r#"{"version":1,"mode":"cloud-only","native":{"target":"claude","model":"sonnet"}}"#;
        let args = ["single", "task", "--permissions", permissions].map(Into::into);
        let mut r = crate::config::Invocation::parse(args.to_vec(), Path::new("/tmp"))
            .unwrap()
            .resolve(
                crate::config::Config::read(config.as_bytes()).unwrap(),
                |_| None,
                &b""[..],
            )
            .unwrap();
        r.agent = agent.map(|(ceiling, tools, effort)| {
            Agent::read(format!("---\nversion: 1\nname: reviewer\ndescription: d\ncapacity: specialized\npermissions: {ceiling}\ntools: {tools}\neffort: {effort}\n---\nRole body\n").as_bytes()).unwrap()
        });
        r
    }

    fn arg(r: &Resolved, prefix: &str) -> Vec<String> {
        args(r)
            .into_iter()
            .map(|a| a.into_string().unwrap())
            .filter(|a| a.starts_with(prefix))
            .collect()
    }

    #[test]
    fn named_roles_intersect_tools_and_map_effort_and_body() {
        // No role: deny offers nothing; trusted offers the whole fixed set.
        assert!(tools(&request("deny", None)).is_empty());
        assert_eq!(tools(&request("trusted", None)), TRUSTED_TOOLS);
        // A deny invocation offers nothing for every role.
        let deny = request(
            "deny",
            Some(("trusted", "[read, search, edit, execute]", "default")),
        );
        assert!(tools(&deny).is_empty());
        assert!(!grants(&deny));
        assert_eq!(
            arg(&deny, "--permission-prompts"),
            ["--permission-prompts=none"]
        );
        // Trusted narrows to the role's tools, in the fixed order.
        let full = request(
            "trusted",
            Some(("trusted", "[execute, edit, search, read]", "default")),
        );
        assert_eq!(tools(&full), TRUSTED_TOOLS);
        assert!(grants(&full));
        let reviewer = request("trusted", Some(("read-only", "[search, read]", "default")));
        assert_eq!(tools(&reviewer), ["Glob", "Grep", "Read"]);
        assert!(
            !grants(&reviewer),
            "read-only ceiling is denied every prompt"
        );
        assert_eq!(arg(&reviewer, "--tools="), ["--tools=Glob,Grep,Read"]);
        let editor = request("trusted", Some(("trusted", "[edit]", "default")));
        assert_eq!(tools(&editor), ["Edit", "Write"]);
        assert!(grants(&editor));
        // A role with no tools launches as deny.
        let none = request("trusted", Some(("trusted", "[]", "default")));
        assert!(tools(&none).is_empty());
        assert!(!grants(&none), "no offered tool, no grant");
        assert_eq!(
            arg(&none, "--permission-prompts"),
            ["--permission-prompts=none"]
        );
        assert_eq!(arg(&none, "--tools="), ["--tools="]);
        // Effort: default passes nothing; every other level maps by name.
        assert!(arg(&full, "--effort").is_empty());
        for level in ["low", "medium", "high", "max"] {
            let r = request("deny", Some(("read-only", "[]", level)));
            assert_eq!(effort(&r), Some(level));
            assert_eq!(arg(&r, "--effort"), [format!("--effort={level}")]);
        }
        // The body is appended after any AGENTS.md file, as one argument.
        assert_eq!(
            arg(&full, "--append-system-prompt="),
            ["--append-system-prompt=Role body\n"]
        );
        assert!(arg(&request("trusted", None), "--append-system-prompt").is_empty());
        let mut both = full;
        both.instructions = Some("/tmp/AGENTS.md".into());
        let all = arg(&both, "--append-system-prompt");
        assert_eq!(all.len(), 2);
        assert!(all[0].starts_with("--append-system-prompt-file="));
        assert!(supported(&both).is_ok());
    }

    #[test]
    fn oversized_role_bodies_refuse_before_launch() {
        let mut r = request("trusted", None);
        let body = "x".repeat(BODY_LIMIT + 1);
        r.agent = Some(Agent::read(format!("---\nversion: 1\nname: big\ndescription: d\ncapacity: primary\npermissions: trusted\ntools: []\n---\n{body}").as_bytes()).unwrap());
        assert!(supported(&r).is_err());
        let body = "x".repeat(BODY_LIMIT);
        r.agent = Some(Agent::read(format!("---\nversion: 1\nname: big\ndescription: d\ncapacity: primary\npermissions: trusted\ntools: []\n---\n{body}").as_bytes()).unwrap());
        assert!(supported(&r).is_ok());
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
        assert!(env.contains(&("CLAUDE_CODE_DISABLE_BACKGROUND_TASKS".into(), "1".into())));
        assert!(environment(|_| None).is_err());
        assert_eq!(escape("a\u{202e}b"), "a\\u{202e}b");
    }
}
