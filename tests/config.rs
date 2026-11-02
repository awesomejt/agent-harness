use awesomejt_agent_harness::config::{
    Config, Exit, Invalid, Invocation, MAX_INPUT_BYTES, Mode, Permissions, Source,
};
use std::ffi::OsString;
use std::io::{Cursor, Read};
use std::path::Path;

const VALID: &str = r#"{"version":1,"mode":"local-only","model":"test-alias","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"TEST_KEY"}}"#;
fn invocation(args: &[&str]) -> Invocation {
    Invocation::parse(
        args.iter().map(OsString::from),
        Path::new(env!("CARGO_MANIFEST_DIR")),
    )
    .unwrap()
}
fn config() -> Config {
    Config::read(VALID.as_bytes()).unwrap()
}

#[test]
fn resolves_overrides_without_reading_unused_stdin() {
    let request = invocation(&[
        "single",
        "edit",
        "--model",
        "other",
        "--permissions",
        "trusted",
        "--timeout-secs",
        "25",
        "--no-sync",
        "--preview",
    ]);
    let resolved = request
        .resolve(
            config(),
            |name| (name == "TEST_KEY").then(|| "key".into()),
            NeverRead,
        )
        .unwrap();
    assert_eq!(resolved.model, "other");
    assert_eq!(resolved.mode, Mode::LocalOnly);
    assert_eq!(resolved.sources.mode, Source::Config);
    assert_eq!(resolved.sources.model, Source::Invocation);
    assert_eq!(resolved.permissions, Permissions::Trusted);
    assert_eq!(resolved.timeout_secs, 25);
    assert!(resolved.no_sync && resolved.preview);
    assert_eq!(resolved.prompt, "edit");
    assert!(resolved.project.is_absolute());
    assert_eq!(resolved.api_key_env, "TEST_KEY");
}

struct NeverRead;
impl Read for NeverRead {
    fn read(&mut self, _: &mut [u8]) -> std::io::Result<usize> {
        panic!("unexpected stdin read")
    }
}

#[test]
fn missing_key_rejects_before_stdin_read() {
    assert!(
        invocation(&["single", "--prompt-file", "-"])
            .resolve(config(), |_| None, NeverRead)
            .is_err()
    );
}

#[test]
fn strict_schema_rejects_unknown_duplicate_secret_and_unsupported_fields() {
    let schema = "invalid config: expected strict version-1 JSON schema";
    for (input, expected) in [
        (
            VALID.replace("\"version\":1", "\"version\":2"),
            "unsupported config version",
        ),
        (
            VALID.replace("\"version\":1", "\"version\":1,\"version\":1"),
            schema,
        ),
        (
            VALID.replace(
                "\"version\":1",
                "\"version\":1,\"api_key\":\"SENTINEL_SECRET\"",
            ),
            schema,
        ),
        (
            VALID.replace(
                "\"api_key_env\":\"TEST_KEY\"",
                "\"api_key_env\":\"TEST_KEY\",\"api_key\":\"SENTINEL_SECRET\"",
            ),
            schema,
        ),
        (
            VALID.replace("local-only", "local-first"),
            "only local-only is supported in the first slice",
        ),
        (
            VALID.replace("\"version\":1", "\"version\":1,\"permissions\":\"prompt\""),
            schema,
        ),
        (
            VALID.replace("\"version\":1", "\"version\":1,\"timeout_secs\":0"),
            "timeout must be 1–86400 seconds",
        ),
        (
            VALID.replace("\"version\":1", "\"version\":1,\"timeout_secs\":86401"),
            "timeout must be 1–86400 seconds",
        ),
        (
            VALID.replace("\"version\":1", "\"version\":1,\"timeout_secs\":1.5"),
            schema,
        ),
        (
            VALID.replace(
                "\"version\":1",
                "\"version\":1,\"permissions\":{\"shell\":\"project\"}",
            ),
            schema,
        ),
        (
            VALID.replace("test-alias", "provider/model"),
            "model must be a 1–128 byte LiteLLM alias using letters, digits, dot, underscore or hyphen",
        ),
        (
            VALID.replace("TEST_KEY", "not a key name"),
            "api_key_env must be an environment variable name",
        ),
    ] {
        let error = Config::read(input.as_bytes())
            .err()
            .expect("invalid config accepted");
        assert_eq!(error, Invalid(expected));
        assert!(!format!("{error:?}").contains("SENTINEL_SECRET"));
    }
}

