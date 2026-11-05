//! Bounded Ralph loops (D045): an outer coordinator over the single-run path.
//! Every iteration is a fresh single run whose prompt is a fixed harness
//! header followed by the task file's in-memory snapshot; nothing from an
//! earlier iteration's transcript, session or grants is passed on. Task
//! progress lives in project files the harness never reads. Each invocation
//! holds the project lock shared with sequences and keeps a durable record.
//! The run stops at the first iteration that does not succeed, at a signal
//! between iterations, or exhausted at either bound.
use crate::config::{Bounds, Config, Exit, Invalid, Invocation, Resolved};
use crate::state::{
    InvocationReason, InvocationRecord, Iteration, IterationReason, RalphRecord, RalphStatus,
    Status,
};
use std::ffi::OsString;
use std::path::Path;
use std::time::Duration;

/// The last non-empty response line that claims completion.
pub const MARKER: &str = "AH-RALPH-COMPLETE";

/// Whether a final response claims completion: its last non-empty line, with
/// trailing ASCII whitespace removed, is exactly the marker. The marker
/// anywhere else is no claim.
pub fn claims(text: &str) -> bool {
    let space = |c: char| c.is_ascii_whitespace();
    text.trim_end_matches(space)
        .rsplit('\n')
        .next()
        .is_some_and(|line| line.trim_end_matches(space) == MARKER)
}

/// The previous iteration as the header reports it, from the harness's own
/// record only.
pub struct Previous<'a> {
    pub outcome: Option<&'a str>,
    pub claim: Option<bool>,
    pub check: Option<&'a str>,
}

/// Recorded values pass through to the header only when they are known
/// enumerated names; anything else reads `unknown`.
fn known(value: Option<&str>, names: &[&'static str], absent: &'static str) -> &'static str {
    match value {
        None => absent,
        Some(value) => names
            .iter()
            .find(|name| **name == value)
            .copied()
            .unwrap_or("unknown"),
    }
}

/// The fixed harness header sent before the task file. It carries only the
/// iteration number and bound, the previous iteration's enumerated outcome,
/// claim and check status, the check name and the completion instruction:
/// never response text, check output, file content or paths.
pub fn header(iteration: u32, bound: u32, previous: Option<Previous>, check: &str) -> String {
    let previous = match previous {
        None => "none (first iteration of this run)".to_owned(),
        Some(p) => format!(
            "agent outcome {}; completion claimed: {}; check status: {}",
            known(
                p.outcome,
                &[
                    "succeeded",
                    "failed",
                    "rejected",
                    "cancelled",
                    "uncertain",
                    "interrupted"
                ],
                "none"
            ),
            match p.claim {
                Some(true) => "yes",
                Some(false) => "no",
                None => "not inspected",
            },
            known(
                p.check,
                &["passed", "failed", "timed_out", "error", "cancelled"],
                "not run"
            ),
        ),
    };
    format!(
        "[agent-harness Ralph loop]\n\
         Iteration: {iteration} of at most {bound}.\n\
         Previous iteration: {previous}.\n\
         Completion check: {check}.\n\
         This iteration starts with fresh context; nothing from earlier iterations is carried over except the project files. \
         Keep task progress in the project files the task below names: read them before you start and update them before you finish.\n\
         When the whole task is complete, end your response with a final line containing exactly {MARKER}. \
         The harness then runs the completion check; only a passing check completes the loop.\n\
         \n\
         --- Task ---\n\
         \n"
    )
}

/// Which bound ended a run.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Bound {
    Iterations,
    Time,
}

/// The decision before each launch.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Next {
    /// Launch with this agent deadline in seconds.
    Launch(u64),
    Exhausted(Bound),
    Cancelled,
}

/// Before each launch (D045): a signal stops first; then the run's iteration
/// bound; then the invocation's remaining wall time, which also caps the
/// iteration's agent deadline. Less than a whole second left is exhausted.
pub fn next(
    counted: u32,
    bound: u32,
    remaining: Duration,
    timeout_secs: u64,
    cancelled: bool,
) -> Next {
    if cancelled {
        Next::Cancelled
    } else if counted >= bound {
        Next::Exhausted(Bound::Iterations)
    } else if remaining.as_secs() == 0 {
        Next::Exhausted(Bound::Time)
    } else {
        Next::Launch(timeout_secs.min(remaining.as_secs()))
    }
}

