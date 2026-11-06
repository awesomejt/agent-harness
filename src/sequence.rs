//! Ordered prompt sequences (D044): a deterministic folder snapshot whose
//! steps each run as a fresh single run through the same route policy,
//! strictly linear and stopping at the first incomplete step. Every step is
//! validated, and its agent and check pinned, before step 1 launches.
//! Each invocation holds the project lock and keeps a durable record, so
//! `show` inspects and `resume` continues a run only by explicit choice.
use crate::config::{Config, Exit, Invalid, Invocation, Resolved};
use crate::state::{Attempt, Reason, Record, RunStatus, Status, StepRecord};
use serde::Deserialize;
use std::ffi::OsString;
use std::path::Path;

pub const MAX_STEPS: usize = 256;
pub const MAX_SNAPSHOT_BYTES: u64 = 16 * 1_048_576;
pub const MAX_NAME_BYTES: usize = 128;

type Result<T> = std::result::Result<T, Invalid>;

/// One snapshot entry. Identity is the file name plus the SHA-256 of its raw
/// bytes; `prompt` is the body after any metadata block.
pub struct Step {
    pub name: String,
    pub number: u32,
    pub sha256: String,
    pub bytes: usize,
    pub agent: Option<String>,
    pub verify: Option<String>,
    pub prompt: String,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Metadata {
    #[serde(default, deserialize_with = "crate::agents::present_text")]
    agent: Option<String>,
    #[serde(default, deserialize_with = "crate::agents::present_text")]
    verify: Option<String>,
}

/// `N-slug.md`: 1–6 ASCII digits, a hyphen, a slug starting alphanumeric.
fn step_number(name: &str) -> Result<u32> {
    const NAME: Invalid = Invalid(
        "prompt folder entries must be regular files named N-slug.md (N 1–6 digits; slug [A-Za-z0-9][A-Za-z0-9._-]*; at most 128 bytes)",
    );
    if name.len() > MAX_NAME_BYTES {
        return Err(NAME);
    }
    let stem = name.strip_suffix(".md").ok_or(NAME)?;
    let (digits, slug) = stem.split_once('-').ok_or(NAME)?;
    let slug_ok = slug
        .as_bytes()
        .first()
        .is_some_and(u8::is_ascii_alphanumeric)
        && slug
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b));
    if !(1..=6).contains(&digits.len()) || !digits.bytes().all(|b| b.is_ascii_digit()) || !slug_ok {
        return Err(NAME);
    }
    digits.parse().map_err(|_| NAME)
}

impl Step {
    /// Parse one step's bytes: optional strict metadata, then a nonempty body.
    pub fn parse(name: &str, text: &str) -> Result<Self> {
        let number = step_number(name)?;
        let (metadata, prompt) = split(text)?;
        let metadata = match metadata {
            None => Metadata {
                agent: None,
                verify: None,
            },
            Some(yaml) => {
                // As for agents (D036): reject tags, then decode the strict
                // struct directly so duplicate keys are refused. Never surface
                // YAML diagnostics, which can quote input.
                let value: serde_yaml_ng::Value = serde_yaml_ng::from_str(yaml)
                    .map_err(|_| Invalid("invalid step metadata: expected agent/verify YAML"))?;
                if crate::agents::has_tag(&value) {
                    return Err(Invalid("step metadata YAML tags are unsupported"));
                }
                serde_yaml_ng::from_str(yaml)
                    .map_err(|_| Invalid("invalid step metadata: expected agent/verify YAML"))?
            }
        };
        if let Some(agent) = &metadata.agent {
            crate::agents::validate_name(agent)?;
        }
        if let Some(check) = &metadata.verify {
            crate::verify::validate_name(check)?;
        }
        if prompt.trim().is_empty() {
            return Err(Invalid("step prompt must not be empty"));
        }
        Ok(Self {
            name: name.to_owned(),
            number,
            sha256: crate::state::sha256(text.as_bytes()),
            bytes: text.len(),
            agent: metadata.agent,
            verify: metadata.verify,
            prompt: prompt.to_owned(),
        })
    }
}

/// Split an optional frontmatter block opened by a first line of exactly
/// `---` and closed by the next `---` line, at most 16 KiB.
fn split(text: &str) -> Result<(Option<&str>, &str)> {
    let mut lines = text.split_inclusive('\n');
    let Some(first) = lines.next() else {
        return Ok((None, text));
    };
    if crate::agents::line(first) != "---" {
        return Ok((None, text));
    }
    let start = first.len();
    let mut end = start;
    for raw in lines {
        if crate::agents::line(raw) == "---" {
            return Ok((Some(&text[start..end]), &text[end + raw.len()..]));
        }
        end += raw.len();
        if end - start > crate::agents::MAX_FRONTMATTER_BYTES {
            return Err(Invalid("step metadata exceeds 16 KiB"));
        }
    }
    Err(Invalid("step metadata is incomplete"))
}

/// Read DIR once, non-recursively, into ordered in-memory steps. Names
/// starting with `.` are ignored; any other entry that is not a regular
/// `N-slug.md` file rejects, so a misnamed step is never skipped silently.
pub fn snapshot(dir: &Path) -> Result<Vec<Step>> {
    if !std::fs::metadata(dir).is_ok_and(|m| m.is_dir()) {
        return Err(Invalid("prompt folder must be a readable directory"));
    }
    let mut steps = Vec::new();
    let mut total = 0u64;
    for entry in std::fs::read_dir(dir).map_err(|_| Invalid("cannot list prompt folder"))? {
        let entry = entry.map_err(|_| Invalid("cannot list prompt folder"))?;
        let name = entry.file_name();
        if name.as_encoded_bytes().first() == Some(&b'.') {
            continue;
        }
        let name = name
            .into_string()
            .map_err(|_| Invalid("step file names must be UTF-8"))?;
        step_number(&name)?;
        // The entry type does not follow symlinks; `read` rechecks the
        // opened file so a swapped entry cannot substitute a stream.
        if !entry.file_type().is_ok_and(|t| t.is_file()) {
            return Err(Invalid(
                "prompt folder entries must be regular files, not symlinks or directories",
            ));
        }
        if steps.len() == MAX_STEPS {
            return Err(Invalid("a sequence holds 1–256 steps"));
        }
        let text = read(&dir.join(&name))?;
        total += text.len() as u64;
        if total > MAX_SNAPSHOT_BYTES {
            return Err(Invalid("prompt folder steps exceed 16 MiB in all"));
        }
        steps.push(Step::parse(&name, &text)?);
    }
    if steps.is_empty() {
        return Err(Invalid(
            "prompt folder has no steps; a sequence holds 1–256 steps",
        ));
    }
    steps.sort_by_key(|step| step.number);
    if steps
        .windows(2)
        .any(|pair| pair[0].number == pair[1].number)
    {
        return Err(Invalid("two steps share a step number"));
    }
    Ok(steps)
}

