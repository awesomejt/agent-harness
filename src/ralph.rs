//! Bounded Ralph loops (D045): an outer coordinator over the single-run path.
//! Every iteration is a fresh single run whose prompt is a fixed harness
//! header followed by the task file's in-memory snapshot; nothing from an
//! earlier iteration's transcript, session or grants is passed on. Task
//! progress lives in project files the harness never reads. Each invocation
//! holds the project lock shared with sequences and keeps a durable record.
//! Completion needs a claim plus a passing pinned check from the same
//! iteration. A rejected claim continues to a bounded repair iteration; any
//! other non-success stops the run, as does a signal between iterations; a
//! bound ends it exhausted. `resume` continues a run only by explicit choice.
use crate::config::{Bounds, Config, Exit, Invalid, Invocation, Resolved};
use crate::sequence::Choice;
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
    crate::progress::last_line(text) == Some(MARKER)
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

/// What a finished iteration means for the run (D045).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum After {
    /// Backend success with no claim, or a claim whose check ended `failed`
    /// or `timed_out` (a rejected claim): the next iteration is the bounded
    /// repair.
    Continue,
    /// A claim whose check passed, or an operator `accept` whose check passed.
    Complete,
    /// Any other result: a non-success agent outcome, a check ending `error`
    /// or `cancelled`, unconfirmed cleanup, or an unfinished iteration.
    Stop,
}

/// Decide from the recorded iteration alone, so a resumed run reads the same
/// decision the loop made.
pub fn after(iteration: &Iteration) -> After {
    let check = iteration.verification.as_ref().map(|v| v.status.as_str());
    match (iteration.reason, iteration.status) {
        (_, Status::Accepted) => return After::Complete,
        (IterationReason::Accept, _) => return After::Stop,
        _ => {}
    }
    if iteration.agent_outcome.as_deref() != Some("succeeded") {
        return After::Stop;
    }
    match (iteration.claim, check, iteration.status) {
        (Some(true), Some("passed"), Status::Succeeded) => After::Complete,
        (Some(true), Some("failed" | "timed_out"), Status::Failed) => After::Continue,
        (Some(false), None, Status::Succeeded) => After::Continue,
        _ => After::Stop,
    }
}

/// Whether bare resume would launch after this last iteration: it never
/// submitted a prompt, or the loop would have continued after it.
fn settled(last: Option<&Iteration>) -> bool {
    last.is_none_or(|last| !last.may_have_effects() || after(last) == After::Continue)
}

/// The D045 resume decision: the first iteration's reason and the run's
/// iteration bound, or `None` for a completed run. `record` must already
/// have a stale `active` iteration marked `interrupted`.
pub fn plan(
    record: &RalphRecord,
    choice: Choice,
    max_iterations: Option<u32>,
) -> std::result::Result<Option<(IterationReason, u32)>, Invalid> {
    if record.status == RalphStatus::Completed {
        return Ok(None);
    }
    let counted = record.counted();
    if max_iterations.is_some_and(|bound| bound <= counted) {
        return Err(Invalid(
            "--max-iterations must be greater than the run's counted iterations",
        ));
    }
    if record.iterations.len() >= crate::state::MAX_ITERATIONS {
        return Err(Invalid(
            "the run reached 100 recorded iterations; start a new run",
        ));
    }
    let bound = max_iterations.unwrap_or(record.max_iterations);
    let last = record.iterations.last();
    let reason = match choice {
        Choice::Accept if last.is_some_and(Iteration::may_have_effects) => {
            // No agent turn, so the iteration bound does not apply.
            return Ok(Some((IterationReason::Accept, bound)));
        }
        Choice::Accept => {
            return Err(Invalid(
                "--accept requires a last iteration that may have had effects",
            ));
        }
        Choice::Retry => IterationReason::Retry,
        Choice::None if settled(last) => IterationReason::Resume,
        Choice::None => {
            return Err(Invalid(
                "its last iteration may have had effects (prompt submitted and not succeeded, uncertain, interrupted, accepted, or a check that stopped the run); inspect the project, then pass --retry or --accept",
            ));
        }
    };
    if counted >= bound {
        return Err(Invalid(
            "the run reached its iteration bound; pass --max-iterations greater than its counted iterations",
        ));
    }
    Ok(Some((reason, bound)))
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

/// `ah ralph run|resume|show` (D045).
pub fn run(args: Vec<OsString>) -> Exit {
    match args.get(1).and_then(|a| a.to_str()) {
        Some("show") => show(args),
        Some("resume") => resume(args),
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

/// Resolve and pin the invocation's request for the snapshot, with the check
/// taken out: it runs only after a completion claim, never as each
/// iteration's single-run gate.
fn pin(
    invocation: &Invocation,
    config: Config,
    snapshot: String,
    bounds: Bounds,
) -> std::result::Result<Task, Exit> {
    use std::io::Write;
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
            return Err(exit);
        }
    };
    let check = request.verify.take().expect("ralph requires --verify");
    Ok(Task {
        sha256: crate::state::sha256(snapshot.as_bytes()),
        snapshot,
        timeout_secs: request.timeout_secs,
        request,
        check,
        bounds,
    })
}

fn start(args: Vec<OsString>) -> Exit {
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
    let task = match pin(&invocation, config, snapshot, bounds) {
        Ok(task) => task,
        Err(exit) => return exit,
    };
    if invocation.preview() {
        return preview(&task, &file, &config_path);
    }
    if let Err(error) = crate::single::workflow_supported(&task.request) {
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
    execute(task, &session, IterationReason::Initial)
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
            "unfinished run {} for this project ({}; {} iterations); this run starts at iteration 1; continue that one with ah ralph resume {}",
            record.run,
            match record.status {
                RalphStatus::Active => "interrupted",
                RalphStatus::Exhausted => "exhausted",
                _ => "stopped",
            },
            record.counted(),
            record.run,
        ));
    }
    if unfinished.len() > 10 {
        note(format_args!(
            "{} older unfinished runs not listed; see ah ralph show",
            unfinished.len() - 10
        ));
    }
}

