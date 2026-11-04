//! P5.2 sequence snapshot, step metadata and per-step resolution (D044).
//! No runtime launch, network or project writes.
use awesomejt_agent_harness::config::{Config, Invalid, Invocation};
use awesomejt_agent_harness::sequence::{self, Step};
use std::ffi::OsString;
use std::path::{Path, PathBuf};

fn folder(tag: &str, files: &[(&str, &str)]) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("ah-p5-2-{tag}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    for (name, text) in files {
        std::fs::write(dir.join(name), text).unwrap();
    }
    dir
}

fn names(steps: &[Step]) -> Vec<&str> {
    steps.iter().map(|s| s.name.as_str()).collect()
}

fn error(result: Result<Vec<Step>, Invalid>) -> &'static str {
    result.err().expect("snapshot rejects").0
}

#[test]
fn steps_order_by_numeric_value_and_dot_entries_are_ignored() {
    let dir = folder(
        "order",
        &[
            ("10-ten.md", "Ten.\n"),
            ("2-two.md", "Two.\n"),
            ("000001-one.md", "One.\n"),
            (".DS_Store", "ignored"),
            (".draft.md", "ignored"),
        ],
    );
    let steps = sequence::snapshot(&dir).unwrap();
    assert_eq!(names(&steps), ["000001-one.md", "2-two.md", "10-ten.md"]);
    assert_eq!(
        steps.iter().map(|s| s.number).collect::<Vec<_>>(),
        [1, 2, 10]
    );
    // SHA-256 of the raw bytes ("Two.\n"), as `shasum -a 256` prints it.
    assert_eq!(
        steps[1].sha256,
        "e497187550b9f2cca2118606b268ab04fa4161af5a30a4c3c4b475f6e311cac0"
    );
    assert_eq!(steps[1].bytes, 5);
}

#[test]
fn identity_is_the_name_and_hash_of_raw_bytes_including_metadata() {
    let plain = Step::parse("1-a.md", "Do it.\n").unwrap();
    let same = Step::parse("1-a.md", "Do it.\n").unwrap();
    let edited = Step::parse("1-a.md", "Do it now.\n").unwrap();
    let tagged = Step::parse("1-a.md", "---\nagent: coder\n---\nDo it.\n").unwrap();
    assert_eq!(plain.sha256, same.sha256);
    assert_eq!(plain.sha256.len(), 64);
    assert!(
        plain
            .sha256
            .bytes()
            .all(|b| b.is_ascii_hexdigit() && !b.is_ascii_uppercase())
    );
    assert_ne!(plain.sha256, edited.sha256);
    // Metadata is part of the identity although the prompt body is unchanged.
    assert_ne!(plain.sha256, tagged.sha256);
    assert_eq!(tagged.prompt, plain.prompt);
    assert_eq!(tagged.agent.as_deref(), Some("coder"));
}

