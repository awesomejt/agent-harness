use std::process::Command;

#[test]
fn version_matches_package_metadata() {
    for flag in ["--version", "-V"] {
        let output = Command::new(env!("CARGO_BIN_EXE_ah"))
            .arg(flag)
            .output()
            .unwrap();
        assert!(output.status.success());
        assert_eq!(
            output.stdout,
            format!("ah {}\n", env!("CARGO_PKG_VERSION")).as_bytes()
        );
        assert!(output.stderr.is_empty());
    }
}

#[test]
fn help_explains_single_scope() {
    for args in [vec![], vec!["--help"], vec!["-h"]] {
        let output = Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(args)
            .output()
            .unwrap();
        assert!(output.status.success());
        let stdout = String::from_utf8(output.stdout).unwrap();
        assert!(stdout.contains("Usage: ah [--help | --version]"));
        assert!(stdout.contains("ah single PROMPT"));
        assert!(output.stderr.is_empty());
    }
}

#[test]
fn unsupported_commands_and_extra_arguments_fail() {
    for args in [
        vec!["single"],
        vec!["--mode", "local-only"],
        vec!["--version", "ignored"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(args)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(2));
        assert!(output.stdout.is_empty());
        assert!(String::from_utf8(output.stderr).unwrap().contains("--help"));
    }
}

#[cfg(unix)]
#[test]
fn closed_stdout_fails_without_panicking() {
    use std::os::fd::OwnedFd;
    use std::os::unix::net::UnixStream;
    use std::process::Stdio;

    let (writer, reader) = UnixStream::pair().unwrap();
    drop(reader);
    let output = Command::new(env!("CARGO_BIN_EXE_ah"))
        .arg("--help")
        .stdout(Stdio::from(OwnedFd::from(writer)))
        .output()
        .unwrap();
    assert_eq!(output.status.code(), Some(1));
    assert!(output.stderr.is_empty());
}

#[cfg(unix)]
#[test]
fn named_agent_preview_reports_selection_and_execution_refuses_without_writes() {
    let project = std::env::temp_dir().join(format!("ah-cli-agent-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&project);
    std::fs::create_dir_all(project.join("agents")).unwrap();
    std::fs::write(
        project.join("agents/reviewer.md"),
        include_str!("../agents/reviewer.md"),
    )
    .unwrap();
    std::fs::write(
        project.join("ah.json"),
        r#"{"version":1,"mode":"local-only","model":"proxy","litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"AH_CLI_AGENT_KEY"}}"#,
    )
    .unwrap();
    let listing = || {
        let mut names: Vec<_> = std::fs::read_dir(&project)
            .unwrap()
            .map(|e| e.unwrap().file_name())
            .collect();
        names.sort();
        names
    };
    let before = listing();
    let run = |extra: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(["single", "review it", "--agent", "reviewer"])
            .args(extra)
            .current_dir(&project)
            .env("AH_CLI_AGENT_KEY", "secret-value")
            .output()
            .unwrap()
    };
    let output = run(&["--preview"]);
    assert_eq!(output.status.code(), Some(0));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("agent: \"reviewer\" (capacity specialized; ceiling read-only; tools [read, search]; effort default)"));
    assert!(stdout.contains(".opencode/agents/reviewer.md: emitted agent"));
    assert!(stdout.contains("named execution refused until constraint enforcement (P4.3)"));
    assert!(!stdout.contains("Inspect the change") && !stdout.contains("secret-value"));
    assert_eq!(listing(), before);

    let output = run(&[]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(
        String::from_utf8(output.stderr)
            .unwrap()
            .contains("named agent execution requires constraint enforcement (P4.3)")
    );
    assert_eq!(listing(), before);
    std::fs::remove_dir_all(project).unwrap();
}
