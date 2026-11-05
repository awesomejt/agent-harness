//! Durable sequence records (D044): versioned JSON under the XDG state
//! directory, outside the project, replaced atomically, with a per-project
//! nonblocking lock. Records hold identities and outcomes only: never prompt
//! text, responses, check output, argv text, environment names or keys.
use crate::config::{Exit, Invalid};
use serde::{Deserialize, Serialize};
use std::ffi::OsString;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

pub const VERSION: u32 = 1;
pub const MAX_RECORD_BYTES: usize = 4 * 1_048_576;
pub const MAX_ATTEMPTS: usize = 32;

/// A state failure and the exit it maps to: policy and input problems exit 2;
/// an unwritable store before any launch exits 1.
#[derive(Debug, PartialEq, Eq)]
pub struct Failure {
    pub exit: Exit,
    pub reason: &'static str,
}

impl From<Invalid> for Failure {
    fn from(error: Invalid) -> Self {
        Self {
            exit: Exit::Invalid,
            reason: error.0,
        }
    }
}

fn io(reason: &'static str) -> Failure {
    Failure {
        exit: Exit::Failed,
        reason,
    }
}

type Result<T> = std::result::Result<T, Failure>;

pub(crate) fn sha256(bytes: &[u8]) -> String {
    use sha2::Digest;
    sha2::Sha256::digest(bytes)
        .iter()
        .map(|b| format!("{b:02x}"))
        .collect()
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum RunStatus {
    Active,
    Stopped,
    Completed,
}

/// Step and attempt status. `pending` applies to steps only; `interrupted`
/// is an `active` attempt whose lock was free (uncertain effects).
#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Status {
    Pending,
    Active,
    Succeeded,
    Accepted,
    Failed,
    Rejected,
    Cancelled,
    Uncertain,
    Interrupted,
}

impl Status {
    pub fn name(self) -> &'static str {
        match self {
            Status::Pending => "pending",
            Status::Active => "active",
            Status::Succeeded => "succeeded",
            Status::Accepted => "accepted",
            Status::Failed => "failed",
            Status::Rejected => "rejected",
            Status::Cancelled => "cancelled",
            Status::Uncertain => "uncertain",
            Status::Interrupted => "interrupted",
        }
    }
    pub fn complete(self) -> bool {
        matches!(self, Status::Succeeded | Status::Accepted)
    }
    /// The D024 exit of a finished agent attempt.
    pub fn of(exit: Exit) -> Self {
        match exit {
            Exit::Success => Status::Succeeded,
            Exit::Failed => Status::Failed,
            Exit::Invalid => Status::Rejected,
            Exit::Cancelled => Status::Cancelled,
            Exit::Uncertain => Status::Uncertain,
        }
    }
}

#[derive(Clone, Copy, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(rename_all = "snake_case")]
pub enum Reason {
    Initial,
    Resume,
    Retry,
    Accept,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Record {
    pub v: u32,
    pub run: String,
    pub created: String,
    pub updated: String,
    pub project: String,
    pub folder: String,
    pub config: String,
    pub status: RunStatus,
    pub steps: Vec<StepRecord>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct StepRecord {
    pub name: String,
    pub sha256: String,
    pub agent: Option<String>,
    pub check: Option<String>,
    pub status: Status,
    pub attempts: Vec<Attempt>,
}

#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Attempt {
    pub number: u32,
    pub reason: Reason,
    pub status: Status,
    pub started: String,
    pub ended: Option<String>,
    pub input_sha256: String,
    pub agent_sha256: Option<String>,
    pub check: Option<CheckIdentity>,
    pub route: String,
    pub model: String,
    pub fallback: Option<String>,
    pub permissions: String,
    pub timeout_secs: u64,
    /// `null` when no agent turn ran (`accept`) or the result is not yet known.
    pub agent_outcome: Option<String>,
    pub exit: Option<u8>,
    pub verification: Option<Verification>,
    pub backends: Vec<Backend>,
}

/// The pinned check: program path as found and the SHA-256 of the JSON array
/// of its arguments (the arguments themselves are not stored).
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct CheckIdentity {
    pub name: String,
    pub program: String,
    pub argv_sha256: String,
}

/// The D043 verification fields.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Verification {
    pub check: String,
    pub status: String,
    pub agent_outcome: Option<String>,
    pub exit_code: Option<i32>,
    pub signal: Option<i32>,
    pub timeout_secs: u64,
    pub duration_ms: Option<u64>,
    pub cleanup_confirmed: Option<bool>,
}