fn read(path: &Path) -> Result<String> {
    let mut options = std::fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_NOCTTY);
    }
    let file = options
        .open(path)
        .map_err(|_| Invalid("cannot open step file"))?;
    if !file
        .metadata()
        .map_err(|_| Invalid("cannot inspect step file"))?
        .is_file()
    {
        return Err(Invalid("step file must be a regular file"));
    }
    crate::config::bounded(file)
}

/// Resolve every step against one config snapshot before anything launches.
/// Each step re-runs the full single-run resolution, so route/agent rules and
/// precedence are identical; metadata cannot widen the invocation.
pub fn resolve(
    invocation: &Invocation,
    config: &Config,
    steps: &[Step],
    key_lookup: impl Fn(&str) -> Option<OsString>,
) -> std::result::Result<Vec<Resolved>, (usize, Invalid)> {
    steps
        .iter()
        .enumerate()
        .map(|(index, step)| {
            invocation
                .step(&step.prompt, step.agent.as_deref(), step.verify.as_deref())
                .and_then(|step| step.resolve(config.clone(), &key_lookup, std::io::empty()))
                .map_err(|error| (index, error))
        })
        .collect()
}

fn reject(message: impl std::fmt::Display) -> Exit {
    use std::io::Write;
    let _ = writeln!(std::io::stderr().lock(), "ah: {message}; use --help");
    Exit::Invalid
}

/// Sequence-level lines on stderr, written only between steps; each step's own
/// diagnostics go through `Progress`. A dedicated thread writes, and the wait is
/// bounded: an unread stderr, or a previous step's writer still holding the
/// stderr lock, must not stall the signal watcher or process exit.
fn note(message: impl std::fmt::Display) {
    use std::io::Write;
    let line = format!("ah: sequence {message}\n");
    let (done, written) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let _ = std::io::stderr().lock().write_all(line.as_bytes());
        let _ = done.send(());
    });
    let _ = written.recv_timeout(std::time::Duration::from_secs(1));
}

/// `ah sequence run|resume|show` (D044).
pub fn run(args: Vec<OsString>) -> Exit {
    match args.get(1).and_then(|a| a.to_str()) {
        Some("resume") => resume(args),
        Some("show") => show(args),
        _ => start(args),
    }
}

fn fail(failure: crate::state::Failure) -> Exit {
    if failure.exit == Exit::Invalid {
        reject(failure.reason)
    } else {
        note(format_args!("{}; nothing launched", failure.reason));
        failure.exit
    }
}

/// Resolve every step, naming the failing step; a missing key adds the hint.
/// For launch, also apply the D038/D040 refusals and the record path rules.
fn resolve_all(
    invocation: &Invocation,
    config: &Config,
    steps: &[Step],
    launch: bool,
) -> std::result::Result<Vec<Resolved>, Exit> {
    use std::io::Write;
    let requests = resolve(invocation, config, steps, |name| std::env::var_os(name)).map_err(
        |(index, error)| {
            let exit = reject(format_args!("step {}: {}", steps[index].name, error.0));
            if error.0 == crate::config::MISSING_KEY {
                let _ = writeln!(
                    std::io::stderr().lock(),
                    "ah: set the environment variable named by the selected route api_key_env before retrying"
                );
            }
            exit
        },
    )?;
    for (step, request) in steps.iter().zip(&requests).filter(|_| launch) {
        if let Err(error) = crate::single::workflow_supported(request) {
            return Err(reject(format_args!("step {}: {}", step.name, error.0)));
        }
        // Surfaces non-UTF-8 record paths before any lock or write.
        if let Err(error) = attempt(step, request, 1, Reason::Initial) {
            return Err(reject(format_args!("step {}: {}", step.name, error.0)));
        }
    }
    Ok(requests)
}

fn start(args: Vec<OsString>) -> Exit {
    let Ok(cwd) = std::env::current_dir() else {
        return reject("current directory is unavailable");
    };
    let (invocation, folder) = match Invocation::parse_sequence(args, &cwd) {
        Ok(parsed) => parsed,
        Err(error) => return reject(error.0),
    };
    // D044: the folder is read before any key lookup, config, runtime or network.
    let steps = match snapshot(&folder) {
        Ok(steps) => steps,
        Err(error) => return reject(error.0),
    };
    let config_path = invocation.config_path();
    let config = match Config::open(&config_path) {
        Ok(config) => config,
        Err(error) => return reject(error.0),
    };
    let requests = match resolve_all(&invocation, &config, &steps, !invocation.preview()) {
        Ok(requests) => requests,
        Err(exit) => return exit,
    };
    if invocation.preview() {
        return preview(&steps, &requests, &folder, &config_path);
    }
    let project = requests[0].project.clone();
    let paths = (|| {
        Ok::<_, Invalid>((
            utf8(&project)?,
            utf8(
                &folder
                    .canonicalize()
                    .map_err(|_| Invalid("prompt folder is unavailable"))?,
            )?,
            utf8(
                &config_path
                    .canonicalize()
                    .map_err(|_| Invalid("config path is unavailable"))?,
            )?,
        ))
    })();
    let (project_text, folder_text, config_text) = match paths {
        Ok(paths) => paths,
        Err(error) => return reject(error.0),
    };
    let run = match crate::state::new_run_id() {
        Ok(run) => run,
        Err(failure) => return fail(failure),
    };
    let store = match crate::state::root(|name| std::env::var_os(name))
        .and_then(|root| crate::state::Store::create(root, &project))
    {
        Ok(store) => store,
        Err(failure) => return fail(failure),
    };
    let lock = match store.lock(&project, &run) {
        Ok(lock) => lock,
        Err(failure) => return fail(failure),
    };
    unfinished(&store, &project);
    let now = crate::state::now();
    let record = Record {
        v: crate::state::VERSION,
        run: run.clone(),
        created: now.clone(),
        updated: now,
        project: project_text,
        folder: folder_text,
        config: config_text,
        status: RunStatus::Active,
        steps: steps
            .iter()
            .zip(&requests)
            .map(|(step, request)| pending(step, request))
            .collect(),
    };
    if let Err(failure) = store.create_record(&record) {
        return fail(failure);
    }
    note(format_args!(
        "run {run} recorded at {:?}; inspect with ah sequence show {run}",
        store.record_path(&run)
    ));
    let session = Session::new(store, record, lock);
    execute(&steps, &requests, &session, 0, Reason::Initial)
}