/// FILE under the single-run prompt rules: a regular UTF-8 file of at most
/// 1 MiB that is not blank. It has no metadata block; every byte is task text.
pub fn read_prompt(path: &Path) -> Result<String, Invalid> {
    let text = crate::config::bounded(crate::config::open_regular_file(path)?)?;
    if text.trim().is_empty() {
        return Err(Invalid("prompt file must not be empty"));
    }
    Ok(text)
}

fn reject(message: impl std::fmt::Display) -> Exit {
    use std::io::Write;
    let _ = writeln!(std::io::stderr().lock(), "ah: {message}; use --help");
    Exit::Invalid
}

/// Loop-level lines on stderr, written only between iterations, with the same
/// bounded wait as sequence notes.
fn note(message: impl std::fmt::Display) {
    use std::io::Write;
    let line = format!("ah: ralph {message}\n");
    let (done, written) = std::sync::mpsc::channel();
    std::thread::spawn(move || {
        let _ = std::io::stderr().lock().write_all(line.as_bytes());
        let _ = done.send(());
    });
    let _ = written.recv_timeout(Duration::from_secs(1));
}

fn fail(failure: crate::state::Failure) -> Exit {
    if failure.exit == Exit::Invalid {
        reject(failure.reason)
    } else {
        note(format_args!("{}; nothing launched", failure.reason));
        failure.exit
    }
}

/// `ah ralph run|show` (D045). `resume` is refused until it is implemented.
pub fn run(args: Vec<OsString>) -> Exit {
    match args.get(1).and_then(|a| a.to_str()) {
        Some("show") => show(args),
        Some("resume") => reject("ralph resume is not supported by this build; start a new run"),
        _ => start(args),
    }
}

/// The task snapshot and its pinned single-run request for one invocation.
struct Task {
    snapshot: String,
    sha256: String,
    request: Resolved,
    check: crate::verify::Check,
    bounds: Bounds,
    timeout_secs: u64,
}

