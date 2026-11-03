#![cfg(unix)]
//! P4.2 name-based selection, model precedence and conflict-aware OpenCode
//! project emission. Golden files pin the exact emitted bytes; set AH_BLESS=1
//! to regenerate them after an intentional mapping change.
use awesomejt_agent_harness::config::{Config, Invalid, Invocation, Mode, Resolved, Source};
use awesomejt_agent_harness::project_config::Plan;
use std::ffi::OsString;
use std::fs;
use std::path::{Path, PathBuf};
use std::sync::atomic::{AtomicUsize, Ordering};

const LOCAL: &str = r#"{"version":1,"mode":"local-only","model":"proxy","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"KEY","groups":{"review":"proxy-review"}},"native":{"target":"opencode","model":"gpt-5.4","api_key_env":"NATIVE_KEY"}}"#;
const CODER: &str = include_str!("../agents/coder.md");
const REVIEWER: &str = include_str!("../agents/reviewer.md");

struct Project(PathBuf);
impl Project {
    fn new() -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let p = std::env::temp_dir().join(format!(
            "ah-emit-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&p).unwrap();
        let project = Self(p.canonicalize().unwrap());
        project.write("agents/coder.md", CODER);
        project.write("agents/reviewer.md", REVIEWER);
        project
    }
    fn resolve(&self, extra: &[&str]) -> Result<Resolved, Invalid> {
        let mut args: Vec<OsString> = vec!["single".into(), "task".into()];
        args.extend(extra.iter().map(OsString::from));
        Invocation::parse(args, &self.0)?.resolve(
            Config::read(LOCAL.as_bytes()).unwrap(),
            |_| Some("SECRET".into()),
            &b""[..],
        )
    }
    fn plan(&self, extra: &[&str]) -> Result<Plan, Invalid> {
        Plan::prepare(&self.resolve(extra)?)
    }
    fn write(&self, name: &str, text: &str) {
        let path = self.0.join(name);
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(path, text).unwrap();
    }
    fn read(&self, name: &str) -> String {
        fs::read_to_string(self.0.join(name)).unwrap()
    }
    fn has(&self, name: &str) -> bool {
        fs::symlink_metadata(self.0.join(name)).is_ok()
    }
    /// Sorted relative listing, excluding canonical sources: detects any write.
    fn tree(&self) -> Vec<(String, String)> {
        fn walk(root: &Path, dir: &Path, out: &mut Vec<(String, String)>) {
            for entry in fs::read_dir(dir).unwrap() {
                let path = entry.unwrap().path();
                let rel = path.strip_prefix(root).unwrap().display().to_string();
                if path.is_dir() {
                    walk(root, &path, out);
                } else {
                    out.push((rel, fs::read_to_string(&path).unwrap_or_default()));
                }
            }
        }
        let mut out = Vec::new();
        walk(&self.0, &self.0, &mut out);
        out.sort();
        out
    }
}
impl Drop for Project {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

fn err<T>(result: Result<T, Invalid>) -> &'static str {
    match result {
        Ok(_) => panic!("expected refusal"),
        Err(Invalid(message)) => message,
    }
}

#[test]
fn selection_is_exact_name_based_and_never_parses_other_definitions() {
    let p = Project::new();
    p.write("agents/broken.md", "not an agent\n");
    p.write("agents/.DS_Store", "");
    let r = p.resolve(&["--agent", "reviewer"]).unwrap();
    assert_eq!(r.agent.as_ref().unwrap().name(), "reviewer");
    assert!(p.resolve(&[]).unwrap().agent.is_none());
    assert_eq!(
        err(p.resolve(&["--agent", "missing"])),
        "agent is not defined in project agents/"
    );
    assert_eq!(
        err(p.resolve(&["--agent", "broken"])),
        "agent requires opening YAML frontmatter delimiter"
    );
    for bad in ["../coder", "Coder", "build", "a/b", ""] {
        assert!(p.resolve(&["--agent", bad]).is_err(), "{bad}");
    }
    assert!(
        p.resolve(&["--agent", "coder", "--agent", "coder"])
            .is_err()
    );

    // A differently cased canonical file never satisfies, or shadows, a name.
    let q = Project::new();
    fs::remove_file(q.0.join("agents/reviewer.md")).unwrap();
    q.write("agents/Reviewer.md", REVIEWER);
    assert_eq!(
        err(q.resolve(&["--agent", "reviewer"])),
        "agent filename must match canonical name exactly"
    );
    let r = Project::new();
    fs::remove_dir_all(r.0.join("agents")).unwrap();
    assert_eq!(
        err(r.resolve(&["--agent", "coder"])),
        "agent is not defined in project agents/"
    );
    std::os::unix::fs::symlink(p.0.join("agents"), r.0.join("agents")).unwrap();
    assert_eq!(
        err(r.resolve(&["--agent", "coder"])),
        "project agents path must be a real directory"
    );
}

#[test]
fn model_precedence_is_invocation_then_agent_route_then_config() {
    let p = Project::new();
    p.write(
        "agents/pinned.md",
        "---\nversion: 1\nname: pinned\ndescription: Pinned models.\ncapacity: both\npermissions: deny\ntools: []\nmodels: {local: 'group:review', native: gpt-5.5}\n---\nBody.\n",
    );
    p.write(
        "agents/native-only.md",
        "---\nversion: 1\nname: native-only\ndescription: Native model only.\ncapacity: primary\npermissions: deny\ntools: []\nmodels: {native: gpt-5.5}\n---\nBody.\n",
    );
    p.write(
        "agents/missing-group.md",
        "---\nversion: 1\nname: missing-group\ndescription: Undefined group.\ncapacity: primary\npermissions: deny\ntools: []\nmodels: {local: 'group:absent'}\n---\nBody.\n",
    );
    let r = p.resolve(&["--agent", "pinned"]).unwrap();
    assert_eq!(
        (r.model.as_str(), r.group.as_deref()),
        ("proxy-review", Some("review"))
    );
    assert_eq!(r.sources.model, Source::Agent);
    let r = p
        .resolve(&["--agent", "pinned", "--model", "explicit"])
        .unwrap();
    assert_eq!(
        (r.model.as_str(), r.sources.model),
        ("explicit", Source::Invocation)
    );
    // An omitted route inherits the invocation/config model.
    let r = p.resolve(&["--agent", "native-only"]).unwrap();
    assert_eq!(
        (r.model.as_str(), r.sources.model),
        ("proxy", Source::Config)
    );
    let r = p.resolve(&["--agent", "coder"]).unwrap();
    assert_eq!(
        (r.model.as_str(), r.sources.model),
        ("proxy", Source::Config)
    );

    let r = p
        .resolve(&["--agent", "pinned", "--mode", "cloud-only"])
        .unwrap();
    assert_eq!((r.mode, r.model.as_str()), (Mode::CloudOnly, "gpt-5.5"));
    assert_eq!(r.sources.model, Source::Agent);
    let r = p
        .resolve(&["--agent", "coder", "--mode", "cloud-only"])
        .unwrap();
    assert_eq!(
        (r.model.as_str(), r.sources.model),
        ("gpt-5.4", Source::Config)
    );

    // Local-first: `--model` selects only the primary; the fallback keeps the
    // agent's native model and the same agent definition.
    let r = p
        .resolve(&["--agent", "pinned", "--mode", "local-first", "--model", "x"])
        .unwrap();
    let fallback = r.fallback.as_deref().unwrap();
    assert_eq!(r.model, "x");
    assert_eq!(
        (fallback.model.as_str(), fallback.sources.model),
        ("gpt-5.5", Source::Agent)
    );
    assert_eq!(fallback.agent.as_ref().unwrap().name(), "pinned");
    let r = p
        .resolve(&["--agent", "coder", "--mode", "local-first"])
        .unwrap();
    let fallback = r.fallback.as_deref().unwrap();
    assert_eq!(
        (fallback.model.as_str(), fallback.sources.model),
        ("gpt-5.4", Source::Config)
    );

    assert_eq!(
        err(p.resolve(&["--agent", "missing-group"])),
        "model group reference is not defined in litellm.groups"
    );
    // The inactive local route's group is not resolved on the native route.
    assert!(
        p.resolve(&["--agent", "missing-group", "--mode", "cloud-only"])
            .is_ok()
    );
}

fn golden(name: &str, actual: &str) {
    let path = Path::new(env!("CARGO_MANIFEST_DIR"))
        .join("tests/fixtures/opencode-agents")
        .join(format!("{name}.md"));
    if std::env::var_os("AH_BLESS").is_some() {
        fs::create_dir_all(path.parent().unwrap()).unwrap();
        fs::write(&path, actual).unwrap();
    }
    assert_eq!(
        actual,
        fs::read_to_string(path).unwrap_or_default(),
        "{name}"
    );
}

#[test]
fn emission_is_deterministic_golden_and_idempotent() {
    let p = Project::new();
    for name in ["coder", "reviewer"] {
        let plan = p.plan(&["--agent", name]).unwrap();
        assert!(plan.needs_write());
        plan.apply().unwrap();
        let emitted = p.read(&format!(".opencode/agents/{name}.md"));
        golden(name, &emitted);
        assert!(!emitted.contains("SECRET") && !emitted.contains("litellm:4000"));
        // Re-planning the same selection is a no-op.
        assert!(!p.plan(&["--agent", name]).unwrap().needs_write());
    }
    let receipt: serde_json::Value =
        serde_json::from_str(&p.read(".ah-opencode-agents.json")).unwrap();
    assert_eq!(receipt["coder"], p.read(".opencode/agents/coder.md"));
    assert_eq!(receipt["reviewer"], p.read(".opencode/agents/reviewer.md"));
    assert_eq!(receipt.as_object().unwrap().len(), 2);

    // A CRLF body is preserved exactly; mapping follows the resolved model.
    let q = Project::new();
    q.write("agents/reviewer.md", &REVIEWER.replace('\n', "\r\n"));
    q.plan(&["--agent", "reviewer", "--model", "group:review"])
        .unwrap()
        .apply()
        .unwrap();
    let emitted = q.read(".opencode/agents/reviewer.md");
    assert!(
        emitted.ends_with(
            &REVIEWER
                .splitn(3, "---\n")
                .nth(2)
                .unwrap()
                .replace('\n', "\r\n")
        )
    );
    assert!(emitted.contains(r#""model":{"providerID":"ah-litellm","model":"proxy-review"}"#));
}

#[test]
fn preview_plans_emission_without_writing() {
    let p = Project::new();
    let before = p.tree();
    let plan = p.plan(&["--agent", "reviewer", "--preview"]).unwrap();
    let changes = plan.preview_changes();
    assert!(changes.contains(
        &".opencode/agents/reviewer.md: emitted agent (native frontmatter, ceiling rules)".into()
    ));
    assert!(changes.contains(&".ah-opencode-agents.json: managed agent receipt".into()));
    assert!(!changes.join(" ").contains("Inspect the change"));
    drop(plan);
    assert_eq!(p.tree(), before);
    assert!(!p.has(".opencode"));

    // No-sync and native routes plan no agent emission at all.
    p.write(
        "opencode.json",
        r#"{"model":"ah-litellm/proxy","small_model":"ah-litellm/proxy","enabled_providers":["ah-litellm"],"provider":{"ah-litellm":{"npm":"@ai-sdk/openai-compatible","options":{"baseURL":"http://litellm:4000/v1","apiKey":"{env:KEY}"},"models":{"proxy":{"name":"proxy"}}}}}"#,
    );
    let plan = p.plan(&["--agent", "reviewer", "--no-sync"]).unwrap();
    assert!(!plan.needs_write() && plan.preview_changes().is_empty());
    plan.apply().unwrap();
    assert!(!p.has(".opencode") && !p.has(".ah-opencode-agents.json"));
}

#[test]
fn every_opencode_project_agent_source_collides() {
    const CONFLICT: &str = "user-owned OpenCode agent definition conflicts with the canonical name";
    let cases: [(&str, &str, &str); 7] = [
        (".opencode/agents/Reviewer.md", "x", CONFLICT),
        (".opencode/agent/reviewer.md", "x", CONFLICT),
        (".opencode/agent/REVIEWER.md", "x", CONFLICT),
        ("opencode.json", r#"{"agent":{"reviewer":{}}}"#, CONFLICT),
        ("opencode.json", r#"{"agents":{"Reviewer":{}}}"#, CONFLICT),
        (
            ".opencode/opencode.json",
            r#"{"agent":{"reviewer":{}}}"#,
            CONFLICT,
        ),
        (
            ".opencode/opencode.jsonc",
            "{}",
            "opencode.jsonc requires manual migration before sync",
        ),
    ];
    for (path, text, expected) in cases {
        let p = Project::new();
        p.write(path, text);
        let before = p.tree();
        assert_eq!(err(p.plan(&["--agent", "reviewer"])), expected, "{path}");
        assert_eq!(p.tree(), before);
    }
    for (path, text) in [
        ("opencode.json", r#"{"agent":[]}"#),
        (".opencode/opencode.json", "{\"a\":1,\"a\":2}"),
    ] {
        let p = Project::new();
        p.write(path, text);
        assert!(p.plan(&["--agent", "reviewer"]).is_err(), "{path}");
    }
    // A user file identical to the emission is still user-owned.
    let p = Project::new();
    p.plan(&["--agent", "reviewer"]).unwrap().apply().unwrap();
    fs::remove_file(p.0.join(".ah-opencode-agents.json")).unwrap();
    assert_eq!(
        err(p.plan(&["--agent", "reviewer"])),
        "user-owned OpenCode agent file conflicts with the canonical name"
    );
    // Other names, nested IDs and non-colliding keys are left alone.
    let p = Project::new();
    p.write(".opencode/agents/mine.md", "user");
    p.write(".opencode/agents/sub/reviewer.md", "nested id sub/reviewer");
    p.write("opencode.json", r#"{"agent":{"mine":{}},"theme":"x"}"#);
    p.plan(&["--agent", "reviewer"]).unwrap().apply().unwrap();
    assert_eq!(p.read(".opencode/agents/mine.md"), "user");
    assert_eq!(
        p.read(".opencode/agents/sub/reviewer.md"),
        "nested id sub/reviewer"
    );
    // Symlinked OpenCode directories or destinations are refused.
    for link in [
        ".opencode",
        ".opencode/agents",
        ".opencode/agents/reviewer.md",
    ] {
        let p = Project::new();
        let outside = Project::new();
        outside.write("target.md", "outside");
        fs::create_dir_all(p.0.join(Path::new(link).parent().unwrap())).unwrap();
        std::os::unix::fs::symlink(outside.0.join("target.md"), p.0.join(link)).unwrap();
        assert!(p.plan(&["--agent", "reviewer"]).is_err(), "{link}");
        assert_eq!(outside.read("target.md"), "outside");
    }
}

#[test]
fn ownership_receipt_protects_user_edits_and_updates_owned_files() {
    let p = Project::new();
    p.plan(&["--agent", "reviewer"]).unwrap().apply().unwrap();
    p.plan(&["--agent", "coder"]).unwrap().apply().unwrap();
    let coder = p.read(".opencode/agents/coder.md");

    // A canonical change updates only the selected owned file.
    p.write(
        "agents/reviewer.md",
        &REVIEWER.replace("Inspect", "Carefully inspect"),
    );
    p.plan(&["--agent", "reviewer"]).unwrap().apply().unwrap();
    assert!(
        p.read(".opencode/agents/reviewer.md")
            .contains("Carefully inspect")
    );
    assert_eq!(p.read(".opencode/agents/coder.md"), coder);
    let receipt: serde_json::Value =
        serde_json::from_str(&p.read(".ah-opencode-agents.json")).unwrap();
    assert_eq!(receipt["coder"], coder);

    // A manual edit is never overwritten.
    p.write(".opencode/agents/reviewer.md", "user edit");
    assert_eq!(
        err(p.plan(&["--agent", "reviewer"])),
        "managed agent file was manually edited; reconcile agent ownership receipt"
    );
    assert_eq!(p.read(".opencode/agents/reviewer.md"), "user edit");
    // A removed owned file is recreated.
    fs::remove_file(p.0.join(".opencode/agents/reviewer.md")).unwrap();
    p.plan(&["--agent", "reviewer"]).unwrap().apply().unwrap();
    assert!(
        p.read(".opencode/agents/reviewer.md")
            .contains("Carefully inspect")
    );

    for bad in [
        "[]",
        r#"{"reviewer":1}"#,
        r#"{"../x":"y"}"#,
        "{\"coder\":\"a\",\"coder\":\"b\"}",
        "not json",
    ] {
        p.write(".ah-opencode-agents.json", bad);
        assert_eq!(
            err(p.plan(&["--agent", "reviewer"])),
            "invalid agent ownership receipt",
            "{bad}"
        );
    }
}

#[test]
fn stale_plans_reject_without_writing() {
    let p = Project::new();
    let plan = p.plan(&["--agent", "reviewer"]).unwrap();
    p.write(".opencode/agent/reviewer.md", "late user file");
    assert!(plan.apply().is_err());
    assert!(!p.has(".opencode/agents"));

    let p = Project::new();
    let plan = p.plan(&["--agent", "reviewer"]).unwrap();
    p.write(".opencode/agents/reviewer.md", "late user file");
    assert!(plan.apply().is_err());
    assert_eq!(p.read(".opencode/agents/reviewer.md"), "late user file");
    assert!(!p.has(".ah-opencode-agents.json"));
}
