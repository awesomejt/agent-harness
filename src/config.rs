//! First-slice input validation. No runtime launch, configuration writes or network I/O.
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
#[derive(Debug, PartialEq, Eq)]
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
#[derive(Deserialize)]
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
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LiteLlm {
    api_base: String,
    api_key_env: String,
    #[serde(default, deserialize_with = "present")]
    groups: Option<Groups>,
}

/// Harness group name -> existing proxy model group. Map deserialization would
/// otherwise keep the last duplicate key silently.
struct Groups(std::collections::BTreeMap<String, String>);
impl<'de> Deserialize<'de> for Groups {
    fn deserialize<D: serde::Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct V;
        impl<'de> serde::de::Visitor<'de> for V {
            type Value = Groups;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("a group object")
            }
            fn visit_map<A: serde::de::MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Groups, A::Error> {
                let mut groups = std::collections::BTreeMap::new();
                while let Some((name, target)) = a.next_entry::<String, String>()? {
                    if groups.insert(name, target).is_some() {
                        return Err(serde::de::Error::custom("duplicate group"));
                    }
                }
                Ok(Groups(groups))
            }
        }
        d.deserialize_map(V)
    }
}

// Optional blocks may be absent but explicit null is not a valid route config.
fn present<'de, D: serde::Deserializer<'de>, T: Deserialize<'de>>(
    d: D,
) -> std::result::Result<Option<T>, D::Error> {
    T::deserialize(d).map(Some)
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct Native {
    target: String,
    model: String,
    api_key_env: String,
}

pub struct Invocation {
    project: PathBuf,
    config: Option<PathBuf>,
    mode: Option<String>,
    model: Option<String>,
    permissions: Option<Permissions>,
    timeout_secs: Option<u64>,
    no_sync: bool,
    preview: bool,
    prompt: PromptSource,
}

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
    pub api_key_env: String,
    pub permissions: Permissions,
    pub timeout_secs: u64,
    pub no_sync: bool,
    pub preview: bool,
    pub prompt: String,
    /// Local-first only: the configured native target, resolved with identical
    /// project, permissions, timeout and prompt. Never nested.
    pub fallback: Option<Box<Resolved>>,
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

fn bounded(mut reader: impl Read) -> Result<String> {
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

fn open_regular_file(path: &Path) -> Result<std::fs::File> {
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
        if let Some(native) = &self.native {
            if native.target != "opencode" {
                return Err(Invalid(
                    "native target must be opencode (built-in API-key provider)",
                ));
            }
            validate_model(&native.model)?;
            validate_key_name(&native.api_key_env)?;
        }
        if self.mode != "cloud-only" && self.model.is_none() {
            return Err(Invalid(
                "local-only and local-first config require a model default",
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
    validate_key_name(&local.api_key_env)
}
fn group_name(reference: &str) -> Option<&str> {
    reference.strip_prefix(GROUP_PREFIX)
}
fn validate_reference(reference: &str) -> Result<()> {
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
    fn key_name(&self, mode: &str) -> Result<&str> {
        let local = self.litellm.as_ref().map(|v| v.api_key_env.as_str());
        let native = self.native.as_ref().map(|v| v.api_key_env.as_str());
        match mode {
            "local-only" => local.ok_or(Invalid("local-only requires litellm configuration")),
            "cloud-only" => native.ok_or(Invalid("cloud-only requires native configuration")),
            "local-first" => native.and(local).ok_or(Invalid(
                "local-first requires litellm and native configuration",
            )),
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
fn validate_model(model: &str) -> Result<()> {
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

impl Invocation {
    /// Parse `single` input without side effects. Paths are relative to
    /// invocation cwd, never project.
    pub fn parse(args: impl IntoIterator<Item = OsString>, cwd: &Path) -> Result<Self> {
        let mut args = args.into_iter();
        if args.next().as_deref() != Some(std::ffi::OsStr::new("single")) {
            return Err(Invalid("expected single command"));
        }
        let mut request = Self {
            project: cwd.to_owned(),
            config: None,
            mode: None,
            model: None,
            permissions: None,
            timeout_secs: None,
            no_sync: false,
            preview: false,
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
                        | "--permissions"
                        | "--timeout-secs"
                        | "--prompt-file"
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
                if prompt.is_some() {
                    return Err(Invalid("conflicting prompt sources"));
                }
                prompt = Some(PromptSource::Inline(arg.to_owned()));
            }
        }
        request.prompt = prompt.ok_or(Invalid("provide inline prompt or --prompt-file PATH|-"))?;
        Ok(request)
    }

    pub fn config_path(&self) -> PathBuf {
        self.config
            .clone()
            .unwrap_or_else(|| self.project.join(CONFIG_NAME))
    }

    /// Checks configuration and credentials before consuming potentially blocking
    /// stdin. The lookup result is checked for nonempty content and immediately
    /// dropped; the resolved request stores only the environment name. Local-first
    /// checks both route keys: its fallback target must be usable before launch.
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
        let mode = self.mode.as_deref().unwrap_or(&config.mode);
        let key_name = config.key_name(mode)?.to_owned();
        // `--model` selects only the LiteLLM primary; fallback uses native.model.
        let fallback = (mode == "local-first")
            .then_some(config.native.as_ref())
            .flatten()
            .map(|native| (native.model.clone(), native.api_key_env.clone()));
        let model = self
            .model
            .clone()
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
        for name in std::iter::once(&key_name).chain(fallback.as_ref().map(|(_, key)| key)) {
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
            model: source(self.model.is_some()),
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
            permissions: self.permissions.or(config.permissions).unwrap_or_default(),
            timeout_secs: self
                .timeout_secs
                .or(config.timeout_secs)
                .unwrap_or(DEFAULT_TIMEOUT_SECS),
            no_sync: self.no_sync,
            preview: self.preview,
            prompt,
            fallback: None,
        };
        if let Some((model, api_key_env)) = fallback {
            resolved.fallback = Some(Box::new(Resolved {
                mode: Mode::CloudOnly,
                sources: Sources {
                    model: Source::Config,
                    ..resolved.sources
                },
                project: resolved.project.clone(),
                model,
                group: None,
                proxy_groups: Vec::new(),
                api_base: None,
                api_key_env,
                permissions: resolved.permissions,
                timeout_secs: resolved.timeout_secs,
                no_sync: resolved.no_sync,
                preview: resolved.preview,
                prompt: resolved.prompt.clone(),
                fallback: None,
            }));
        }
        Ok(resolved)
    }
}

impl Resolved {
    pub fn runtime_model(&self) -> String {
        format!(
            "{}/{}",
            if self.mode == Mode::LocalOnly {
                "ah-litellm"
            } else {
                "opencode"
            },
            self.model
        )
    }
}