/// A new `run` never resumes implicitly; it lists this project's unfinished
/// runs (under the held lock, an `active` one is interrupted).
fn unfinished(store: &crate::state::Store, project: &Path) {
    let Ok(runs) = store.list::<Record>() else {
        return;
    };
    let unfinished: Vec<_> = runs
        .iter()
        .filter_map(|(_, record)| record.as_ref().ok())
        .filter(|r| Path::new(&r.project) == project && r.status != RunStatus::Completed)
        .collect();
    for record in unfinished.iter().rev().take(10).rev() {
        note(format_args!(
            "unfinished run {} for this project ({}; {}/{} steps complete); this run starts at step 1; continue that one with ah sequence resume {}",
            record.run,
            if record.status == RunStatus::Active {
                "interrupted"
            } else {
                "stopped"
            },
            record.completed(),
            record.steps.len(),
            record.run
        ));
    }
    if unfinished.len() > 10 {
        note(format_args!(
            "{} older unfinished runs not listed; see ah sequence show",
            unfinished.len() - 10
        ));
    }
}

pub(crate) fn utf8(path: &Path) -> std::result::Result<String, Invalid> {
    path.to_str()
        .map(str::to_owned)
        .ok_or(Invalid("workflow records require UTF-8 paths"))
}

pub(crate) fn route(request: &Resolved) -> &'static str {
    match (request.mode, &request.fallback) {
        (crate::config::Mode::LocalOnly, Some(_)) => "local-first",
        (crate::config::Mode::LocalOnly, None) => "local-only",
        _ => "cloud-only",
    }
}

fn pending(step: &Step, request: &Resolved) -> StepRecord {
    StepRecord {
        name: step.name.clone(),
        sha256: step.sha256.clone(),
        agent: request.agent.as_ref().map(|a| a.name().to_owned()),
        check: request.verify.as_ref().map(|c| c.name.clone()),
        status: Status::Pending,
        attempts: Vec::new(),
    }
}

/// A new `active` attempt recording this step's identities under `request`.
fn attempt(
    step: &Step,
    request: &Resolved,
    number: u32,
    reason: Reason,
) -> std::result::Result<Attempt, Invalid> {
    let check = request.verify.as_ref().map(identity).transpose()?;
    Ok(Attempt {
        number,
        reason,
        status: Status::Active,
        started: crate::state::now(),
        ended: None,
        input_sha256: step.sha256.clone(),
        agent_sha256: request.agent.as_ref().map(|a| a.sha256().to_owned()),
        check,
        route: route(request).to_owned(),
        model: request.runtime_model(),
        fallback: request.fallback.as_ref().map(|f| f.runtime_model()),
        permissions: permissions(request).to_owned(),
        timeout_secs: request.timeout_secs,
        agent_outcome: None,
        exit: None,
        verification: None,
        backends: Vec::new(),
    })
}

/// The pinned check: program path as found and the SHA-256 of its argument
/// array, never the arguments themselves.
pub(crate) fn identity(
    check: &crate::verify::Check,
) -> std::result::Result<crate::state::CheckIdentity, Invalid> {
    Ok(crate::state::CheckIdentity {
        name: check.name.clone(),
        program: utf8(&check.program)?,
        argv_sha256: crate::state::sha256(
            serde_json::to_string(&check.args)
                .unwrap_or_default()
                .as_bytes(),
        ),
    })
}

/// The recorded permission policy name.
pub(crate) fn permissions(request: &Resolved) -> &'static str {
    match request.permissions {
        crate::config::Permissions::Deny => "deny",
        crate::config::Permissions::Trusted => "trusted",
    }
}

/// Identity fields that differ from the step's previous attempt.
fn changes(previous: &Attempt, next: &Attempt) -> Vec<&'static str> {
    let mut changed = Vec::new();
    for (name, differs) in [
        ("input sha256", previous.input_sha256 != next.input_sha256),
        (
            "agent definition",
            previous.agent_sha256 != next.agent_sha256,
        ),
        (
            "check name",
            previous.check.as_ref().map(|c| &c.name) != next.check.as_ref().map(|c| &c.name),
        ),
        (
            "check program",
            previous.check.as_ref().map(|c| &c.program) != next.check.as_ref().map(|c| &c.program),
        ),
        (
            "check argv sha256",
            previous.check.as_ref().map(|c| &c.argv_sha256)
                != next.check.as_ref().map(|c| &c.argv_sha256),
        ),
        ("route", previous.route != next.route),
        ("model", previous.model != next.model),
        ("fallback", previous.fallback != next.fallback),
        ("permissions", previous.permissions != next.permissions),
        ("timeout", previous.timeout_secs != next.timeout_secs),
    ] {
        if differs {
            changed.push(name);
        }
    }
    changed
}