/// Mark an `active` iteration found without its lock holder `interrupted`;
/// only the last iteration can be one.
fn interrupted(record: &mut RalphRecord) {
    for iteration in &mut record.iterations {
        if iteration.status == Status::Active {
            iteration.status = Status::Interrupted;
        }
    }
}

/// The check name the run's iterations were gated by.
fn recorded_check(record: &RalphRecord) -> Option<&str> {
    record
        .iterations
        .iter()
        .rev()
        .find_map(|i| i.check.as_ref())
        .map(|c| c.name.as_str())
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
    let (mut invocation, run, iterations, runtime) =
        match Invocation::parse_ralph_resume(rest, &cwd) {
            Ok(parsed) => parsed,
            Err(error) => return reject(error.0),
        };
    let kind = crate::state::Kind::Ralph;
    if !kind.valid(&run) {
        return reject("run ID must be rYYYYMMDDTHHMMSSZ-xxxxxxxx");
    }
    let root = match crate::state::root(|name| std::env::var_os(name)) {
        Ok(root) => root,
        Err(failure) => return fail(failure),
    };
    let original: RalphRecord = match crate::state::Store::existing_for(kind, root.clone()) {
        Ok(Some(store)) => match store.read(&run) {
            Ok(record) => record,
            Err(failure) => return fail(failure),
        },
        Ok(None) => return reject("no Ralph record with that run ID"),
        Err(failure) => return fail(failure),
    };
    // A completed run is a no-op that needs neither FILE nor the config.
    if original.status == RalphStatus::Completed {
        note(format_args!(
            "run {run} is already completed; nothing launched"
        ));
        return Exit::Success;
    }
    // A full record refuses every choice; say so before FILE is needed.
    if original.iterations.len() >= crate::state::MAX_ITERATIONS {
        return reject(format_args!(
            "run {run}: the run reached 100 recorded iterations; start a new run"
        ));
    }
    let project = std::path::PathBuf::from(&original.project);
    let config_path = std::path::PathBuf::from(&original.config);
    // D045: FILE is re-read from the recorded path before any key lookup,
    // config, lock or write. A changed prompt is allowed and reported.
    let snapshot = match read_prompt(Path::new(&original.prompt)) {
        Ok(text) => text,
        Err(error) => return reject(format_args!("recorded prompt file: {}", error.0)),
    };
    // Plan on a copy with a stale `active` iteration marked `interrupted`;
    // the lock below confirms no other invocation is running this project,
    // and the re-read confirms the plan's record is still current.
    let mut record = original.clone();
    interrupted(&mut record);
    let counted = record.counted();
    let (reason, bound) = match plan(&record, choice, iterations) {
        Ok(Some(plan)) => plan,
        Ok(None) => {
            note(format_args!(
                "run {run} is already completed; nothing launched"
            ));
            return Exit::Success;
        }
        Err(error) => {
            return reject(format_args!(
                "run {run} ({counted} counted iterations of at most {}): {}",
                record.max_iterations, error.0
            ));
        }
    };
    if let Some(recorded) = recorded_check(&record)
        && invocation.verify() != Some(recorded)
    {
        return reject(format_args!(
            "run {run} was gated by check \"{recorded}\"; resume requires --verify {recorded}"
        ));
    }
    // Route options resolve afresh from the current config and this
    // invocation; the check is re-pinned and must keep its recorded identity.
    invocation.rebase(project.clone(), config_path.clone());
    let config = match Config::open(&config_path) {
        Ok(config) => config,
        Err(error) => return reject(error.0),
    };
    let bounds = Bounds {
        max_iterations: bound,
        max_runtime_secs: runtime,
    };
    let task = match pin(&invocation, config, snapshot, bounds) {
        Ok(task) => task,
        Err(exit) => return exit,
    };
    if task.request.project != project {
        return reject("recorded project path no longer resolves to itself; start a new run");
    }
    let pinned = match crate::single::workflow_supported(&task.request)
        .and_then(|()| crate::sequence::identity(&task.check))
    {
        Ok(pinned) => pinned,
        Err(error) => return reject(error.0),
    };
    // The definition of done binds the run (R06-02): a check whose program
    // or argv changed since it was recorded never completes it.
    if let Some(recorded) = record
        .iterations
        .iter()
        .rev()
        .find_map(|i| i.check.as_ref())
    {
        let changed = pinned.changed_from(recorded);
        if !changed.is_empty() {
            return reject(format_args!(
                "run {run}: check \"{}\" changed since it was recorded ({}); restore the recorded check or start a new run; nothing launched",
                recorded.name,
                changed.join(", ")
            ));
        }
    }
    let store = match crate::state::Store::create_for(kind, root, &project) {
        Ok(store) => store,
        Err(failure) => return fail(failure),
    };
    let lock = match store.lock(&project, &run) {
        Ok(lock) => lock,
        Err(failure) => return fail(failure),
    };
    match store.read::<RalphRecord>(&run) {
        Ok(current) if current == original => {}
        Ok(_) => return reject("Ralph record changed while resuming; nothing launched"),
        Err(failure) => return fail(failure),
    }
    note(format_args!(
        "resuming run {run} ({}) after {counted} counted iterations; at most {bound}; prompt file re-read: {} bytes sha256 {}",
        reason.name(),
        task.snapshot.len(),
        task.sha256,
    ));
    record.invocations.push(InvocationRecord {
        started: crate::state::now(),
        reason: match reason {
            IterationReason::Accept => InvocationReason::Accept,
            IterationReason::Retry => InvocationReason::Retry,
            _ => InvocationReason::Resume,
        },
        max_runtime_secs: runtime,
    });
    record.max_iterations = bound;
    record.status = RalphStatus::Active;
    record.updated = crate::state::now();
    if let Err(failure) = store.write(&record) {
        return fail(failure);
    }
    let session = Session::new(store, record, lock);
    execute(task, &session, reason)
}