#[test]
fn folder_errors_reject_rather_than_skip() {
    let empty = folder("empty", &[(".hidden", "x")]);
    assert!(error(sequence::snapshot(&empty)).contains("no steps"));
    assert!(error(sequence::snapshot(&empty.join("missing"))).contains("directory"));
    let file = empty.join(".hidden");
    assert!(error(sequence::snapshot(&file)).contains("directory"));

    let equal = folder("equal", &[("1-a.md", "A.\n"), ("01-b.md", "B.\n")]);
    assert_eq!(
        error(sequence::snapshot(&equal)),
        "two steps share a step number"
    );

    let long = format!("1-{}.md", "a".repeat(124));
    assert_eq!(long.len(), 129);
    for bad in [
        "a.md",
        "1.md",
        "1-.md",
        "-a.md",
        "1234567-a.md",
        "1-_a.md",
        "1-a b.md",
        "1-a.txt",
        "1-a.MD",
        "x1-a.md",
        long.as_str(),
    ] {
        let dir = folder("name", &[("1-ok.md", "Ok.\n"), (bad, "Bad.\n")]);
        assert!(
            error(sequence::snapshot(&dir)).contains("N-slug.md"),
            "{bad}"
        );
    }
    let longest = format!("1-{}.md", "a".repeat(123));
    let dir = folder("longest", &[(longest.as_str(), "Ok.\n")]);
    assert_eq!(sequence::snapshot(&dir).unwrap().len(), 1);

    let dir = folder("dir", &[("1-ok.md", "Ok.\n")]);
    std::fs::create_dir(dir.join("2-dir.md")).unwrap();
    assert!(error(sequence::snapshot(&dir)).contains("not symlinks or directories"));
    #[cfg(unix)]
    {
        let dir = folder("link", &[("1-ok.md", "Ok.\n")]);
        std::os::unix::fs::symlink(dir.join("1-ok.md"), dir.join("2-link.md")).unwrap();
        assert!(error(sequence::snapshot(&dir)).contains("not symlinks or directories"));
    }

    let dir = folder("utf8", &[("1-ok.md", "Ok.\n")]);
    std::fs::write(dir.join("2-bad.md"), [0xff, 0xfe]).unwrap();
    assert_eq!(error(sequence::snapshot(&dir)), "input must be UTF-8");
    let dir = folder("large", &[("1-ok.md", "Ok.\n")]);
    std::fs::write(dir.join("2-big.md"), "x".repeat(1_048_577)).unwrap();
    assert_eq!(error(sequence::snapshot(&dir)), "input exceeds 1 MiB");
}

#[test]
fn step_and_snapshot_bounds() {
    let many: Vec<(String, &str)> = (1..=257).map(|n| (format!("{n}-s.md"), "Go.\n")).collect();
    let refs: Vec<(&str, &str)> = many.iter().map(|(n, t)| (n.as_str(), *t)).collect();
    let dir = folder("many", &refs[..256]);
    assert_eq!(sequence::snapshot(&dir).unwrap().len(), 256);
    std::fs::write(dir.join("257-s.md"), "Go.\n").unwrap();
    assert_eq!(
        error(sequence::snapshot(&dir)),
        "a sequence holds 1–256 steps"
    );

    // 17 files just under 1 MiB exceed the 16 MiB snapshot bound.
    let dir = folder("total", &[]);
    let body = "x".repeat(1_000_000);
    for n in 1..=17 {
        std::fs::write(dir.join(format!("{n}-big.md")), &body).unwrap();
    }
    assert_eq!(
        error(sequence::snapshot(&dir)),
        "prompt folder steps exceed 16 MiB in all"
    );
}

#[test]
fn metadata_is_strict_and_limited_to_agent_and_verify() {
    let step = Step::parse("1-a.md", "---\nagent: coder\nverify: build\n---\nBody\n").unwrap();
    assert_eq!(
        (
            step.agent.as_deref(),
            step.verify.as_deref(),
            step.prompt.as_str()
        ),
        (Some("coder"), Some("build"), "Body\n")
    );
    // CRLF delimiters and a body-only file.
    let step = Step::parse("1-a.md", "---\r\nverify: test\r\n---\r\nBody\r\n").unwrap();
    assert_eq!(
        (step.verify.as_deref(), step.prompt.as_str()),
        (Some("test"), "Body\r\n")
    );
    let step = Step::parse("1-a.md", "Body with --- inside\n---\n").unwrap();
    assert_eq!((step.agent, step.verify), (None, None));

    for (text, reason) in [
        (
            "---\nmode: cloud-only\n---\nBody\n",
            "invalid step metadata",
        ),
        ("---\nmodel: x\n---\nBody\n", "invalid step metadata"),
        (
            "---\npermissions: trusted\n---\nBody\n",
            "invalid step metadata",
        ),
        (
            "---\nagent: a\nagent: b\n---\nBody\n",
            "invalid step metadata",
        ),
        ("---\nagent: 7\n---\nBody\n", "invalid step metadata"),
        ("---\nagent: true\n---\nBody\n", "invalid step metadata"),
        ("---\nagent: null\n---\nBody\n", "invalid step metadata"),
        ("---\nverify: [a]\n---\nBody\n", "invalid step metadata"),
        (
            "---\nagent: !tag coder\n---\nBody\n",
            "step metadata YAML tags are unsupported",
        ),
        ("---\n- agent\n---\nBody\n", "invalid step metadata"),
        ("---\nagent: Coder\n---\nBody\n", "agent name"),
        ("---\nverify: Bad_Name\n---\nBody\n", "check name"),
        ("---\nagent: coder\n", "step metadata is incomplete"),
        (
            "---\nagent: coder\n---\n  \n",
            "step prompt must not be empty",
        ),
        ("", "step prompt must not be empty"),
        (" \n\t\n", "step prompt must not be empty"),
    ] {
        let error = Step::parse("1-a.md", text).err().expect(text).0;
        assert!(error.contains(reason), "{text:?}: {error}");
    }
    let oversized = format!("---\n# {}\nagent: coder\n---\nBody\n", "x".repeat(16_384));
    assert_eq!(
        Step::parse("1-a.md", &oversized).err().unwrap().0,
        "step metadata exceeds 16 KiB"
    );
}