/// Fill a finished attempt from the step's run summary.
fn conclude(attempt: &mut Attempt, exit: Exit, progress: &crate::progress::Progress) -> bool {
    use serde_json::{Value, json};
    let (backends, verification) = progress.snapshot();
    let backends: std::result::Result<Vec<_>, _> = backends
        .iter()
        .map(|b| {
            serde_json::from_value(json!({
                "attempt": b["attempt"], "launched": b["launched"],
                "prompt_submitted": b["prompt_submitted"], "backend_stop": b["backend_stop"],
                "cleanup_confirmed": b["cleanup_confirmed"], "grants": b["grants"],
                "tool_events": b["tool_events"],
            }))
        })
        .collect();
    let verification: std::result::Result<Option<crate::state::Verification>, _> = verification
        .map(|v| serde_json::from_value(Value::Object(v)))
        .transpose();
    let (Ok(backends), Ok(mut verification)) = (backends, verification) else {
        return false;
    };
    let accept = attempt.reason == Reason::Accept;
    if accept {
        // No agent turn ran; the check was the operator's acceptance test.
        if let Some(v) = &mut verification {
            v.agent_outcome = None;
        }
        attempt.agent_outcome = None;
    } else {
        attempt.agent_outcome = Some(
            verification
                .as_ref()
                .and_then(|v| v.agent_outcome.clone())
                .unwrap_or_else(|| crate::progress::outcome(exit).to_owned()),
        );
    }
    attempt.backends = backends;
    attempt.verification = verification;
    attempt.exit = Some(exit as u8);
    attempt.ended = Some(crate::state::now());
    attempt.status = match exit {
        Exit::Success if accept => Status::Accepted,
        exit => Status::of(exit),
    };
    true
}

/// The durable record of the running invocation and the lock it holds.
struct Session {
    store: crate::state::Store,
    record: std::cell::RefCell<Record>,
    launched: std::cell::Cell<bool>,
    _lock: crate::state::Lock,
}

impl Session {
    fn new(store: crate::state::Store, record: Record, lock: crate::state::Lock) -> Self {
        Self {
            store,
            record: std::cell::RefCell::new(record),
            launched: std::cell::Cell::new(false),
            _lock: lock,
        }
    }

    /// Write a changed copy; memory follows only a durable write.
    fn commit(&self, change: impl FnOnce(&mut Record)) -> bool {
        let mut next = self.record.borrow().clone();
        change(&mut next);
        next.updated = crate::state::now();
        let written = self.store.write(&next).is_ok();
        if written {
            *self.record.borrow_mut() = next;
        }
        written
    }

    /// Mark a new attempt `active` before anything launches (exit 1 if that
    /// write fails), reporting identities changed since the previous attempt.
    fn begin(
        &self,
        index: usize,
        step: &Step,
        request: &Resolved,
        reason: Reason,
        progress: &crate::progress::Progress,
    ) -> std::result::Result<(), Exit> {
        let previous = self.record.borrow().steps[index].attempts.last().cloned();
        let number = previous.as_ref().map_or(1, |a| a.number + 1);
        let Ok(attempt) = attempt(step, request, number, reason) else {
            return Err(Exit::Invalid);
        };
        if let Some(previous) = &previous {
            let changed = changes(previous, &attempt);
            progress.event(format!(
                "sequence step {} attempt {number} ({}) changed since attempt {}: {}",
                step.name,
                match reason {
                    Reason::Initial => "initial",
                    Reason::Resume => "resume",
                    Reason::Retry => "retry",
                    Reason::Accept => "accept",
                },
                previous.number,
                if changed.is_empty() {
                    "nothing".to_owned()
                } else {
                    changed.join(", ")
                }
            ));
        }
        if !self.commit(|record| {
            record.steps[index].attempts.push(attempt);
            record.steps[index].status = Status::Active;
            record.status = RunStatus::Active;
        }) {
            progress.event("cannot write the sequence record before launch; nothing launched");
            return Err(Exit::Failed);
        }
        self.launched.set(true);
        Ok(())
    }

    /// Record the attempt's result before the next step; if that write fails,
    /// the record may not reflect what happened (exit 4).
    fn finish(&self, index: usize, exit: Exit, progress: &crate::progress::Progress) -> Exit {
        let mut concluded = true;
        let written = self.commit(|record| {
            let total = record.steps.len();
            let step = &mut record.steps[index];
            let attempt = step.attempts.last_mut().expect("begun attempt");
            concluded = conclude(attempt, exit, progress);
            step.status = attempt.status;
            record.status = if !step.status.complete() {
                RunStatus::Stopped
            } else if index + 1 == total {
                RunStatus::Completed
            } else {
                RunStatus::Active
            };
        });
        if concluded && written {
            if self.record.borrow().steps[index].status.complete() {
                Exit::Success
            } else {
                exit
            }
        } else {
            progress.event(
                "cannot write the sequence step result; the durable record may not reflect this attempt",
            );
            Exit::Uncertain
        }
    }

    /// An operator `accept` without a check: no agent turn and nothing run;
    /// recorded `accepted`, never labeled verified.
    fn accept_ungated(
        &self,
        index: usize,
        step: &Step,
        request: &Resolved,
        progress: &crate::progress::Progress,
    ) -> Exit {
        let previous = self.record.borrow().steps[index].attempts.last().cloned();
        let number = previous.as_ref().map_or(1, |a| a.number + 1);
        let Ok(mut attempt) = attempt(step, request, number, Reason::Accept) else {
            return Exit::Invalid;
        };
        if let Some(previous) = &previous {
            let changed = changes(previous, &attempt);
            progress.event(format!(
                "sequence step {} attempt {number} (accept) changed since attempt {}: {}",
                step.name,
                previous.number,
                if changed.is_empty() {
                    "nothing".to_owned()
                } else {
                    changed.join(", ")
                }
            ));
        }
        attempt.status = Status::Accepted;
        attempt.exit = Some(0);
        attempt.ended = Some(crate::state::now());
        if self.commit(|record| {
            let total = record.steps.len();
            record.steps[index].attempts.push(attempt);
            record.steps[index].status = Status::Accepted;
            record.status = if index + 1 == total {
                RunStatus::Completed
            } else {
                RunStatus::Active
            };
        }) {
            Exit::Success
        } else {
            note("cannot write the sequence record; nothing launched");
            Exit::Failed
        }
    }