fn start(args: Vec<OsString>) -> Exit {
    use std::io::Write;
    let Ok(cwd) = std::env::current_dir() else {
        return reject("current directory is unavailable");
    };
    let (invocation, file, bounds) = match Invocation::parse_ralph(args, &cwd) {
        Ok(parsed) => parsed,
        Err(error) => return reject(error.0),
    };
    // D045: FILE is read once, before any key lookup, config, runtime,
    // network check, lock or state write.
    let snapshot = match read_prompt(&file) {
        Ok(text) => text,
        Err(error) => return reject(error.0),
    };
    let config_path = invocation.config_path();
    let config = match Config::open(&config_path) {
        Ok(config) => config,
        Err(error) => return reject(error.0),
    };
    // Agent, model, route, permissions and the check resolve and pin once
    // for the whole invocation, as for a sequence step.
    let resolved = invocation
        .step(&snapshot, None, None)
        .and_then(|step| step.resolve(config, |name| std::env::var_os(name), std::io::empty()));
    let mut request = match resolved {
        Ok(request) => request,
        Err(error) => {
            let exit = reject(error.0);
            if error.0 == crate::config::MISSING_KEY {
                let _ = writeln!(
                    std::io::stderr().lock(),
                    "ah: set the environment variable named by the selected route api_key_env before retrying"
                );
            }
            return exit;
        }
    };
    // The check runs only after a completion claim, never as each
    // iteration's single-run gate.
    let check = request.verify.take().expect("ralph run requires --verify");
    let task = Task {
        sha256: crate::state::sha256(snapshot.as_bytes()),
        snapshot,
        timeout_secs: request.timeout_secs,
        request,
        check,
        bounds,
    };
    if invocation.preview() {
        return preview(&task, &file, &config_path);
    }
    if let Err(error) = crate::single::supported(&task.request) {
        return reject(error.0);
    }
    let project = task.request.project.clone();
    let paths = (|| {
        Ok::<_, Invalid>((
            crate::sequence::utf8(&project)?,
            crate::sequence::utf8(
                &file
                    .canonicalize()
                    .map_err(|_| Invalid("prompt file is unavailable"))?,
            )?,
            crate::sequence::utf8(
                &config_path
                    .canonicalize()
                    .map_err(|_| Invalid("config path is unavailable"))?,
            )?,
            crate::sequence::identity(&task.check)?,
        ))
    })();
    let (project_text, prompt_text, config_text, _) = match paths {
        Ok(paths) => paths,
        Err(error) => return reject(error.0),
    };
    let kind = crate::state::Kind::Ralph;
    let run = match crate::state::new_id(kind) {
        Ok(run) => run,
        Err(failure) => return fail(failure),
    };
    let store = match crate::state::root(|name| std::env::var_os(name))
        .and_then(|root| crate::state::Store::create_for(kind, root, &project))
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
    let record = RalphRecord {
        v: crate::state::VERSION,
        run: run.clone(),
        created: now.clone(),
        updated: now.clone(),
        project: project_text,
        prompt: prompt_text,
        config: config_text,
        status: RalphStatus::Active,
        max_iterations: bounds.max_iterations,
        invocations: vec![InvocationRecord {
            started: now,
            reason: InvocationReason::Run,
            max_runtime_secs: bounds.max_runtime_secs,
        }],
        iterations: Vec::new(),
    };
    if let Err(failure) = store.create_record(&record) {
        return fail(failure);
    }
    note(format_args!(
        "run {run} recorded at {:?}; inspect with ah ralph show {run}",
        store.record_path(&run)
    ));
    let session = Session::new(store, record, lock);
    execute(task, &session)
}

/// A new `run` never resumes implicitly; it lists this project's unfinished
/// Ralph runs (under the held lock, an `active` one is interrupted).
fn unfinished(store: &crate::state::Store, project: &Path) {
    let Ok(runs) = store.list::<RalphRecord>() else {
        return;
    };
    let unfinished: Vec<_> = runs
        .iter()
        .filter_map(|(_, record)| record.as_ref().ok())
        .filter(|r| Path::new(&r.project) == project && r.status != RalphStatus::Completed)
        .collect();
    for record in unfinished.iter().rev().take(10).rev() {
        note(format_args!(
            "unfinished run {} for this project ({}; {} iterations); this run starts at iteration 1",
            record.run,
            match record.status {
                RalphStatus::Active => "interrupted",
                RalphStatus::Exhausted => "exhausted",
                _ => "stopped",
            },
            record.counted(),
        ));
    }
    if unfinished.len() > 10 {
        note(format_args!(
            "{} older unfinished runs not listed; see ah ralph show",
            unfinished.len() - 10
        ));
    }
}

/// A new `active` iteration recording the identities it launches under.
fn iteration(
    task: &Task,
    number: u32,
    reason: IterationReason,
    input: &str,
) -> std::result::Result<Iteration, Invalid> {
    let request = &task.request;
    Ok(Iteration {
        number,
        reason,
        status: Status::Active,
        started: crate::state::now(),
        ended: None,
        prompt_sha256: task.sha256.clone(),
        input_sha256: crate::state::sha256(input.as_bytes()),
        agent_sha256: request.agent.as_ref().map(|a| a.sha256().to_owned()),
        check: Some(crate::sequence::identity(&task.check)?),
        route: crate::sequence::route(request).to_owned(),
        model: request.runtime_model(),
        fallback: request.fallback.as_ref().map(|f| f.runtime_model()),
        permissions: crate::sequence::permissions(request).to_owned(),
        timeout_secs: request.timeout_secs,
        agent_outcome: None,
        exit: None,
        claim: None,
        verification: None,
        backends: Vec::new(),
    })
}

