//! Ordered prompt sequences (D044): a deterministic folder snapshot whose
//! steps each run as a fresh single run through the same route policy,
//! strictly linear and stopping at the first incomplete step. Every step is
//! validated, and its agent and check pinned, before step 1 launches.
//! Durable records, locking and resume belong to P5.3.
use crate::config::{Config, Exit, Invalid, Invocation, Resolved};
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

fn hex(digest: &[u8]) -> String {
    digest.iter().map(|b| format!("{b:02x}")).collect()
}

impl Step {
    /// Parse one step's bytes: optional strict metadata, then a nonempty body.
    pub fn parse(name: &str, text: &str) -> Result<Self> {
        use sha2::Digest;
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
            sha256: hex(&sha2::Sha256::digest(text.as_bytes())),
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

/// Sequence-level lines on stderr. Written only between steps, when no
/// runtime is supervised; each step's own diagnostics go through `Progress`.
fn note(message: impl std::fmt::Display) {
    use std::io::Write;
    let _ = writeln!(std::io::stderr().lock(), "ah: sequence {message}");
}

pub fn run(args: Vec<OsString>) -> Exit {
    use std::io::Write;
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
    let requests = match resolve(&invocation, &config, &steps, |name| std::env::var_os(name)) {
        Ok(requests) => requests,
        Err((index, error)) => {
            let exit = reject(format_args!("step {}: {}", steps[index].name, error.0));
            if error.0 == crate::config::MISSING_KEY {
                let _ = writeln!(
                    std::io::stderr().lock(),
                    "ah: set the environment variable named by the selected route api_key_env before retrying"
                );
            }
            return exit;
        }
    };
    if invocation.preview() {
        return preview(&steps, &requests, &folder, &config_path);
    }
    for (step, request) in steps.iter().zip(&requests) {
        if let Err(error) = crate::single::supported(request) {
            return reject(format_args!("step {}: {}", step.name, error.0));
        }
    }
    execute(&steps, &requests)
}

#[cfg(not(target_os = "macos"))]
fn execute(_: &[Step], _: &[Resolved]) -> Exit {
    reject("coding runs currently support tested macOS only")
}

#[cfg(target_os = "macos")]
fn execute(steps: &[Step], requests: &[Resolved]) -> Exit {
    let Ok(runtime) = tokio::runtime::Builder::new_current_thread()
        .enable_all()
        .build()
    else {
        return Exit::Failed;
    };
    let total = steps.len();
    note(format_args!(
        "{total} steps; each a fresh single run; stops at the first step that does not complete; no durable record or resume yet"
    ));
    runtime.block_on(async {
        // One watcher spans every step, so a signal between steps is seen
        // before the next launch rather than terminating the process.
        let signals = crate::runtime::Signals::watch();
        let cancelled = signals.token();
        drive(steps, &cancelled, |index, progress| {
            let request = &requests[index];
            let cancelled = cancelled.clone();
            progress.event(format!(
                "sequence step {}/{total} {} sha256={} agent={} check={}",
                index + 1,
                steps[index].name,
                steps[index].sha256,
                request.agent.as_ref().map_or("none", |a| a.name()),
                request.verify.as_ref().map_or("none", |c| c.name.as_str()),
            ));
            if let Some(check) = &request.verify {
                progress.verification(crate::verify::pending(check));
            }
            async move { crate::single::launch(request, cancelled, &progress).await }
        })
        .await
    })
}

/// The strictly linear loop (D044): each step gets its own run diagnostics; a
/// step that does not complete, or a signal seen before the next launch,
/// stops the sequence with that exit.
#[cfg_attr(not(target_os = "macos"), allow(dead_code))]
async fn drive<F, Fut>(
    steps: &[Step],
    cancelled: &tokio_util::sync::CancellationToken,
    mut launch: F,
) -> Exit
where
    F: FnMut(usize, crate::progress::Progress) -> Fut,
    Fut: std::future::Future<Output = Exit>,
{
    let total = steps.len();
    for (index, step) in steps.iter().enumerate() {
        let position = index + 1;
        if cancelled.is_cancelled() {
            note(format_args!(
                "stopped by signal before step {position}/{total} {}; it and later steps not launched",
                step.name
            ));
            return Exit::Cancelled;
        }
        let progress = crate::progress::Progress::new(false);
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
        let route = match (request.mode, &request.fallback) {
            (crate::config::Mode::LocalOnly, Some(_)) => "local-first",
            (crate::config::Mode::LocalOnly, None) => "local-only",
            _ => "cloud-only",
        };
        let changes = match crate::single::prepare_plan(request) {
            Ok(Some(plan)) if !plan.preview_changes().is_empty() => {
                plan.preview_changes().join("; ")
            }
            Ok(_) => "none".to_owned(),
            Err(error) => format!("refused: {}", error.0),
        };
        let refusal = match crate::single::supported(request) {
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
        let exit = block_on(drive(&steps(3), &token, |index, _| {
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
            let exit = block_on(drive(&steps(3), &token, |index, _| {
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
        let exit = block_on(drive(&steps(3), &token, |index, _| {
            ran.borrow_mut().push(index);
            token.cancel();
            async { Exit::Success }
        }));
        assert_eq!((exit, ran.take()), (Exit::Cancelled, vec![0]));
        // Already signalled: nothing launches.
        let exit = block_on(drive(&steps(2), &token, |index, _| {
            ran.borrow_mut().push(index);
            async { Exit::Success }
        }));
        assert_eq!((exit, ran.take()), (Exit::Cancelled, vec![]));
    }
}