#[test]
fn endpoint_rejects_embedded_credentials_and_non_api_urls() {
    for endpoint in [
        "file:///v1",
        "http:///",
        "https://u:secret@host/v1",
        "https://host/v1?key=secret",
        "https://host/v1#secret",
        "https://host/other",
        "https://host/v1/",
        " https://host/v1",
        "http://host/x/../v1",
        "http://host/./v1",
        "http://@host/v1",
        "HTTP://HOST/v1",
        "http://host:80/v1",
    ] {
        assert!(
            Config::read(VALID.replace("http://litellm:4000/v1", endpoint).as_bytes()).is_err()
        );
    }
    assert!(
        Config::read(
            VALID
                .replace("http://litellm:4000/v1", "https://[::1]:4000/v1")
                .as_bytes()
        )
        .is_ok()
    );
}

#[test]
fn invalid_invocations_reject_without_io() {
    for (args, expected) in [
        (
            vec!["single"],
            "provide inline prompt or --prompt-file PATH|-",
        ),
        (vec!["single", "a", "b"], "conflicting prompt sources"),
        (
            vec!["single", "a", "--prompt-file", "-"],
            "conflicting prompt sources",
        ),
        (
            vec!["single", "--prompt-file", "-", "a"],
            "conflicting prompt sources",
        ),
        (
            vec!["single", "a", "--mode", "cloud-only"],
            "only local-only is supported in the first slice",
        ),
        (
            vec!["single", "a", "--permissions", "project-shell"],
            "unsupported permission policy",
        ),
        (
            vec!["single", "a", "--permissions", "prompt"],
            "unsupported permission policy",
        ),
        (
            vec!["single", "a", "--no-sync", "--no-sync"],
            "duplicate option",
        ),
        (
            vec!["single", "a", "--model", "--preview"],
            "missing option value",
        ),
        (
            vec!["single", "a", "--model", "bad/model"],
            "model must be a 1–128 byte LiteLLM alias using letters, digits, dot, underscore or hyphen",
        ),
        (
            vec!["single", "a", "--timeout-secs", "0"],
            "timeout must be 1–86400 seconds",
        ),
        (
            vec!["single", "a", "--agent", "coder"],
            "unsupported option",
        ),
    ] {
        assert_eq!(
            Invocation::parse(args.iter().map(OsString::from), Path::new(".")).err(),
            Some(Invalid(expected))
        );
    }
    assert_eq!(
        invocation(&["single", ""])
            .resolve(config(), |_| Some("key".into()), NeverRead)
            .err(),
        Some(Invalid("prompt must not be empty"))
    );
}

#[test]
fn stdin_requires_explicit_selection_and_rejects_empty_or_invalid_utf8() {
    for bytes in [
        vec![],
        b" \n".to_vec(),
        vec![0xff],
        vec![b'x'; MAX_INPUT_BYTES as usize + 1],
    ] {
        assert!(
            invocation(&["single", "--prompt-file", "-"])
                .resolve(config(), |_| Some("key".into()), Cursor::new(bytes))
                .is_err()
        );
    }
    let resolved = invocation(&["single", "--prompt-file", "-"])
        .resolve(config(), |_| Some("key".into()), Cursor::new("read me\n"))
        .unwrap();
    assert_eq!(resolved.prompt, "read me\n");
    assert_eq!(resolved.permissions, Permissions::Deny);
    assert_eq!(resolved.timeout_secs, 1800);
}

#[test]
fn config_is_bounded_and_invalid_utf8_is_rejected() {
    assert!(Config::read(Cursor::new(vec![b' '; MAX_INPUT_BYTES as usize + 1])).is_err());
    assert!(Config::read(Cursor::new([0xff])).is_err());
}

#[test]
fn project_and_prompt_file_validation() {
    assert!(
        invocation(&["single", "x", "--project", "Cargo.toml"])
            .resolve(config(), |_| Some("key".into()), NeverRead)
            .is_err()
    );
    assert!(
        invocation(&["single", "x", "--project", "absent-project"])
            .resolve(config(), |_| Some("key".into()), NeverRead)
            .is_err()
    );
    assert!(
        invocation(&["single", "--prompt-file", "."])
            .resolve(config(), |_| Some("key".into()), NeverRead)
            .is_err()
    );
    assert!(
        invocation(&["single", "--prompt-file", "absent-prompt"])
            .resolve(config(), |_| Some("key".into()), NeverRead)
            .is_err()
    );
    let resolved = invocation(&["single", "--prompt-file", "Cargo.toml"])
        .resolve(config(), |_| Some("key".into()), NeverRead)
        .unwrap();
    assert!(resolved.prompt.contains("[package]"));
}