/// Fill a finished iteration from its run summary; `claim` is `None` unless
/// the iteration ended in backend success.
fn conclude(
    iteration: &mut Iteration,
    exit: Exit,
    claim: Option<bool>,
    progress: &crate::progress::Progress,
) -> bool {
    use serde_json::{Value, json};
    let (backends, verification) = progress.snapshot();
    let backends: std::result::Result<Vec<_>, _> = backends
        .iter()
        .map(|b| {
            serde_json::from_value(json!({
                "attempt": b["attempt"], "launched": b["launched"],
                "prompt_submitted": b["prompt_submitted"], "backend_stop": b["backend_stop"],
                "cleanup_confirmed": b["cleanup_confirmed"], "grants": b["grants"],
                "tool_events": b["tool_events"], "usage": b["usage"],
            }))
        })
        .collect();
    let verification: std::result::Result<Option<crate::state::Verification>, _> = verification
        .map(|v| serde_json::from_value(Value::Object(v)))
        .transpose();
    let (Ok(backends), Ok(verification)) = (backends, verification) else {
        return false;
    };
    iteration.agent_outcome = Some(crate::progress::outcome(exit).to_owned());
    iteration.backends = backends;
    iteration.verification = verification;
    iteration.claim = claim;
    iteration.exit = Some(exit as u8);
    iteration.ended = Some(crate::state::now());
    iteration.status = Status::of(exit);
    true
}

/// The durable record of the running invocation and the lock it holds.
struct Session {
    store: crate::state::Store,
    record: std::cell::RefCell<RalphRecord>,
    launched: std::cell::Cell<bool>,
    _lock: crate::state::Lock,
}

impl Session {
    fn new(store: crate::state::Store, record: RalphRecord, lock: crate::state::Lock) -> Self {
        Self {
            store,
            record: std::cell::RefCell::new(record),
            launched: std::cell::Cell::new(false),
            _lock: lock,
        }
    }

    /// Write a changed copy; memory follows only a durable write.
    fn commit(&self, change: impl FnOnce(&mut RalphRecord)) -> bool {
        let mut next = self.record.borrow().clone();
        change(&mut next);
        next.updated = crate::state::now();
        let written = self.store.write(&next).is_ok();
        if written {
            *self.record.borrow_mut() = next;
        }
        written
    }

    /// Mark the iteration `active` before anything launches (exit 1 if that
    /// write fails).
    fn begin(
        &self,
        iteration: Iteration,
        progress: &crate::progress::Progress,
    ) -> std::result::Result<(), Exit> {
        if !self.commit(|record| {
            record.iterations.push(iteration);
            record.status = RalphStatus::Active;
        }) {
            progress.event("cannot write the Ralph record before launch; nothing launched");
            return Err(Exit::Failed);
        }
        self.launched.set(true);
        Ok(())
    }

    /// Record the iteration's result before the next launch; if that write
    /// fails, the record may not reflect what happened (exit 4).
    fn finish(
        &self,
        exit: Exit,
        claim: Option<bool>,
        progress: &crate::progress::Progress,
    ) -> Exit {
        let mut concluded = true;
        let written = self.commit(|record| {
            let iteration = record.iterations.last_mut().expect("begun iteration");
            concluded = conclude(iteration, exit, claim, progress);
            if iteration.status != Status::Succeeded {
                record.status = RalphStatus::Stopped;
            }
        });
        if concluded && written {
            exit
        } else {
            progress.event(
                "cannot write the Ralph iteration result; the durable record may not reflect this iteration",
            );
            Exit::Uncertain
        }
    }

