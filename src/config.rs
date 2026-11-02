//! First-slice input validation. No runtime launch, configuration writes or network I/O.
use serde::Deserialize;
use std::ffi::OsString;
use std::io::Read;
use std::path::{Path, PathBuf};

pub const CONFIG_NAME: &str = "ah.json";
pub const MAX_INPUT_BYTES: u64 = 1_048_576;
pub const DEFAULT_TIMEOUT_SECS: u64 = 1800;

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
    model: String,
    litellm: LiteLlm,
    permissions: Option<Permissions>,
    timeout_secs: Option<u64>,
}

#[derive(Deserialize)]
#[serde(deny_unknown_fields)]
struct LiteLlm {
    api_base: String,
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
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Source {
    Invocation,
    Config,
    Default,
}

pub struct Sources {
    pub mode: Source,
    pub model: Source,
    pub permissions: Source,
    pub timeout: Source,
}

pub struct Resolved {
    pub mode: Mode,
    pub sources: Sources,
    pub project: PathBuf,
    pub model: String,
    pub api_base: String,
    pub api_key_env: String,
    pub permissions: Permissions,
    pub timeout_secs: u64,
    pub no_sync: bool,
    pub preview: bool,
    pub prompt: String,
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

impl Config {
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
        validate_model(&self.model)?;
        validate_timeout(self.timeout_secs.unwrap_or(DEFAULT_TIMEOUT_SECS))?;
        let endpoint = url::Url::parse(&self.litellm.api_base)
            .map_err(|_| Invalid("invalid LiteLLM API base"))?;
        if !matches!(endpoint.scheme(), "http" | "https")
            || endpoint.host_str().is_none()
            || !endpoint.username().is_empty()
            || endpoint.password().is_some()
            || endpoint.query().is_some()
            || endpoint.fragment().is_some()
            || endpoint.path() != "/v1"
            || self.litellm.api_base.trim() != self.litellm.api_base
            || self.litellm.api_base.chars().any(char::is_control)
        {
            return Err(Invalid(
                "API base requires http(s), a host, /v1 and no credentials/query/fragment",
            ));
        }
        let name = self.litellm.api_key_env.as_bytes();
        if name.is_empty()
            || !(name[0].is_ascii_alphabetic() || name[0] == b'_')
            || !name.iter().all(|b| b.is_ascii_alphanumeric() || *b == b'_')
        {
            return Err(Invalid("api_key_env must be an environment variable name"));
        }
        Ok(())
    }
}

fn validate_mode(mode: &str) -> Result<()> {
    if mode != "local-only" {
        return Err(Invalid("only local-only is supported in the first slice"));
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
            "model must be a 1–128 byte LiteLLM alias using letters, digits, dot, underscore or hyphen",
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
    /// Parse the selected future `single` interface without exposing a runnable
    /// command before P2.2. Paths are relative to invocation cwd, never project.
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
                        validate_model(value)?;
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
    /// dropped; the resolved request stores only the environment name.
    pub fn resolve(
        self,
        config: Config,
        key_lookup: impl FnOnce(&str) -> Option<OsString>,
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
        if key_lookup(&config.litellm.api_key_env).is_none_or(|key| key.is_empty()) {
            return Err(Invalid("API key environment reference is missing or empty"));
        }
        let prompt = match self.prompt {
            PromptSource::Inline(text) => bounded(text.as_bytes())?,
            PromptSource::File(path) => {
                let mut options = std::fs::OpenOptions::new();
                options.read(true);
                #[cfg(unix)]
                {
                    use std::os::unix::fs::OpenOptionsExt;
                    options.custom_flags(libc::O_NONBLOCK | libc::O_NOCTTY);
                }
                let file = options
                    .open(path)
                    .map_err(|_| Invalid("cannot open prompt file"))?;
                // Inspect the opened handle so a path swap cannot turn a regular
                // file into an accepted stream. Unix nonblocking open avoids FIFO waits.
                if !file
                    .metadata()
                    .map_err(|_| Invalid("cannot inspect prompt file"))?
                    .is_file()
                {
                    return Err(Invalid("prompt path must be a regular file"));
                }
                bounded(file)?
            }
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
        Ok(Resolved {
            mode: Mode::LocalOnly,
            sources,
            project,
            model: self.model.unwrap_or(config.model),
            api_base: config.litellm.api_base,
            api_key_env: config.litellm.api_key_env,
            permissions: self.permissions.or(config.permissions).unwrap_or_default(),
            timeout_secs: self
                .timeout_secs
                .or(config.timeout_secs)
                .unwrap_or(DEFAULT_TIMEOUT_SECS),
            no_sync: self.no_sync,
            preview: self.preview,
            prompt,
        })
    }
}