#[test]
fn config_location_is_project_only_unless_explicitly_selected() {
    let cwd = Path::new(env!("CARGO_MANIFEST_DIR"));
    assert_eq!(
        invocation(&["single", "x", "--project", "src"]).config_path(),
        cwd.join("src/ah.json")
    );
    assert_eq!(
        invocation(&[
            "single",
            "x",
            "--project",
            "src",
            "--config",
            "selected.json"
        ])
        .config_path(),
        cwd.join("selected.json")
    );
}

#[test]
fn invalid_config_is_not_repaired_by_cli_override() {
    assert!(Config::read(VALID.replace("local-only", "cloud-only").as_bytes()).is_err());
}

#[test]
fn shell_exit_contract_is_distinct() {
    assert_eq!(
        [
            Exit::Success as u8,
            Exit::Failed as u8,
            Exit::Invalid as u8,
            Exit::Cancelled as u8,
            Exit::Uncertain as u8
        ],
        [0, 1, 2, 3, 4]
    );
}

#[test]
fn empty_key_is_rejected_before_stdin() {
    assert!(
        invocation(&["single", "--prompt-file", "-"])
            .resolve(config(), |_| Some(OsString::new()), NeverRead)
            .is_err()
    );
}

#[test]
fn checked_in_config_cannot_authorize_host_access() {
    let input = VALID.replace("\"version\":1", "\"version\":1,\"permissions\":\"trusted\"");
    assert!(Config::read(input.as_bytes()).is_err());
}

#[test]
fn effective_mode_has_invocation_provenance() {
    let resolved = invocation(&["single", "x", "--mode", "local-only"])
        .resolve(config(), |_| Some("key".into()), NeverRead)
        .unwrap();
    assert_eq!(resolved.mode, Mode::LocalOnly);
    assert_eq!(resolved.sources.mode, Source::Invocation);
}

#[cfg(unix)]
#[test]
fn fifo_prompt_rejects_without_waiting_for_a_writer() {
    use std::os::unix::ffi::OsStrExt;
    let path = std::env::temp_dir().join(format!("ah-p2-1-fifo-{}", std::process::id()));
    let cpath = std::ffi::CString::new(path.as_os_str().as_bytes()).unwrap();
    assert_eq!(unsafe { libc::mkfifo(cpath.as_ptr(), 0o600) }, 0);
    let result = invocation(&["single", "--prompt-file", path.to_str().unwrap()]).resolve(
        config(),
        |_| Some("key".into()),
        NeverRead,
    );
    std::fs::remove_file(path).unwrap();
    assert!(result.is_err());
}

#[test]
fn config_file_open_is_regular_and_bounded() {
    let directory = std::env::temp_dir().join(format!("ah-p2-1-config-{}", std::process::id()));
    std::fs::create_dir(&directory).unwrap();
    let path = directory.join("ah.json");
    std::fs::write(&path, VALID).unwrap();
    assert!(Config::open(&path).is_ok());
    assert_eq!(
        Config::open(&directory).err(),
        Some(Invalid("input path must be a regular file"))
    );
    std::fs::write(&path, vec![b' '; MAX_INPUT_BYTES as usize + 1]).unwrap();
    assert_eq!(
        Config::open(&path).err(),
        Some(Invalid("input exceeds 1 MiB"))
    );
    std::fs::remove_file(&path).unwrap();
    assert_eq!(
        Config::open(&path).err(),
        Some(Invalid("cannot open input file"))
    );
    #[cfg(unix)]
    {
        use std::os::unix::ffi::OsStrExt;
        let cpath = std::ffi::CString::new(path.as_os_str().as_bytes()).unwrap();
        assert_eq!(unsafe { libc::mkfifo(cpath.as_ptr(), 0o600) }, 0);
        assert_eq!(
            Config::open(&path).err(),
            Some(Invalid("input path must be a regular file"))
        );
        std::fs::remove_file(&path).unwrap();
        assert_eq!(
            Config::open(Path::new("/dev/null")).err(),
            Some(Invalid("input path must be a regular file"))
        );
    }
    std::fs::remove_dir(&directory).unwrap();
}