/// The per-backend summary of the D039 result attempt entry.
#[derive(Clone, Debug, PartialEq, Eq, Serialize, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Backend {
    pub attempt: u8,
    pub launched: bool,
    pub prompt_submitted: bool,
    pub backend_stop: Option<String>,
    pub cleanup_confirmed: Option<bool>,
    pub grants: Option<u64>,
    pub tool_events: Option<u64>,
}

impl Attempt {
    /// Whether the attempt may have crossed the submission boundary. Only an
    /// agent attempt that ended rejected, failed or cancelled with no backend
    /// prompt submitted is known to have had no agent effects.
    pub fn may_have_effects(&self) -> bool {
        self.reason == Reason::Accept
            || !matches!(
                self.status,
                Status::Rejected | Status::Failed | Status::Cancelled
            )
            || self.backends.iter().any(|b| b.prompt_submitted)
    }
}

impl Record {
    /// Leading completed steps; resume starts after them.
    pub fn completed(&self) -> usize {
        self.steps
            .iter()
            .take_while(|step| step.status.complete())
            .count()
    }
}

/// `sYYYYMMDDTHHMMSSZ-` plus 8 lowercase hex characters, checked before any
/// path is formed from it.
pub fn valid_run_id(id: &str) -> bool {
    let b = id.as_bytes();
    b.len() == 26
        && b[0] == b's'
        && b[1..9].iter().all(u8::is_ascii_digit)
        && b[9] == b'T'
        && b[10..16].iter().all(u8::is_ascii_digit)
        && b[16] == b'Z'
        && b[17] == b'-'
        && b[18..]
            .iter()
            .all(|c| c.is_ascii_digit() || (b'a'..=b'f').contains(c))
}

fn civil(secs: u64) -> (i64, u64, u64, u64, u64, u64) {
    // Days to proleptic Gregorian date (Hinnant's civil_from_days).
    let z = (secs / 86400) as i64 + 719_468;
    let era = z.div_euclid(146_097);
    let doe = z.rem_euclid(146_097);
    let yoe = (doe - doe / 1460 + doe / 36524 - doe / 146_096) / 365;
    let doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
    let mp = (5 * doy + 2) / 153;
    let day = (doy - (153 * mp + 2) / 5 + 1) as u64;
    let month = if mp < 10 { mp + 3 } else { mp - 9 } as u64;
    let year = yoe + era * 400 + i64::from(month <= 2);
    let rem = secs % 86400;
    (year, month, day, rem / 3600, rem / 60 % 60, rem % 60)
}

fn now_secs() -> u64 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .unwrap_or_default()
        .as_secs()
}

/// RFC 3339 UTC timestamp with second precision.
pub fn timestamp(secs: u64) -> String {
    let (y, mo, d, h, mi, s) = civil(secs);
    format!("{y:04}-{mo:02}-{d:02}T{h:02}:{mi:02}:{s:02}Z")
}

pub fn now() -> String {
    timestamp(now_secs())
}

/// A new run ID from the current UTC time and 4 bytes of `/dev/urandom`.
pub fn new_run_id() -> Result<String> {
    let mut random = [0u8; 4];
    File::open("/dev/urandom")
        .and_then(|mut f| f.read_exact(&mut random))
        .map_err(|_| io("cannot read /dev/urandom for a sequence run ID"))?;
    let (y, mo, d, h, mi, s) = civil(now_secs());
    let hex: String = random.iter().map(|b| format!("{b:02x}")).collect();
    Ok(format!("s{y:04}{mo:02}{d:02}T{h:02}{mi:02}{s:02}Z-{hex}"))
}

/// `$XDG_STATE_HOME/agent-harness` when that is absolute, else
/// `$HOME/.local/state/agent-harness`; only the fallback requires `HOME`.
pub fn root(lookup: impl Fn(&str) -> Option<OsString>) -> Result<PathBuf> {
    if let Some(xdg) = lookup("XDG_STATE_HOME")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
    {
        return Ok(xdg.join("agent-harness"));
    }
    let home = lookup("HOME")
        .map(PathBuf::from)
        .filter(|p| p.is_absolute())
        .ok_or(Invalid(
            "sequence state needs an absolute XDG_STATE_HOME or HOME",
        ))?;
    Ok(home.join(".local/state/agent-harness"))
}

