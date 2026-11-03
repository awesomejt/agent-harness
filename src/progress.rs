//! Bounded human diagnostics and optional version-1 machine records (D039).
//! A blocked consumer must never stall supervision.
use crate::config::Exit;
use serde_json::{Map, Value, json};
use std::{
    io::Write,
    sync::{
        Arc, Mutex,
        atomic::{AtomicU64, AtomicUsize, Ordering},
        mpsc,
    },
    time::{Duration, Instant, SystemTime, UNIX_EPOCH},
};

#[derive(Clone)]
pub(crate) struct Progress {
    sender: mpsc::SyncSender<String>,
    dropped: Arc<AtomicUsize>,
    usage: Arc<Mutex<Option<String>>>,
    terminal: Arc<Mutex<Option<String>>>,
    drained: Arc<Mutex<Option<mpsc::Receiver<()>>>>,
    start: Instant,
    run: String,
    /// Attempt identity; attempts of one invocation share `run`.
    attempt: String,
    recovery: Arc<Mutex<&'static str>>,
    number: u8,
    machine: Option<Arc<Machine>>,
    summary: Arc<Mutex<Summary>>,
}

/// Machine records share one ordered stdout writer. Non-terminal records are
/// best-effort (a full queue drops them, leaving a `seq` gap); the terminal
/// `result` record is written last, after every queued record.
struct Machine {
    sender: Mutex<Option<mpsc::SyncSender<String>>>,
    seq: AtomicU64,
    dropped: AtomicUsize,
    last: Arc<Mutex<Option<String>>>,
    written: Mutex<Option<mpsc::Receiver<bool>>>,
}

/// Facts retained for the terminal record; never backend text other than the
/// final response, prompts, tool arguments, paths or credentials.
#[derive(Default)]
struct Summary {
    attempts: Vec<Map<String, Value>>,
    response: Option<String>,
    reason: Option<&'static str>,
    fallback: bool,
}

/// Unknown metrics are `null`, never zero.
fn unknown_usage() -> Value {
    json!({"source": null, "context_used_tokens": null, "context_capacity_tokens": null,
           "turn_tokens": null, "session_cost": null})
}

fn machine() -> Arc<Machine> {
    let (sender, receiver) = mpsc::sync_channel::<String>(256);
    let (done, written) = mpsc::channel();
    let last = Arc::new(Mutex::new(None::<String>));
    let final_record = last.clone();
    std::thread::spawn(move || {
        let write = |line: &str| {
            let mut out = std::io::stdout().lock();
            writeln!(out, "{line}").and_then(|()| out.flush()).is_ok()
        };
        // After a failed write, keep draining so senders never block, but
        // write nothing more: a later record would follow a partial line.
        let mut ok = true;
        while let Ok(line) = receiver.recv() {
            ok = ok && write(&line);
        }
        let record = final_record.lock().unwrap().take();
        let _ = done.send(ok && record.is_some_and(|line| write(&line)));
    });
    Arc::new(Machine {
        sender: Mutex::new(Some(sender)),
        seq: AtomicU64::new(0),
        dropped: AtomicUsize::new(0),
        last,
        written: Mutex::new(Some(written)),
    })
}

