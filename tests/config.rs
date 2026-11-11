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
    assert_eq!(resolved.api_key_env.as_deref(), Some("TEST_KEY"));
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
            "local-first requires litellm and native configuration",
        ),
        (
            VALID.replace("local-only", "hybrid"),
            "mode must be local-only, cloud-only or local-first",
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
            "model must be a 1–128 byte identifier using letters, digits, dot, underscore or hyphen",
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
            vec!["single", "a", "--mode", "hybrid"],
            "mode must be local-only, cloud-only or local-first",
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
            "model must be a 1–128 byte identifier using letters, digits, dot, underscore or hyphen",
        ),
        (
            vec!["single", "a", "--timeout-secs", "0"],
            "timeout must be 1–86400 seconds",
        ),
        (
            vec!["single", "a", "--agent", "../coder"],
            "agent name requires 1–64 lowercase letters/digits with single hyphens",
        ),
        (
            vec!["single", "a", "--agent", "build"],
            "agent name is reserved by OpenCode",
        ),
        (
            vec!["single", "a", "--runtime", "opencode"],
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

const NATIVE: &str = r#"{"version":1,"mode":"cloud-only","native":{"target":"opencode","model":"gpt-5.4","api_key_env":"NATIVE_KEY"}}"#;

#[test]
fn native_resolution_needs_only_selected_credential_and_never_a_local_plan() {
    let both = NATIVE.replace("\"version\":1", "\"version\":1,\"litellm\":{\"api_base\":\"http://127.0.0.1:9/v1\",\"api_key_env\":\"UNAVAILABLE_LOCAL_KEY\"}");
    for input in [NATIVE, both.as_str()] {
        let r = invocation(&["single", "task", "--model", "selected-model", "--no-sync"])
            .resolve(
                Config::read(input.as_bytes()).unwrap(),
                |name| {
                    assert_eq!(name, "NATIVE_KEY");
                    Some("native secret".into())
                },
                NeverRead,
            )
            .unwrap();
        assert_eq!(r.mode, Mode::CloudOnly);
        assert_eq!(r.runtime_model(), "opencode/selected-model");
        assert!(r.api_base.is_none());
        assert!(awesomejt_agent_harness::project_config::Plan::prepare(&r).is_err());
    }
}

#[test]
fn mode_override_selects_explicit_route_and_credentials_before_stdin() {
    let both = VALID.replace(
        "\"version\":1",
        "\"version\":1,\"native\":{\"target\":\"opencode\",\"model\":\"gpt-5.4\",\"api_key_env\":\"NATIVE_KEY\"}",
    );
    let r = invocation(&["single", "task", "--mode", "cloud-only"])
        .resolve(
            Config::read(both.as_bytes()).unwrap(),
            |name| {
                assert_eq!(name, "NATIVE_KEY");
                Some("secret".into())
            },
            NeverRead,
        )
        .unwrap();
    assert_eq!(r.runtime_model(), "opencode/gpt-5.4");
    assert_eq!(r.mode, Mode::CloudOnly);
    assert_eq!(r.sources.mode, Source::Invocation);
    let reverse = both.replace("local-only", "cloud-only");
    let local = invocation(&["single", "task", "--mode", "local-only"])
        .resolve(
            Config::read(reverse.as_bytes()).unwrap(),
            |name| {
                assert_eq!(name, "TEST_KEY");
                Some("local secret".into())
            },
            NeverRead,
        )
        .unwrap();
    assert_eq!(local.runtime_model(), "ah-litellm/test-alias");
    assert!(
        invocation(&["single", "--prompt-file", "-", "--mode", "cloud-only"])
            .resolve(
                config(),
                |_| panic!("missing route must reject before key lookup"),
                NeverRead
            )
            .is_err()
    );
    assert!(
        invocation(&["single", "--prompt-file", "-"])
            .resolve(
                Config::read(NATIVE.as_bytes()).unwrap(),
                |_| None,
                NeverRead
            )
            .is_err()
    );
    assert!(
        invocation(&["single", "--prompt-file", "-", "--mode", "local-only"])
            .resolve(
                Config::read(NATIVE.as_bytes()).unwrap(),
                |_| panic!("missing route must reject"),
                NeverRead
            )
            .is_err()
    );
}

#[test]
fn native_schema_rejects_proxy_targets_credentials_and_inactive_invalid_blocks() {
    for input in [
        NATIVE.replace("opencode", "ah-litellm"),
        NATIVE.replace(
            "\"target\":\"opencode\"",
            "\"target\":\"opencode\",\"target\":\"opencode\"",
        ),
        NATIVE.replace(
            "\"target\":\"opencode\"",
            "\"target\":\"opencode\",\"api_key\":\"SECRET_SENTINEL\"",
        ),
        NATIVE.replace(
            "\"target\":\"opencode\"",
            "\"target\":\"opencode\",\"api_base\":\"http://proxy/v1\"",
        ),
        NATIVE.replace("gpt-5.4", "ah-litellm/model"),
        NATIVE.replace("NATIVE_KEY", "invalid-name"),
        NATIVE.replace(
            "\"native\":{\"target\":\"opencode\",\"model\":\"gpt-5.4\",\"api_key_env\":\"NATIVE_KEY\"}",
            "\"native\":null",
        ),
        NATIVE.replace("\"version\":1", "\"version\":1,\"litellm\":null"),
        NATIVE.replace(
            "\"version\":1",
            "\"version\":1,\"litellm\":{\"api_base\":\"bad\",\"api_key_env\":\"LOCAL_KEY\"}",
        ),
        VALID.replace(
            "\"version\":1",
            "\"version\":1,\"native\":{\"target\":\"other\",\"api_key_env\":\"NATIVE_KEY\"}",
        ),
    ] {
        assert!(Config::read(input.as_bytes()).is_err());
    }
}

#[test]
fn explicit_local_model_completes_a_native_config_mode_switch() {
    let both = NATIVE.replace("\"version\":1", "\"version\":1,\"litellm\":{\"api_base\":\"http://127.0.0.1:9/v1\",\"api_key_env\":\"LOCAL_KEY\"}");
    let local = invocation(&[
        "single",
        "task",
        "--mode",
        "local-only",
        "--model",
        "explicit-local",
    ])
    .resolve(
        Config::read(both.as_bytes()).unwrap(),
        |name| {
            assert_eq!(name, "LOCAL_KEY");
            Some("local secret".into())
        },
        NeverRead,
    )
    .unwrap();
    assert_eq!(local.runtime_model(), "ah-litellm/explicit-local");
    assert_eq!(local.sources.model, Source::Invocation);
    assert!(
        invocation(&["single", "--prompt-file", "-", "--mode", "local-only"])
            .resolve(
                Config::read(both.as_bytes()).unwrap(),
                |_| panic!("model validation precedes key lookup"),
                NeverRead
            )
            .is_err()
    );
    // A config whose own default mode is local-only still needs a model; CLI
    // flags do not repair malformed default configuration.
    assert!(Config::read(both.replace("cloud-only", "local-only").as_bytes()).is_err());
}

const GROUPED: &str = r#"{"version":1,"mode":"local-only","model":"group:coder","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"TEST_KEY","groups":{"coder":"proxy-coder","review":"proxy-review","spare":"proxy-coder"}}}"#;

fn local_key(name: &str) -> Option<OsString> {
    assert_eq!(name, "TEST_KEY");
    Some("secret".into())
}

#[test]
fn group_references_resolve_to_one_existing_proxy_group() {
    let r = invocation(&["single", "task"])
        .resolve(
            Config::read(GROUPED.as_bytes()).unwrap(),
            local_key,
            NeverRead,
        )
        .unwrap();
    assert_eq!(r.group.as_deref(), Some("coder"));
    assert_eq!(r.model, "proxy-coder");
    assert_eq!(r.runtime_model(), "ah-litellm/proxy-coder");
    assert_eq!(r.sources.model, Source::Config);
    // Handoff lists each distinct proxy group once, independent of selection.
    assert_eq!(r.proxy_groups, ["proxy-coder", "proxy-review"]);

    let r = invocation(&["single", "task", "--model", "group:review"])
        .resolve(
            Config::read(GROUPED.as_bytes()).unwrap(),
            local_key,
            NeverRead,
        )
        .unwrap();
    assert_eq!(
        (r.group.as_deref(), r.model.as_str()),
        (Some("review"), "proxy-review")
    );
    assert_eq!(r.sources.model, Source::Invocation);

    // A bare name is always a direct proxy model group, never a harness group.
    let r = invocation(&["single", "task", "--model", "coder"])
        .resolve(
            Config::read(GROUPED.as_bytes()).unwrap(),
            local_key,
            NeverRead,
        )
        .unwrap();
    assert_eq!((r.group.as_deref(), r.model.as_str()), (None, "coder"));

    let r = invocation(&["single", "task"])
        .resolve(config(), local_key, NeverRead)
        .unwrap();
    assert!(r.group.is_none() && r.proxy_groups.is_empty());
}

#[test]
fn undefined_or_native_group_references_reject_before_key_lookup() {
    for (args, input, expected) in [
        (
            vec!["single", "--prompt-file", "-", "--model", "group:missing"],
            GROUPED.to_owned(),
            "model group reference is not defined in litellm.groups",
        ),
        (
            vec!["single", "--prompt-file", "-", "--model", "group:coder"],
            VALID.to_owned(),
            "model group reference is not defined in litellm.groups",
        ),
        (
            vec!["single", "--prompt-file", "-", "--mode", "cloud-only", "--model", "group:coder"],
            GROUPED.replace(
                "\"version\":1",
                "\"version\":1,\"native\":{\"target\":\"opencode\",\"model\":\"gpt-5.4\",\"api_key_env\":\"NATIVE_KEY\"}",
            ),
            "model groups apply only to the LiteLLM route",
        ),
    ] {
        assert_eq!(
            invocation(&args)
                .resolve(
                    Config::read(input.as_bytes()).unwrap(),
                    |_| panic!("group validation precedes key lookup"),
                    NeverRead,
                )
                .err(),
            Some(Invalid(expected))
        );
    }
    for value in [
        "group:",
        "group:a/b",
        "Group:coder",
        "group:group:coder",
        "litellm:coder",
    ] {
        assert!(
            Invocation::parse(
                ["single", "task", "--model", value].map(OsString::from),
                Path::new("/")
            )
            .is_err(),
            "{value}"
        );
    }
}

#[test]
fn native_route_ignores_local_group_default() {
    let both = GROUPED.replace("local-only", "cloud-only").replace(
        "\"version\":1",
        "\"version\":1,\"native\":{\"target\":\"opencode\",\"model\":\"gpt-5.4\",\"api_key_env\":\"NATIVE_KEY\"}",
    );
    let r = invocation(&["single", "task"])
        .resolve(
            Config::read(both.as_bytes()).unwrap(),
            |name| {
                assert_eq!(name, "NATIVE_KEY");
                Some("secret".into())
            },
            NeverRead,
        )
        .unwrap();
    assert_eq!(r.runtime_model(), "opencode/gpt-5.4");
    assert!(r.group.is_none() && r.proxy_groups.is_empty());
    // A mode override back to LiteLLM uses the configured group default.
    let local = invocation(&["single", "task", "--mode", "local-only"])
        .resolve(Config::read(both.as_bytes()).unwrap(), local_key, NeverRead)
        .unwrap();
    assert_eq!(local.runtime_model(), "ah-litellm/proxy-coder");
}

#[test]
fn group_schema_rejects_duplicates_bounds_and_unresolved_defaults() {
    let groups =
        r#""groups":{"coder":"proxy-coder","review":"proxy-review","spare":"proxy-coder"}"#;
    let many = (0..65)
        .map(|i| format!("\"g{i}\":\"proxy\""))
        .collect::<Vec<_>>()
        .join(",");
    for (input, expected) in [
        (
            GROUPED.replace(r#""review":"proxy-review""#, r#""coder":"proxy-review""#),
            Some("invalid config: expected strict version-1 JSON schema"),
        ),
        (
            GROUPED.replace(groups, r#""groups":{}"#),
            Some("litellm.groups requires 1–64 entries"),
        ),
        (
            GROUPED.replace(groups, &format!("\"groups\":{{{many}}}")),
            Some("litellm.groups requires 1–64 entries"),
        ),
        (GROUPED.replace(groups, r#""groups":null"#), None),
        (GROUPED.replace(groups, r#""groups":["proxy-coder"]"#), None),
        (
            GROUPED.replace("\"proxy-review\"", "{\"model\":\"proxy-review\"}"),
            None,
        ),
        (
            GROUPED.replace("\"proxy-review\"", "\"provider/model\""),
            None,
        ),
        (GROUPED.replace("\"proxy-review\"", "\"group:coder\""), None),
        (GROUPED.replace("\"review\"", "\"bad name\""), None),
        (GROUPED.replace("\"review\"", "\"\""), None),
        (
            GROUPED.replace("group:coder", "group:missing"),
            Some("model group reference is not defined in litellm.groups"),
        ),
        (
            GROUPED.replace(groups, "\"x\":1").replace(",\"x\":1", ""),
            Some("model group reference is not defined in litellm.groups"),
        ),
        (
            NATIVE.replace("\"version\":1", "\"version\":1,\"model\":\"group:coder\""),
            Some("model group reference is not defined in litellm.groups"),
        ),
    ] {
        let result = Config::read(input.as_bytes());
        assert!(result.is_err(), "{input}");
        if let Some(expected) = expected {
            assert_eq!(result.err(), Some(Invalid(expected)), "{input}");
        }
    }
    // A native config may hold an inactive valid group default for --mode local-only.
    assert!(
        Config::read(
            NATIVE
                .replace("\"version\":1", "\"version\":1,\"model\":\"group:coder\",\"litellm\":{\"api_base\":\"http://litellm:4000/v1\",\"api_key_env\":\"TEST_KEY\",\"groups\":{\"coder\":\"proxy-coder\"}}")
                .as_bytes()
        )
        .is_ok()
    );
}

const LOCAL_FIRST: &str = r#"{"version":1,"mode":"local-first","model":"group:coder","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"TEST_KEY","groups":{"coder":"proxy-coder"}},"native":{"target":"opencode","model":"gpt-5.4","api_key_env":"NATIVE_KEY"}}"#;

#[test]
fn local_first_resolves_litellm_primary_with_configured_native_fallback() {
    let r = invocation(&[
        "single",
        "task",
        "--model",
        "direct-alias",
        "--permissions",
        "trusted",
        "--timeout-secs",
        "30",
    ])
    .resolve(
        Config::read(LOCAL_FIRST.as_bytes()).unwrap(),
        |name| {
            assert!(matches!(name, "TEST_KEY" | "NATIVE_KEY"));
            Some("secret".into())
        },
        NeverRead,
    )
    .unwrap();
    assert_eq!(r.mode, Mode::LocalOnly);
    assert_eq!(r.runtime_model(), "ah-litellm/direct-alias");
    assert!(r.api_base.is_some());
    let native = r.fallback.as_deref().unwrap();
    // --model selects only the primary; the fallback is the configured target.
    assert_eq!(native.mode, Mode::CloudOnly);
    assert_eq!(native.runtime_model(), "opencode/gpt-5.4");
    assert_eq!(native.sources.model, Source::Config);
    assert_eq!(native.api_key_env.as_deref(), Some("NATIVE_KEY"));
    assert!(native.api_base.is_none() && native.group.is_none());
    assert!(native.proxy_groups.is_empty() && native.fallback.is_none());
    assert_eq!(native.project, r.project);
    assert_eq!(native.permissions, Permissions::Trusted);
    assert_eq!(native.timeout_secs, 30);
    assert_eq!(native.prompt, r.prompt);
    // The repository's own AGENTS.md is named for both attempts (D040).
    assert!(
        r.instructions
            .as_ref()
            .is_some_and(|p| p.ends_with("AGENTS.md"))
    );
    assert_eq!(native.instructions, r.instructions);
    let grouped = invocation(&["single", "task"])
        .resolve(
            Config::read(LOCAL_FIRST.as_bytes()).unwrap(),
            |_| Some("secret".into()),
            NeverRead,
        )
        .unwrap();
    assert_eq!(grouped.runtime_model(), "ah-litellm/proxy-coder");
    assert_eq!(grouped.group.as_deref(), Some("coder"));
}

#[test]
fn local_first_requires_both_routes_and_both_keys_before_stdin() {
    for name in ["TEST_KEY", "NATIVE_KEY"] {
        let missing = invocation(&["single", "--prompt-file", "-"]).resolve(
            Config::read(LOCAL_FIRST.as_bytes()).unwrap(),
            |key| (key != name).then(|| "secret".into()),
            NeverRead,
        );
        assert_eq!(
            missing.err(),
            Some(Invalid("API key environment reference is missing or empty"))
        );
    }
    let no_native = r#"{"version":1,"mode":"local-first","model":"a","litellm":{"api_base":"http://litellm:4000/v1","api_key_env":"TEST_KEY"}}"#;
    let no_local = r#"{"version":1,"mode":"local-first","model":"a","native":{"target":"opencode","model":"gpt-5.4","api_key_env":"NATIVE_KEY"}}"#;
    let no_model = LOCAL_FIRST.replace("\"model\":\"group:coder\",", "");
    for (input, error) in [
        (
            no_native,
            "local-first requires litellm and native configuration",
        ),
        (
            no_local,
            "local-first requires litellm and native configuration",
        ),
        (
            no_model.as_str(),
            "local-only and local-first config require a model default",
        ),
    ] {
        assert_eq!(Config::read(input.as_bytes()).err(), Some(Invalid(error)));
    }
    // An explicit mode switch needs the selected route's own configuration.
    let cloud = NATIVE.to_owned();
    assert_eq!(
        invocation(&["single", "--prompt-file", "-", "--mode", "local-first"])
            .resolve(
                Config::read(cloud.as_bytes()).unwrap(),
                |_| panic!("missing route must reject before key lookup"),
                NeverRead
            )
            .err(),
        Some(Invalid(
            "local-first requires litellm and native configuration"
        ))
    );
    // C03-01: `--model` can supply the local model only when the config's own
    // mode is cloud-only; the own-mode local-first case above still rejects.
    let switched = NATIVE.replace(
        "\"version\":1",
        "\"version\":1,\"litellm\":{\"api_base\":\"http://litellm:4000/v1\",\"api_key_env\":\"TEST_KEY\"}",
    );
    let r = invocation(&[
        "single",
        "task",
        "--mode",
        "local-first",
        "--model",
        "fixture",
    ])
    .resolve(
        Config::read(switched.as_bytes()).unwrap(),
        |_| Some("secret".into()),
        NeverRead,
    )
    .unwrap();
    assert_eq!(r.runtime_model(), "ah-litellm/fixture");
    assert_eq!(
        r.fallback.as_deref().unwrap().runtime_model(),
        "opencode/gpt-5.4"
    );
    assert!(
        invocation(&["single", "task", "--mode", "local-first"])
            .resolve(
                Config::read(switched.as_bytes()).unwrap(),
                |_| Some("secret".into()),
                NeverRead,
            )
            .is_err()
    );
}

#[test]
fn output_format_parses_and_machine_mode_is_detected_before_validation() {
    use awesomejt_agent_harness::config::machine_output;
    let parse = |args: &[&str]| {
        Invocation::parse(args.iter().map(OsString::from), Path::new("."))
            .err()
            .map(|e| e.0)
    };
    assert_eq!(parse(&["single", "x", "--output", "human"]), None);
    assert_eq!(parse(&["single", "x", "--output", "jsonl"]), None);
    assert_eq!(
        parse(&["single", "x", "--output", "json"]),
        Some("unsupported output format")
    );
    assert_eq!(
        parse(&["single", "x", "--output", "jsonl", "--preview"]),
        Some("--output jsonl does not support --preview; preview is human-readable only")
    );
    assert_eq!(
        parse(&["single", "x", "--output", "human", "--preview"]),
        None
    );
    let scan = |args: &[&str]| machine_output(&args.iter().map(OsString::from).collect::<Vec<_>>());
    assert!(scan(&["single", "--output", "jsonl"]));
    assert!(scan(&["single", "x", "--bogus", "--output", "jsonl"]));
    assert!(!scan(&["single", "x", "--output", "human"]));
    assert!(!scan(&["single", "x", "--output"]));
    assert!(!scan(&["single", "x", "jsonl", "--output"]));
}

#[test]
fn project_instructions_are_only_a_regular_root_agents_file_inside_the_project() {
    let base = std::env::temp_dir().join(format!("ah-p4-8-instructions-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    let project = base.join("project");
    std::fs::create_dir_all(project.join("sub")).unwrap();
    let resolve = || {
        let args = ["single", "x", "--project"].map(OsString::from);
        Invocation::parse(args.into_iter().chain([project.clone().into()]), &base)
            .unwrap()
            .resolve(config(), |_| Some("key".into()), NeverRead)
    };
    // Absent: no instructions. Parent, nested and CLAUDE.md files are never named.
    std::fs::write(base.join("AGENTS.md"), "parent").unwrap();
    std::fs::write(project.join("CLAUDE.md"), "claude").unwrap();
    std::fs::write(project.join("sub/AGENTS.md"), "nested").unwrap();
    assert_eq!(resolve().unwrap().instructions, None);
    // A regular file, or a symlink to one inside the project, is named canonically.
    std::fs::write(project.join("RULES.md"), "rules").unwrap();
    std::os::unix::fs::symlink("RULES.md", project.join("AGENTS.md")).unwrap();
    let canonical = project.canonicalize().unwrap();
    assert_eq!(
        resolve().unwrap().instructions,
        Some(canonical.join("RULES.md"))
    );
    std::fs::remove_file(project.join("AGENTS.md")).unwrap();
    std::fs::write(project.join("AGENTS.md"), "rules").unwrap();
    assert_eq!(
        resolve().unwrap().instructions,
        Some(canonical.join("AGENTS.md"))
    );
    // Outside targets, dangling links and non-files refuse before key lookup or stdin.
    std::fs::remove_file(project.join("AGENTS.md")).unwrap();
    for target in [
        base.join("AGENTS.md"),
        project.join("absent"),
        project.join("sub"),
    ] {
        std::os::unix::fs::symlink(&target, project.join("AGENTS.md")).unwrap();
        let error = resolve().err().map(|e| e.0);
        assert_eq!(
            error,
            Some("project AGENTS.md must resolve to a regular file inside the project"),
            "{target:?}"
        );
        std::fs::remove_file(project.join("AGENTS.md")).unwrap();
    }
    std::fs::create_dir(project.join("AGENTS.md")).unwrap();
    assert!(resolve().is_err());
    std::fs::remove_dir_all(base).unwrap();
}

#[test]
fn packaged_example_configs_validate() {
    let examples = Path::new(env!("CARGO_MANIFEST_DIR")).join("examples");
    let mut files: Vec<_> = std::fs::read_dir(&examples)
        .unwrap()
        .map(|entry| entry.unwrap().file_name().into_string().unwrap())
        .collect();
    files.sort();
    assert_eq!(
        files,
        [
            "ah.cloud-only.json",
            "ah.local-first.json",
            "ah.local-only.json"
        ]
    );
    for (file, mode, litellm, native) in [
        ("ah.local-only.json", "local-only", true, false),
        ("ah.cloud-only.json", "cloud-only", false, true),
        ("ah.local-first.json", "local-first", true, true),
    ] {
        let path = examples.join(file);
        assert!(Config::open(&path).is_ok(), "{file}");
        let value: serde_json::Value =
            serde_json::from_slice(&std::fs::read(&path).unwrap()).unwrap();
        assert_eq!(value["mode"], mode, "{file}");
        assert_eq!(value.get("litellm").is_some(), litellm, "{file}");
        assert_eq!(value.get("native").is_some(), native, "{file}");
    }
}

fn with_checks(checks: &str) -> String {
    VALID.replacen('}', &format!("}},\"checks\":{checks}"), 1)
}

#[test]
fn check_schema_requires_named_argv_definitions() {
    let valid = with_checks(r#"{"test":{"argv":["/bin/echo","ok"],"timeout_secs":5}}"#);
    assert!(Config::read(valid.as_bytes()).is_ok(), "{valid}");
    let schema = "invalid config: expected strict version-1 JSON schema";
    for (checks, expected) in [
        ("{}", "checks requires 1–64 entries"),
        ("null", schema),
        (r#"{"test":"cargo test"}"#, schema),
        (r#"{"test":{"argv":["true"],"shell":true}}"#, schema),
        (
            r#"{"test":{"argv":["true"]},"test":{"argv":["false"]}}"#,
            schema,
        ),
        (
            r#"{"Test":{"argv":["true"]}}"#,
            "check name requires 1–64 lowercase letters/digits with single hyphens",
        ),
        (
            r#"{"test":{"argv":[]}}"#,
            "check argv requires 1–64 arguments",
        ),
        (
            r#"{"test":{"argv":["true","a\u0000b"]}}"#,
            "check argv requires 1–64 arguments of at most 4096 bytes without NUL",
        ),
        (
            r#"{"test":{"argv":["./scripts/check.sh"]}}"#,
            "check program must be an absolute path or a bare name resolved on PATH",
        ),
        (
            r#"{"test":{"argv":[""]}}"#,
            "check program must be an absolute path or a bare name resolved on PATH",
        ),
        (
            r#"{"test":{"argv":["true"],"timeout_secs":0}}"#,
            "check timeout must be 1–86400 seconds",
        ),
    ] {
        let input = with_checks(checks);
        assert_eq!(
            Config::read(input.as_bytes()).err(),
            Some(Invalid(expected)),
            "{checks}"
        );
    }
    let many: Vec<_> = (0..65)
        .map(|i| format!(r#""c{i}":{{"argv":["true"]}}"#))
        .collect();
    let input = with_checks(&format!("{{{}}}", many.join(",")));
    assert_eq!(
        Config::read(input.as_bytes()).err(),
        Some(Invalid("checks requires 1–64 entries"))
    );
    let args: Vec<_> = (0..65).map(|_| "\"a\"").collect();
    let input = with_checks(&format!(
        r#"{{"test":{{"argv":["true",{}]}}}}"#,
        args.join(",")
    ));
    assert!(Config::read(input.as_bytes()).is_err());
    // Declaring a check never runs it; an invalid --verify name rejects at parse.
    assert_eq!(
        Invocation::parse(
            ["single", "x", "--verify", "Bad"].map(OsString::from),
            Path::new("/")
        )
        .err(),
        Some(Invalid(
            "check name requires 1–64 lowercase letters/digits with single hyphens"
        ))
    );
}

#[test]
fn verify_resolves_a_declared_check_and_pins_its_program_outside_the_project() {
    use std::os::unix::fs::PermissionsExt;
    let base = std::env::temp_dir().join(format!("ah-p5-5-verify-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&base);
    let project = base.join("project");
    let bin = base.join("bin");
    std::fs::create_dir_all(project.join("bin")).unwrap();
    std::fs::create_dir_all(&bin).unwrap();
    for path in [bin.join("checker"), project.join("bin/checker")] {
        std::fs::write(&path, "#!/bin/sh\n").unwrap();
        std::fs::set_permissions(&path, std::fs::Permissions::from_mode(0o755)).unwrap();
    }
    std::fs::write(bin.join("plain"), "").unwrap();
    let resolve = |checks: &str, name: &str, path: &str| {
        let config = Config::read(with_checks(checks).as_bytes()).unwrap();
        let args = ["single", "x", "--verify", name, "--project"].map(OsString::from);
        let path = path.to_owned();
        Invocation::parse(args.into_iter().chain([project.clone().into()]), &base)
            .unwrap()
            .resolve(
                config,
                move |n| {
                    Some(
                        if n == "PATH" {
                            path.clone()
                        } else {
                            "key".into()
                        }
                        .into(),
                    )
                },
                NeverRead,
            )
    };
    let checks = r#"{"test":{"argv":["checker","--quick"]}}"#;
    // First absolute PATH entry wins; relative entries are skipped.
    let path = format!("bin:{}:/usr/bin", bin.display());
    let check = resolve(checks, "test", &path).unwrap().verify.unwrap();
    assert_eq!(check.name, "test");
    assert_eq!(check.program, bin.join("checker"));
    assert_eq!(check.args, ["--quick"]);
    assert_eq!(check.timeout_secs, 600);
    // An undeclared name is untrusted; nothing runs.
    assert_eq!(
        resolve(checks, "lint", &path).err(),
        Some(Invalid(
            "verification check is not defined in config checks"
        ))
    );
    // A program the agent could edit is rejected, through PATH or absolutely,
    // including a symlink outside the project that points into it.
    std::os::unix::fs::symlink(project.join("bin/checker"), bin.join("linked")).unwrap();
    let inside =
        "check program must resolve outside the project; agent-editable programs are untrusted";
    let in_project = format!("{}:{}", project.join("bin").display(), bin.display());
    assert_eq!(
        resolve(checks, "test", &in_project).err(),
        Some(Invalid(inside))
    );
    let absolute = format!(
        r#"{{"test":{{"argv":["{}"]}}}}"#,
        project.join("bin/checker").display()
    );
    assert_eq!(
        resolve(&absolute, "test", "/usr/bin").err(),
        Some(Invalid(inside))
    );
    let linked = r#"{"test":{"argv":["linked"]}}"#;
    assert_eq!(resolve(linked, "test", &path).err(), Some(Invalid(inside)));
    // Any in-project hop is retargetable: an in-project link to an outside
    // program, and an outside chain passing through the project, both reject.
    std::os::unix::fs::symlink(bin.join("checker"), project.join("bin/out")).unwrap();
    std::os::unix::fs::symlink(project.join("bin/out"), bin.join("chain")).unwrap();
    for program in ["out", "chain"] {
        let checks = format!(r#"{{"test":{{"argv":["{program}"]}}}}"#);
        assert_eq!(
            resolve(&checks, "test", &in_project).err(),
            Some(Invalid(inside))
        );
    }
    // K05-01: Directory symlinks traversing the project also reject.
    let outside_dir = base.join("outside_dir");
    std::fs::create_dir(&outside_dir).unwrap();
    std::os::unix::fs::symlink(project.join("bin"), outside_dir.join("to_project_bin")).unwrap();
    std::os::unix::fs::symlink(&bin, project.join("bin/to_outside_bin")).unwrap();
    let checks_dir_link = format!(
        r#"{{"test":{{"argv":["{}"]}}}}"#,
        outside_dir
            .join("to_project_bin/to_outside_bin/checker")
            .display()
    );
    assert_eq!(
        resolve(&checks_dir_link, "test", &path).err(),
        Some(Invalid(inside))
    );
    // An outside link to an outside program is executed by its found name.
    std::os::unix::fs::symlink(bin.join("checker"), bin.join("alias")).unwrap();
    let alias = r#"{"test":{"argv":["alias"]}}"#;
    assert_eq!(
        resolve(alias, "test", &path)
            .unwrap()
            .verify
            .unwrap()
            .program,
        bin.join("alias")
    );
    let missing =
        "check program is not an executable file (bare names use absolute PATH entries only)";
    for (checks, path) in [
        (r#"{"test":{"argv":["plain"]}}"#, path.as_str()),
        (r#"{"test":{"argv":["checker"]}}"#, "bin"),
        (
            r#"{"test":{"argv":["/nonexistent/checker"]}}"#,
            path.as_str(),
        ),
    ] {
        assert_eq!(
            resolve(checks, "test", path).err(),
            Some(Invalid(missing)),
            "{checks}"
        );
    }
    // No --verify: no check, even when one is declared.
    let config = Config::read(with_checks(checks).as_bytes()).unwrap();
    let args = ["single", "x", "--project"].map(OsString::from);
    let resolved = Invocation::parse(args.into_iter().chain([project.clone().into()]), &base)
        .unwrap()
        .resolve(config, |_| Some("key".into()), NeverRead)
        .unwrap();
    assert!(resolved.verify.is_none());
    std::fs::remove_dir_all(base).unwrap();
}

const CLAUDE: &str =
    r#"{"version":1,"mode":"cloud-only","native":{"target":"claude","model":"sonnet"}}"#;

#[test]
fn claude_target_uses_the_existing_login_and_reads_no_key() {
    let r = invocation(&["single", "task"])
        .resolve(
            Config::read(CLAUDE.as_bytes()).unwrap(),
            |name| panic!("no key lookup for the Claude login: {name}"),
            NeverRead,
        )
        .unwrap();
    assert_eq!(r.mode, Mode::CloudOnly);
    assert_eq!(
        r.runtime,
        awesomejt_agent_harness::config::RuntimeKind::Claude
    );
    assert_eq!(r.api_key_env, None);
    assert_eq!(r.runtime_model(), "sonnet");
    assert!(r.api_base.is_none());
    let full = invocation(&["single", "task", "--model", "claude-sonnet-5-5"])
        .resolve(
            Config::read(CLAUDE.as_bytes()).unwrap(),
            |_| None,
            NeverRead,
        )
        .unwrap();
    assert_eq!(full.runtime_model(), "claude-sonnet-5-5");
    assert_eq!(full.sources.model, Source::Invocation);
    // The LiteLLM route still runs OpenCode when a mode override selects it.
    let both = CLAUDE.replace(
        "\"version\":1",
        "\"version\":1,\"litellm\":{\"api_base\":\"http://127.0.0.1:9/v1\",\"api_key_env\":\"LOCAL_KEY\"}",
    );
    let local = invocation(&["single", "task", "--mode", "local-only", "--model", "m"])
        .resolve(
            Config::read(both.as_bytes()).unwrap(),
            |name| {
                assert_eq!(name, "LOCAL_KEY");
                Some("local".into())
            },
            NeverRead,
        )
        .unwrap();
    assert_eq!(
        local.runtime,
        awesomejt_agent_harness::config::RuntimeKind::OpenCode
    );
    assert_eq!(local.runtime_model(), "ah-litellm/m");
}

#[test]
fn claude_target_rejects_keys_and_groups() {
    for (input, message) in [
        (
            CLAUDE.replace(
                "\"sonnet\"",
                "\"sonnet\",\"api_key_env\":\"ANTHROPIC_API_KEY\"",
            ),
            "native target claude uses the existing official CLI login; api_key_env is unsupported",
        ),
        (
            CLAUDE.replace("\"sonnet\"", "\"sonnet\",\"api_key_env\":null"),
            "invalid config: expected strict version-1 JSON schema",
        ),
        (
            NATIVE.replace(",\"api_key_env\":\"NATIVE_KEY\"", ""),
            "native target opencode requires api_key_env",
        ),
        (
            CLAUDE.replace("claude", "codex"),
            "native target must be opencode (built-in API-key provider) or claude (official CLI login)",
        ),
    ] {
        assert_eq!(
            Config::read(input.as_bytes()).err(),
            Some(Invalid(message)),
            "{input}"
        );
    }
    let group = invocation(&["single", "task", "--model", "group:coder"]).resolve(
        Config::read(CLAUDE.as_bytes()).unwrap(),
        |_| None,
        NeverRead,
    );
    assert!(group.is_err());
}

#[test]
fn claude_fallback_resolves_runtime_without_reading_native_credentials() {
    use awesomejt_agent_harness::config::RuntimeKind;
    let both = CLAUDE.replace(
        "\"version\":1",
        "\"version\":1,\"litellm\":{\"api_base\":\"http://127.0.0.1:9/v1\",\"api_key_env\":\"LOCAL_KEY\"}",
    );
    let r = invocation(&[
        "single",
        "task",
        "--mode",
        "local-first",
        "--model",
        "m",
        "--permissions",
        "trusted",
    ])
    .resolve(
        Config::read(both.as_bytes()).unwrap(),
        |name| {
            assert_eq!(name, "LOCAL_KEY");
            Some("local".into())
        },
        NeverRead,
    )
    .unwrap();
    assert_eq!(r.runtime, RuntimeKind::OpenCode);
    assert_eq!(r.runtime_model(), "ah-litellm/m");
    let f = r.fallback.as_deref().unwrap();
    assert_eq!(f.runtime, RuntimeKind::Claude);
    assert_eq!(f.record_model(), "claude/sonnet");
    assert_eq!(f.sources.model, Source::Config);
    assert_eq!(f.mode, Mode::CloudOnly);
    assert!(f.api_key_env.is_none() && f.api_base.is_none() && f.fallback.is_none());
    assert_eq!(f.project, r.project);
    assert_eq!(f.prompt, r.prompt);
    assert_eq!(f.permissions, r.permissions);
    assert_eq!(f.instructions, r.instructions);
    assert_eq!(f.timeout_secs, r.timeout_secs);
    assert!(
        invocation(&[
            "single",
            "--prompt-file",
            "-",
            "--mode",
            "local-first",
            "--model",
            "m"
        ])
        .resolve(Config::read(both.as_bytes()).unwrap(), |_| None, NeverRead)
        .is_err()
    );
}

#[test]
fn pi_runtime_resolves_for_local_only() {
    use awesomejt_agent_harness::config::RuntimeKind;
    let pi = VALID.replace(
        "\"api_key_env\":\"TEST_KEY\"}",
        "\"api_key_env\":\"TEST_KEY\",\"runtime\":\"pi\"}",
    );
    let r = invocation(&["single", "task"])
        .resolve(
            Config::read(pi.as_bytes()).unwrap(),
            |name| {
                assert_eq!(name, "TEST_KEY");
                Some("secret".into())
            },
            NeverRead,
        )
        .unwrap();
    assert_eq!(r.runtime, RuntimeKind::Pi);
    assert_eq!(r.runtime_model(), "pi/test-alias");
    assert_eq!(r.record_model(), "pi/test-alias");
}

#[test]
fn pi_runtime_rejects_non_local_only_modes() {
    for text in [
        VALID.replace(
            "\"mode\":\"local-only\"",
            "\"mode\":\"local-first\",\"native\":{\"target\":\"opencode\",\"model\":\"m\",\"api_key_env\":\"NATIVE_KEY\"}",
        )
        .replace(
            "\"api_key_env\":\"TEST_KEY\"}",
            "\"api_key_env\":\"TEST_KEY\",\"runtime\":\"pi\"}",
        ),
        r#"{"version":1,"mode":"cloud-only","native":{"target":"opencode","model":"m","api_key_env":"K"},"litellm":{"api_base":"http://127.0.0.1:9/v1","api_key_env":"TEST_KEY","runtime":"pi"}}"#.to_string(),
        VALID.replace(
            "\"api_key_env\":\"TEST_KEY\"}",
            "\"api_key_env\":\"TEST_KEY\",\"runtime\":\"codex\"}",
        ),
    ] {
        assert!(Config::read(text.as_bytes()).is_err());
    }
}
