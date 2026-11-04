//! Canonical agent schema and name-based selection. Parsing is separate from
//! project emission (`project_config`) and runtime capability checks (P4.3).
use crate::config::{self, Invalid};
use serde::Deserialize;
use std::collections::{BTreeMap, HashSet};
use std::io::Read;
use std::path::{Path, PathBuf};

pub const MAX_FRONTMATTER_BYTES: usize = 16_384;
pub const MAX_AGENTS: usize = 64;
type Result<T> = std::result::Result<T, Invalid>;

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Capacity {
    Primary,
    Specialized,
    Both,
}

/// A ceiling, never a grant. P4.3 must intersect it with invocation permissions.
#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Permissions {
    Deny,
    ReadOnly,
    Trusted,
}

#[derive(Clone, Copy, Debug, Deserialize, PartialEq, Eq, Hash)]
#[serde(rename_all = "kebab-case")]
pub enum Tool {
    Read,
    Search,
    Edit,
    Execute,
}

/// Non-default values are requirements, not a promise of backend support.
#[derive(Clone, Copy, Debug, Default, Deserialize, PartialEq, Eq)]
#[serde(rename_all = "kebab-case")]
pub enum Effort {
    #[default]
    Default,
    Low,
    Medium,
    High,
    Max,
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
pub struct Models {
    #[serde(default, deserialize_with = "present_text")]
    pub local: Option<String>,
    #[serde(default, deserialize_with = "present_text")]
    pub native: Option<String>,
}

fn present<'de, D: serde::Deserializer<'de>, T: Deserialize<'de>>(
    d: D,
) -> std::result::Result<Option<T>, D::Error> {
    T::deserialize(d).map(Some)
}

// YAML's deserialize_string coerces null/numbers/booleans into strings. Route
// aliases, names and descriptions must be actual string scalars.
fn text<'de, D: serde::Deserializer<'de>>(d: D) -> std::result::Result<String, D::Error> {
    struct V;
    impl serde::de::Visitor<'_> for V {
        type Value = String;
        fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
            f.write_str("a string scalar")
        }
        fn visit_str<E: serde::de::Error>(self, value: &str) -> std::result::Result<String, E> {
            Ok(value.to_owned())
        }
    }
    d.deserialize_any(V)
}
pub(crate) fn present_text<'de, D: serde::Deserializer<'de>>(
    d: D,
) -> std::result::Result<Option<String>, D::Error> {
    text(d).map(Some)
}

#[derive(Clone, Deserialize)]
#[serde(deny_unknown_fields)]
struct Header {
    version: u8,
    #[serde(deserialize_with = "text")]
    name: String,
    #[serde(deserialize_with = "text")]
    description: String,
    capacity: Capacity,
    permissions: Permissions,
    tools: Vec<Tool>,
    #[serde(default, deserialize_with = "present")]
    models: Option<Models>,
    #[serde(default)]
    effort: Effort,
}

// No Debug/Serialize: agent instructions and model choices may contain private
// content. Errors are static; callers choose what to disclose in previews.
#[derive(Clone)]
pub struct Agent {
    header: Header,
    body: String,
    /// SHA-256 of the definition's bytes, for sequence records (D044).
    sha256: String,
}