    /// Settle the run status after the loop (a signal between steps leaves it
    /// `active`).
    fn close(&self, exit: Exit) -> Exit {
        if self.record.borrow().status != RunStatus::Active {
            return exit;
        }
        let complete = self
            .record
            .borrow()
            .steps
            .iter()
            .all(|s| s.status.complete());
        if self.commit(|record| {
            record.status = if complete {
                RunStatus::Completed
            } else {
                RunStatus::Stopped
            };
        }) {
            exit
        } else if self.launched.get() {
            note(
                "cannot write the final sequence status; the durable record may not reflect this run",
            );
            Exit::Uncertain
        } else {
            note("cannot write the final sequence status");
            Exit::Failed
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn execute(_: &[Step], _: &[Resolved], _: &Session, _: usize, _: Reason) -> Exit {
    reject("coding runs currently support tested macOS only")
}

/// Run steps from `start` (`requests` covers them); the step at `start` takes
/// `first` as its attempt reason, later steps `initial` in a new run and
/// `resume` otherwise.
#[cfg(target_os = "macos")]
fn execute(
    steps: &[Step],
    requests: &[Resolved],
    session: &Session,
    start: usize,
    first: Reason,
) -> Exit {
    let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    else {
        return Exit::Failed;
    };
    let total = steps.len();
    note(format_args!(
        "{} of {total} steps to run; each a fresh single run; stops at the first step that does not complete",
        total - start
    ));
    runtime.block_on(async {
        // One watcher spans every step, so a signal between steps is seen
        // before the next launch rather than terminating the process.
        let signals = crate::runtime::Signals::watch();
        let cancelled = signals.token();
        let exit = drive(steps, start, &cancelled, |index, progress| {
            let request = &requests[index - start];
            let step = &steps[index];
            let cancelled = cancelled.clone();
            let reason = match first {
                _ if index == start => first,
                Reason::Initial => Reason::Initial,
                _ => Reason::Resume,
            };
            progress.event(format!(
                "sequence step {}/{total} {} sha256={} agent={} check={}",
                index + 1,
                step.name,
                step.sha256,
                request.agent.as_ref().map_or("none", |a| a.name()),
                request.verify.as_ref().map_or("none", |c| c.name.as_str()),
            ));
            async move {
                if reason == Reason::Accept && request.verify.is_none() {
                    progress.event(format!(
                        "sequence step {} accepted by the operator; no agent turn and no check; not labeled verified",
                        step.name
                    ));
                    return session.accept_ungated(index, step, request, &progress);
                }
                if let Err(exit) = session.begin(index, step, request, reason, &progress) {
                    return exit;
                }
                if let Some(check) = &request.verify {
                    progress.verification(crate::verify::pending(check));
                }
                let exit = if reason == Reason::Accept {
                    progress.event(format!(
                        "sequence step {} accept: no agent turn; running its check",
                        step.name
                    ));
                    let check = request.verify.as_ref().expect("gated accept");
                    crate::verify::gate(check, &request.project, Exit::Success, &cancelled, &progress)
                        .await
                } else {
                    crate::single::launch(request, cancelled, &progress).await
                };
                session.finish(index, exit, &progress)
            }
        })
        .await;
        session.close(exit)
    })
}

/// The strictly linear loop (D044) from `start`: each step gets its own run
/// diagnostics; a step that does not complete, or a signal seen before the
/// next launch, stops the sequence with that exit.
#[cfg_attr(not(target_os = "macos"), allow(dead_code))]
async fn drive<F, Fut>(
    steps: &[Step],
    start: usize,
    cancelled: &tokio_util::sync::CancellationToken,
    mut launch: F,
) -> Exit
where
    F: FnMut(usize, crate::progress::Progress) -> Fut,
    Fut: std::future::Future<Output = Exit>,
{
    let total = steps.len();
    for (index, step) in steps.iter().enumerate().skip(start) {
        let position = index + 1;
        if cancelled.is_cancelled() {
            note(format_args!(
                "stopped by signal before step {position}/{total} {}; it and later steps not launched",
                step.name
            ));
            return Exit::Cancelled;
        }
        let progress = crate::progress::Progress::step();
        // The launcher's clone drops with its future, before `finish` drains.
        let exit = launch(index, progress.clone()).await;
        let exit = progress.finish(exit);
        if exit != Exit::Success {
            note(format_args!(
                "stopped at step {position}/{total} {} (outcome {}); {} later steps pending and not launched",
                step.name,
                crate::progress::outcome(exit),
                total - position
            ));
            return exit;
        }
    }
    note(format_args!("completed all {total} steps"));
    Exit::Success
}

/// The caller's explicit choice for a step that may have had effects.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Choice {
    None,
    Retry,
    Accept,
}

/// The D044 resume decision against a fresh folder snapshot: the index of the
/// first step to run and its attempt reason, or `None` when nothing remains.
/// Errors name the step. `record` must already have stale `active` attempts
/// marked `interrupted`.
pub fn plan(
    record: &Record,
    steps: &[Step],
    choice: Choice,
) -> std::result::Result<Option<(usize, Reason)>, (String, Invalid)> {
    let done = record.completed();
    if let Some(stray) = record.steps[done..]
        .iter()
        .skip(1)
        .find(|s| !s.attempts.is_empty())
    {
        return Err((
            stray.name.clone(),
            Invalid("sequence record is inconsistent: attempts after the first incomplete step"),
        ));
    }
    for (index, recorded) in record.steps[..done].iter().enumerate() {
        match steps.get(index) {
            Some(step) if step.name == recorded.name && step.sha256 == recorded.sha256 => {}
            _ => {
                return Err((
                    recorded.name.clone(),
                    Invalid(
                        "a completed step changed, moved or was removed; completed steps must still lead unchanged",
                    ),
                ));
            }
        }
    }
    // An attempted stopping step must remain next, even when the folder now
    // ends at the completed prefix: removing it never settles its effects.
    let stopping = record.steps.get(done).filter(|s| !s.attempts.is_empty());
    if let Some(stopping) = stopping
        && steps
            .get(done)
            .is_none_or(|step| step.name != stopping.name)
    {
        return Err((
            stopping.name.clone(),
            Invalid(
                "the step with recorded attempts must remain the next step; restore it or start a new run",
            ),
        ));
    }
    if steps.len() == done {
        return Ok(None);
    }
    let Some(stopping) = stopping else {
        // Never attempted: run it with no choice needed.
        if choice == Choice::Accept {
            return Err((
                steps[done].name.clone(),
                Invalid(
                    "this step has not been attempted; --accept requires an attempt that may have had effects",
                ),
            ));
        }
        return Ok(Some((
            done,
            match choice {
                Choice::None => Reason::Resume,
                Choice::Retry => Reason::Retry,
                Choice::Accept => unreachable!(),
            },
        )));
    };
    if stopping.attempts.len() >= crate::state::MAX_ATTEMPTS {
        return Err((
            stopping.name.clone(),
            Invalid("the step reached 32 attempts; start a new run"),
        ));
    }
    let last = stopping.attempts.last().expect("attempted");
    if choice == Choice::Accept && !last.may_have_effects() {
        return Err((
            stopping.name.clone(),
            Invalid(
                "its last attempt had no effects; --accept requires an attempt that may have had effects",
            ),
        ));
    }
    let reason = match choice {
        Choice::Retry => Reason::Retry,
        Choice::Accept => Reason::Accept,
        Choice::None if !last.may_have_effects() => Reason::Resume,
        Choice::None => {
            return Err((
                stopping.name.clone(),
                Invalid(
                    "its last attempt may have had effects (prompt submitted, uncertain, interrupted, accepted or gate not passed); inspect the project, then pass --retry or --accept",
                ),
            ));
        }
    };
    Ok(Some((done, reason)))
}

/// Recorded steps after a resume decision: the completed prefix as recorded,
/// then the fresh snapshot, keeping the next step's attempt history.
/// `requests` covers the steps from `start`.
pub fn rebuild(
    record: &Record,
    steps: &[Step],
    requests: &[Resolved],
    start: usize,
) -> Vec<StepRecord> {
    let mut rebuilt = record.steps[..start].to_vec();
    for ((index, step), request) in steps.iter().enumerate().skip(start).zip(requests) {
        let mut entry = pending(step, request);
        if let Some(previous) = record
            .steps
            .get(index)
            .filter(|s| index == start && s.name == step.name && !s.attempts.is_empty())
        {
            entry.status = previous.status;
            entry.attempts = previous.attempts.clone();
        }
        rebuilt.push(entry);
    }
    rebuilt
}

fn resume(args: Vec<OsString>) -> Exit {
    let Ok(cwd) = std::env::current_dir() else {
        return reject("current directory is unavailable");
    };
    let mut choice = Choice::None;
    let mut rest = Vec::new();
    for arg in args {
        let picked = match arg.to_str() {
            Some("--retry") => Choice::Retry,
            Some("--accept") => Choice::Accept,
            _ => {
                rest.push(arg);
                continue;
            }
        };
        if choice != Choice::None {
            return reject("pass at most one of --retry or --accept");
        }
        choice = picked;
    }
    let (mut invocation, run) = match Invocation::parse_resume(rest, &cwd) {
        Ok(parsed) => parsed,
        Err(error) => return reject(error.0),
    };
    if !crate::state::valid_run_id(&run) {
        return reject("run ID must be sYYYYMMDDTHHMMSSZ-xxxxxxxx");
    }
    let root = match crate::state::root(|name| std::env::var_os(name)) {
        Ok(root) => root,
        Err(failure) => return fail(failure),
    };
    let original: Record = match crate::state::Store::existing(root.clone()) {
        Ok(Some(store)) => match store.read(&run) {
            Ok(record) => record,
            Err(failure) => return fail(failure),
        },
        Ok(None) => return reject("no sequence record with that run ID"),
        Err(failure) => return fail(failure),
    };
    let project = std::path::PathBuf::from(&original.project);
    let config_path = std::path::PathBuf::from(&original.config);
    // D044: the folder is re-read before any key lookup, config, lock or write.
    let steps = match snapshot(Path::new(&original.folder)) {
        Ok(steps) => steps,
        Err(error) => return reject(error.0),
    };
    // Plan on a copy with stale `active` attempts marked `interrupted`; the
    // lock below confirms no other invocation is running this project, and
    // the re-read confirms the plan's record is still current.
    let mut record = original.clone();
    for step in &mut record.steps {
        for attempt in &mut step.attempts {
            if attempt.status == Status::Active {
                attempt.status = Status::Interrupted;
            }
        }
        if step.status == Status::Active {
            step.status = Status::Interrupted;
        }
    }
    let (start, reason) = match plan(&record, &steps, choice) {
        Ok(Some(plan)) => plan,
        Ok(None) => {
            note(format_args!(
                "run {run} has no remaining steps; nothing launched"
            ));
            return Exit::Success;
        }
        Err((step, error)) => return reject(format_args!("step {step}: {}", error.0)),
    };
    // D044: a step whose last attempt was gated stays gated from the record
    // on any resume (bare, --retry or --accept); check before resolving later
    // steps so subsequent metadata cannot obscure it.
    let recorded_gate = record
        .steps
        .get(start)
        .and_then(|s| s.attempts.last())
        .and_then(|a| a.check.as_ref());
    if let Some(gate) = recorded_gate {
        let action = match reason {
            Reason::Accept => "--accept",
            Reason::Retry => "--retry",
            _ => "resume",
        };
        if invocation.verify() != Some(&gate.name) {
            return reject(format_args!(
                "step {}: its last attempt was gated by check \"{}\"; {action} requires --verify and the same check",
                steps[start].name, gate.name
            ));
        }
    }
    // Only the remaining steps resolve, afresh from the current config and
    // this invocation's route options.
    invocation.rebase(project.clone(), config_path.clone());
    let config = match Config::open(&config_path) {
        Ok(config) => config,
        Err(error) => return reject(error.0),
    };
    let requests = match resolve_all(&invocation, &config, &steps[start..], true) {
        Ok(requests) => requests,
        Err(exit) => return exit,
    };
    if requests[0].project != project {
        return reject("recorded project path no longer resolves to itself; start a new run");
    }
    if let Some(gate) = recorded_gate {
        if requests[0].verify.as_ref().map(|c| &c.name) != Some(&gate.name) {
            let action = match reason {
                Reason::Accept => "--accept",
                Reason::Retry => "--retry",
                _ => "resume",
            };
            return reject(format_args!(
                "step {}: its last attempt was gated by check \"{}\"; {action} requires --verify and the same check",
                steps[start].name, gate.name
            ));
        }
        // The recorded definition of done binds the step (R06-02).
        let changed = match requests[0].verify.as_ref().map(identity) {
            Some(Ok(pinned)) => pinned.changed_from(gate),
            Some(Err(error)) => return reject(error.0),
            None => unreachable!("the gate name matched above"),
        };
        if !changed.is_empty() {
            return reject(format_args!(
                "step {}: check \"{}\" changed since its last attempt ({}); restore the recorded check or start a new run; nothing launched",
                steps[start].name,
                gate.name,
                changed.join(", ")
            ));
        }
    }
    let store = match crate::state::Store::create(root, &project) {
        Ok(store) => store,
        Err(failure) => return fail(failure),
    };
    let lock = match store.lock(&project, &run) {
        Ok(lock) => lock,
        Err(failure) => return fail(failure),
    };
    match store.read::<Record>(&run) {
        Ok(current) if current == original => {}
        Ok(_) => return reject("sequence record changed while resuming; nothing launched"),
        Err(failure) => return fail(failure),
    }
    note(format_args!(
        "resuming run {run} at step {}/{} {} ({}); folder re-read: {} steps",
        start + 1,
        steps.len(),
        steps[start].name,
        match reason {
            Reason::Accept => "accept",
            Reason::Retry => "retry",
            _ => "resume",
        },
        steps.len()
    ));
    record.steps = rebuild(&record, &steps, &requests, start);
    record.status = RunStatus::Active;
    record.updated = crate::state::now();
    if let Err(failure) = store.write(&record) {
        return fail(failure);
    }
    let session = Session::new(store, record, lock);
    execute(&steps, &requests, &session, start, reason)
}

/// Read-only inspection without a model, lock or write. `show RUN_ID` details
/// one run; `show [--project PATH]` lists the project's runs.
fn show(args: Vec<OsString>) -> Exit {
    use std::io::Write;
    let Ok(cwd) = std::env::current_dir() else {
        return reject("current directory is unavailable");
    };
    let mut run = None;
    let mut project = None;
    let mut args = args.into_iter().skip(2);
    while let Some(arg) = args.next() {
        let Some(arg) = arg.to_str() else {
            return reject("arguments must be UTF-8");
        };
        match arg {
            "--project" if project.is_none() => match args.next() {
                Some(value) if !value.is_empty() => project = Some(cwd.join(value)),
                _ => return reject("missing option value"),
            },
            "--output" => {
                return reject(
                    "--output jsonl is unsupported for sequence commands; use human output",
                );
            }
            _ if arg.starts_with('-') => return reject("unsupported option for sequence show"),
            _ if run.is_none() => run = Some(arg.to_owned()),
            _ => return reject("sequence show takes at most one run ID"),
        }
    }
    if run.is_some() && project.is_some() {
        return reject("sequence show RUN_ID takes no --project");
    }
    if run
        .as_deref()
        .is_some_and(|r| !crate::state::valid_run_id(r))
    {
        return reject("run ID must be sYYYYMMDDTHHMMSSZ-xxxxxxxx");
    }
    let store = match crate::state::root(|name| std::env::var_os(name))
        .and_then(crate::state::Store::existing)
    {
        Ok(store) => store,
        Err(failure) => return fail(failure),
    };
    let report = match run {
        Some(run) => {
            let Some(store) = store else {
                return reject("no sequence record with that run ID");
            };
            match store.read(&run) {
                Ok(record) => detail(&store, &record),
                Err(failure) => return fail(failure),
            }
        }
        None => {
            let Ok(project) = project.unwrap_or(cwd).canonicalize() else {
                return reject("project path is unavailable");
            };
            match &store {
                None => "no sequence runs recorded for this project\n".to_owned(),
                Some(store) => match store.list() {
                    Ok(runs) => listing(store, &project, &runs),
                    Err(failure) => return fail(failure),
                },
            }
        }
    };
    if std::io::stdout()
        .lock()
        .write_all(report.as_bytes())
        .is_ok()
    {
        Exit::Success
    } else {
        Exit::Failed
    }
}

/// Run status as observed now: `active` only while its own holder has the lock.
fn observed(store: &crate::state::Store, record: &Record) -> &'static str {
    match record.status {
        RunStatus::Active if store.holds(Path::new(&record.project), &record.run) => "active",
        RunStatus::Active => "interrupted",
        RunStatus::Stopped => "stopped",
        RunStatus::Completed => "completed",
    }
}

fn listing(
    store: &crate::state::Store,
    project: &Path,
    runs: &[(String, std::result::Result<Record, crate::state::Failure>)],
) -> String {
    use std::fmt::Write as _;
    let mut report = String::new();
    for (run, record) in runs {
        match record {
            Ok(record) if Path::new(&record.project) == project => {
                let _ = writeln!(
                    report,
                    "{run} {}; {}/{} steps complete; created {}; updated {}",
                    observed(store, record),
                    record.completed(),
                    record.steps.len(),
                    record.created,
                    record.updated
                );
            }
            Ok(_) => {}
            Err(failure) => {
                let _ = writeln!(
                    report,
                    "{run} unreadable (project unknown): {}",
                    failure.reason
                );
            }
        }
    }
    if report.is_empty() {
        report.push_str("no sequence runs recorded for this project\n");
    }
    report
}

fn detail(store: &crate::state::Store, record: &Record) -> String {
    use std::fmt::Write as _;
    let status = observed(store, record);
    let live = status == "active";
    let mut report = format!(
        "run {}: {status}; {}/{} steps complete; created {}; updated {}\nproject: {:?}\nfolder: {:?}\nconfig: {:?}\n",
        record.run,
        record.completed(),
        record.steps.len(),
        record.created,
        record.updated,
        record.project,
        record.folder,
        record.config,
    );
    let shown = |status: Status| match status {
        Status::Active if !live => "interrupted",
        status => status.name(),
    };
    for (index, step) in record.steps.iter().enumerate() {
        let _ = writeln!(
            report,
            "step {} {}: {}; sha256 {}; agent {}; check {}",
            index + 1,
            step.name,
            shown(step.status),
            step.sha256,
            step.agent.as_deref().unwrap_or("none"),
            step.check.as_deref().unwrap_or("none"),
        );
        for attempt in &step.attempts {
            let verification = attempt
                .verification
                .as_ref()
                .map_or("none".to_owned(), |v| {
                    format!(
                        "{} {}{}",
                        v.check,
                        v.status,
                        v.exit_code
                            .map(|c| format!(" (exit {c})"))
                            .unwrap_or_default()
                    )
                });
            let _ = writeln!(
                report,
                "  attempt {} {}: {}; exit {}; agent outcome {}; verification {verification}; prompt submitted {}; route {}; model {}; fallback {}; permissions {}; input sha256 {}; started {}; ended {}",
                attempt.number,
                match attempt.reason {
                    Reason::Initial => "initial",
                    Reason::Resume => "resume",
                    Reason::Retry => "retry",
                    Reason::Accept => "accept",
                },
                shown(attempt.status),
                attempt.exit.map_or("none".to_owned(), |e| e.to_string()),
                attempt.agent_outcome.as_deref().unwrap_or("none"),
                if attempt.backends.iter().any(|b| b.prompt_submitted) {
                    "yes"
                } else if matches!(attempt.status, Status::Active | Status::Interrupted) {
                    // Its result was never written; a stored `interrupted` is
                    // as uncertain as a stale `active` (P5.4).
                    "unknown"
                } else {
                    "no"
                },
                attempt.route,
                attempt.model,
                attempt.fallback.as_deref().unwrap_or("none"),
                attempt.permissions,
                attempt.input_sha256,
                attempt.started,
                attempt.ended.as_deref().unwrap_or("none"),
            );
        }
    }
    let next = record.steps.iter().find(|s| !s.status.complete());
    let _ = match next {
        None => writeln!(report, "next: complete; nothing to resume"),
        Some(_) if live => writeln!(report, "next: running"),
        Some(step)
            if step
                .attempts
                .last()
                .is_some_and(|a| a.status == Status::Active || a.may_have_effects()) =>
        {
            writeln!(
                report,
                "next: step {} may have had effects; inspect the project, then ah sequence resume {} --retry or --accept",
                step.name, record.run
            )
        }
        Some(_) => writeln!(report, "next: ah sequence resume {}", record.run),
    };
    report
}

/// D044 preview: snapshot, metadata, agents and pinned checks, one line per
/// step. Reads no state, takes no lock, launches nothing and writes nothing.
fn preview(steps: &[Step], requests: &[Resolved], folder: &Path, config: &Path) -> Exit {
    use std::fmt::Write as _;
    use std::io::Write;
    let first = &requests[0];
    let mut report = format!(
        "ah {} sequence preview: {} steps; nothing launched; execution readiness unverified\n\
         project: {:?}\nfolder: {:?}\nconfig: {:?}\n\
         policy: strictly linear; each step a fresh single run; stops at the first step that does not complete\n\
         timeout: {} seconds per step attempt; no whole-sequence deadline\n",
        env!("CARGO_PKG_VERSION"),
        steps.len(),
        first.project,
        folder,
        config,
        first.timeout_secs,
    );
    for (step, request) in steps.iter().zip(requests) {
        let route = route(request);
        let changes = match crate::single::prepare_plan(request) {
            Ok(Some(plan)) if !plan.preview_changes().is_empty() => {
                plan.preview_changes().join("; ")
            }
            Ok(_) => "none".to_owned(),
            Err(error) => format!("refused: {}", error.0),
        };
        let refusal = match crate::single::workflow_supported(request) {
            Ok(()) => String::new(),
            Err(error) => format!("; execution refused: {}", error.0),
        };
        // Names and check names follow strict grammars, so they print safely;
        // prompt text and check arguments are omitted.
        let _ = writeln!(
            report,
            "step {} {}: sha256 {}; {} bytes; agent {}; route {route}; model {}; check {}; planned changes: {changes}{refusal}",
            step.number,
            step.name,
            step.sha256,
            step.bytes,
            request
                .agent
                .as_ref()
                .map_or("none".to_owned(), |a| format!("\"{}\"", a.name())),
            request.runtime_model(),
            request
                .verify
                .as_ref()
                .map_or("none".to_owned(), |c| format!(
                    "\"{}\" (program {:?} pinned)",
                    c.name, c.program
                )),
        );
    }
    if std::io::stdout()
        .lock()
        .write_all(report.as_bytes())
        .is_ok()
    {
        Exit::Success
    } else {
        Exit::Failed
    }
}

#[cfg(test)]
mod tests {
    use super::{Exit, Step, drive};
    use std::cell::RefCell;