/// A new `active` iteration recording the identities it launches under. An
/// `accept` iteration sends nothing; its input hash is that of empty input.
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

/// Identity fields that differ from the previous iteration. The timeout is
/// left out: the wall bound caps it per iteration. An `accept` runs no agent
/// turn, so only its prompt and check identity are compared (R06-05).
fn changes(previous: &Iteration, next: &Iteration) -> Vec<&'static str> {
    let (before, after) = (previous.check.as_ref(), next.check.as_ref());
    let accept = next.reason == IterationReason::Accept;
    [
        (
            "prompt sha256",
            previous.prompt_sha256 != next.prompt_sha256,
        ),
        (
            "agent definition",
            previous.agent_sha256 != next.agent_sha256,
        ),
        (
            "check name",
            before.map(|c| &c.name) != after.map(|c| &c.name),
        ),
        (
            "check program",
            before.map(|c| &c.program) != after.map(|c| &c.program),
        ),
        (
            "check argv sha256",
            before.map(|c| &c.argv_sha256) != after.map(|c| &c.argv_sha256),
        ),
        ("route", previous.route != next.route),
        ("model", previous.model != next.model),
        ("fallback", previous.fallback != next.fallback),
        ("permissions", previous.permissions != next.permissions),
    ]
    .into_iter()
    .filter(|(name, _)| !accept || name.starts_with("prompt") || name.starts_with("check"))
    .filter_map(|(name, differs)| differs.then_some(name))
    .collect()
}