impl Agent {
    /// Library parser for caller-owned readers; application file loading uses
    /// `open` to reject streams/devices and bind the filename to the name.
    pub fn read(reader: impl Read) -> Result<Self> {
        let text = config::bounded(reader)?;
        let mut lines = text.split_inclusive('\n');
        if lines.next().map(line) != Some("---") {
            return Err(Invalid("agent requires opening YAML frontmatter delimiter"));
        }
        let start = text
            .find('\n')
            .ok_or(Invalid("agent frontmatter is incomplete"))?
            + 1;
        let mut end = start;
        let mut body_start = None;
        for raw in lines {
            if line(raw) == "---" {
                body_start = Some(end + raw.len());
                break;
            }
            end += raw.len();
            if end - start > MAX_FRONTMATTER_BYTES {
                return Err(Invalid("agent frontmatter exceeds 16 KiB"));
            }
        }
        let body_start = body_start.ok_or(Invalid("agent frontmatter is incomplete"))?;
        // Typed YAML enum/number deserializers can accept tagged encodings.
        // Reject custom tags throughout the bounded document before decoding
        // the strict struct. Still decode directly below to retain duplicate
        // field rejection, independent of the intermediate mapping behavior.
        let value: serde_yaml_ng::Value = serde_yaml_ng::from_str(&text[start..end])
            .map_err(|_| Invalid("invalid agent: expected version-1 YAML schema"))?;
        if has_tag(&value) {
            return Err(Invalid("agent YAML tags are unsupported"));
        }
        // Deserialize directly, never via a YAML Value/map that could discard
        // duplicate fields. Never surface YAML diagnostics containing input.
        let header: Header = serde_yaml_ng::from_str(&text[start..end])
            .map_err(|_| Invalid("invalid agent: expected version-1 YAML schema"))?;
        validate_header(&header)?;
        let body = &text[body_start..];
        if body.trim().is_empty()
            || body
                .chars()
                .any(|c| c.is_control() && !matches!(c, '\n' | '\r' | '\t'))
        {
            return Err(Invalid("agent Markdown body must be nonempty text"));
        }
        Ok(Self {
            header,
            body: body.to_owned(),
            sha256: crate::state::sha256(text.as_bytes()),
        })
    }

    /// Only a flat NAME.md input is valid; symlinks are refused. No directory
    /// discovery, project writes or backend calls occur here.
    pub fn open(path: &Path) -> Result<Self> {
        if path
            .components()
            .any(|c| matches!(c, std::path::Component::ParentDir))
            || std::fs::symlink_metadata(path)
                .map_err(|_| Invalid("cannot inspect agent file"))?
                .file_type()
                .is_symlink()
        {
            return Err(Invalid("agent path must not traverse or be a symlink"));
        }
        let mut options = std::fs::OpenOptions::new();
        options.read(true);
        #[cfg(unix)]
        {
            use std::os::unix::fs::OpenOptionsExt;
            options.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK | libc::O_NOCTTY);
        }
        let file = options
            .open(path)
            .map_err(|_| Invalid("cannot open agent file"))?;
        if !file
            .metadata()
            .map_err(|_| Invalid("cannot inspect agent file"))?
            .is_file()
        {
            return Err(Invalid("agent path must be a regular file"));
        }
        let agent = Self::read(file)?;
        if path.file_name().and_then(|v| v.to_str()) != Some(&format!("{}.md", agent.name())) {
            return Err(Invalid("agent filename must match canonical name"));
        }
        Ok(agent)
    }

    pub fn name(&self) -> &str {
        &self.header.name
    }
    pub fn description(&self) -> &str {
        &self.header.description
    }
    pub fn capacity(&self) -> Capacity {
        self.header.capacity
    }
    pub fn permissions(&self) -> Permissions {
        self.header.permissions
    }
    pub fn tools(&self) -> &[Tool] {
        &self.header.tools
    }
    pub fn models(&self) -> Option<&Models> {
        self.header.models.as_ref()
    }
    pub fn effort(&self) -> Effort {
        self.header.effort
    }
    pub fn body(&self) -> &str {
        &self.body
    }
    pub fn sha256(&self) -> &str {
        &self.sha256
    }

    /// Relative project destination for the conflict-aware transaction.
    /// Runtime execution instead uses the native `agents.NAME` document entry.
    pub fn opencode_path(&self) -> PathBuf {
        Path::new(".opencode/agents").join(format!("{}.md", self.name()))
    }

    /// Load one canonical definition by name from `PROJECT/agents/`. The
    /// directory must be real (not a symlink) and contain exactly `NAME.md`;
    /// a case-insensitive filesystem match on another spelling is refused.
    /// Other definitions are not parsed, so they cannot affect this selection.
    pub fn select(project: &Path, name: &str) -> Result<Self> {
        validate_name(name)?;
        let dir = project.join("agents");
        match std::fs::symlink_metadata(&dir) {
            Ok(m) if m.is_dir() => {}
            Ok(_) => return Err(Invalid("project agents path must be a real directory")),
            Err(e) if e.kind() == std::io::ErrorKind::NotFound => {
                return Err(Invalid("agent is not defined in project agents/"));
            }
            Err(_) => return Err(Invalid("cannot inspect project agents directory")),
        }
        let file = format!("{name}.md");
        let mut found = false;
        for entry in std::fs::read_dir(&dir).map_err(|_| Invalid("cannot list project agents"))? {
            let entry = entry.map_err(|_| Invalid("cannot list project agents"))?;
            let entry = entry.file_name();
            if entry == file.as_str() {
                found = true;
            } else if entry
                .to_str()
                .is_some_and(|e| e.eq_ignore_ascii_case(&file))
            {
                return Err(Invalid("agent filename must match canonical name exactly"));
            }
        }
        if !found {
            return Err(Invalid("agent is not defined in project agents/"));
        }
        Self::open(&dir.join(file))
    }
}

