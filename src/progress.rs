//! Bounded human diagnostics. A blocked consumer must never stall supervision.
use crate::config::Exit;
use std::{
    io::Write,
    sync::{
        Arc, Mutex,
        atomic::{AtomicUsize, Ordering},
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
}
impl Progress {
    pub fn new() -> Self {
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
    pub fn event(&self, message: impl AsRef<str>) {
        // Callers supply safe diagnostics, never backend text, paths or arguments.
        let message: String = message.as_ref().chars().take(512).collect();
        let line = format!(
            "ah: run={} elapsed={:.1}s {message}",
            self.run,
            self.start.elapsed().as_secs_f64()
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
    }
    pub fn finish(self, exit: Exit) -> Exit {
        *self.terminal.lock().unwrap() = Some(format!(
            "ah: run={} elapsed={:.1}s outcome={exit:?}; usage={}; no automatic retry or fallback; diagnostics_omitted={}{}",
            self.run,
            self.start.elapsed().as_secs_f64(),
            self.usage
                .lock()
                .unwrap()
                .as_deref()
                .unwrap_or("unknown (OpenCode ACP; no supported report)"),
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
pub(crate) async fn response(text: String) -> bool {
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
