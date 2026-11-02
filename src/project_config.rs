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
            json!({PROVIDER: {"npm": "@ai-sdk/openai-compatible", "options": {"baseURL": r.api_base, "apiKey": format!("{{env:{}}}", r.api_key_env)}, "models": {&r.model: {"name": r.model}}}}),
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

pub struct Plan {
    project: PathBuf,
    before: Option<String>,
    owner_before: Option<String>,
    after: String,
    owner_after: String,
    desired: BTreeMap<String, Value>,
    no_sync: bool,
}
impl Plan {
    /// Read-only; never consults HOME, environment values or global settings.
    pub fn prepare(r: &Resolved) -> Result<Self> {
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
        Ok(Self {
            project,
            before,
            owner_before,
            after,
            owner_after,
            desired: wanted,
            no_sync: r.no_sync,
        })
    }
    /// The validated routing snapshot for an isolated runtime. Unmanaged project
    /// settings stay on disk and are never executed by the first-slice adapter.
    pub fn runtime_routing(&self) -> Value {
        serde_json::to_value(&self.desired).expect("JSON values")
    }
    pub fn needs_write(&self) -> bool {
        !self.no_sync
            && (self.before.as_deref() != Some(&self.after)
                || self.owner_before.as_deref() != Some(&self.owner_after))
    }
    /// Static field names only: never expose old user values or credentials.
    pub fn preview_changes(&self) -> Vec<&'static str> {
        let mut changes = Vec::new();
        if !self.no_sync {
            if self.before.as_deref() != Some(&self.after) {
                changes.push(
                    "opencode.json: provider.ah-litellm, enabled_providers, model, small_model",
                );
            }
            if self.owner_before.as_deref() != Some(&self.owner_after) {
                changes.push(".ah-opencode-owner.json: managed routing receipt");
            }
        }
        changes
    }
    /// Inspect the adapter-observed effective config after isolated launch setup.
    /// P2.2 must separately verify tools, agents, plugins and permission policy.
    pub fn validate_effective(&self, effective: &Value) -> Result<()> {
        for (k, v) in &self.desired {
            if managed_value(k, effective.get(k))?.as_ref() != Some(v) {
                return Err(Invalid(
                    "effective runtime routing differs from planned project routing",
                ));
            }
        }
        for section in ["agent", "mode"] {
            let (section_error, entry_error, model_error) = if section == "agent" {
                (
                    "effective agents must be an object",
                    "effective agent must be an object",
                    "effective agent overrides the selected model",
                )
            } else {
                (
                    "effective modes must be an object",
                    "effective mode must be an object",
                    "effective mode overrides the selected model",
                )
            };
            if let Some(agents) = effective.get(section) {
                let agents = agents.as_object().ok_or(Invalid(section_error))?;
                for agent in agents.values() {
                    if !agent.is_object() {
                        return Err(Invalid(entry_error));
                    }
                    if let Some(model) = agent.get("model") {
                        if model != &self.desired["model"] {
                            return Err(Invalid(model_error));
                        }
                    }
                }
            }
        }
        Ok(())
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
            if !self.needs_write() {
                return Ok(());
            }
            replace(&self.project, CONFIG, &self.after)?;
            replace(&self.project, OWNER, &self.owner_after)?;
            File::open(&self.project)
                .and_then(|f| f.sync_all())
                .map_err(|_| Invalid("cannot sync project directory; inspect transaction state"))?;
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