pub(crate) fn line(raw: &str) -> &str {
    let raw = raw.strip_suffix('\n').unwrap_or(raw);
    raw.strip_suffix('\r').unwrap_or(raw)
}

pub(crate) fn has_tag(value: &serde_yaml_ng::Value) -> bool {
    use serde_yaml_ng::Value;
    match value {
        Value::Tagged(_) => true,
        Value::Sequence(items) => items.iter().any(has_tag),
        Value::Mapping(items) => items.iter().any(|(k, v)| has_tag(k) || has_tag(v)),
        _ => false,
    }
}

fn validate_header(h: &Header) -> Result<()> {
    if h.version != 1 {
        return Err(Invalid("unsupported agent version"));
    }
    validate_name(&h.name)?;
    if h.description.is_empty()
        || h.description.len() > 512
        || h.description.trim() != h.description
        || h.description
            .chars()
            .any(|c| c.is_control() || matches!(c, '\u{2028}' | '\u{2029}'))
    {
        return Err(Invalid(
            "agent description must be 1–512 bytes of single-line text",
        ));
    }
    let mut seen = HashSet::new();
    if h.tools.iter().any(|tool| !seen.insert(tool)) {
        return Err(Invalid("duplicate agent tool"));
    }
    if (h.permissions == Permissions::Deny && !h.tools.is_empty())
        || (h.permissions == Permissions::ReadOnly
            && h.tools
                .iter()
                .any(|t| matches!(t, Tool::Edit | Tool::Execute)))
    {
        return Err(Invalid("agent tools exceed permission ceiling"));
    }
    if let Some(models) = &h.models {
        if models.local.is_none() && models.native.is_none() {
            return Err(Invalid("agent models requires local or native"));
        }
        if let Some(local) = &models.local {
            config::validate_reference(local)?;
        }
        if let Some(native) = &models.native {
            config::validate_model(native)?;
        }
    }
    Ok(())
}

pub fn validate_name(name: &str) -> Result<()> {
    if name.is_empty()
        || name.len() > 64
        || !name.as_bytes()[0].is_ascii_lowercase()
        || name.ends_with('-')
        || name.contains("--")
        || !name
            .bytes()
            .all(|b| b.is_ascii_lowercase() || b.is_ascii_digit() || b == b'-')
    {
        return Err(Invalid(
            "agent name requires 1–64 lowercase letters/digits with single hyphens",
        ));
    }
    if [
        "build",
        "plan",
        "general",
        "explore",
        "compaction",
        "title",
        "summary",
    ]
    .contains(&name)
    {
        return Err(Invalid("agent name is reserved by OpenCode"));
    }
    Ok(())
}

/// Deterministic name-based collection; duplicate definitions never override.
pub struct Catalog(BTreeMap<String, Agent>);
impl Catalog {
    pub fn new(agents: impl IntoIterator<Item = Agent>) -> Result<Self> {
        let mut entries = BTreeMap::new();
        for agent in agents {
            if entries.len() == MAX_AGENTS {
                return Err(Invalid("agent catalog exceeds 64 entries"));
            }
            if entries.insert(agent.name().to_owned(), agent).is_some() {
                return Err(Invalid("duplicate canonical agent name"));
            }
        }
        Ok(Self(entries))
    }
    pub fn get(&self, name: &str) -> Option<&Agent> {
        self.0.get(name)
    }
    pub fn iter(&self) -> impl Iterator<Item = &Agent> {
        self.0.values()
    }
}
