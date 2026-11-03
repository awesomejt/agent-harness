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
fn named_agent_preview_reports_mapping_and_unsupported_effort_refuses_without_writes() {
    let project = std::env::temp_dir().join(format!("ah-cli-agent-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&project);
    std::fs::create_dir_all(project.join("agents")).unwrap();
    std::fs::write(
        project.join("agents/reviewer.md"),
        include_str!("../agents/reviewer.md"),
    )
    .unwrap();
    std::fs::write(
        project.join("agents/thinker.md"),
        include_str!("../agents/reviewer.md")
            .replace("name: reviewer", "name: thinker")
            .replace("\ntools:", "\neffort: high\ntools:"),
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
    let run = |name: &str, extra: &[&str]| {
        Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(["single", "review it", "--agent", name])
            .args(extra)
            .current_dir(&project)
            .env("AH_CLI_AGENT_KEY", "secret-value")
            .output()
            .unwrap()
    };
    let output = run("reviewer", &["--preview", "--permissions", "trusted"]);
    assert_eq!(output.status.code(), Some(0));
    let stdout = String::from_utf8(output.stdout).unwrap();
    assert!(stdout.contains("agent: \"reviewer\" (capacity specialized; ceiling read-only; tools [read, search]; effort default)"));
    assert!(stdout.contains(".opencode/agents/reviewer.md: emitted agent"));
    assert!(
        stdout
            .contains("runtime: default agent with effective permissions [\"read\", \"search\"]\n")
    );
    assert!(!stdout.contains("Inspect the change") && !stdout.contains("secret-value"));
    assert_eq!(listing(), before);
    let output = run("reviewer", &["--preview"]);
    assert!(
        String::from_utf8(output.stdout)
            .unwrap()
            .contains("effective permissions deny (invocation)\n")
    );

    let output = run("thinker", &["--preview"]);
    assert_eq!(output.status.code(), Some(0));
    assert!(String::from_utf8(output.stdout).unwrap().contains(
        "effort high); OpenCode emission: managed project file (see planned changes); runtime: default agent with effective permissions deny (invocation); execution refused: agent effort is unsupported"
    ));
    // Refusal precedes runtime discovery, the network and project writes.
    let output = run("thinker", &[]);
    assert_eq!(output.status.code(), Some(2));
    assert!(output.stdout.is_empty());
    assert!(
        String::from_utf8(output.stderr)
            .unwrap()
            .contains("agent effort is unsupported by OpenCode 2.2.5; only default effort runs")
    );
    assert_eq!(listing(), before);
    std::fs::remove_dir_all(project).unwrap();
}

/// D039: a machine consumer sees only version-1 records on stdout, ending in
/// exactly one result record, even when the invocation is rejected.
#[test]
fn machine_output_rejections_end_in_one_result_record() {
    let project = std::env::temp_dir().join(format!("ah-cli-machine-{}", std::process::id()));
    std::fs::create_dir_all(&project).unwrap();
    let project_arg = project.to_str().unwrap();
    for (args, reason) in [
        (
            vec![
                "single",
                "Task",
                "--project",
                project_arg,
                "--output",
                "jsonl",
            ],
            "cannot open input file",
        ),
        (
            vec!["single", "Task", "--output", "jsonl", "--preview"],
            "--output jsonl does not support --preview; preview is human-readable only",
        ),
        (
            vec!["single", "Task", "--output", "jsonl", "--output", "jsonl"],
            "duplicate option",
        ),
        (
            vec!["single", "--output", "jsonl"],
            "provide inline prompt or --prompt-file PATH|-",
        ),
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(&args)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(2), "{args:?}");
        let stdout = String::from_utf8(output.stdout).unwrap();
        let records: Vec<serde_json::Value> = stdout
            .lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect();
        assert!(stdout.ends_with('\n'));
        assert_eq!(records.len(), 2, "{stdout}");
        assert_eq!(records[0]["type"], "run.started");
        assert_eq!(records[0]["seq"], 0);
        assert_eq!(records[0]["harness_version"], env!("CARGO_PKG_VERSION"));
        let result = &records[1];
        assert_eq!(result["v"], 1);
        assert_eq!(result["seq"], 1);
        assert_eq!(result["run"], records[0]["run"]);
        assert_eq!(result["type"], "result");
        assert_eq!(result["outcome"], "rejected");
        assert_eq!(result["exit"], 2);
        assert_eq!(result["reason"], reason, "{args:?}");
        assert_eq!(result["response"], serde_json::Value::Null);
        assert_eq!(result["attempts"], serde_json::json!([]));
        assert_eq!(result["fallback"], false);
        assert!(result.get("attempt").is_none());
        // Diagnostics stay on stderr in the human format.
        let stderr = String::from_utf8(output.stderr).unwrap();
        assert!(stderr.lines().all(|line| line.starts_with("ah: run=")));
        assert!(stderr.contains(reason));
    }
    // An unsupported or absent value is not machine mode: human rejection only.
    for args in [
        vec!["single", "Task", "--output", "xml"],
        vec!["single", "Task", "--output"],
    ] {
        let output = Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(&args)
            .output()
            .unwrap();
        assert_eq!(output.status.code(), Some(2));
        assert!(output.stdout.is_empty(), "{args:?}");
    }
    std::fs::remove_dir_all(project).unwrap();
}