impl Progress {
    /// `machine` selects `--output jsonl`: stdout then carries only records.
    pub fn new(machine: bool) -> Self {
        let (sender, receiver) = mpsc::sync_channel::<String>(64);
        let (done, drained) = mpsc::channel();
        let terminal = Arc::new(Mutex::new(None::<String>));
        let final_line = terminal.clone();
        std::thread::spawn(move || {
            // Never retain the global stderr lock while idle. Active paths must
            // still use Progress instead of synchronous stderr writes.
            while let Ok(line) = receiver.recv() {
                if writeln!(std::io::stderr().lock(), "{line}").is_err() {
                    break;
                }
            }
            if let Some(line) = final_line.lock().unwrap().take() {
                let _ = writeln!(std::io::stderr().lock(), "{line}");
            }
            let _ = done.send(());
        });
        Self {
            sender,
            terminal,
            usage: Arc::default(),
            dropped: Arc::default(),
            drained: Arc::new(Mutex::new(Some(drained))),
            start: Instant::now(),
            attempt: String::new(),
            recovery: Arc::new(Mutex::new("no automatic retry or fallback")),
            number: 0,
            machine: machine.then(self::machine),
            summary: Arc::default(),
            run: format!(
                "{:x}-{:x}",
                std::process::id(),
                SystemTime::now()
                    .duration_since(UNIX_EPOCH)
                    .unwrap_or_default()
                    .as_nanos()
            ),
        }
    }
    /// Diagnostics scoped to one linked attempt of this run.
    pub fn attempt(&self, number: u8) -> Self {
        Self {
            attempt: format!("attempt={number} "),
            number,
            ..self.clone()
        }
    }
    fn envelope(&self, kind: &str, seq: u64, data: Value) -> String {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap_or_default();
        let mut fields = Map::new();
        fields.insert("v".into(), json!(1));
        fields.insert("seq".into(), json!(seq));
        fields.insert("run".into(), json!(self.run));
        fields.insert("type".into(), json!(kind));
        fields.insert("ts_ms".into(), json!(now.as_millis() as u64));
        fields.insert(
            "elapsed_ms".into(),
            json!(self.start.elapsed().as_millis() as u64),
        );
        if self.number > 0 {
            fields.insert("attempt".into(), json!(self.number));
        }
        let Value::Object(data) = data else {
            unreachable!("record data is an object")
        };
        fields.extend(data);
        Value::Object(fields).to_string()
    }
    /// Best-effort machine record; a no-op in human mode.
    pub fn emit(&self, kind: &'static str, data: Value) {
        let Some(machine) = &self.machine else {
            return;
        };
        // Numbering under the queue lock keeps stdout order equal to `seq`.
        let sender = machine.sender.lock().unwrap();
        let seq = machine.seq.fetch_add(1, Ordering::SeqCst);
        let line = self.envelope(kind, seq, data);
        let sent = sender
            .as_ref()
            .is_some_and(|sender| sender.try_send(line).is_ok());
        if !sent {
            machine.dropped.fetch_add(1, Ordering::Relaxed);
        }
    }
    /// Merge facts into this attempt's terminal summary.
    pub fn note(&self, data: Value) {
        let mut summary = self.summary.lock().unwrap();
        let number = self.number;
        let index = match summary
            .attempts
            .iter()
            .position(|a| a["attempt"] == json!(number))
        {
            Some(index) => index,
            None => {
                let mut entry = Map::new();
                entry.insert("attempt".into(), json!(number));
                for key in [
                    "route",
                    "model",
                    "group",
                    "permissions",
                    "agent",
                    "session",
                    "backend_stop",
                    "cleanup_confirmed",
                    "permission_requests",
                    "grants",
                    "tool_events",
                    "protocol_violation",
                    "runtime_state_removed",
                ] {
                    entry.insert(key.into(), Value::Null);
                }
                entry.insert("launched".into(), json!(false));
                entry.insert("prompt_submitted".into(), json!(false));
                entry.insert("usage".into(), unknown_usage());
                summary.attempts.push(entry);
                summary.attempts.len() - 1
            }
        };
        if let Value::Object(fields) = data {
            summary.attempts[index].extend(fields);
        }
    }
    /// Start this attempt once; repeated calls for the same number are ignored.
    pub fn start(&self, description: Value) {
        let known = self
            .summary
            .lock()
            .unwrap()
            .attempts
            .iter()
            .any(|a| a["attempt"] == json!(self.number));
        if !known {
            self.note(description.clone());
            self.emit("attempt.started", description);
        }
    }
    /// Report a static harness rejection on stderr and in the result record.
    pub fn reject(&self, reason: &'static str) {
        self.event(reason);
        self.reason(reason);
    }
    /// The first static harness reason is kept for the result record.
    pub fn reason(&self, reason: &'static str) {
        self.summary.lock().unwrap().reason.get_or_insert(reason);
    }
    pub fn fallback(&self) {
        self.summary.lock().unwrap().fallback = true;
        self.emit(
            "fallback",
            json!({"from_attempt": 1, "to_attempt": 2,
                   "reason": "litellm_unreachable_before_submission"}),
        );
    }
    /// Recovery summary reported on the final line.
    pub fn recovery(&self, summary: &'static str) {
        *self.recovery.lock().unwrap() = summary;
    }
    pub fn event(&self, message: impl AsRef<str>) {
        // Callers supply safe diagnostics, never backend text, paths or arguments.
        let message: String = message.as_ref().chars().take(512).collect();
        let line = format!(
            "ah: run={} elapsed={:.1}s {}{message}",
            self.run,
            self.start.elapsed().as_secs_f64(),
            self.attempt
        );
        if self.sender.try_send(line).is_err() {
            self.dropped.fetch_add(1, Ordering::Relaxed);
        }
    }
    #[cfg(target_os = "macos")]
    pub fn usage(&self, update: &serde_json::Value) {
        let (Some(used), Some(size)) = (update["used"].as_u64(), update["size"].as_u64()) else {
            return;
        };
        let mut report = format!(
            "source=OpenCode ACP session/update; context_used={used} tokens; context_capacity={size} tokens; turn_tokens=unknown; session_cost=unknown"
        );
        if let (Some(amount), Some(currency)) = (
            update["cost"]["amount"].as_f64(),
            update["cost"]["currency"].as_str(),
        ) {
            if amount.is_finite()
                && amount >= 0.0
                && currency.len() == 3
                && currency.bytes().all(|b| b.is_ascii_uppercase())
            {
                report = format!(
                    "source=OpenCode ACP session/update; context_used={used} tokens; context_capacity={size} tokens; turn_tokens=unknown; session_cost={amount} {currency}"
                );
            }
        }
        *self.usage.lock().unwrap() = Some(report);
        let cost = update["cost"]["amount"]
            .as_f64()
            .zip(update["cost"]["currency"].as_str())
            .filter(|(amount, currency)| {
                amount.is_finite()
                    && *amount >= 0.0
                    && currency.len() == 3
                    && currency.bytes().all(|b| b.is_ascii_uppercase())
            })
            .map(|(amount, currency)| json!({"amount": amount, "currency": currency}));
        let usage = json!({"source": "opencode-acp-usage-update", "context_used_tokens": used,
                           "context_capacity_tokens": size, "turn_tokens": null,
                           "session_cost": cost});
        self.note(json!({"usage": usage}));
        self.emit("attempt.usage", usage);
    }
    fn result(&self, exit: Exit) -> Value {
        let summary = self.summary.lock().unwrap();
        // An explicit public mapping, not serialization of the Rust enum.
        let outcome = match exit {
            Exit::Success => "succeeded",
            Exit::Failed => "failed",
            Exit::Invalid => "rejected",
            Exit::Cancelled => "cancelled",
            Exit::Uncertain => "uncertain",
        };
        json!({
            "outcome": outcome,
            "exit": exit as u8,
            "reason": summary.reason,
            "response": summary.response,
            "attempts": summary.attempts,
            "fallback": summary.fallback,
            "recovery": *self.recovery.lock().unwrap(),
            "diagnostics_omitted": self.dropped.load(Ordering::Relaxed),
            "records_dropped": self.machine.as_ref().map_or(0, |m| m.dropped.load(Ordering::Relaxed)),
        })
    }
    pub fn finish(self, exit: Exit) -> Exit {
        let mut exit = exit;
        if let Some(machine) = &self.machine {
            // Closing the queue lets the writer append the result last.
            let sender = machine.sender.lock().unwrap().take();
            let seq = machine.seq.fetch_add(1, Ordering::SeqCst);
            let record = self.envelope("result", seq, self.result(exit));
            *machine.last.lock().unwrap() = Some(record);
            drop(sender);
            let written = machine.written.lock().unwrap().take();
            let delivered =
                written.is_some_and(|w| w.recv_timeout(Duration::from_secs(2)) == Ok(true));
            if !delivered {
                self.event("machine result delivery failed or blocked; stdout records may be missing or partial");
                if exit == Exit::Success {
                    exit = Exit::Failed;
                }
            }
        }
        *self.terminal.lock().unwrap() = Some(format!(
            "ah: run={} elapsed={:.1}s outcome={exit:?}; usage={}; {}; diagnostics_omitted={}{}",
            self.run,
            self.start.elapsed().as_secs_f64(),
            self.usage
                .lock()
                .unwrap()
                .as_deref()
                .unwrap_or("unknown (OpenCode ACP; no supported report)"),
            self.recovery.lock().unwrap(),
            self.dropped.load(Ordering::Relaxed),
            if exit == Exit::Uncertain {
                "; uncertain completion or cleanup; inspect project effects before retrying"
            } else {
                ""
            }
        ));
        // Closing the last sender flushes queued diagnostics. Never join a writer
        // blocked in the OS; process exit ends that dedicated thread.
        let drained = self.drained.lock().unwrap().take();
        drop(self);
        if let Some(drained) = drained {
            let _ = drained.recv_timeout(Duration::from_secs(1));
        }
        exit
    }
}

#[cfg(target_os = "macos")]
impl Progress {
    /// Human mode writes the final response to stdout now; machine mode
    /// carries it in the terminal result record instead.
    pub(crate) async fn deliver(&self, text: String) -> bool {
        if self.machine.is_some() {
            self.summary.lock().unwrap().response = Some(text);
            return true;
        }
        response(text).await
    }
}

#[cfg(target_os = "macos")]
async fn response(text: String) -> bool {
    let (send, receive) = tokio::sync::oneshot::channel();
    std::thread::spawn(move || {
        let result = std::io::stdout().lock().write_all(text.as_bytes()).is_ok();
        let _ = send.send(result);
    });
    matches!(
        tokio::time::timeout(Duration::from_secs(2), receive).await,
        Ok(Ok(true))
    )
}