const AGENT: &str = "---\nversion: 1\nname: NAME\ndescription: Test role.\ncapacity: both\npermissions: trusted\ntools: [read, search, edit, execute]\n---\nWork carefully.\n";

fn project(tag: &str) -> PathBuf {
    let dir = folder(tag, &[]);
    std::fs::create_dir(dir.join("agents")).unwrap();
    for name in ["coder", "reviewer"] {
        std::fs::write(
            dir.join(format!("agents/{name}.md")),
            AGENT.replace("NAME", name),
        )
        .unwrap();
    }
    dir.canonicalize().unwrap()
}

fn config() -> Config {
    Config::read(
        br#"{"version":1,"mode":"local-only","model":"fixture","litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"TEST_KEY"},"checks":{"test":{"argv":["/usr/bin/true"]},"build":{"argv":["/usr/bin/true"],"timeout_secs":5}}}"#.as_slice(),
    )
    .unwrap()
}

fn invocation(project: &Path, extra: &[&str]) -> Invocation {
    let mut args: Vec<OsString> = ["sequence", "run", "prompts", "--project"]
        .map(OsString::from)
        .to_vec();
    args.push(project.into());
    args.extend(extra.iter().map(OsString::from));
    let (invocation, folder) = Invocation::parse_sequence(args, project).unwrap();
    assert_eq!(folder, project.join("prompts"));
    invocation
}

fn key(name: &str) -> Option<OsString> {
    (name == "TEST_KEY").then(|| "secret".into())
}

#[test]
fn sequence_options_reject_prompt_sources_jsonl_and_other_commands() {
    let cwd = std::env::temp_dir();
    let parse = |args: &[&str]| {
        Invocation::parse_sequence(args.iter().map(OsString::from), &cwd)
            .err()
            .map(|e| e.0)
    };
    assert_eq!(parse(&["sequence", "run", "dir"]), None);
    assert_eq!(
        parse(&["sequence", "run", "dir", "--preview", "--no-sync"]),
        None
    );
    assert_eq!(
        parse(&["sequence", "run", "dir", "--output", "human"]),
        None
    );
    for (args, reason) in [
        (&["sequence", "run"][..], "provide a prompt folder"),
        (&["sequence", "run", "a", "b"], "one prompt folder"),
        (
            &["sequence", "run", "a", "--prompt-file", "p"],
            "prompt sources reject",
        ),
        (
            &["sequence", "run", "a", "--output", "jsonl"],
            "--output jsonl is unsupported",
        ),
        (&["sequence", "show"], "unsupported sequence command"),
        (
            &["sequence", "resume", "s1"],
            "unsupported sequence command",
        ),
        (&["sequence"], "unsupported sequence command"),
        (&["single", "run", "a"], "expected sequence command"),
        (&["sequence", "run", "a", "--mode", "nope"], "mode must be"),
    ] {
        let error = parse(args).expect("rejects");
        assert!(error.contains(reason), "{args:?}: {error}");
    }
}

