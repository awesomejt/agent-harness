//! Project-only routing plans. Runtime environment isolation and inspection are
//! mandatory adapter gates; a successful disk plan is not execution readiness.
use crate::config::{Invalid, MAX_INPUT_BYTES, Resolved};
use serde::de::{MapAccess, Visitor};
use serde::{Deserialize, Deserializer};
use serde_json::{Value, json, value::RawValue};
use std::collections::BTreeMap;
use std::fs::{self, File, OpenOptions};
use std::io::{Read, Write};
use std::path::{Path, PathBuf};

const CONFIG: &str = "opencode.json";
const OWNER: &str = ".ah-opencode-owner.json";
const LOCK: &str = ".ah-opencode.lock";
const AGENTS: &str = ".ah-opencode-agents.json";
const AGENT_DIR: &str = ".opencode/agents";
const PROVIDER: &str = "ah-litellm";
type Result<T> = std::result::Result<T, Invalid>;

// Borrow raw values to replace managed spans without reformatting other fields.
struct Object<'a>(BTreeMap<String, &'a RawValue>);
impl<'de> Deserialize<'de> for Object<'de> {
    fn deserialize<D: Deserializer<'de>>(d: D) -> std::result::Result<Self, D::Error> {
        struct V;
        impl<'de> Visitor<'de> for V {
            type Value = Object<'de>;
            fn expecting(&self, f: &mut std::fmt::Formatter) -> std::fmt::Result {
                f.write_str("a strict JSON object")
            }
            fn visit_map<A: MapAccess<'de>>(
                self,
                mut a: A,
            ) -> std::result::Result<Self::Value, A::Error> {
                let mut fields = BTreeMap::new();
                while let Some((key, value)) = a.next_entry::<String, &'de RawValue>()? {
                    if fields.insert(key, value).is_some() {
                        return Err(serde::de::Error::custom("duplicate field"));
                    }
                }
                Ok(Object(fields))
            }
        }
        d.deserialize_map(V)
    }
}
fn object(text: &str) -> Result<Object<'_>> {
    // Check duplicates recursively as well, including unmanaged content.
    fn check(raw: &RawValue) -> Result<()> {
        let s = raw.get();
        if s.starts_with('{') {
            for v in serde_json::from_str::<Object<'_>>(s)
                .map_err(|_| {
                    Invalid("project config must be strict JSON without duplicate fields")
                })?
                .0
                .values()
            {
                check(v)?;
            }
        } else if s.starts_with('[') {
            for v in serde_json::from_str::<Vec<&RawValue>>(s)
                .map_err(|_| Invalid("invalid project array"))?
            {
                check(v)?;
            }
        }
        Ok(())
    }
    let raw: &RawValue = serde_json::from_str(text)
        .map_err(|_| Invalid("project config must be strict JSON; convert JSONC manually"))?;
    // serde_json enforces a recursion limit during typed parsing; cap raw nesting
    // before recursive traversal, whose RawValue parser otherwise skips depth.
    let _: Value = serde_json::from_str(text)
        .map_err(|_| Invalid("invalid or excessively nested project config"))?;
    check(raw)?;
    serde_json::from_str(text).map_err(|_| Invalid("project config must be a JSON object"))
}
fn snapshot(path: &Path) -> Result<Option<String>> {
    let metadata = match fs::symlink_metadata(path) {
        Ok(m) => m,
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => return Ok(None),
        Err(_) => return Err(Invalid("cannot inspect project transaction file")),
    };
    if !metadata.is_file() {
        return Err(Invalid(
            "project transaction files must be regular, not symlinked",
        ));
    }
    let mut opts = OpenOptions::new();
    opts.read(true);
    #[cfg(unix)]
    {
        use std::os::unix::fs::OpenOptionsExt;
        opts.custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK);
    }
    let file = opts
        .open(path)
        .map_err(|_| Invalid("cannot open project transaction file"))?;
    if !file
        .metadata()
        .map_err(|_| Invalid("cannot inspect project file"))?
        .is_file()
    {
        return Err(Invalid("project file is not regular"));
    }
    let mut s = String::new();
    file.take(MAX_INPUT_BYTES + 1)
        .read_to_string(&mut s)
        .map_err(|_| Invalid("cannot read project JSON"))?;
    if s.len() as u64 > MAX_INPUT_BYTES {
        return Err(Invalid("project JSON exceeds 1 MiB"));
    }
    Ok(Some(s))
}
fn desired(r: &Resolved) -> BTreeMap<String, Value> {
    let model = format!("{PROVIDER}/{}", r.model);
    BTreeMap::from([
        ("model".into(), json!(model)),
        ("small_model".into(), json!(model)),
        ("enabled_providers".into(), json!([PROVIDER])),
        (
            "provider".into(),
            json!({PROVIDER: {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": r.api_base, "apiKey": format!("{{env:{}}}", r.api_key_env.as_deref().unwrap_or_default())}, "models": {&r.model: {"name": r.model}}}}),
        ),
    ])
}
fn values(text: &str) -> Result<BTreeMap<String, Value>> {
    object(text)?
        .0
        .into_iter()
        .map(|(k, v)| {
            Ok((
                k,
                serde_json::from_str(v.get()).map_err(|_| Invalid("invalid project value"))?,
            ))
        })
        .collect()
}

fn exists(path: &Path) -> Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(_) => Ok(true),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(_) => Err(Invalid("cannot inspect alternate project config")),
    }
}
fn managed_value(key: &str, value: Option<&Value>) -> Result<Option<Value>> {
    if key != "provider" {
        return Ok(value.cloned());
    }
    match value {
        None => Ok(None),
        Some(v) => {
            let providers = v.as_object().ok_or(Invalid("provider must be an object"))?;
            Ok(providers.get(PROVIDER).map(|p| json!({PROVIDER:p})))
        }
    }
}
fn patch(source: &str, wanted: &BTreeMap<String, Value>) -> Result<String> {
    let fields = object(source)?.0;
    let mut after = source.to_owned();
    let mut replacements = Vec::new();
    let mut added = Vec::new();
    for (k, v) in wanted {
        let serialized = if k == "provider" && fields.contains_key(k) {
            let children: BTreeMap<String, Value> = serde_json::from_value(v.clone()).unwrap();
            patch(fields[k].get(), &children)?
        } else {
            serde_json::to_string(v).unwrap()
        };
        if let Some(raw) = fields.get(k) {
            let start = raw.get().as_ptr() as usize - source.as_ptr() as usize;
            replacements.push((start, start + raw.get().len(), serialized));
        } else {
            added.push(format!(
                "{}:{serialized}",
                serde_json::to_string(k).unwrap()
            ));
        }
    }
    replacements.sort_by_key(|r| std::cmp::Reverse(r.0));
    for (start, end, value) in replacements {
        after.replace_range(start..end, &value);
    }
    if !added.is_empty() {
        let end = after.rfind('}').unwrap();
        let prefix = if fields.is_empty() { "" } else { "," };
        after.insert_str(end, &format!("{prefix}\n{}\n", added.join(",\n")));
    }
    Ok(after)
}

/// Real directory or absent; a symlink or other file type refuses.
fn directory(path: &Path) -> Result<bool> {
    match fs::symlink_metadata(path) {
        Ok(m) if m.is_dir() => Ok(true),
        Ok(_) => Err(Invalid(
            "OpenCode project directories must be real, not symlinked",
        )),
        Err(e) if e.kind() == std::io::ErrorKind::NotFound => Ok(false),
        Err(_) => Err(Invalid("cannot inspect OpenCode project directory")),
    }
}

/// Every project source OpenCode 2.2.5 loads agents from (D037). Names compare
/// case-insensitively: a case-insensitive filesystem would otherwise overwrite
/// a differently spelled user file. Only the exact emitted path is exempt; its
/// ownership is decided by the receipt. Global/user sources are never read.
fn collisions(project: &Path, name: &str) -> Result<()> {
    const CONFLICT: Invalid =
        Invalid("user-owned OpenCode agent definition conflicts with the canonical name");
    let file = format!("{name}.md");
    directory(&project.join(".opencode"))?;
    for dir in [AGENT_DIR, ".opencode/agent"] {
        if !directory(&project.join(dir))? {
            continue;
        }
        for entry in
            fs::read_dir(project.join(dir)).map_err(|_| Invalid("cannot list OpenCode agents"))?
        {
            let entry = entry
                .map_err(|_| Invalid("cannot list OpenCode agents"))?
                .file_name();
            let exact = dir == AGENT_DIR && entry == file.as_str();
            if !exact && entry.to_str().is_none_or(|e| e.eq_ignore_ascii_case(&file)) {
                return Err(CONFLICT);
            }
        }
    }
    if exists(&project.join(".opencode/opencode.jsonc"))? {
        return Err(Invalid(
            "opencode.jsonc requires manual migration before sync",
        ));
    }
    for config in [CONFIG, ".opencode/opencode.json"] {
        let Some(text) = snapshot(&project.join(config))? else {
            continue;
        };
        let fields = values(&text)?;
        for key in ["agent", "agents"] {
            let Some(agents) = fields.get(key) else {
                continue;
            };
            let agents = agents
                .as_object()
                .ok_or(Invalid("cannot verify OpenCode agent names"))?;
            if agents.keys().any(|k| k.eq_ignore_ascii_case(name)) {
                return Err(CONFLICT);
            }
        }
    }
    Ok(())
}

fn receipt(text: Option<&str>) -> Result<BTreeMap<String, String>> {
    const INVALID: Invalid = Invalid("invalid agent ownership receipt");
    let Some(text) = text else {
        return Ok(BTreeMap::new());
    };
    values(text)
        .map_err(|_| INVALID)?
        .into_iter()
        .map(|(name, content)| match content {
            Value::String(content) if crate::agents::validate_name(&name).is_ok() => {
                Ok((name, content))
            }
            _ => Err(INVALID),
        })
        .collect()
}

/// Selected agent's project file plus a receipt holding the exact content
/// the harness last wrote for each owned name. Only an unchanged owned file is
/// replaced; a missing file is (re)created. Other owned entries stay as-is.
struct Emission {
    name: String,
    before: Option<String>,
    receipt_before: Option<String>,
    after: String,
    receipt_after: String,
}
impl Emission {
    fn prepare(project: &Path, r: &Resolved, agent: &crate::agents::Agent) -> Result<Self> {
        let name = agent.name().to_owned();
        collisions(project, &name)?;
        let before = snapshot(&project.join(agent.opencode_path()))?;
        let receipt_before = snapshot(&project.join(AGENTS))?;
        let mut owned = receipt(receipt_before.as_deref())?;
        if let Some(current) = &before {
            match owned.get(&name) {
                Some(old) if old == current => {}
                Some(_) => {
                    return Err(Invalid(
                        "managed agent file was manually edited; reconcile agent ownership receipt",
                    ));
                }
                None => {
                    return Err(Invalid(
                        "user-owned OpenCode agent file conflicts with the canonical name",
                    ));
                }
            }
        }
        let after = crate::opencode::agent_markdown(agent, r);
        owned.insert(name.clone(), after.clone());
        let receipt_after = serde_json::to_string(&owned).unwrap();
        if after.len() as u64 > MAX_INPUT_BYTES || receipt_after.len() as u64 > MAX_INPUT_BYTES {
            return Err(Invalid("planned agent emission exceeds 1 MiB"));
        }
        Ok(Self {
            name,
            before,
            receipt_before,
            after,
            receipt_after,
        })
    }
    fn path(&self) -> PathBuf {
        Path::new(AGENT_DIR).join(format!("{}.md", self.name))
    }
    fn file_changes(&self) -> bool {
        self.before.as_deref() != Some(&self.after)
    }
    fn receipt_changes(&self) -> bool {
        self.receipt_before.as_deref() != Some(&self.receipt_after)
    }
}

pub struct Plan {
    project: PathBuf,
    before: Option<String>,
    owner_before: Option<String>,
    after: String,
    owner_after: String,
    no_sync: bool,
    agent: Option<Emission>,
}
impl Plan {
    /// Read-only; never consults HOME, environment values or global settings.
    pub fn prepare(r: &Resolved) -> Result<Self> {
        if r.mode != crate::config::Mode::LocalOnly
            || r.api_base.is_none()
            || r.api_key_env.is_none()
        {
            return Err(Invalid("managed LiteLLM plan requires local-only routing"));
        }
        let project = r
            .project
            .canonicalize()
            .map_err(|_| Invalid("invalid project directory"))?;
        if !project.is_dir() {
            return Err(Invalid("invalid project directory"));
        }
        if exists(&project.join("opencode.jsonc"))? {
            return Err(Invalid(
                "opencode.jsonc requires manual migration before sync",
            ));
        }
        let before = snapshot(&project.join(CONFIG))?;
        let owner_before = snapshot(&project.join(OWNER))?;
        let source = before.as_deref().unwrap_or("{}");
        let fields = object(source)?.0;
        let wanted = desired(r);
        let old = owner_before.as_deref().map(values).transpose()?;
        if old
            .as_ref()
            .is_some_and(|o| o.len() != wanted.len() || !wanted.keys().all(|k| o.contains_key(k)))
        {
            return Err(Invalid("invalid project ownership receipt"));
        }
        for (k, v) in &wanted {
            let raw = fields
                .get(k)
                .map(|raw| serde_json::from_str::<Value>(raw.get()).unwrap());
            let current = managed_value(k, raw.as_ref())?;
            if r.no_sync {
                if current.as_ref() != Some(v) {
                    return Err(Invalid(
                        "no-sync project route differs from requested route",
                    ));
                }
            } else if let Some(old) = &old {
                if current.as_ref() != old.get(k) {
                    return Err(Invalid(
                        "managed project field was manually edited; reconcile ownership receipt",
                    ));
                }
            } else if current.is_some() {
                return Err(Invalid(
                    "user-owned routing field conflicts; move it or use exact no-sync configuration",
                ));
            }
        }
        let after = patch(source, &wanted)?;
        if after.len() as u64 > MAX_INPUT_BYTES {
            return Err(Invalid("planned project config exceeds 1 MiB"));
        }
        let owner_after = serde_json::to_string(&wanted).unwrap();
        // No-sync writes nothing; the isolated runtime never loads this file.
        let agent = match &r.agent {
            Some(agent) if !r.no_sync => Some(Emission::prepare(&project, r, agent)?),
            _ => None,
        };
        Ok(Self {
            project,
            before,
            owner_before,
            after,
            owner_after,
            no_sync: r.no_sync,
            agent,
        })
    }
    fn routing_changes(&self) -> bool {
        self.before.as_deref() != Some(&self.after)
            || self.owner_before.as_deref() != Some(&self.owner_after)
    }
    pub fn needs_write(&self) -> bool {
        !self.no_sync
            && (self.routing_changes()
                || self
                    .agent
                    .as_ref()
                    .is_some_and(|a| a.file_changes() || a.receipt_changes()))
    }
    /// Field names and the validated agent name only: never old user values,
    /// agent content or credentials.
    pub fn preview_changes(&self) -> Vec<String> {
        let mut changes = Vec::new();
        if !self.no_sync {
            if self.before.as_deref() != Some(&self.after) {
                changes.push(
                    "opencode.json: provider.ah-litellm, enabled_providers, model, small_model"
                        .into(),
                );
            }
            if self.owner_before.as_deref() != Some(&self.owner_after) {
                changes.push(".ah-opencode-owner.json: managed routing receipt".into());
            }
        }
        if let Some(agent) = &self.agent {
            if agent.file_changes() {
                changes.push(format!(
                    "{AGENT_DIR}/{}.md: emitted agent (native frontmatter, ceiling rules)",
                    agent.name
                ));
            }
            if agent.receipt_changes() {
                changes.push(format!("{AGENTS}: managed agent receipt"));
            }
        }
        changes
    }
    /// Atomic file replacement under a nonblocking advisory lock; stale plans
    /// reject. A crash between config and receipt is a visible ownership conflict.
    pub fn apply(self) -> Result<()> {
        if self.no_sync {
            return Ok(());
        }
        #[cfg(not(unix))]
        {
            return Err(Invalid("project transactions currently require Unix"));
        }
        #[cfg(unix)]
        {
            use std::os::fd::AsRawFd;
            use std::os::unix::fs::OpenOptionsExt;
            let lock = OpenOptions::new()
                .read(true)
                .write(true)
                .create(true)
                .truncate(false)
                .mode(0o600)
                .custom_flags(libc::O_NOFOLLOW | libc::O_NONBLOCK)
                .open(self.project.join(LOCK))
                .map_err(|_| Invalid("cannot open project transaction lock"))?;
            if !lock
                .metadata()
                .map_err(|_| Invalid("cannot inspect lock"))?
                .is_file()
            {
                return Err(Invalid("invalid project transaction lock"));
            }
            if unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) } != 0 {
                return Err(Invalid("project transaction is busy"));
            }
            if snapshot(&self.project.join(CONFIG))? != self.before
                || snapshot(&self.project.join(OWNER))? != self.owner_before
                || exists(&self.project.join("opencode.jsonc"))?
            {
                return Err(Invalid("project config changed since planning; re-plan"));
            }
            if let Some(agent) = &self.agent {
                collisions(&self.project, &agent.name)?;
                if snapshot(&self.project.join(agent.path()))? != agent.before
                    || snapshot(&self.project.join(AGENTS))? != agent.receipt_before
                {
                    return Err(Invalid("project agents changed since planning; re-plan"));
                }
            }
            if !self.needs_write() {
                return Ok(());
            }
            let sync = |dir: &Path| {
                File::open(dir).and_then(|f| f.sync_all()).map_err(|_| {
                    Invalid("cannot sync project directory; inspect transaction state")
                })
            };
            if self.routing_changes() {
                replace(&self.project, CONFIG, &self.after)?;
                replace(&self.project, OWNER, &self.owner_after)?;
            }
            if let Some(agent) = self.agent.as_ref().filter(|a| a.file_changes()) {
                // A crash before the receipt leaves a visible ownership conflict.
                for dir in [".opencode", AGENT_DIR] {
                    let path = self.project.join(dir);
                    match fs::create_dir(&path) {
                        Ok(()) => sync(path.parent().unwrap())?,
                        Err(e) if e.kind() == std::io::ErrorKind::AlreadyExists => {}
                        Err(_) => return Err(Invalid("cannot create OpenCode agent directory")),
                    }
                    if !directory(&path)? {
                        return Err(Invalid("cannot create OpenCode agent directory"));
                    }
                }
                let dir = self.project.join(AGENT_DIR);
                replace(&dir, &format!("{}.md", agent.name), &agent.after)?;
                sync(&dir)?;
            }
            if let Some(agent) = self.agent.as_ref().filter(|a| a.receipt_changes()) {
                replace(&self.project, AGENTS, &agent.receipt_after)?;
            }
            sync(&self.project)?;
            Ok(())
        }
    }
}
#[cfg(unix)]
fn replace(project: &Path, name: &str, content: &str) -> Result<()> {
    use std::os::unix::fs::OpenOptionsExt;
    use std::sync::atomic::{AtomicU64, Ordering};
    static NEXT: AtomicU64 = AtomicU64::new(0);
    let temp = project.join(format!(
        ".ah-write-{}-{}",
        std::process::id(),
        NEXT.fetch_add(1, Ordering::Relaxed)
    ));
    let mut file = OpenOptions::new()
        .write(true)
        .create_new(true)
        .mode(0o600)
        .open(&temp)
        .map_err(|_| Invalid("cannot stage project transaction"))?;
    let result = (|| {
        if name == CONFIG {
            if let Ok(metadata) = fs::metadata(project.join(name)) {
                file.set_permissions(metadata.permissions())
                    .map_err(|_| Invalid("cannot preserve project config permissions"))?;
            }
        }
        file.write_all(content.as_bytes())
            .and_then(|_| file.sync_all())
            .map_err(|_| Invalid("cannot flush project transaction"))?;
        fs::rename(&temp, project.join(name))
            .map_err(|_| Invalid("cannot replace project file; inspect transaction state"))
    })();
    let _ = fs::remove_file(&temp);
    result
}
