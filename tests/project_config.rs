#![cfg(unix)]
use awesomejt_agent_harness::config::{Config, Invocation, Resolved};
use awesomejt_agent_harness::project_config::Plan;
use serde_json::Value;
use std::ffi::OsString;
use std::fs;
use std::path::PathBuf;
use std::sync::atomic::{AtomicUsize, Ordering};

struct Project(PathBuf);
impl Project {
    fn new() -> Self {
        static NEXT: AtomicUsize = AtomicUsize::new(0);
        let p = std::env::temp_dir().join(format!(
            "ah-sync-{}-{}",
            std::process::id(),
            NEXT.fetch_add(1, Ordering::Relaxed)
        ));
        fs::create_dir(&p).unwrap();
        Self(p)
    }
    fn request(&self, model: &str, no_sync: bool) -> Resolved {
        let config = Config::read(format!(r#"{{"version":1,"mode":"local-only","model":"{model}","litellm":{{"api_base":"http://litellm:4000/v1","api_key_env":"TEST_KEY"}}}}"#).as_bytes()).unwrap();
        let mut args = vec![
            OsString::from("single"),
            OsString::from("task"),
            OsString::from("--project"),
            self.0.clone().into_os_string(),
        ];
        if no_sync {
            args.push("--no-sync".into());
        }
        Invocation::parse(args, &self.0)
            .unwrap()
            .resolve(
                config,
                |_| Some("SENTINEL_SECRET_DO_NOT_WRITE".into()),
                &b""[..],
            )
            .unwrap()
    }
    fn write(&self, name: &str, text: &str) {
        fs::write(self.0.join(name), text).unwrap();
    }
    fn read(&self, name: &str) -> String {
        fs::read_to_string(self.0.join(name)).unwrap()
    }
}
impl Drop for Project {
    fn drop(&mut self) {
        let _ = fs::remove_dir_all(&self.0);
    }
}

#[test]
fn preserves_unrelated_bytes_updates_owned_route_and_never_writes_key() {
    let p = Project::new();
    let unrelated = "\"theme\" : \"system\", \"formatter\": { \"x\" : false }";
    p.write("opencode.json", &format!("{{ {unrelated} }}\n"));
    let outside = Project::new();
    outside.write("opencode.json", "global sentinel");
    let r = p.request("first", false);
    let plan = Plan::prepare(&r).unwrap();
    assert!(plan.needs_write());
    // Planning writes nothing.
    assert_eq!(fs::read_dir(&p.0).unwrap().count(), 1);
    plan.apply().unwrap();
    assert!(p.read("opencode.json").contains(unrelated));
    Plan::prepare(&p.request("second", false))
        .unwrap()
        .apply()
        .unwrap();
    let text = p.read("opencode.json");
    assert!(text.contains("ah-litellm/second"));
    assert!(text.contains(unrelated));
    for entry in fs::read_dir(&p.0).unwrap() {
        assert!(
            !fs::read_to_string(entry.unwrap().path())
                .unwrap()
                .contains("SENTINEL_SECRET_DO_NOT_WRITE")
        );
    }
    assert!(text.contains("{env:TEST_KEY}"));
    assert!(
        !Plan::prepare(&p.request("second", false))
            .unwrap()
            .needs_write()
    );
    assert_eq!(outside.read("opencode.json"), "global sentinel");
}

#[test]
fn rejects_user_owned_fields_comments_duplicates_and_alternate_config() {
    let p = Project::new();
    for bad in [
        r#"{"model":"other"}"#,
        r#"{/*comment*/}"#,
        r#"{"theme":1,"theme":2}"#,
        r#"{"custom":{"x":1,"x":2}}"#,
        "[]",
        "{broken",
    ] {
        p.write("opencode.json", bad);
        assert!(Plan::prepare(&p.request("m", false)).is_err());
        assert_eq!(p.read("opencode.json"), bad);
    }
    p.write("opencode.json", "{}");
    p.write("opencode.jsonc", "{}");
    assert!(Plan::prepare(&p.request("m", false)).is_err());
}

#[test]
fn detects_manual_edits_stale_plans_and_interrupted_receipts() {
    let p = Project::new();
    Plan::prepare(&p.request("first", false))
        .unwrap()
        .apply()
        .unwrap();
    let plan = Plan::prepare(&p.request("second", false)).unwrap();
    let original = p.read("opencode.json");
    p.write(
        "opencode.json",
        &original.replace("ah-litellm/first", "native/other"),
    );
    assert!(plan.apply().is_err());
    assert!(Plan::prepare(&p.request("second", false)).is_err());
    p.write("opencode.json", &original);
    let old_receipt = p.read(".ah-opencode-owner.json");
    Plan::prepare(&p.request("second", false))
        .unwrap()
        .apply()
        .unwrap();
    p.write(".ah-opencode-owner.json", &old_receipt); // crash after config rename
    assert!(Plan::prepare(&p.request("second", false)).is_err());
    fs::remove_file(p.0.join(".ah-opencode-owner.json")).unwrap();
    assert!(Plan::prepare(&p.request("second", false)).is_err());
}

#[test]
fn no_sync_validates_without_writing_and_effective_route_must_match() {
    let p = Project::new();
    assert!(Plan::prepare(&p.request("first", true)).is_err());
    Plan::prepare(&p.request("first", false))
        .unwrap()
        .apply()
        .unwrap();
    fs::remove_file(p.0.join(".ah-opencode-owner.json")).unwrap();
    let r = p.request("first", true);
    let plan = Plan::prepare(&r).unwrap();
    assert!(!plan.needs_write());
    let mut effective: Value = serde_json::from_str(&p.read("opencode.json")).unwrap();
    plan.validate_effective(&effective).unwrap();
    effective["small_model"] = "native/other".into();
    assert!(plan.validate_effective(&effective).is_err());
    effective = serde_json::from_str(&p.read("opencode.json")).unwrap();
    effective["agent"] = serde_json::json!({"helper":{"model":"native/other"}});
    assert!(plan.validate_effective(&effective).is_err());
    assert!(Plan::prepare(&p.request("other", true)).is_err());
    let before = fs::read_dir(&p.0).unwrap().count();
    plan.apply().unwrap();
    assert_eq!(fs::read_dir(&p.0).unwrap().count(), before);
}

#[test]
fn symlinks_streams_and_busy_lock_refuse() {
    use std::os::fd::AsRawFd;
    use std::os::unix::fs::symlink;
    let p = Project::new();
    let outside = Project::new();
    outside.write("target", "{}");
    symlink(outside.0.join("target"), p.0.join("opencode.json")).unwrap();
    assert!(Plan::prepare(&p.request("m", false)).is_err());
    fs::remove_file(p.0.join("opencode.json")).unwrap();
    let fifo = std::ffi::CString::new(p.0.join("opencode.json").to_str().unwrap()).unwrap();
    assert_eq!(unsafe { libc::mkfifo(fifo.as_ptr(), 0o600) }, 0);
    assert!(Plan::prepare(&p.request("m", false)).is_err());
    fs::remove_file(p.0.join("opencode.json")).unwrap();
    let plan = Plan::prepare(&p.request("m", false)).unwrap();
    let lock = fs::File::create(p.0.join(".ah-opencode.lock")).unwrap();
    assert_eq!(
        unsafe { libc::flock(lock.as_raw_fd(), libc::LOCK_EX | libc::LOCK_NB) },
        0
    );
    assert!(plan.apply().is_err());
    assert!(!p.0.join("opencode.json").exists());
    assert_eq!(outside.read("target"), "{}");
}

#[test]
fn preserves_inactive_providers_and_refuses_malformed_effective_agents() {
    use std::os::unix::fs::PermissionsExt;
    let p = Project::new();
    let sibling = r#""other" : { "options" : {"baseURL":"http://unused"} }"#;
    p.write("opencode.json", &format!("{{\"provider\":{{{sibling}}}}}"));
    fs::set_permissions(p.0.join("opencode.json"), fs::Permissions::from_mode(0o640)).unwrap();
    Plan::prepare(&p.request("m", false))
        .unwrap()
        .apply()
        .unwrap();
    assert!(p.read("opencode.json").contains(sibling));
    assert_eq!(
        fs::metadata(p.0.join("opencode.json"))
            .unwrap()
            .permissions()
            .mode()
            & 0o777,
        0o640
    );
    Plan::prepare(&p.request("next", false))
        .unwrap()
        .apply()
        .unwrap();
    assert!(p.read("opencode.json").contains(sibling));
    let plan = Plan::prepare(&p.request("next", true)).unwrap();
    let mut effective: Value = serde_json::from_str(&p.read("opencode.json")).unwrap();
    plan.validate_effective(&effective).unwrap();
    for malformed in [
        serde_json::json!([]),
        serde_json::json!({"helper":null}),
        serde_json::json!({"helper":false}),
    ] {
        effective["agent"] = malformed;
        assert!(plan.validate_effective(&effective).is_err());
    }
}

#[test]
fn legacy_mode_models_cannot_override_selected_route() {
    let p = Project::new();
    Plan::prepare(&p.request("m", false))
        .unwrap()
        .apply()
        .unwrap();
    let plan = Plan::prepare(&p.request("m", true)).unwrap();
    let mut effective: Value = serde_json::from_str(&p.read("opencode.json")).unwrap();
    effective["mode"] = serde_json::json!({"build":{"model":"ah-litellm/m"}});
    plan.validate_effective(&effective).unwrap();
    for bad in [
        serde_json::json!({"build":{"model":"native/other"}}),
        serde_json::json!([]),
        serde_json::json!({"build":null}),
    ] {
        effective["mode"] = bad;
        assert!(plan.validate_effective(&effective).is_err());
    }
}

#[test]
fn group_reference_manages_only_the_resolved_proxy_group() {
    let p = Project::new();
    let config = Config::read(br#"{"version":1,"mode":"local-only","model":"group:coder","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"TEST_KEY","groups":{"coder":"proxy-coder","review":"proxy-review"}}}"#.as_slice()).unwrap();
    let r = Invocation::parse(
        [
            OsString::from("single"),
            OsString::from("task"),
            OsString::from("--project"),
            p.0.clone().into_os_string(),
        ],
        &p.0,
    )
    .unwrap()
    .resolve(
        config,
        |_| Some("SENTINEL_SECRET_DO_NOT_WRITE".into()),
        &b""[..],
    )
    .unwrap();
    let plan = Plan::prepare(&r).unwrap();
    let routing = plan.runtime_routing();
    assert_eq!(routing["model"], "ah-litellm/proxy-coder");
    assert_eq!(routing["small_model"], "ah-litellm/proxy-coder");
    let models = routing["provider"]["ah-litellm"]["models"]
        .as_object()
        .unwrap();
    assert_eq!(models.keys().collect::<Vec<_>>(), ["proxy-coder"]);
    plan.apply().unwrap();
    for name in ["opencode.json", ".ah-opencode-owner.json"] {
        let text = p.read(name);
        // Harness group names and unselected groups are not runtime routing.
        assert!(!text.contains("\"coder\"") && !text.contains("/coder\""));
        assert!(!text.contains("review") && !text.contains("group:"));
        assert!(!text.contains("SENTINEL_SECRET_DO_NOT_WRITE"));
    }
    // Effective validation rejects a runtime that selected a different group.
    let mut effective = routing.clone();
    effective["model"] = "ah-litellm/proxy-review".into();
    assert!(
        Plan::prepare(&r)
            .unwrap()
            .validate_effective(&effective)
            .is_err()
    );
}
