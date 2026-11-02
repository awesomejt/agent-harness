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
fn help_explains_scaffold_scope() {
    for args in [vec![], vec!["--help"], vec!["-h"]] {
        let output = Command::new(env!("CARGO_BIN_EXE_ah"))
            .args(args)
            .output()
            .unwrap();
        assert!(output.status.success());
        let stdout = String::from_utf8(output.stdout).unwrap();
        assert!(stdout.contains("Usage: ah [--help | --version]"));
        assert!(stdout.contains("coding runs are not implemented yet"));
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