    fn steps(count: usize) -> Vec<Step> {
        (1..=count)
            .map(|n| Step::parse(&format!("{n}-step.md"), "Do it.\n").unwrap())
            .collect()
    }

    fn block_on<T>(future: impl std::future::Future<Output = T>) -> T {
        tokio::runtime::Builder::new_current_thread()
            .build()
            .unwrap()
            .block_on(future)
    }

    #[test]
    fn every_step_runs_in_order_and_a_failure_stops_later_steps() {
        let token = tokio_util::sync::CancellationToken::new();
        let ran = RefCell::new(Vec::new());
        let exit = block_on(drive(&steps(3), 0, &token, |index, _| {
            ran.borrow_mut().push(index);
            async { Exit::Success }
        }));
        assert_eq!((exit, ran.take()), (Exit::Success, vec![0, 1, 2]));
        for stop in [
            Exit::Failed,
            Exit::Invalid,
            Exit::Cancelled,
            Exit::Uncertain,
        ] {
            let exit = block_on(drive(&steps(3), 0, &token, |index, _| {
                ran.borrow_mut().push(index);
                async move { if index == 1 { stop } else { Exit::Success } }
            }));
            assert_eq!((exit, ran.take()), (stop, vec![0, 1]));
        }
    }

    #[test]
    fn a_signal_between_steps_stops_before_the_next_launch() {
        let token = tokio_util::sync::CancellationToken::new();
        let ran = RefCell::new(Vec::new());
        // Step 1 completes, then the signal arrives before step 2 launches.
        let exit = block_on(drive(&steps(3), 0, &token, |index, _| {
            ran.borrow_mut().push(index);
            token.cancel();
            async { Exit::Success }
        }));
        assert_eq!((exit, ran.take()), (Exit::Cancelled, vec![0]));
        // Already signalled: nothing launches.
        let exit = block_on(drive(&steps(2), 0, &token, |index, _| {
            ran.borrow_mut().push(index);
            async { Exit::Success }
        }));
        assert_eq!((exit, ran.take()), (Exit::Cancelled, vec![]));
    }
}