/// Fill a finished iteration from its run summary; `claim` is `None` unless
/// the iteration ended in backend success. The agent outcome is the one the
/// check saw, so a rejected claim keeps `succeeded`; an `accept` has none.
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
    let (Ok(backends), Ok(mut verification)) = (backends, verification) else {
        return false;
    };
    let accept = iteration.reason == IterationReason::Accept;
    if accept {
        if let Some(v) = &mut verification {
            v.agent_outcome = None;
        }
        iteration.agent_outcome = None;
    } else {
        iteration.agent_outcome = Some(
            verification
                .as_ref()
                .and_then(|v| v.agent_outcome.clone())
                .unwrap_or_else(|| crate::progress::outcome(exit).to_owned()),
        );
    }
    iteration.backends = backends;
    iteration.verification = verification;
    iteration.claim = claim;
    iteration.exit = Some(exit as u8);
    iteration.ended = Some(crate::state::now());
    iteration.status = match exit {
        Exit::Success if accept => Status::Accepted,
        exit => Status::of(exit),
    };
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
    /// write fails). The first iteration of a resumed invocation reports the
    /// identities changed since the previous iteration.
    fn begin(
        &self,
        iteration: Iteration,
        progress: &crate::progress::Progress,
    ) -> std::result::Result<(), Exit> {
        let resumed = matches!(
            iteration.reason,
            IterationReason::Resume | IterationReason::Retry | IterationReason::Accept
        );
        // An accept compares with the last iteration; an agent iteration with
        // the last agent iteration, since an accept's route fields describe
        // no agent turn.
        let basis = {
            let record = self.record.borrow();
            let mut earlier = record.iterations.iter().rev();
            if iteration.reason == IterationReason::Accept {
                earlier.next().cloned()
            } else {
                earlier
                    .find(|i| i.reason != IterationReason::Accept)
                    .cloned()
            }
        };
        if let Some(previous) = basis.as_ref().filter(|_| resumed) {
            let changed = changes(previous, &iteration);
            progress.event(format!(
                "ralph iteration {} ({}) changed since iteration {}: {}",
                iteration.number,
                iteration.reason.name(),
                previous.number,
                if changed.is_empty() {
                    "nothing".to_owned()
                } else {
                    changed.join(", ")
                }
            ));
        }
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

    /// Record the iteration's result and what it means for the run before
    /// the next launch; if that write fails, the record may not reflect what
    /// happened (exit 4, stop).
    fn finish(
        &self,
        exit: Exit,
        claim: Option<bool>,
        progress: &crate::progress::Progress,
    ) -> (Exit, After) {
        let mut concluded = true;
        let mut decision = After::Stop;
        let written = self.commit(|record| {
            let iteration = record.iterations.last_mut().expect("begun iteration");
            concluded = conclude(iteration, exit, claim, progress);
            decision = after(iteration);
            record.status = match decision {
                After::Continue => RalphStatus::Active,
                After::Complete => RalphStatus::Completed,
                After::Stop => RalphStatus::Stopped,
            };
        });
        if concluded && written {
            (exit, decision)
        } else {
            progress.event(
                "cannot write the Ralph iteration result; the durable record may not reflect this iteration",
            );
            (Exit::Uncertain, After::Stop)
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
fn execute(_: Task, _: &Session, _: IterationReason) -> Exit {
    reject("coding runs currently support tested macOS only")
}

/// Run iterations from `first` until completion, a stop, a signal between
/// iterations or a bound. Each agent iteration is one single run; only a
/// claim starts the pinned check, under the D043 gate.
#[cfg(target_os = "macos")]
fn execute(mut task: Task, session: &Session, first: IterationReason) -> Exit {
    let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    else {
        return Exit::Failed;
    };
    if first == IterationReason::Accept {
        note("accept: no agent turn; running the pinned check; a pass completes the run");
    } else {
        note(format_args!(
            "at most {} iterations, {} seconds of wall time; each a fresh single run; completes only when a claim's check passes; stops at an iteration that does not succeed",
            task.bounds.max_iterations, task.bounds.max_runtime_secs
        ));
    }
    runtime.block_on(async {
        // One watcher spans every iteration, so a signal between iterations
        // is seen before the next launch rather than terminating the process.
        let signals = crate::runtime::Signals::watch();
        let cancelled = signals.token();
        let token = cancelled.clone();
        drive(
            &mut task,
            session,
            first,
            &cancelled,
            move |task, reason, progress| {
                let cancelled = token.clone();
                Box::pin(async move {
                    let check = &task.check;
                    let project = &task.request.project;
                    if reason == IterationReason::Accept {
                        progress.verification(crate::verify::pending(check));
                        let exit = crate::verify::gate(
                            check,
                            project,
                            Exit::Success,
                            &cancelled,
                            &progress,
                        )
                        .await;
                        return (exit, None);
                    }
                    let exit =
                        crate::single::launch(&task.request, cancelled.clone(), &progress).await;
                    let claim = (exit == Exit::Success)
                        .then(|| progress.final_line().as_deref() == Some(MARKER));
                    if claim != Some(true) {
                        return (exit, claim);
                    }
                    progress.verification(crate::verify::pending(check));
                    let exit =
                        crate::verify::gate(check, project, exit, &cancelled, &progress).await;
                    (exit, claim)
                })
            },
        )
        .await
    })
}

/// The boxed iteration future: the final iteration exit (after any check)
/// and the claim (`None` unless the agent outcome was success).
type Launched<'a> = std::pin::Pin<Box<dyn std::future::Future<Output = (Exit, Option<bool>)> + 'a>>;

/// The D045 loop over the session's record. `launch` runs one iteration of
/// the pinned task (an agent turn and, after a claim, the check; or for
/// `accept` the check alone).
#[cfg_attr(not(target_os = "macos"), allow(dead_code))]
async fn drive<L>(
    task: &mut Task,
    session: &Session,
    first: IterationReason,
    cancelled: &tokio_util::sync::CancellationToken,
    mut launch: L,
) -> Exit
where
    L: for<'a> FnMut(&'a Task, IterationReason, crate::progress::Progress) -> Launched<'a>,
{
    let bound = task.bounds.max_iterations;
    let wall = Duration::from_secs(task.bounds.max_runtime_secs);
    let started = tokio::time::Instant::now();
    let mut reason = first;
    loop {
        let (counted, number, previous, full) = {
            let record = session.record.borrow();
            (
                record.counted(),
                record.iterations.len() as u32 + 1,
                record.iterations.last().cloned(),
                record.iterations.len() >= crate::state::MAX_ITERATIONS,
            )
        };
        let accept = reason == IterationReason::Accept;
        let decision = next(
            counted,
            bound,
            wall.saturating_sub(started.elapsed()),
            task.timeout_secs,
            cancelled.is_cancelled(),
        );
        let timeout = match decision {
            Next::Cancelled => {
                note(format_args!(
                    "stopped by signal before iteration {number}; not launched"
                ));
                return session.close(Exit::Cancelled, false);
            }
            // The record holds at most 100 iterations, agent and accept alike
            // (R06-01); checked before every append.
            _ if full => {
                note(format_args!(
                    "exhausted: the run holds {} recorded iterations, the record limit; start a new run",
                    crate::state::MAX_ITERATIONS
                ));
                return session.close(Exit::Failed, true);
            }
            // An accept runs no agent turn, so neither bound applies.
            _ if accept => task.timeout_secs,
            Next::Launch(timeout) => timeout,
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
        let input = if accept {
            String::new()
        } else {
            header(
                counted + 1,
                bound,
                previous.as_ref().map(|p| Previous {
                    outcome: if p.status == Status::Interrupted {
                        Some("interrupted")
                    } else {
                        p.agent_outcome.as_deref()
                    },
                    claim: p.claim,
                    check: p.verification.as_ref().map(|v| v.status.as_str()),
                }),
                &task.check.name,
            ) + &task.snapshot
        };
        task.request.prompt.clone_from(&input);
        task.request.timeout_secs = timeout;
        if let Some(fallback) = task.request.fallback.as_mut() {
            fallback.prompt.clone_from(&input);
            fallback.timeout_secs = timeout;
        }
        let progress = crate::progress::Progress::step();
        let Ok(record) = iteration(task, number, reason, &input) else {
            return session.close(progress.finish(Exit::Invalid), false);
        };
        if accept {
            progress.event(format!(
                "ralph iteration {number} (accept) by the operator: no agent turn; check={} prompt sha256={}",
                task.check.name, record.prompt_sha256,
            ));
        } else {
            progress.event(format!(
                "ralph iteration {number} ({}); agent iteration {}/{bound}; prompt sha256={} input sha256={} timeout={timeout}s agent={} check={}",
                reason.name(),
                counted + 1,
                record.prompt_sha256,
                record.input_sha256,
                task.request.agent.as_ref().map_or("none", |a| a.name()),
                task.check.name,
            ));
        }
        if let Err(exit) = session.begin(record, &progress) {
            return session.close(progress.finish(exit), false);
        }
        // The launcher's clone drops with its future, before `finish` drains.
        let (exit, claim) = launch(task, reason, progress.clone()).await;
        let (exit, decision) = session.finish(exit, claim, &progress);
        if decision == After::Continue && claim == Some(true) {
            // The shared gate says there is no automatic repair; for a
            // rejected claim Ralph's loop is that repair (R06-04).
            progress.recovery(
                "claim rejected; Ralph continues with a bounded repair iteration unless a bound is reached",
            );
        }
        let check = session
            .record
            .borrow()
            .iterations
            .last()
            .and_then(|i| i.verification.as_ref().map(|v| v.status.clone()))
            .unwrap_or_else(|| "not run".to_owned());
        let finished = progress.finish(exit);
        note(format_args!(
            "iteration {number} ({}) outcome {}; completion claimed: {}; check: {check}",
            reason.name(),
            crate::progress::outcome(finished),
            match claim {
                Some(true) => "yes",
                Some(false) => "no",
                None if accept => "accept (operator)",
                None => "not inspected",
            },
        ));
        match decision {
            // Output delivery that failed after the record was written
            // still stops the run.
            _ if finished != exit => {
                note(format_args!(
                    "stopped at iteration {number} (outcome {})",
                    crate::progress::outcome(finished)
                ));
                return session.close(finished, false);
            }
            After::Complete => {
                note(format_args!(
                    "completed at iteration {number}: {}",
                    if accept {
                        "accepted by the operator after a passing check"
                    } else {
                        "claim verified by a passing check"
                    }
                ));
                return finished;
            }
            After::Continue => {
                if claim == Some(true) {
                    note(format_args!(
                        "claim rejected at iteration {number}: check {check}; the next iteration is the bounded repair"
                    ));
                }
                reason = IterationReason::Continue;
            }
            After::Stop => {
                note(format_args!(
                    "stopped at iteration {number} (outcome {}; check {check})",
                    crate::progress::outcome(finished)
                ));
                return session.close(finished, false);
            }
        }
    }
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
        // An accept runs no agent turn, so its resolved route policy is not
        // the row's policy (R06-05).
        let (route, model, fallback, permissions) = if iteration.reason == IterationReason::Accept {
            let none = "n/a (no agent turn)";
            (none, none, none, none)
        } else {
            (
                iteration.route.as_str(),
                iteration.model.as_str(),
                iteration.fallback.as_deref().unwrap_or("none"),
                iteration.permissions.as_str(),
            )
        };
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
            route,
            model,
            fallback,
            permissions,
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
    let mut stale = record.clone();
    interrupted(&mut stale);
    let resume = format!(
        "ah ralph resume {} --verify {}",
        record.run,
        recorded_check(record).unwrap_or("CHECK")
    );
    let counted = record.counted();
    let _ = match status {
        "completed" => writeln!(report, "next: complete; nothing to resume"),
        "active" => writeln!(report, "next: running"),
        _ if stale.iterations.len() >= crate::state::MAX_ITERATIONS => writeln!(
            report,
            "next: the run reached 100 recorded iterations; start a new run"
        ),
        _ if !settled(stale.iterations.last()) && counted >= record.max_iterations => writeln!(
            report,
            "next: its last iteration may have had effects; inspect the project, then {resume} --retry --max-iterations N (N greater than {counted}, at most 100) or {resume} --accept (needs no larger bound)"
        ),
        _ if !settled(stale.iterations.last()) => writeln!(
            report,
            "next: its last iteration may have had effects; inspect the project, then {resume} --retry or --accept"
        ),
        _ if counted >= record.max_iterations => writeln!(
            report,
            "next: {resume} --max-iterations N, with N greater than {counted} (at most 100)"
        ),
        _ => writeln!(report, "next: {resume}"),
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
    let refusal = match crate::single::workflow_supported(request) {
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

#[cfg(all(test, target_os = "macos"))]
mod tests {
    use super::{After, Exit, IterationReason, Launched, RalphStatus, Session, Status, Task};
    use std::cell::RefCell;
    use std::ffi::OsString;

    /// A pinned task and a session over a fresh record in a temporary store
    /// outside the project.
    fn fixture(name: &str, bound: u32) -> (std::path::PathBuf, Task, Session) {
        let dir =
            std::env::temp_dir().join(format!("ah-ralph-drive-{name}-{}", std::process::id()));
        let _ = std::fs::remove_dir_all(&dir);
        let project = dir.join("project");
        std::fs::create_dir_all(&project).unwrap();
        let project = project.canonicalize().unwrap();
        std::fs::write(
            project.join("ah.json"),
            r#"{"version":1,"mode":"local-only","model":"fixture","litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"TEST_KEY"},"checks":{"test":{"argv":["/usr/bin/true"]}}}"#,
        )
        .unwrap();
        let args = [
            "ralph",
            "run",
            "TASK.md",
            "--verify",
            "test",
            "--max-iterations",
        ]
        .into_iter()
        .map(OsString::from)
        .chain([OsString::from(bound.to_string())]);
        let (invocation, _, bounds) =
            crate::config::Invocation::parse_ralph(args, &project).unwrap();
        let config = crate::config::Config::open(&invocation.config_path()).unwrap();
        let mut request = invocation
            .step("Work.\n", None, None)
            .unwrap()
            .resolve(config, |_| Some("key".into()), std::io::empty())
            .unwrap();
        let check = request.verify.take().unwrap();
        let task = Task {
            snapshot: "Work.\n".into(),
            sha256: crate::state::sha256(b"Work.\n"),
            timeout_secs: request.timeout_secs,
            request,
            check,
            bounds,
        };
        let kind = crate::state::Kind::Ralph;
        let run = crate::state::new_id(kind).unwrap();
        let store = crate::state::Store::create_for(kind, dir.join("state"), &project).unwrap();
        let lock = store.lock(&project, &run).unwrap();
        let record = crate::state::RalphRecord {
            v: crate::state::VERSION,
            run,
            created: crate::state::now(),
            updated: crate::state::now(),
            project: project.to_str().unwrap().into(),
            prompt: project.join("TASK.md").to_str().unwrap().into(),
            config: project.join("ah.json").to_str().unwrap().into(),
            status: RalphStatus::Active,
            max_iterations: bound,
            invocations: vec![crate::state::InvocationRecord {
                started: crate::state::now(),
                reason: crate::state::InvocationReason::Run,
                max_runtime_secs: bounds.max_runtime_secs,
            }],
            iterations: Vec::new(),
        };
        store.create_record(&record).unwrap();
        (dir, task, Session::new(store, record, lock))
    }

    /// One scripted iteration: its final exit, claim and check status.
    type Script = (Exit, Option<bool>, Option<&'static str>);

    /// Drive the session from `first` with scripted iterations, returning
    /// the run exit and the reason each launch received. `cancel_after`
    /// signals once that many launches have returned.
    fn drive(
        task: &mut Task,
        session: &Session,
        first: IterationReason,
        script: &[Script],
        cancel_after: Option<usize>,
    ) -> (Exit, Vec<IterationReason>) {
        let token = tokio_util::sync::CancellationToken::new();
        let launches = RefCell::new(Vec::new());
        let exit = tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
            .unwrap()
            .block_on(super::drive(
                task,
                session,
                first,
                &token,
                |_, reason, progress| -> Launched<'_> {
                    let mut launches = launches.borrow_mut();
                    let (exit, claim, check) = script[launches.len()];
                    launches.push(reason);
                    if let Some(status) = check {
                        progress.verification(serde_json::json!({
                            "check": "test", "status": status,
                            "agent_outcome": "succeeded",
                            "exit_code": null, "signal": null, "timeout_secs": 600,
                            "duration_ms": 1, "cleanup_confirmed": exit != Exit::Uncertain,
                        }));
                    }
                    if cancel_after == Some(launches.len()) {
                        token.cancel();
                    }
                    Box::pin(async move { (exit, claim) })
                },
            ));
        (exit, launches.take())
    }

    fn statuses(session: &Session) -> Vec<(Status, Option<bool>)> {
        session
            .record
            .borrow()
            .iterations
            .iter()
            .map(|i| (i.status, i.claim))
            .collect()
    }

    #[test]
    fn a_signal_between_iterations_stops_before_the_next_launch() {
        let (dir, mut task, session) = fixture("signal", 5);
        let ok = (Exit::Success, Some(false), None);
        let (exit, launches) = drive(
            &mut task,
            &session,
            IterationReason::Initial,
            &[ok; 5],
            Some(1),
        );
        assert_eq!(
            (exit, launches),
            (Exit::Cancelled, vec![IterationReason::Initial])
        );
        assert_eq!(statuses(&session), vec![(Status::Succeeded, Some(false))]);
        let stored: crate::state::RalphRecord =
            session.store.read(&session.record.borrow().run).unwrap();
        assert_eq!(stored.status, RalphStatus::Stopped);
        // The stopped run resumes without a choice.
        assert!(super::settled(stored.iterations.last()));
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn a_rejected_claim_repairs_until_a_verified_claim_completes() {
        let (dir, mut task, session) = fixture("complete", 5);
        let script = [
            (Exit::Failed, Some(true), Some("failed")),
            (Exit::Success, Some(false), None),
            (Exit::Failed, Some(true), Some("timed_out")),
            (Exit::Success, Some(true), Some("passed")),
            (Exit::Success, Some(false), None),
        ];
        let (exit, launches) = drive(&mut task, &session, IterationReason::Initial, &script, None);
        use IterationReason::{Continue, Initial};
        assert_eq!(exit, Exit::Success);
        assert_eq!(launches, vec![Initial, Continue, Continue, Continue]);
        assert_eq!(session.record.borrow().status, RalphStatus::Completed);
        let record = session.record.borrow();
        let last = record.iterations.last().unwrap();
        assert_eq!(super::after(last), After::Complete);
        assert_eq!(
            record.iterations[0].agent_outcome.as_deref(),
            Some("succeeded")
        );
        assert_eq!(record.iterations[0].status, Status::Failed);
        drop(record);
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn checks_that_cannot_decide_and_failed_agents_stop_the_run() {
        for (script, stop) in [
            ((Exit::Failed, Some(true), Some("error")), Exit::Failed),
            (
                (Exit::Cancelled, Some(true), Some("cancelled")),
                Exit::Cancelled,
            ),
            (
                (Exit::Uncertain, Some(true), Some("failed")),
                Exit::Uncertain,
            ),
            ((Exit::Failed, None, None), Exit::Failed),
            ((Exit::Uncertain, None, None), Exit::Uncertain),
        ] {
            let (dir, mut task, session) = fixture("stop", 5);
            let (exit, launches) = drive(
                &mut task,
                &session,
                IterationReason::Initial,
                &[script],
                None,
            );
            assert_eq!((exit, launches.len()), (stop, 1), "{script:?}");
            assert_eq!(session.record.borrow().status, RalphStatus::Stopped);
            std::fs::remove_dir_all(dir).unwrap();
        }
    }

    #[test]
    fn rejected_claims_still_exhaust_the_iteration_bound() {
        let (dir, mut task, session) = fixture("exhaust", 2);
        let rejected = (Exit::Failed, Some(true), Some("failed"));
        let (exit, launches) = drive(
            &mut task,
            &session,
            IterationReason::Initial,
            &[rejected; 2],
            None,
        );
        assert_eq!((exit, launches.len()), (Exit::Failed, 2));
        assert_eq!(session.record.borrow().status, RalphStatus::Exhausted);
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn an_accept_runs_only_the_check_and_is_not_counted() {
        // Bound already reached: accept needs no larger bound.
        let (dir, mut task, session) = fixture("accept", 1);
        let ok = (Exit::Success, Some(false), None);
        let (exit, _) = drive(&mut task, &session, IterationReason::Initial, &[ok], None);
        assert_eq!(exit, Exit::Failed);
        assert_eq!(session.record.borrow().status, RalphStatus::Exhausted);
        let (exit, launches) = drive(
            &mut task,
            &session,
            IterationReason::Accept,
            &[(Exit::Success, None, Some("passed"))],
            None,
        );
        assert_eq!(
            (exit, launches),
            (Exit::Success, vec![IterationReason::Accept])
        );
        let record = session.record.borrow();
        assert_eq!(
            (record.status, record.counted()),
            (RalphStatus::Completed, 1)
        );
        let accept = record.iterations.last().unwrap();
        assert_eq!(
            (accept.status, accept.agent_outcome.as_deref(), accept.claim),
            (Status::Accepted, None, None)
        );
        assert_eq!(accept.verification.as_ref().unwrap().agent_outcome, None);
        assert_eq!(accept.input_sha256, crate::state::sha256(b""));
        drop(record);
        // A failed accept stops the run with the D043 exit.
        let (dir2, mut task, session) = fixture("accept-fail", 1);
        let (exit, _) = drive(
            &mut task,
            &session,
            IterationReason::Accept,
            &[(Exit::Failed, None, Some("failed"))],
            None,
        );
        assert_eq!(exit, Exit::Failed);
        assert_eq!(session.record.borrow().status, RalphStatus::Stopped);
        std::fs::remove_dir_all(dir).unwrap();
        std::fs::remove_dir_all(dir2).unwrap();
    }

    /// A concluded iteration of the fixture task.
    fn concluded(task: &Task, number: u32, reason: IterationReason) -> crate::state::Iteration {
        let mut iteration = super::iteration(task, number, reason, "x").unwrap();
        iteration.status = if reason == IterationReason::Accept {
            Status::Failed
        } else {
            iteration.agent_outcome = Some("succeeded".into());
            iteration.claim = Some(false);
            Status::Succeeded
        };
        iteration
    }

    #[test]
    fn a_full_record_ends_exhausted_before_any_launch() {
        // R06-01: 99 agent iterations and one accept are below the agent
        // bound of 100 but fill the record; nothing more is appended.
        let (dir, mut task, session) = fixture("full", 100);
        session.record.borrow_mut().iterations = (1..=100)
            .map(|n| {
                let reason = if n == 50 {
                    IterationReason::Accept
                } else {
                    IterationReason::Continue
                };
                concluded(&task, n, reason)
            })
            .collect();
        assert_eq!(session.record.borrow().counted(), 99);
        let (exit, launches) = drive(&mut task, &session, IterationReason::Retry, &[], None);
        assert_eq!((exit, launches), (Exit::Failed, vec![]));
        let stored: crate::state::RalphRecord =
            session.store.read(&session.record.borrow().run).unwrap();
        assert_eq!(
            (stored.status, stored.iterations.len()),
            (RalphStatus::Exhausted, 100)
        );
        // The store never writes a 101-iteration record its reader refuses.
        let mut over = stored.clone();
        over.iterations
            .push(concluded(&task, 101, IterationReason::Continue));
        let refused = session.store.write(&over).unwrap_err();
        assert_eq!(
            (refused.exit, refused.reason),
            (
                Exit::Failed,
                "refusing to write an inconsistent Ralph record"
            )
        );
        let unchanged: crate::state::RalphRecord = session.store.read(&stored.run).unwrap();
        assert_eq!(unchanged, stored);
        std::fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn an_accept_reports_only_prompt_and_check_changes() {
        // R06-05: an accept's route fields describe no agent turn.
        let (dir, task, _session) = fixture("accept-changes", 5);
        let previous = concluded(&task, 1, IterationReason::Initial);
        let mut next = concluded(&task, 2, IterationReason::Accept);
        next.permissions = "trusted".into();
        next.route = "cloud-only".into();
        next.agent_sha256 = Some("0".repeat(64));
        assert!(super::changes(&previous, &next).is_empty());
        next.prompt_sha256 = "1".repeat(64);
        next.check.as_mut().unwrap().argv_sha256 = "2".repeat(64);
        assert_eq!(
            super::changes(&previous, &next),
            vec!["prompt sha256", "check argv sha256"]
        );
        // An agent iteration still reports its route policy.
        next.reason = IterationReason::Retry;
        assert_eq!(
            super::changes(&previous, &next),
            vec![
                "prompt sha256",
                "agent definition",
                "check argv sha256",
                "route",
                "permissions"
            ]
        );
        std::fs::remove_dir_all(dir).unwrap();
    }
}