#[test]
fn every_step_resolves_with_its_metadata_before_launch() {
    let project = project("resolve");
    let steps = vec![
        Step::parse("1-a.md", "Plain.\n").unwrap(),
        Step::parse(
            "2-b.md",
            "---\nagent: reviewer\nverify: build\n---\nReview.\n",
        )
        .unwrap(),
        Step::parse("3-c.md", "Plain again.\n").unwrap(),
    ];
    let requests = sequence::resolve(
        &invocation(&project, &["--verify", "test"]),
        &config(),
        &steps,
        key,
    )
    .unwrap();
    let agents: Vec<_> = requests
        .iter()
        .map(|r| r.agent.as_ref().map(|a| a.name().to_owned()))
        .collect();
    assert_eq!(agents, [None, Some("reviewer".into()), None]);
    let checks: Vec<_> = requests
        .iter()
        .map(|r| r.verify.as_ref().map(|c| (c.name.clone(), c.timeout_secs)))
        .collect();
    assert_eq!(
        checks,
        [
            Some(("test".into(), 600)),
            Some(("build".into(), 5)),
            Some(("test".into(), 600))
        ]
    );
    assert_eq!(
        requests
            .iter()
            .map(|r| r.prompt.as_str())
            .collect::<Vec<_>>(),
        ["Plain.\n", "Review.\n", "Plain again.\n"]
    );
    // Invocation options apply to every step; metadata cannot change them.
    assert!(
        requests
            .iter()
            .all(|r| r.model == "fixture" && r.timeout_secs == 1800)
    );

    // --agent applies to every step; agreeing metadata is accepted.
    let requests = sequence::resolve(
        &invocation(&project, &["--agent", "reviewer", "--verify", "test"]),
        &config(),
        &steps,
        key,
    )
    .unwrap();
    assert!(
        requests
            .iter()
            .all(|r| r.agent.as_ref().unwrap().name() == "reviewer")
    );
    // Without --verify, nothing is gated.
    let ungated = [
        Step::parse("1-a.md", "Plain.\n").unwrap(),
        Step::parse("3-c.md", "Plain again.\n").unwrap(),
    ];
    let requests = sequence::resolve(&invocation(&project, &[]), &config(), &ungated, key).unwrap();
    assert!(requests.iter().all(|r| r.verify.is_none()));
}

#[test]
fn metadata_conflicts_and_missing_references_name_the_step() {
    let project = project("conflict");
    let config = config();
    let reject = |extra: &[&str], text: &str| {
        let steps = vec![
            Step::parse("1-a.md", "Plain.\n").unwrap(),
            Step::parse("2-b.md", text).unwrap(),
        ];
        let (index, error) = sequence::resolve(&invocation(&project, extra), &config, &steps, key)
            .err()
            .expect("rejects");
        assert_eq!(index, 1);
        error.0
    };
    assert_eq!(
        reject(&["--agent", "coder"], "---\nagent: reviewer\n---\nB\n"),
        "step metadata agent conflicts with --agent"
    );
    assert_eq!(
        reject(&[], "---\nverify: build\n---\nB\n"),
        "step metadata verify requires --verify"
    );
    assert_eq!(
        reject(&["--verify", "test"], "---\nverify: missing\n---\nB\n"),
        "verification check is not defined in config checks"
    );
    assert_eq!(
        reject(&[], "---\nagent: absent\n---\nB\n"),
        "agent is not defined in project agents/"
    );
    // A missing key rejects at the first step, before any launch.
    let steps = vec![Step::parse("1-a.md", "Plain.\n").unwrap()];
    let (index, error) = sequence::resolve(&invocation(&project, &[]), &config, &steps, |_| None)
        .err()
        .unwrap();
    assert_eq!(
        (index, error.0),
        (0, "API key environment reference is missing or empty")
    );
}
