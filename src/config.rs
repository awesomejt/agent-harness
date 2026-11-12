//! First-slice input validation. No runtime launch, configuration writes or network I/O.
use crate::agents::Agent;
use serde::Deserialize;
use std::ffi::OsString;
use std::io::Read;
use std::path::{Path, PathBuf};

pub(crate) const MISSING_KEY: &str = "API key environment reference is missing or empty";

pub const CONFIG_NAME: &str = "ah.json";
pub const MAX_INPUT_BYTES: u64 = 1_048_576;
pub const DEFAULT_TIMEOUT_SECS: u64 = 1800;
/// Explicit harness model-group reference syntax for `model`/`--model`.
pub const GROUP_PREFIX: &str = "group:";
pub const MAX_GROUPS: usize = 64;

/// Errors deliberately exclude untrusted input, paths, prompt text and credentials.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Invalid(pub &'static str);

type Result<T> = std::result::Result<T, Invalid>;

#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Permissions {
    #[default]
    Deny,
    Trusted,
}

// Neither raw config nor resolved requests implement Serialize or Debug: callers
// must build an explicitly redacted preview rather than dump input structures.
// Clone lets a sequence resolve every step from one loaded snapshot (D044).
#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Config {
    version: u8,
    mode: String,
    #[serde(default, deserialize_with = "present")]
    model: Option<String>,
    #[serde(default, deserialize_with = "present")]
    litellm: Option<LiteLlm>,
    #[serde(default, deserialize_with = "present")]
    native: Option<Native>,
    permissions: Option<Permissions>,
    timeout_secs: Option<u64>,
    /// Declared verification checks (D043); only `--verify NAME` runs one.
    #[serde(default, deserialize_with = "present")]
    checks: Option<Named<crate::verify::Definition>>,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct LiteLlm {
    api_base: String,
    api_key_env: String,
    /// Local LiteLLM executor: `opencode` (default) or `pi` (D080).
    #[serde(default, deserialize_with = "present")]
    runtime: Option<String>,
    #[serde(default, deserialize_with = "present")]
    groups: Option<Named<String>>,
}

/// Name -> entry (harness group -> existing proxy model group, or check name
/// -> definition). Map deserialization would otherwise keep the last
/// duplicate key silently.
#[derive(Clone)]
struct Named<T>(std::collections::BTreeMap<String, T>);
impl<'de, T: Deserialize<'de>> Deserialize<'de> for Named<T> {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct V<T>(std::marker::PhantomData<T>);
        impl<'de, T: Deserialize<'de>> serde::de::Visitor<'de> for V<T> {
            type Value = Named<T>;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("a named-entry object")
            }
            fn visit_map<A: serde::de::MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Named<T>, A::Error> {
                let mut entries = std::collections::BTreeMap::new();
                while let Some((name, entry)) = a.next_entry::<String, T>()? {
                    if entries.insert(name, entry).is_some() {
                        return Err(serde::de::Error::custom("duplicate name"));
                    }
                }
                Ok(Named(entries))
            }
        }
        d.deserialize_map(V(std::marker::PhantomData))
    }
}

