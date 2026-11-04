//! Unix process ownership with bounded escalation, reap and group verification.
use std::sync::{
    Arc,
    atomic::{AtomicUsize, Ordering},
};
use std::{io, process::Stdio, time::Duration};
use tokio::process::{Child, Command};

pub(crate) struct OwnedChild {
    pub child: Child,
    group: i32,
    escalated: bool,
    stderr_bytes: Arc<AtomicUsize>,
    stderr_drain: Option<tokio::task::JoinHandle<()>>,
}
impl OwnedChild {
    pub fn spawn(command: &mut Command) -> io::Result<Self> {
        let mut owned = Self::start(
            command
                .stdin(Stdio::piped())
                .stdout(Stdio::piped())
                .stderr(Stdio::piped()),
        )?;
        let mut stderr = owned.child.stderr.take().unwrap();
        let count = owned.stderr_bytes.clone();
        owned.stderr_drain = Some(tokio::spawn(async move {
            use tokio::io::AsyncReadExt;
            let mut buf = [0u8; 8192];
            while let Ok(n) = stderr.read(&mut buf).await {
                if n == 0 {
                    break;
                }
                // Retain no raw backend data; cap counters as well as storage.
                let _ = count.fetch_update(Ordering::Relaxed, Ordering::Relaxed, |v| {
                    Some(v.saturating_add(n).min(1_048_577))
                });
            }
        }));
        Ok(owned)
    }
    /// A verification check (D043): no stdin; output goes to the given handles.
    pub fn spawn_output(command: &mut Command, stdout: Stdio, stderr: Stdio) -> io::Result<Self> {
        Self::start(command.stdin(Stdio::null()).stdout(stdout).stderr(stderr))
    }
    fn start(command: &mut Command) -> io::Result<Self> {
        let child = command.kill_on_drop(true).process_group(0).spawn()?;
        let group = child.id().ok_or_else(|| io::Error::other("missing pid"))? as i32;
        Ok(Self {
            child,
            group,
            escalated: false,
            stderr_bytes: Arc::default(),
            stderr_drain: None,
        })
    }
    fn signal(&self, signal: i32) {
        if self.group > 0 {
            unsafe {
                libc::kill(-self.group, signal);
            }
        }
    }
    pub fn stderr_bytes(&self) -> usize {
        self.stderr_bytes.load(Ordering::Relaxed)
    }
    pub async fn cleanup(&mut self) -> bool {
        let reaped = matches!(self.child.try_wait(), Ok(Some(_)));
        self.signal(libc::SIGTERM);
        if !reaped {
            let _ = tokio::time::timeout(Duration::from_secs(2), self.child.wait()).await;
        }
        self.signal(libc::SIGKILL);
        self.escalated = true;
        if !matches!(
            tokio::time::timeout(Duration::from_secs(5), self.child.wait()).await,
            Ok(Ok(_))
        ) {
            return false;
        }
        if let Some(drain) = &mut self.stderr_drain
            && tokio::time::timeout(Duration::from_millis(500), &mut *drain)
                .await
                .is_err()
        {
            drain.abort();
        }
        // A reaped leader alone says nothing about descendants. ps is bounded,
        // invoked without a shell, and zombies count as terminated.
        for _ in 0..10 {
            let mut ps = Command::new("/bin/ps");
            ps.args(["-axo", "pgid=,stat="])
                .env_clear()
                .env("LC_ALL", "C");
            let Ok(mut child) = OwnedChild::spawn_check(&mut ps) else {
                return false;
            };
            let output = tokio::time::timeout(Duration::from_secs(1), async {
                use tokio::io::AsyncReadExt;
                let mut bytes = Vec::new();
                child
                    .stdout
                    .take()
                    .unwrap()
                    .take(1_048_577)
                    .read_to_end(&mut bytes)
                    .await?;
                let status = child.wait().await?;
                Ok::<_, io::Error>((bytes, status))
            })
            .await;
            let Ok(Ok((bytes, status))) = output else {
                let _ = child.start_kill();
                return false;
            };
            if !status.success() || bytes.len() > 1_048_576 {
                return false;
            }
            let Ok(text) = std::str::from_utf8(&bytes) else {
                return false;
            };
            let live = text.lines().any(|line| {
                let mut fields = line.split_whitespace();
                fields.next().and_then(|s| s.parse::<i32>().ok()) == Some(self.group)
                    && fields.next().is_none_or(|s| !s.starts_with('Z'))
            });
            if !live {
                self.group = 0;
                return true;
            }
            tokio::time::sleep(Duration::from_millis(100)).await;
        }
        false
    }
    fn spawn_check(command: &mut Command) -> io::Result<Child> {
        command
            .stdin(Stdio::null())
            .stdout(Stdio::piped())
            .stderr(Stdio::null())
            .kill_on_drop(true)
            .spawn()
    }
}
impl Drop for OwnedChild {
    fn drop(&mut self) {
        if let Some(drain) = &self.stderr_drain {
            drain.abort();
        }
        if !self.escalated {
            self.signal(libc::SIGKILL);
        }
        let _ = self.child.start_kill();
    }
}
