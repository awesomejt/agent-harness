use awesomejt_agent_harness::agents::{
    Agent, Capacity, Catalog, Effort, Permissions, validate_name,
};
use awesomejt_agent_harness::config::MAX_INPUT_BYTES;
use std::io::Cursor;
use std::path::Path;

const REVIEWER: &str = include_str!("../agents/reviewer.md");
fn parse(text: &str) -> Result<Agent, awesomejt_agent_harness::config::Invalid> {
    Agent::read(text.as_bytes())
}
fn reject(text: &str) {
    assert!(parse(text).is_err(), "accepted invalid fixture");
}

#[test]
fn examples_preserve_body_and_destination() {
    let r = parse(REVIEWER).unwrap();
    assert_eq!(r.name(), "reviewer");
    assert_eq!(r.capacity(), Capacity::Specialized);
    assert_eq!(r.permissions(), Permissions::ReadOnly);
    assert_eq!(r.effort(), Effort::Default);
    assert_eq!(r.body(), REVIEWER.splitn(3, "---\n").nth(2).unwrap());
    assert_eq!(r.opencode_path(), Path::new(".opencode/agents/reviewer.md"));
    assert!(parse(include_str!("../agents/coder.md")).is_ok());
    assert!(parse(&REVIEWER.replace('\n', "\r\n")).is_ok());
}

#[test]
fn invalid_names_cannot_escape_or_shadow() {
    for name in [
        "",
        "../x",
        "a/b",
        "a\\b",
        ".",
        "..",
        "/x",
        "-x",
        "X",
        "a--b",
        "x-",
        "a_b",
        "a.b",
        "é",
        "title",
        "build",
        "plan",
        "general",
        "explore",
        "compaction",
        "summary",
    ] {
        assert!(validate_name(name).is_err());
    }
    assert!(validate_name(&"a".repeat(65)).is_err());
    for name in ["a", "code-reviewer", "role2", &"a".repeat(64)] {
        validate_name(name).unwrap();
    }
}

#[test]
fn rejects_ambiguous_yaml_and_schema() {
    for (old, new) in [
        ("version: 1", "version: 2"),
        ("version: 1", "version: !custom 1"),
        ("name: reviewer", "name: null"),
        ("name: reviewer", "name: !custom reviewer"),
        (
            "description: Review a change for correctness and regressions.",
            "description: true",
        ),
        ("capacity: specialized", "capacity: !specialized null"),
        ("tools: [read, search]", "tools: [!read null]"),
        ("version: 1", "version: 1\nversion: 1"),
        (
            "capacity: specialized",
            "capacity: primary\ncapacity: specialized",
        ),
        ("capacity: specialized", "capacity: subagent"),
        ("permissions: read-only", "permissions: allow"),
        ("tools: [read, search]", "tools: [read, read]"),
        ("tools: [read, search]", "tools: [web]"),
        ("tools: [read, search]", "tools: null"),
        ("version: 1", "version: 1\nunknown: secret"),
        ("version: 1", "version: 1\n<<: {name: other}"),
        ("version: 1", "version: 1\nmodels: null"),
        ("version: 1", "version: 1\neffort: null"),
        ("version: 1", "version: 1\neffort: extreme"),
    ] {
        reject(&REVIEWER.replace(old, new));
    }
    for key in [
        "version: 1\n",
        "name: reviewer\n",
        "capacity: specialized\n",
        "permissions: read-only\n",
        "tools: [read, search]\n",
    ] {
        reject(&REVIEWER.replace(key, ""));
    }
    reject(&REVIEWER.replace("tools: [read, search]", "tools: [[[[[read]]]]]"));
    reject(&REVIEWER.replace("name: reviewer", "name: *missing"));
    reject(&REVIEWER.replace("name: reviewer", "name: &x [*x]"));
    reject(&REVIEWER.replace(
        "tools: [read, search]",
        &format!("tools: {}read{}", "[".repeat(150), "]".repeat(150)),
    ));
}

#[test]
fn permission_ceiling_is_not_implied_by_prompt() {
    reject(&REVIEWER.replace("tools: [read, search]", "tools: [read, execute]"));
    reject(&REVIEWER.replace("tools: [read, search]", "tools: [edit]"));
    reject(&REVIEWER.replace("permissions: read-only", "permissions: deny"));
    assert!(
        parse(
            &REVIEWER
                .replace("permissions: read-only", "permissions: deny")
                .replace("[read, search]", "[]")
        )
        .is_ok()
    );
}