/// The state root must lie outside the canonical project, so a project clean
/// or an agent edit cannot remove it. Missing components resolve through the
/// deepest existing ancestor.
fn outside(root: &Path, project: &Path) -> Result<()> {
    const UNAVAILABLE: Invalid = Invalid("sequence state directory is unavailable");
    let mut existing = root.to_path_buf();
    let mut missing = Vec::new();
    let canonical = loop {
        match existing.canonicalize() {
            Ok(path) => break path,
            Err(_) => {
                missing.push(existing.file_name().ok_or(UNAVAILABLE)?.to_owned());
                existing = existing.parent().ok_or(UNAVAILABLE)?.to_path_buf();
            }
        }
    };
    let full = missing.iter().rev().fold(canonical, |p, n| p.join(n));
    if full.starts_with(project) {
        return Err(Invalid("sequence state directory must lie outside the project").into());
    }
    Ok(())
}

/// A reused harness-owned directory or lock file must belong to the current
/// user and grant no group or other access; creation modes cannot protect
/// objects that already exist. Refused, never repaired: a permissive store
/// may already hold replaced records or locks.
#[cfg(unix)]
fn private(meta: &std::fs::Metadata) -> Result<()> {
    use std::os::unix::fs::MetadataExt;
    if meta.uid() != unsafe { libc::geteuid() } || meta.mode() & 0o077 != 0 {
        return Err(Invalid(
            "sequence state must be owned by the current user and private (directories 0700, files 0600)",
        )
        .into());
    }
    Ok(())
}

#[cfg(not(unix))]
fn private(_: &std::fs::Metadata) -> Result<()> {
    Ok(())
}

/// A harness-owned directory must be a real, private directory, never a
/// symlink.
fn real_dir(path: &Path) -> Result<bool> {
    match std::fs::symlink_metadata(path) {
        Ok(m) if m.is_dir() => private(&m).map(|()| true),
        Ok(_) => Err(Invalid(
            "sequence state directories must be real directories, not symlinks or files",
        )
        .into()),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(_) => Err(Invalid("sequence state directory is unavailable").into()),
    }
}

pub struct Store {
    root: PathBuf,
}

/// A held project lock; dropping it releases the lock.
pub struct Lock {
    _file: File,
}

impl Store {
    /// Create (0700) or reuse the store for `run`/`resume`.
    pub fn create(root: PathBuf, project: &Path) -> Result<Self> {
        outside(&root, project)?;
        let mut builder = std::fs::DirBuilder::new();
        builder.recursive(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::DirBuilderExt;
            builder.mode(0o700);
        }
        if !real_dir(&root)? {
            builder
                .create(&root)
                .map_err(|_| io("cannot create sequence state directory"))?;
        }
        for dir in [&root, &root.join("sequences"), &root.join("locks")] {
            if !real_dir(dir)? {
                builder
                    .create(dir)
                    .map_err(|_| io("cannot create sequence state directory"))?;
                real_dir(dir)?;
            }
        }
        Ok(Self { root })
    }

    /// Read-only access for `show` and `resume`; never creates anything.
    /// `None` when no run has ever been recorded.
    pub fn existing(root: PathBuf) -> Result<Option<Self>> {
        for dir in [&root, &root.join("sequences")] {
            if !real_dir(dir)? {
                return Ok(None);
            }
        }
        Ok(Some(Self { root }))
    }

    pub fn record_path(&self, run: &str) -> PathBuf {
        debug_assert!(valid_run_id(run));
        self.root.join("sequences").join(format!("{run}.json"))
    }

    fn lock_path(&self, project: &Path) -> PathBuf {
        self.root.join("locks").join(format!(
            "{}.lock",
            sha256(project.as_os_str().as_encoded_bytes())
        ))
    }