    /// Settle the run status after the loop: `exhausted` at a bound,
    /// otherwise `stopped` (a signal between iterations leaves it `active`
    /// until now).
    fn close(&self, exit: Exit, exhausted: bool) -> Exit {
        if self.record.borrow().status != RalphStatus::Active {
            return exit;
        }
        if self.commit(|record| {
            record.status = if exhausted {
                RalphStatus::Exhausted
            } else {
                RalphStatus::Stopped
            };
        }) {
            exit
        } else if self.launched.get() {
            note(
                "cannot write the final Ralph status; the durable record may not reflect this run",
            );
            Exit::Uncertain
        } else {
            note("cannot write the final Ralph status");
            Exit::Failed
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn execute(_: Task, _: &Session) -> Exit {
    reject("coding runs currently support tested macOS only")
}

/// Run iterations until one does not succeed, a signal arrives between
/// iterations, or a bound is reached. Completion verification is not yet
/// enforced: a claim is recorded and reported to the next iteration only.
#[cfg(target_os = "macos")]
fn execute(mut task: Task, session: &Session) -> Exit {
    let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    else {
        return Exit::Failed;
    };
    let bound = task.bounds.max_iterations;
    let wall = Duration::from_secs(task.bounds.max_runtime_secs);
    note(format_args!(
        "at most {bound} iterations, {} seconds of wall time; each a fresh single run; stops at the first iteration that does not succeed; completion verification is not enforced by this build",
        wall.as_secs()
    ));
    runtime.block_on(async {
        // One watcher spans every iteration, so a signal between iterations
        // is seen before the next launch rather than terminating the process.
        let signals = crate::runtime::Signals::watch();
        let cancelled = signals.token();
        let started = tokio::time::Instant::now();
        loop {
            let (counted, number, previous) = {
                let record = session.record.borrow();
                (
                    record.counted(),
                    record.iterations.len() as u32 + 1,
                    record.iterations.last().cloned(),
                )
            };
            let timeout = match next(
                counted,
                bound,
                wall.saturating_sub(started.elapsed()),
                task.timeout_secs,
                cancelled.is_cancelled(),
            ) {
                Next::Launch(timeout) => timeout,
                Next::Cancelled => {
                    note(format_args!(
                        "stopped by signal before iteration {}; not launched",
                        counted + 1
                    ));
                    return session.close(Exit::Cancelled, false);
                }
                Next::Exhausted(Bound::Iterations) => {
                    note(format_args!(
                        "exhausted: reached {bound} iterations without completion"
                    ));
                    return session.close(Exit::Failed, true);
                }
                Next::Exhausted(Bound::Time) => {
                    note(format_args!(
                        "exhausted: reached the {}-second wall-time bound after {counted} iterations without completion",
                        wall.as_secs()
                    ));
                    return session.close(Exit::Failed, true);
                }
            };
            let header = header(
                counted + 1,
                bound,
                previous.as_ref().map(|p| Previous {
                    outcome: p.agent_outcome.as_deref(),
                    claim: p.claim,
                    check: p.verification.as_ref().map(|v| v.status.as_str()),
                }),
                &task.check.name,
            );
            let input = header + &task.snapshot;
            let reason = if number == 1 {
                IterationReason::Initial
            } else {
                IterationReason::Continue
            };
            task.request.prompt.clone_from(&input);
            task.request.timeout_secs = timeout;
            if let Some(fallback) = task.request.fallback.as_mut() {
                fallback.prompt.clone_from(&input);
                fallback.timeout_secs = timeout;
            }
            let progress = crate::progress::Progress::step();
            let Ok(record) = iteration(&task, number, reason, &input) else {
                return progress.finish(Exit::Invalid);
            };
            progress.event(format!(
                "ralph iteration {}/{bound} ({}) prompt sha256={} input sha256={} timeout={timeout}s agent={} check={}",
                counted + 1,
                reason.name(),
                record.prompt_sha256,
                record.input_sha256,
                task.request.agent.as_ref().map_or("none", |a| a.name()),
                task.check.name,
            ));
            if let Err(exit) = session.begin(record, &progress) {
                return session.close(progress.finish(exit), false);
            }
            let exit = crate::single::launch(&task.request, cancelled.clone(), &progress).await;
            let claim = (exit == Exit::Success).then(|| progress.claimed());
            let exit = session.finish(exit, claim, &progress);
            let exit = progress.finish(exit);
            note(format_args!(
                "iteration {} outcome {}; completion claimed: {}; check: not run",
                counted + 1,
                crate::progress::outcome(exit),
                match claim {
                    Some(true) => "yes (not verified by this build)",
                    Some(false) => "no",
                    None => "not inspected",
                }
            ));
            if exit != Exit::Success {
                note(format_args!(
                    "stopped at iteration {} (outcome {})",
                    counted + 1,
                    crate::progress::outcome(exit)
                ));
                return session.close(exit, false);
            }
        }
    })
}

/// Read-only inspection without a model, lock or write. `show RUN_ID` details
/// one run; `show [--project PATH]` lists the project's runs.
fn show(args: Vec<OsString>) -> Exit {
    use std::io::Write;
    let kind = crate::state::Kind::Ralph;
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
                    "--output jsonl is unsupported for ralph commands; use human output",
                );
            }
            _ if arg.starts_with('-') => return reject("unsupported option for ralph show"),
            _ if run.is_none() => run = Some(arg.to_owned()),
            _ => return reject("ralph show takes at most one run ID"),
        }
    }
    if run.is_some() && project.is_some() {
        return reject("ralph show RUN_ID takes no --project");
    }
    if run.as_deref().is_some_and(|r| !kind.valid(r)) {
        return reject("run ID must be rYYYYMMDDTHHMMSSZ-xxxxxxxx");
    }
    let store = match crate::state::root(|name| std::env::var_os(name))
        .and_then(|root| crate::state::Store::existing_for(kind, root))
    {
        Ok(store) => store,
        Err(failure) => return fail(failure),
    };
    let report = match run {
        Some(run) => {
            let Some(store) = store else {
                return reject("no Ralph record with that run ID");
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
                None => "no Ralph runs recorded for this project\n".to_owned(),
                Some(store) => match store.list::<RalphRecord>() {
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
fn observed(store: &crate::state::Store, record: &RalphRecord) -> &'static str {
    match record.status {
        RalphStatus::Active if store.holds(Path::new(&record.project), &record.run) => "active",
        RalphStatus::Active => "interrupted",
        RalphStatus::Stopped => "stopped",
        RalphStatus::Completed => "completed",
        RalphStatus::Exhausted => "exhausted",
    }
}

fn listing(
    store: &crate::state::Store,
    project: &Path,
    runs: &[(
        String,
        std::result::Result<RalphRecord, crate::state::Failure>,
    )],
) -> String {
    use std::fmt::Write as _;
    let mut report = String::new();
    for (run, record) in runs {
        match record {
            Ok(record) if Path::new(&record.project) == project => {
                let _ = writeln!(
                    report,
                    "{run} {}; {}/{} iterations; created {}; updated {}",
                    observed(store, record),
                    record.counted(),
                    record.max_iterations,
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
        report.push_str("no Ralph runs recorded for this project\n");
    }
    report
}

/// The backend-reported cost total, given only when every backend attempt
/// that submitted a prompt reported a cost in one currency (D045).
pub fn cost(record: &RalphRecord) -> Option<(f64, String)> {
    let mut total = 0.0;
    let mut currency: Option<&str> = None;
    let mut any = false;
    for backend in record
        .iterations
        .iter()
        .flat_map(|i| &i.backends)
        .filter(|b| b.prompt_submitted)
    {
        let cost = backend.usage.session_cost.as_ref()?;
        if currency.is_some_and(|c| c != cost.currency) {
            return None;
        }
        currency = Some(&cost.currency);
        total += cost.amount;
        any = true;
    }
    any.then(|| (total, currency.unwrap_or_default().to_owned()))
}

fn detail(store: &crate::state::Store, record: &RalphRecord) -> String {
    use std::fmt::Write as _;
    let status = observed(store, record);
    let live = status == "active";
    let mut report = format!(
        "run {}: {status}; {}/{} iterations; created {}; updated {}\nproject: {:?}\nprompt: {:?}\nconfig: {:?}\n",
        record.run,
        record.counted(),
        record.max_iterations,
        record.created,
        record.updated,
        record.project,
        record.prompt,
        record.config,
    );
    for (index, invocation) in record.invocations.iter().enumerate() {
        let _ = writeln!(
            report,
            "invocation {} {}: started {}; wall bound {} seconds",
            index + 1,
            match invocation.reason {
                InvocationReason::Run => "run",
                InvocationReason::Resume => "resume",
                InvocationReason::Retry => "retry",
                InvocationReason::Accept => "accept",
            },
            invocation.started,
            invocation.max_runtime_secs,
        );
    }
    for iteration in &record.iterations {
        let status = match iteration.status {
            Status::Active if !live => "interrupted",
            status => status.name(),
        };
        let verification = iteration
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
            "iteration {} {}: {status}; exit {}; agent outcome {}; claim {}; verification {verification}; prompt submitted {}; route {}; model {}; fallback {}; permissions {}; timeout {}s; prompt sha256 {}; input sha256 {}; started {}; ended {}",
            iteration.number,
            iteration.reason.name(),
            iteration.exit.map_or("none".to_owned(), |e| e.to_string()),
            iteration.agent_outcome.as_deref().unwrap_or("none"),
            match iteration.claim {
                Some(true) => "yes",
                Some(false) => "no",
                None => "none",
            },
            if iteration.backends.iter().any(|b| b.prompt_submitted) {
                "yes"
            } else if matches!(iteration.status, Status::Active | Status::Interrupted) {
                // Its result was never written, so submission is unknown.
                "unknown"
            } else {
                "no"
            },
            iteration.route,
            iteration.model,
            iteration.fallback.as_deref().unwrap_or("none"),
            iteration.permissions,
            iteration.timeout_secs,
            iteration.prompt_sha256,
            iteration.input_sha256,
            iteration.started,
            iteration.ended.as_deref().unwrap_or("none"),
        );
    }
    let _ = match cost(record) {
        Some((amount, currency)) => writeln!(
            report,
            "usage: backend-reported cost {amount} {currency} (not billing)"
        ),
        None => writeln!(report, "usage: cost unknown"),
    };
    let _ = match status {
        "completed" => writeln!(report, "next: complete; nothing to resume"),
        "active" => writeln!(report, "next: running"),
        _ => writeln!(
            report,
            "next: not resumable by this build; inspect the project, then start a new run"
        ),
    };
    report
}

/// D045 preview: FILE, agent, route, the pinned check, both bounds and the
/// iteration-1 header. Reads no state, takes no lock, launches nothing and
/// writes nothing.
fn preview(task: &Task, file: &Path, config: &Path) -> Exit {
    use std::io::Write;
    let request = &task.request;
    let changes = match crate::single::prepare_plan(request) {
        Ok(Some(plan)) if !plan.preview_changes().is_empty() => plan.preview_changes().join("; "),
        Ok(_) => "none".to_owned(),
        Err(error) => format!("refused: {}", error.0),
    };
    let refusal = match crate::single::supported(request) {
        Ok(()) => String::new(),
        Err(error) => format!("execution refused: {}\n", error.0),
    };
    // Names and check names follow strict grammars, so they print safely;
    // prompt text and check arguments are omitted.
    let report = format!(
        "ah {} ralph preview: nothing launched; execution readiness unverified\n\
         project: {:?}\nprompt file: {:?}; {} bytes; sha256 {}\nconfig: {:?}\n\
         agent: {}; route {}; model {}; permissions {}\n\
         check: \"{}\" (program {:?} pinned); runs only after a completion claim\n\
         bounds: at most {} iterations per run; {} seconds of wall time per invocation; {} seconds per iteration\n\
         planned changes: {changes}\n{refusal}\
         iteration 1 header:\n{}",
        env!("CARGO_PKG_VERSION"),
        request.project,
        file,
        task.snapshot.len(),
        task.sha256,
        config,
        request
            .agent
            .as_ref()
            .map_or("none".to_owned(), |a| format!("\"{}\"", a.name())),
        crate::sequence::route(request),
        request.runtime_model(),
        crate::sequence::permissions(request),
        task.check.name,
        task.check.program,
        task.bounds.max_iterations,
        task.bounds.max_runtime_secs,
        task.timeout_secs,
        header(1, task.bounds.max_iterations, None, &task.check.name),
    );
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