#[test]
fn route_models_are_explicit_and_never_provider_urls() {
    let with = |value: &str| REVIEWER.replace("version: 1", &format!("version: 1\n{value}"));
    let r = parse(&with(
        "models: {local: 'group:code', native: gpt-5.4}\neffort: high",
    ))
    .unwrap();
    assert_eq!(r.models().unwrap().local.as_deref(), Some("group:code"));
    assert_eq!(r.models().unwrap().native.as_deref(), Some("gpt-5.4"));
    assert_eq!(r.effort(), Effort::High);
    for value in [
        "models: {}",
        "models: {local: null}",
        "models: {local: 123}",
        "models: {native: true}",
        "models: {native: null}",
        "models: {other: x}",
        "models: {local: x, local: y}",
        "models: {native: 'group:x'}",
        "models: {native: 'opencode/x'}",
        "models: {local: 'http://host/v1'}",
        "models: {local: ''}",
    ] {
        assert!(parse(&with(value)).is_err(), "accepted {value}");
    }
}

#[test]
fn bounded_input_and_redacted_errors() {
    assert!(Agent::read(Cursor::new(vec![b'a'; MAX_INPUT_BYTES as usize + 1])).is_err());
    assert!(Agent::read(&b"\xff"[..]).is_err());
    reject(&format!("---\n#{}\n{}", "a".repeat(16_384), &REVIEWER[4..]));
    reject(&REVIEWER.replace(
        "description: Review a change for correctness and regressions.",
        "description: ''",
    ));
    reject(&REVIEWER.replace(
        "description: Review a change for correctness and regressions.",
        &format!("description: {}", "a".repeat(513)),
    ));
    reject("---\nversion: 1");
    reject(&format!("\u{feff}{REVIEWER}"));
    reject(&REVIEWER.replace("---\nInspect", "...\nInspect"));
    reject(&format!(
        "{}---\n \n",
        REVIEWER
            .split("---")
            .take(2)
            .collect::<Vec<_>>()
            .join("---")
    ));
    reject(&format!("{REVIEWER}\0"));
    let invalid = REVIEWER.replace("capacity: specialized", "capacity: SECRET-CREDENTIAL");
    let err = parse(&invalid).err().unwrap();
    assert!(!format!("{err:?}").contains("SECRET"));
}

#[test]
fn catalog_rejects_duplicates_and_orders_by_name() {
    assert!(Catalog::new([parse(REVIEWER).unwrap(), parse(REVIEWER).unwrap()]).is_err());
    let c = Catalog::new([
        parse(REVIEWER).unwrap(),
        parse(include_str!("../agents/coder.md")).unwrap(),
    ])
    .unwrap();
    assert_eq!(
        c.iter().map(Agent::name).collect::<Vec<_>>(),
        ["coder", "reviewer"]
    );
    assert!(c.get("absent").is_none());
    let entries = (0..65)
        .map(|n| parse(&REVIEWER.replace("name: reviewer", &format!("name: role{n}"))).unwrap());
    assert!(Catalog::new(entries).is_err());
}

#[test]
fn file_loading_checks_filename_and_regular_file() {
    let dir = std::env::temp_dir().join(format!("ah-agent-schema-{}", std::process::id()));
    std::fs::create_dir(&dir).unwrap();
    std::fs::write(dir.join("reviewer.md"), REVIEWER).unwrap();
    Agent::open(&dir.join("reviewer.md")).unwrap();
    std::fs::write(dir.join("wrong.md"), REVIEWER).unwrap();
    assert!(Agent::open(&dir.join("wrong.md")).is_err());
    assert!(Agent::open(&dir).is_err());
    assert!(Agent::open(&dir.join("../reviewer.md")).is_err());
    #[cfg(unix)]
    {
        std::os::unix::fs::symlink(dir.join("reviewer.md"), dir.join("link.md")).unwrap();
        assert!(Agent::open(&dir.join("link.md")).is_err());
        assert!(Agent::open(Path::new("/dev/null")).is_err());
    }
    std::fs::remove_dir_all(dir).unwrap();
}