// Optional blocks may be absent but explicit null is not a valid route config.
fn present<'de, D: serde::Deserializer<'de>, T: Deserialize<'de>>(
    d: D,
) -> std::result::Result<Option<T>, D::Error> {
    T::deserialize(d).map(Some)
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Native {
    target: String,
    model: String,
    /// Required for `opencode`; rejected for `claude`, which uses the
    /// operator's existing official CLI login (D047/D048).
    #[serde(default, deserialize_with = "present")]
    api_key_env: Option<String>,
}

/// Runtime executing an attempt. The LiteLLM route runs OpenCode or Pi (D080);
/// the native route runs the runtime named by `native.target` (D048).
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum RuntimeKind {
    OpenCode,
    Claude,
    Pi,
}

#[derive(Clone)]
pub struct Invocation {
    project: PathBuf,
    config: Option<PathBuf>,
    mode: Option<String>,
    model: Option<String>,
    agent: Option<String>,
    permissions: Option<Permissions>,
    timeout_secs: Option<u64>,
    no_sync: bool,
    preview: bool,
    machine: bool,
    verify: Option<String>,
    prompt: PromptSource,
}

/// Whether `--output jsonl` was requested, decided before full validation so
/// that even a rejected invocation ends with a machine result record (D039).
pub fn machine_output(args: &[OsString]) -> bool {
    args.windows(2)
        .any(|pair| pair[0] == "--output" && pair[1] == "jsonl")
}

#[derive(Clone)]
enum PromptSource {
    Inline(String),
    File(PathBuf),
    Stdin,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    LocalOnly,
    CloudOnly,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Source {
    Invocation,
    /// The selected canonical agent's route-specific model.
    Agent,
    Config,
    Default,
}

#[derive(Clone, Copy)]
pub struct Sources {
    pub mode: Source,
    pub model: Source,
    pub permissions: Source,
    pub timeout: Source,
}

pub struct Resolved {
    /// Route of this attempt; local-first resolves a LiteLLM primary.
    pub mode: Mode,
    pub sources: Sources,
    pub project: PathBuf,
    /// Proxy model group (local) or built-in model (native) sent to the runtime.
    pub model: String,
    /// Harness group name when `model` was selected through `group:NAME`.
    pub group: Option<String>,
    /// Distinct proxy model groups named by `litellm.groups`, for the read-only
    /// operator handoff. Empty for native requests.
    pub proxy_groups: Vec<String>,
    pub api_base: Option<String>,
    /// Environment name of the selected route key; `None` for the Claude
    /// runtime, which uses the operator's existing CLI login (D047).
    pub api_key_env: Option<String>,
    pub runtime: RuntimeKind,
    pub permissions: Permissions,
    pub timeout_secs: u64,
    pub no_sync: bool,
    pub preview: bool,
    pub prompt: String,
    /// Canonical project-root `AGENTS.md`, named explicitly to the isolated
    /// runtime, which itself reads it (D040). `None` when absent.
    pub instructions: Option<PathBuf>,
    /// Selected canonical definition, enforced at runtime as the default agent
    /// with its ceiling intersected with `permissions` (D038).
    pub agent: Option<Agent>,
    /// Local-first only: the configured native target, resolved with identical
    /// project, permissions, timeout and prompt. Never nested.
    pub fallback: Option<Box<Resolved>>,
    /// Check named by `--verify`, run once after the final backend outcome
    /// (D043). The fallback request never carries one.
    pub verify: Option<crate::verify::Check>,
}

/// Numeric shell contract; runtime mapping is implemented by P2.2/P2.4.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
#[repr(u8)]
pub enum Exit {
    Success = 0,
    Failed = 1,
    Invalid = 2,
    Cancelled = 3,
    Uncertain = 4,
}

pub(crate) fn bounded(mut reader: impl Read) -> Result<String> {
    let mut bytes = Vec::new();
    reader
        .by_ref()
        .take(MAX_INPUT_BYTES + 1)
        .read_to_end(&mut bytes)
        .map_err(|_| Invalid("cannot read input"))?;
    if bytes.len() as u64 > MAX_INPUT_BYTES {
        return Err(Invalid("input exceeds 1 MiB"));
    }
    String::from_utf8(bytes).map_err(|_| Invalid("input must be UTF-8"))
}

/// Project instructions the isolated runtime may load (D040): only the
/// project-root `AGENTS.md`, resolving to a regular file inside the project.
/// OpenCode 2.2.5 skips project instructions once project configuration is
/// disabled, so the harness names this one path. The Pi runtime reads and
/// bounds it when composing the RPC prompt (D082); other routes pass the path only.
pub(crate) fn instructions(project: &Path) -> Result<Option<PathBuf>> {
    const OUTSIDE: Invalid =
        Invalid("project AGENTS.md must resolve to a regular file inside the project");
    let path = project.join("AGENTS.md");
    match std::fs::symlink_metadata(&path) {
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(OUTSIDE),
        Ok(_) => {}
    }
    let resolved = path.canonicalize().map_err(|_| OUTSIDE)?;
    let regular = std::fs::metadata(&resolved).is_ok_and(|m| m.is_file());
    if regular && resolved.starts_with(project) {
        Ok(Some(resolved))
    } else {
        Err(OUTSIDE)
    }
}

pub(crate) fn open_regular_file(path: &Path) -> Result<std::fs::File> {
    let mut options = std::fs::OpenOptions::new();
    options.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        options.custom_flags(libc::O_NONBLOCK | libc::O_NOCTTY);
    }
    let file = options
        .open(path)
        .map_err(|_| Invalid("cannot open input file"))?;
    if !file
        .metadata()
        .map_err(|_| Invalid("cannot inspect input file"))?
        .is_file()
    {
        return Err(Invalid("input path must be a regular file"));
    }
    Ok(file)
}

impl Config {
    /// Application file entry point: reject streams/devices before reading.
    pub fn open(path: &Path) -> Result<Self> {
        Self::read(open_regular_file(path)?)
    }

    /// Validate a caller-owned reader (e.g. fixture bytes). Application config
    /// loading must use `open` to enforce regular-file/nonblocking semantics.
    pub fn read(reader: impl Read) -> Result<Self> {
        // Direct struct deserialization also rejects duplicate fields. Never
        // surface serde's error: it can contain arbitrary secret-bearing input.
        let config: Self = serde_json::from_str(&bounded(reader)?)
            .map_err(|_| Invalid("invalid config: expected strict version-1 JSON schema"))?;
        config.validate()?;
        Ok(config)
    }

    fn validate(&self) -> Result<()> {
        if self.version != 1 {
            return Err(Invalid("unsupported config version"));
        }
        if self
            .permissions
            .is_some_and(|policy| policy != Permissions::Deny)
        {
            return Err(Invalid(
                "trusted permissions require explicit --permissions trusted, not project config",
            ));
        }
        validate_mode(&self.mode)?;
        if let Some(model) = &self.model {
            validate_reference(model)?;
        }
        validate_timeout(self.timeout_secs.unwrap_or(DEFAULT_TIMEOUT_SECS))?;
        if let Some(local) = &self.litellm {
            validate_local(local)?;
        }
        if let Some(group) = self.model.as_deref().and_then(group_name) {
            self.group(group)?;
        }
        if let Some(checks) = &self.checks {
            if checks.0.is_empty() || checks.0.len() > crate::verify::MAX_CHECKS {
                return Err(Invalid("checks requires 1–64 entries"));
            }
            for (name, check) in &checks.0 {
                crate::verify::validate_name(name)?;
                check.validate()?;
            }
        }
        if let Some(native) = &self.native {
            match (native.target.as_str(), &native.api_key_env) {
                ("opencode", Some(key)) => validate_key_name(key)?,
                ("opencode", None) => {
                    return Err(Invalid("native target opencode requires api_key_env"));
                }
                ("claude", None) => {}
                ("claude", Some(_)) => {
                    return Err(Invalid(
                        "native target claude uses the existing official CLI login; api_key_env is unsupported",
                    ));
                }
                _ => {
                    return Err(Invalid(
                        "native target must be opencode (built-in API-key provider) or claude (official CLI login)",
                    ));
                }
            }
            validate_model(&native.model)?;
        }
        if self.mode != "cloud-only" && self.model.is_none() {
            return Err(Invalid(
                "local-only and local-first config require a model default",
            ));
        }
        if self.litellm.as_ref().and_then(|l| l.runtime.as_deref()) == Some("pi")
            && self.mode != "local-only"
        {
            return Err(Invalid(
                "litellm.runtime pi applies only to local-only configuration",
            ));
        }
        self.key_name(&self.mode)?;
        Ok(())
    }
}

fn validate_local(local: &LiteLlm) -> Result<()> {
    let endpoint =
        url::Url::parse(&local.api_base).map_err(|_| Invalid("invalid LiteLLM API base"))?;
    if !matches!(endpoint.scheme(), "http" | "https")
        || endpoint.host_str().is_none()
        || !endpoint.username().is_empty()
        || endpoint.password().is_some()
        || endpoint.query().is_some()
        || endpoint.fragment().is_some()
        || endpoint.path() != "/v1"
        || endpoint.as_str() != local.api_base
        || local.api_base.trim() != local.api_base
        || local.api_base.chars().any(char::is_control)
    {
        return Err(Invalid(
            "API base requires canonical http(s), a host, /v1 and no credentials/query/fragment",
        ));
    }
    if let Some(groups) = &local.groups {
        if groups.0.is_empty() || groups.0.len() > MAX_GROUPS {
            return Err(Invalid("litellm.groups requires 1–64 entries"));
        }
        for (name, target) in &groups.0 {
            validate_model(name)?;
            validate_model(target)?;
        }
    }
    if let Some(runtime) = &local.runtime {
        if runtime != "opencode" && runtime != "pi" {
            return Err(Invalid("litellm.runtime must be opencode or pi"));
        }
    }
    validate_key_name(&local.api_key_env)
}
fn group_name(reference: &str) -> Option<&str> {
    reference.strip_prefix(GROUP_PREFIX)
}
pub(crate) fn validate_reference(reference: &str) -> Result<()> {
    validate_model(group_name(reference).unwrap_or(reference))
}
fn validate_key_name(value: &str) -> Result<()> {
    let name = value.as_bytes();
    if name.is_empty()
        || !(name[0].is_ascii_alphabetic() || name[0] == b'_')
        || !name.iter().all(|b| b.is_ascii_alphanumeric() || *b == b'_')
    {
        return Err(Invalid("api_key_env must be an environment variable name"));
    }
    Ok(())
}
impl Config {
    fn group(&self, name: &str) -> Result<&str> {
        self.litellm
            .as_ref()
            .and_then(|local| local.groups.as_ref())
            .and_then(|groups| groups.0.get(name))
            .map(String::as_str)
            .ok_or(Invalid(
                "model group reference is not defined in litellm.groups",
            ))
    }
    /// The selected route's key reference. Claude uses its official CLI login;
    /// a local-first primary still requires the LiteLLM key (D052).
    fn key_name(&self, mode: &str) -> Result<Option<&str>> {
        let local = self.litellm.as_ref().map(|v| v.api_key_env.as_str());
        let native = self.native.as_ref();
        match mode {
            "local-only" => local
                .map(Some)
                .ok_or(Invalid("local-only requires litellm configuration")),
            "cloud-only" => native
                .map(|n| n.api_key_env.as_deref())
                .ok_or(Invalid("cloud-only requires native configuration")),
            "local-first" => {
                let (Some(_), Some(local)) = (native, local) else {
                    return Err(Invalid(
                        "local-first requires litellm and native configuration",
                    ));
                };
                Ok(Some(local))
            }
            _ => Err(Invalid(UNSUPPORTED_MODE)),
        }
    }
}
const UNSUPPORTED_MODE: &str = "mode must be local-only, cloud-only or local-first";
fn validate_mode(mode: &str) -> Result<()> {
    if !matches!(mode, "local-only" | "cloud-only" | "local-first") {
        return Err(Invalid(UNSUPPORTED_MODE));
    }
    Ok(())
}
pub(crate) fn validate_model(model: &str) -> Result<()> {
    if model.is_empty()
        || model.len() > 128
        || !model
            .bytes()
            .all(|b| b.is_ascii_alphanumeric() || b"._-".contains(&b))
    {
        return Err(Invalid(
            "model must be a 1–128 byte identifier using letters, digits, dot, underscore or hyphen",
        ));
    }
    Ok(())
}
fn validate_timeout(seconds: u64) -> Result<()> {
    if !(1..=86400).contains(&seconds) {
        return Err(Invalid("timeout must be 1–86400 seconds"));
    }
    Ok(())
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum SequenceCommand {
    None,
    Run,
    Resume,
    Ralph,
    RalphResume,
}

/// Ralph loop bounds (D045): iterations per run, wall time per invocation.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub struct Bounds {
    pub max_iterations: u32,
    pub max_runtime_secs: u64,
}

impl Default for Bounds {
    fn default() -> Self {
        Self {
            max_iterations: 10,
            max_runtime_secs: 3600,
        }
    }
}

impl Invocation {
    /// Parse `single` input without side effects. Paths are relative to
    /// invocation cwd, never project.
    pub fn parse(args: impl IntoIterator<Item = OsString>, cwd: &Path) -> Result<Self> {
        let mut args = args.into_iter();
        if args.next().as_deref() != Some(std::ffi::OsStr::new("single")) {
            return Err(Invalid("expected single command"));
        }
        Self::options(args, cwd, SequenceCommand::None).map(|(request, _)| request)
    }

    /// Parse `sequence run DIR` (D044): the `single` coding options plus
    /// `--preview`; steps come only from DIR, so prompt sources reject, and
    /// `--output jsonl` rejects in Phase 5. DIR is relative to cwd.
    pub fn parse_sequence(
        args: impl IntoIterator<Item = OsString>,
        cwd: &Path,
    ) -> Result<(Self, PathBuf)> {
        let mut args = args.into_iter();
        if args.next().as_deref() != Some(std::ffi::OsStr::new("sequence")) {
            return Err(Invalid("expected sequence command"));
        }
        if args.next().as_deref() != Some(std::ffi::OsStr::new("run")) {
            return Err(Invalid(
                "unsupported sequence command; use sequence run DIR",
            ));
        }
        let (request, folder) = Self::options(args, cwd, SequenceCommand::Run)?;
        if request.machine {
            return Err(Invalid(
                "--output jsonl is unsupported for sequence commands; use human output",
            ));
        }
        Ok((request, folder.ok_or(Invalid("provide a prompt folder"))?))
    }

    /// Parse `sequence resume RUN_ID` (D044) after the caller removes
    /// `--retry`/`--accept`: the coding options except `--project`,
    /// `--config` and `--preview`, which come from the record or do not
    /// apply. Returns the raw run ID; its grammar is checked by the caller.
    pub fn parse_resume(
        args: impl IntoIterator<Item = OsString>,
        cwd: &Path,
    ) -> Result<(Self, String)> {
        let args: Vec<OsString> = args.into_iter().collect();
        if args.len() < 2 || args[0] != "sequence" || args[1] != "resume" {
            return Err(Invalid("expected sequence resume"));
        }
        if args[2..]
            .iter()
            .any(|a| a == "--project" || a == "--config" || a == "--preview")
        {
            return Err(Invalid(
                "sequence resume takes project and config from the record; --project, --config and --preview reject",
            ));
        }
        let (request, run) = Self::options(args.into_iter().skip(2), cwd, SequenceCommand::Resume)?;
        if request.machine {
            return Err(Invalid(
                "--output jsonl is unsupported for sequence commands; use human output",
            ));
        }
        let run = run.ok_or(Invalid("provide a run ID"))?;
        // The positional was joined to cwd; recover the raw argument.
        let run = run
            .strip_prefix(cwd)
            .ok()
            .and_then(Path::to_str)
            .ok_or(Invalid("run ID must be sYYYYMMDDTHHMMSSZ-xxxxxxxx"))?
            .to_owned();
        Ok((request, run))
    }

    /// Parse `ralph run FILE` (D045): the `single` coding options plus
    /// `--preview` and the loop bounds. FILE is the only prompt source, so
    /// inline text, `--prompt-file` and stdin reject; `--verify` is required
    /// and `--output jsonl` rejects. FILE is relative to cwd.
    pub fn parse_ralph(
        args: impl IntoIterator<Item = OsString>,
        cwd: &Path,
    ) -> Result<(Self, PathBuf, Bounds)> {
        let mut args = args.into_iter();
        if args.next().as_deref() != Some(std::ffi::OsStr::new("ralph")) {
            return Err(Invalid("expected ralph command"));
        }
        if args.next().as_deref() != Some(std::ffi::OsStr::new("run")) {
            return Err(Invalid(
                "unsupported ralph command; use ralph run FILE, ralph resume RUN_ID or ralph show",
            ));
        }
        let (rest, iterations, runtime) = Self::ralph_bounds(args)?;
        let defaults = Bounds::default();
        let bounds = Bounds {
            max_iterations: iterations.unwrap_or(defaults.max_iterations),
            max_runtime_secs: runtime.unwrap_or(defaults.max_runtime_secs),
        };
        let (request, file) = Self::options(rest.into_iter(), cwd, SequenceCommand::Ralph)?;
        let file = file.ok_or(Invalid("provide a prompt file"))?;
        request.ralph_checked("ralph run")?;
        Ok((request, file, bounds))
    }

    /// Parse `ralph resume RUN_ID` (D045) after the caller removes
    /// `--retry`/`--accept`: the coding options except `--project`,
    /// `--config` and `--preview`, which come from the record or do not
    /// apply, plus the loop bounds. `--verify` is required. Returns the raw
    /// run ID (its grammar is checked by the caller), the iteration bound
    /// only when given, and this invocation's wall bound.
    pub fn parse_ralph_resume(
        args: impl IntoIterator<Item = OsString>,
        cwd: &Path,
    ) -> Result<(Self, String, Option<u32>, u64)> {
        let args: Vec<OsString> = args.into_iter().collect();
        if args.len() < 2 || args[0] != "ralph" || args[1] != "resume" {
            return Err(Invalid("expected ralph resume"));
        }
        if args[2..]
            .iter()
            .any(|a| a == "--project" || a == "--config" || a == "--preview")
        {
            return Err(Invalid(
                "ralph resume takes project, config and prompt file from the record; --project, --config and --preview reject",
            ));
        }
        let (rest, iterations, runtime) = Self::ralph_bounds(args.into_iter().skip(2))?;
        let (request, run) = Self::options(rest.into_iter(), cwd, SequenceCommand::RalphResume)?;
        let run = run.ok_or(Invalid("provide a run ID"))?;
        request.ralph_checked("ralph resume")?;
        // The positional was joined to cwd; recover the raw argument.
        let run = run
            .strip_prefix(cwd)
            .ok()
            .and_then(Path::to_str)
            .ok_or(Invalid("run ID must be rYYYYMMDDTHHMMSSZ-xxxxxxxx"))?
            .to_owned();
        let runtime = runtime.unwrap_or(Bounds::default().max_runtime_secs);
        Ok((request, run, iterations, runtime))
    }

    /// Remove `--max-iterations` (1–100) and `--max-runtime-secs`
    /// (1–86400), each at most once, returning the remaining arguments.
    fn ralph_bounds(
        mut args: impl Iterator<Item = OsString>,
    ) -> Result<(Vec<OsString>, Option<u32>, Option<u64>)> {
        let (mut iterations, mut runtime) = (None, None);
        let mut rest = Vec::new();
        while let Some(arg) = args.next() {
            let name = match arg.to_str() {
                Some(name @ ("--max-iterations" | "--max-runtime-secs")) => name,
                _ => {
                    rest.push(arg);
                    continue;
                }
            };
            let value = args.next().ok_or(Invalid("missing option value"))?;
            let value = value.to_str().ok_or(Invalid("arguments must be UTF-8"))?;
            let duplicate = if name == "--max-iterations" {
                iterations
                    .replace(
                        value
                            .parse()
                            .ok()
                            .filter(|n| (1..=100).contains(n))
                            .ok_or(Invalid("--max-iterations must be 1–100"))?,
                    )
                    .is_some()
            } else {
                runtime
                    .replace(
                        value
                            .parse()
                            .ok()
                            .filter(|s| (1..=86400).contains(s))
                            .ok_or(Invalid("--max-runtime-secs must be 1–86400 seconds"))?,
                    )
                    .is_some()
            };
            if duplicate {
                return Err(Invalid("duplicate option"));
            }
        }
        Ok((rest, iterations, runtime))
    }

    /// Ralph commands reject machine output and require a check.
    fn ralph_checked(&self, command: &'static str) -> Result<()> {
        if self.machine {
            return Err(Invalid(
                "--output jsonl is unsupported for ralph commands; use human output",
            ));
        }
        if self.verify.is_none() {
            return Err(Invalid(if command == "ralph run" {
                "ralph run requires --verify CHECK; there is no unverified Ralph completion"
            } else {
                "ralph resume requires --verify CHECK; there is no unverified Ralph completion"
            }));
        }
        Ok(())
    }

    /// Point a resumed invocation at its recorded project and config.
    pub fn rebase(&mut self, project: PathBuf, config: PathBuf) {
        self.project = project;
        self.config = Some(config);
    }

    /// One step of a sequence (D044): the invocation with the step's prompt
    /// and metadata. Metadata may name an agent only when it agrees with
    /// `--agent`, and may substitute a check only under `--verify`.
    pub fn step(&self, prompt: &str, agent: Option<&str>, verify: Option<&str>) -> Result<Self> {
        if let (Some(invoked), Some(agent)) = (&self.agent, agent)
            && invoked != agent
        {
            return Err(Invalid("step metadata agent conflicts with --agent"));
        }
        if verify.is_some() && self.verify.is_none() {
            return Err(Invalid("step metadata verify requires --verify"));
        }
        Ok(Self {
            agent: agent.map(str::to_owned).or_else(|| self.agent.clone()),
            verify: verify.map(str::to_owned).or_else(|| self.verify.clone()),
            prompt: PromptSource::Inline(prompt.to_owned()),
            ..self.clone()
        })
    }

    pub fn preview(&self) -> bool {
        self.preview
    }

    pub fn verify(&self) -> Option<&str> {
        self.verify.as_deref()
    }

    fn options(
        mut args: impl Iterator<Item = OsString>,
        cwd: &Path,
        sequence: SequenceCommand,
    ) -> Result<(Self, Option<PathBuf>)> {
        let mut folder = None;
        let mut request = Self {
            project: cwd.to_owned(),
            config: None,
            mode: None,
            model: None,
            agent: None,
            permissions: None,
            timeout_secs: None,
            no_sync: false,
            preview: false,
            machine: false,
            verify: None,
            prompt: PromptSource::Stdin,
        };
        let mut prompt = None;
        let mut seen = std::collections::HashSet::new();
        while let Some(arg) = args.next() {
            let arg = arg.to_str().ok_or(Invalid("arguments must be UTF-8"))?;
            if arg.starts_with("--") {
                if !seen.insert(arg.to_owned()) {
                    return Err(Invalid("duplicate option"));
                }
                if arg == "--no-sync" {
                    request.no_sync = true;
                    continue;
                }
                if arg == "--preview" {
                    request.preview = true;
                    continue;
                }
                if !matches!(
                    arg,
                    "--project"
                        | "--config"
                        | "--mode"
                        | "--model"
                        | "--agent"
                        | "--permissions"
                        | "--timeout-secs"
                        | "--prompt-file"
                        | "--output"
                        | "--verify"
                ) {
                    return Err(Invalid("unsupported option"));
                }
                let value = args.next().ok_or(Invalid("missing option value"))?;
                let value = value.to_str().ok_or(Invalid("arguments must be UTF-8"))?;
                if value.is_empty() || value.starts_with("--") {
                    return Err(Invalid("missing option value"));
                }
                match arg {
                    "--project" => request.project = cwd.join(value),
                    "--config" => request.config = Some(cwd.join(value)),
                    "--mode" => {
                        validate_mode(value)?;
                        request.mode = Some(value.to_owned());
                    }
                    "--model" => {
                        validate_reference(value)?;
                        request.model = Some(value.to_owned());
                    }
                    "--agent" => {
                        crate::agents::validate_name(value)?;
                        request.agent = Some(value.to_owned());
                    }
                    "--permissions" => {
                        request.permissions = Some(match value {
                            "deny" => Permissions::Deny,
                            "trusted" => Permissions::Trusted,
                            _ => return Err(Invalid("unsupported permission policy")),
                        })
                    }
                    "--timeout-secs" => {
                        let seconds = value.parse().map_err(|_| Invalid("invalid timeout"))?;
                        validate_timeout(seconds)?;
                        request.timeout_secs = Some(seconds);
                    }
                    "--verify" => {
                        crate::verify::validate_name(value)?;
                        request.verify = Some(value.to_owned());
                    }
                    "--output" => {
                        request.machine = match value {
                            "human" => false,
                            "jsonl" => true,
                            _ => return Err(Invalid("unsupported output format")),
                        }
                    }
                    "--prompt-file"
                        if matches!(
                            sequence,
                            SequenceCommand::Ralph | SequenceCommand::RalphResume
                        ) =>
                    {
                        return Err(Invalid(
                            "ralph reads its prompt only from FILE; prompt sources reject",
                        ));
                    }
                    "--prompt-file" if sequence != SequenceCommand::None => {
                        return Err(Invalid(
                            "sequence steps come from the prompt folder; prompt sources reject",
                        ));
                    }
                    "--prompt-file" => {
                        if prompt.is_some() {
                            return Err(Invalid("conflicting prompt sources"));
                        }
                        prompt = Some(if value == "-" {
                            PromptSource::Stdin
                        } else {
                            PromptSource::File(cwd.join(value))
                        });
                    }
                    _ => unreachable!(),
                }
            } else {
                if arg.starts_with('-') {
                    return Err(Invalid(
                        "unsupported option; use --prompt-file for leading-dash text",
                    ));
                }
                if sequence != SequenceCommand::None {
                    if folder.is_some() {
                        return Err(Invalid(match sequence {
                            SequenceCommand::Resume => "sequence resume takes one run ID",
                            SequenceCommand::RalphResume => "ralph resume takes one run ID",
                            SequenceCommand::Ralph => {
                                "ralph run takes one prompt file; prompt sources reject"
                            }
                            _ => "sequence run takes one prompt folder; prompt sources reject",
                        }));
                    }
                    folder = Some(cwd.join(arg));
                    continue;
                }
                if prompt.is_some() {
                    return Err(Invalid("conflicting prompt sources"));
                }
                prompt = Some(PromptSource::Inline(arg.to_owned()));
            }
        }
        // Each sequence step and Ralph iteration substitutes its own prompt
        // (`step`).
        request.prompt = if sequence != SequenceCommand::None {
            PromptSource::Inline(String::new())
        } else {
            prompt.ok_or(Invalid("provide inline prompt or --prompt-file PATH|-"))?
        };
        if request.machine && request.preview {
            return Err(Invalid(
                "--output jsonl does not support --preview; preview is human-readable only",
            ));
        }
        Ok((request, folder))
    }

    pub fn config_path(&self) -> PathBuf {
        self.config
            .clone()
            .unwrap_or_else(|| self.project.join(CONFIG_NAME))
    }

    /// Checks configuration and credentials before consuming potentially blocking
    /// stdin. The lookup result is checked for nonempty content and immediately
    /// dropped; the resolved request stores only the environment name. Local-first
    /// checks the LiteLLM key and, for an OpenCode fallback, the native key;
    /// a Claude fallback uses the official CLI login without a key lookup.
    /// A `--verify` check also uses the lookup for `PATH` to pin its program.
    pub fn resolve(
        self,
        config: Config,
        key_lookup: impl Fn(&str) -> Option<OsString>,
        stdin: impl Read,
    ) -> Result<Resolved> {
        config.validate()?;
        let project = self
            .project
            .canonicalize()
            .map_err(|_| Invalid("project path is unavailable"))?;
        if !project.is_dir() {
            return Err(Invalid("project must be a directory"));
        }
        let instructions = instructions(&project)?;
        let mode = self.mode.as_deref().unwrap_or(&config.mode);
        let key_name = config.key_name(mode)?.map(str::to_owned);
        let runtime = if mode == "cloud-only" {
            match config.native.as_ref() {
                Some(native) if native.target == "claude" => RuntimeKind::Claude,
                _ => RuntimeKind::OpenCode,
            }
        } else if config.litellm.as_ref().and_then(|l| l.runtime.as_deref()) == Some("pi") {
            if mode != "local-only" {
                return Err(Invalid(
                    "litellm.runtime pi is unsupported with local-first and cloud-only overrides",
                ));
            }
            RuntimeKind::Pi
        } else {
            RuntimeKind::OpenCode
        };
        let agent = self
            .agent
            .as_deref()
            .map(|name| Agent::select(&project, name))
            .transpose()?;
        let verify = match &self.verify {
            None => None,
            Some(name) => {
                let definition = config
                    .checks
                    .as_ref()
                    .and_then(|checks| checks.0.get(name))
                    .ok_or(Invalid(
                        "verification check is not defined in config checks",
                    ))?;
                let scrub = [
                    config.litellm.as_ref().map(|l| l.api_key_env.clone()),
                    config.native.as_ref().and_then(|n| n.api_key_env.clone()),
                ]
                .into_iter()
                .flatten()
                .collect();
                Some(definition.resolve(name, &project, key_lookup("PATH"), scrub)?)
            }
        };
        let agent_model = |native: bool| {
            let models = agent.as_ref().and_then(Agent::models)?;
            if native {
                models.native.clone()
            } else {
                models.local.clone()
            }
        };
        // Precedence per route: --model, then the agent's route model, then
        // config. `--model` selects only the LiteLLM primary; fallback uses the
        // agent's native model, else native.model.
        let fallback = (mode == "local-first")
            .then_some(config.native.as_ref())
            .flatten()
            .map(|native| {
                let agent = agent_model(true);
                let source = if agent.is_some() {
                    Source::Agent
                } else {
                    Source::Config
                };
                (
                    agent.unwrap_or_else(|| native.model.clone()),
                    native.api_key_env.clone(),
                    source,
                    if native.target == "claude" {
                        RuntimeKind::Claude
                    } else {
                        RuntimeKind::OpenCode
                    },
                )
            });
        let route_agent = agent_model(mode == "cloud-only");
        let model_source = if self.model.is_some() {
            Source::Invocation
        } else if route_agent.is_some() {
            Source::Agent
        } else {
            Source::Config
        };
        let model = self
            .model
            .clone()
            .or(route_agent)
            .or_else(|| {
                if mode == "cloud-only" {
                    config.native.as_ref().map(|native| native.model.clone())
                } else {
                    config.model.clone()
                }
            })
            .ok_or(Invalid(
                "selected route requires a model default or explicit --model",
            ))?;
        // Groups are LiteLLM routing choices; a native route never reinterprets one.
        let (group, model) = match group_name(&model) {
            Some(_) if mode == "cloud-only" => {
                return Err(Invalid("model groups apply only to the LiteLLM route"));
            }
            Some(name) => (Some(name.to_owned()), config.group(name)?.to_owned()),
            None => (None, model),
        };
        let mode = if mode == "cloud-only" {
            Mode::CloudOnly
        } else {
            Mode::LocalOnly
        };
        for name in key_name
            .iter()
            .chain(fallback.as_ref().and_then(|(_, key, _, _)| key.as_ref()))
        {
            if key_lookup(name).is_none_or(|key| key.is_empty()) {
                return Err(Invalid(MISSING_KEY));
            }
        }
        let prompt = match self.prompt {
            PromptSource::Inline(text) => bounded(text.as_bytes())?,
            PromptSource::File(path) => bounded(open_regular_file(&path)?)?,
            PromptSource::Stdin => bounded(stdin)?,
        };
        if prompt.trim().is_empty() {
            return Err(Invalid("prompt must not be empty"));
        }
        let source = |overridden| {
            if overridden {
                Source::Invocation
            } else {
                Source::Config
            }
        };
        let sources = Sources {
            mode: source(self.mode.is_some()),
            model: model_source,
            permissions: if self.permissions.is_some() {
                Source::Invocation
            } else if config.permissions.is_some() {
                Source::Config
            } else {
                Source::Default
            },
            timeout: if self.timeout_secs.is_some() {
                Source::Invocation
            } else if config.timeout_secs.is_some() {
                Source::Config
            } else {
                Source::Default
            },
        };
        let mut resolved = Resolved {
            mode,
            sources,
            project,
            model,
            group,
            proxy_groups: match (
                mode,
                config.litellm.as_ref().and_then(|l| l.groups.as_ref()),
            ) {
                (Mode::LocalOnly, Some(groups)) => groups
                    .0
                    .values()
                    .cloned()
                    .collect::<std::collections::BTreeSet<_>>()
                    .into_iter()
                    .collect(),
                _ => Vec::new(),
            },
            api_base: if mode == Mode::LocalOnly {
                config.litellm.map(|v| v.api_base)
            } else {
                None
            },
            api_key_env: key_name,
            runtime,
            permissions: self.permissions.or(config.permissions).unwrap_or_default(),
            timeout_secs: self
                .timeout_secs
                .or(config.timeout_secs)
                .unwrap_or(DEFAULT_TIMEOUT_SECS),
            no_sync: self.no_sync,
            preview: self.preview,
            prompt,
            instructions,
            agent,
            fallback: None,
            verify,
        };
        if let Some((model, api_key_env, model_source, runtime)) = fallback {
            resolved.fallback = Some(Box::new(Resolved {
                mode: Mode::CloudOnly,
                sources: Sources {
                    model: model_source,
                    ..resolved.sources
                },
                project: resolved.project.clone(),
                model,
                group: None,
                proxy_groups: Vec::new(),
                api_base: None,
                api_key_env,
                runtime,
                permissions: resolved.permissions,
                timeout_secs: resolved.timeout_secs,
                no_sync: resolved.no_sync,
                preview: resolved.preview,
                prompt: resolved.prompt.clone(),
                instructions: resolved.instructions.clone(),
                agent: resolved.agent.clone(),
                fallback: None,
                verify: None,
            }));
        }
        Ok(resolved)
    }
}

impl Resolved {
    /// Model as the runtime selects it: `PROVIDER/MODEL` for OpenCode, the
    /// alias or full model name for Claude Code.
    pub fn runtime_model(&self) -> String {
        match self.runtime {
            RuntimeKind::Claude => self.model.clone(),
            RuntimeKind::Pi => format!("pi/{}", self.model),
            RuntimeKind::OpenCode => format!(
                "{}/{}",
                if self.mode == Mode::LocalOnly {
                    "ah-litellm"
                } else {
                    "opencode"
                },
                self.model
            ),
        }
    }

    /// Model as workflow records and previews name it (D051): the OpenCode
    /// runtime model, or `claude/MODEL` / `pi/MODEL` so a record names its runtime.
    pub fn record_model(&self) -> String {
        match self.runtime {
            RuntimeKind::Claude => format!("claude/{}", self.model),
            RuntimeKind::Pi => format!("pi/{}", self.model),
            RuntimeKind::OpenCode => self.runtime_model(),
        }
    }
}