    /// Take the project's nonblocking lock and name its holder run, so `show`
    /// can tell an active run from one interrupted while another holds it.
    #[cfg(unix)]
    pub fn lock(&self, project: &Path, run: &str) -> Result<Lock> {
        use std::os::fd::AsRawFd;
        use std::os::unix::fs::OpenOptionsExt;
        let mut file = OpenOptions::new()
            .read(true)
            .write(true)
            .create(true)
            .truncate(false)
            .mode(0o600)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(self.lock_path(project))
            .map_err(|_| io("cannot open sequence project lock"))?;
        match file.metadata() {
            Ok(m) if m.is_file() => private(&m)?,
            _ => return Err(Invalid("invalid sequence project lock").into()),
        }
        if unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
            return Err(
                Invalid("another sequence holds this project's lock; nothing launched").into(),
            );
        }
        file.set_len(0)
            .and_then(|()| file.write_all(run.as_bytes()))
            .map_err(|_| io("cannot write sequence project lock"))?;
        Ok(Lock { _file: file })
    }

    #[cfg(not(unix))]
    pub fn lock(&self, _: &Path, _: &str) -> Result<Lock> {
        Err(Invalid("sequence locks require Unix").into())
    }

    /// Whether `run` is the live holder of its project's lock. A momentary
    /// nonblocking shared probe; it is released at once.
    #[cfg(unix)]
    pub fn holds(&self, project: &Path, run: &str) -> bool {
        use std::os::fd::AsRawFd;
        use std::os::unix::fs::OpenOptionsExt;
        let Ok(mut file) = OpenOptions::new()
            .read(true)
            .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
            .open(self.lock_path(project))
        else {
            return false;
        };
        let mut holder = String::new();
        if (&mut file).take(64).read_to_string(&mut holder).is_err() || holder != run {
            return false;
        }
        unsafe { libc::flock(file.as_raw_fd(), libc::LOCK_SH | libc::LOCK_NB) != 0 }
    }

    #[cfg(not(unix))]
    pub fn holds(&self, _: &Path, _: &str) -> bool {
        false
    }

    /// Strict read: a bounded regular file, `v` 1, no unknown fields, and the
    /// run ID it is filed under. Nothing is rewritten on refusal.
    pub fn read(&self, run: &str) -> Result<Record> {
        if !valid_run_id(run) {
            return Err(Invalid("run ID must be sYYYYMMDDTHHMMSSZ-xxxxxxxx").into());
        }
        let mut options = OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_NOCTTY);
        }
        let file = match options.open(self.record_path(run)) {
            Ok(file) => file,
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                return Err(Invalid("no sequence record with that run ID").into());
            }
            Err(_) => return Err(Invalid("cannot open sequence record").into()),
        };
        if !file.metadata().is_ok_and(|m| m.is_file()) {
            return Err(Invalid("sequence record must be a regular file").into());
        }
        let mut bytes = Vec::new();
        file.take(MAX_RECORD_BYTES as u64 + 1)
            .read_to_end(&mut bytes)
            .map_err(|_| Invalid("cannot read sequence record"))?;
        if bytes.len() > MAX_RECORD_BYTES {
            return Err(Invalid("sequence record exceeds 4 MiB").into());
        }
        parse(&bytes, run)
    }

    /// Atomic initial publication (D044): write and fsync an exclusive temporary
    /// file in `sequences/`, publish via hard link so an existing record is never
    /// overwritten (refusing with `already recorded`), then fsync the directory.
    pub fn create_record(&self, record: &Record) -> Result<()> {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let mut text = serde_json::to_string_pretty(record)
            .map_err(|_| io("cannot encode sequence record"))?;
        text.push('\n');
        if text.len() > MAX_RECORD_BYTES {
            return Err(io("sequence record would exceed 4 MiB"));
        }
        let dir = self.root.join("sequences");
        let temp = dir.join(format!(
            ".{}.tmp-{}-{}",
            record.run,
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600).custom_flags(libc::O_NOFOLLOW);
        }
        let mut file = options
            .open(&temp)
            .map_err(|_| io("cannot stage sequence record"))?;
        let staged = file
            .write_all(text.as_bytes())
            .and_then(|()| file.sync_all());
        if staged.is_err() {
            let _ = std::fs::remove_file(&temp);
            return Err(io("cannot stage sequence record"));
        }
        let target = self.record_path(&record.run);
        let published = std::fs::hard_link(&temp, &target);
        let _ = std::fs::remove_file(&temp);
        match published {
            Ok(()) => {
                File::open(&dir)
                    .and_then(|d| d.sync_all())
                    .map_err(|_| io("cannot write sequence record"))?;
                Ok(())
            }
            Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => Err(Failure {
                exit: Exit::Failed,
                reason: "sequence run ID already recorded",
            }),
            Err(_) => Err(io("cannot write sequence record")),
        }
    }

    /// Atomic replace (D025): exclusive 0600 temporary file in the same
    /// directory, write, fsync, rename, then fsync the directory.
    pub fn write(&self, record: &Record) -> Result<()> {
        use std::sync::atomic::{AtomicU64, Ordering};
        static NEXT: AtomicU64 = AtomicU64::new(0);
        let mut text = serde_json::to_string_pretty(record)
            .map_err(|_| io("cannot encode sequence record"))?;
        text.push('\n');
        if text.len() > MAX_RECORD_BYTES {
            return Err(io("sequence record would exceed 4 MiB"));
        }
        let dir = self.root.join("sequences");
        let temp = dir.join(format!(
            ".{}.tmp-{}-{}",
            record.run,
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        let mut options = OpenOptions::new();
        options.write(true).create_new(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.mode(0o600).custom_flags(libc::O_NOFOLLOW);
        }
        let mut file = options
            .open(&temp)
            .map_err(|_| io("cannot stage sequence record"))?;
        let result = file
            .write_all(text.as_bytes())
            .and_then(|()| file.sync_all())
            .and_then(|()| std::fs::rename(&temp, self.record_path(&record.run)))
            .and_then(|()| File::open(&dir)?.sync_all())
            .map_err(|_| io("cannot write sequence record"));
        let _ = std::fs::remove_file(&temp);
        result
    }

    /// Every record file, ordered by run ID (creation time); unreadable ones
    /// are reported, not skipped silently.
    pub fn list(&self) -> Result<Vec<(String, Result<Record>)>> {
        let mut runs = Vec::new();
        for entry in std::fs::read_dir(self.root.join("sequences"))
            .map_err(|_| Invalid("cannot list sequence records"))?
        {
            let entry = entry.map_err(|_| Invalid("cannot list sequence records"))?;
            let Some(run) = entry
                .file_name()
                .to_str()
                .and_then(|n| n.strip_suffix(".json"))
                .filter(|n| valid_run_id(n))
                .map(str::to_owned)
            else {
                continue;
            };
            let record = self.read(&run);
            runs.push((run, record));
        }
        runs.sort_by(|a, b| a.0.cmp(&b.0));
        Ok(runs)
    }
}

/// Parse record bytes: the schema version first, so a future version is
/// refused as such rather than as unknown fields.
pub fn parse(bytes: &[u8], run: &str) -> Result<Record> {
    #[derive(Deserialize)]
    struct Versioned {
        v: serde_json::Value,
    }
    let versioned: Versioned = serde_json::from_slice(bytes)
        .map_err(|_| Invalid("sequence record is unparsable; not rewritten"))?;
    if versioned.v != serde_json::json!(VERSION) {
        return Err(Invalid("sequence record schema version is unsupported; not rewritten").into());
    }
    let record: Record = serde_json::from_slice(bytes)
        .map_err(|_| Invalid("sequence record is invalid for schema v1; not rewritten"))?;
    if record.run != run || record.steps.is_empty() {
        return Err(Invalid("sequence record is invalid for schema v1; not rewritten").into());
    }
    Ok(record)
}

#[cfg(test)]
mod tests {
    use super::{civil, timestamp, valid_run_id};

    #[test]
    fn civil_dates_and_run_id_grammar() {
        assert_eq!(timestamp(0), "1970-01-01T00:00:00Z");
        assert_eq!(timestamp(951_782_400), "2000-02-29T00:00:00Z");
        assert_eq!(timestamp(1_793_793_601), "2026-11-04T12:00:01Z");
        assert_eq!(civil(4_107_542_399).0, 2100);
        assert!(valid_run_id("s20261103T140000Z-1a2b3c4d"));
        for bad in [
            "",
            "s20261103T140000Z-1a2b3c4",
            "s20261103T140000Z-1A2B3C4D",
            "s20261103t140000Z-1a2b3c4d",
            "x20261103T140000Z-1a2b3c4d",
            "s2026110xT140000Z-1a2b3c4d",
            "s20261103T140000Z_1a2b3c4d",
            "../../../etc/passwd-aaaaa",
        ] {
            assert!(!valid_run_id(bad), "{bad}");
        }
    }
}
