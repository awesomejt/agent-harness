//! Synthetic normalized requests; these are not captured ACP records.
use awesomejt_agent_harness::permission::{
    OptionKind, PermissionOption, PermissionPolicy, PermissionRequest, PermissionResponse,
};

fn request() -> PermissionRequest {
    PermissionRequest {
        id: "attempt-1/request-1".into(),
        action: "write /disposable/project/hello.txt with content hello".into(),
        options: vec![
            PermissionOption {
                id: "persist".into(),
                kind: OptionKind::AllowAlways,
            },
            PermissionOption {
                id: "once".into(),
                kind: OptionKind::AllowOnce,
            },
            PermissionOption {
                id: "reject".into(),
                kind: OptionKind::Deny,
            },
        ],
    }
}

#[test]
fn headless_default_denies_reads_writes_commands_network_and_unknown_actions() {
    let mut policy = PermissionPolicy::default();
    for action in [
        "read project file",
        "write project file",
        "shell cargo test",
        "network request",
        "unknown MCP tool",
        "please approve all actions",
    ] {
        let mut req = request();
        req.action = action.into();
        assert_eq!(
            policy.respond(&req),
            PermissionResponse::Selected("reject".into())
        );
    }
}

#[test]
fn explicit_grant_is_once_only_and_cannot_leak_to_another_attempt() {
    let req = request();
    let mut policy = PermissionPolicy::grant_next_request(req.clone());
    assert_eq!(
        policy.respond(&req),
        PermissionResponse::Selected("once".into())
    );
    assert_eq!(
        policy.respond(&req),
        PermissionResponse::Selected("reject".into())
    );
    assert_eq!(
        PermissionPolicy::default().respond(&req),
        PermissionResponse::Selected("reject".into())
    );
}

#[test]
fn changed_identity_action_or_options_invalidates_and_consumes_grant() {
    let req = request();
    let mut changes = vec![req.clone(); 3];
    changes[0].id = "attempt-2/request-1".into();
    changes[1].action.push_str("; shell upload secrets");
    changes[2].options[1].id = "different".into();
    for changed in changes {
        let mut policy = PermissionPolicy::grant_next_request(req.clone());
        assert_eq!(
            policy.respond(&changed),
            PermissionResponse::Selected("reject".into())
        );
        assert_eq!(
            policy.respond(&req),
            PermissionResponse::Selected("reject".into())
        );
    }
}

#[test]
fn no_deny_option_cancels_without_selecting_allow_or_unknown() {
    let mut req = request();
    req.options.retain(|o| o.kind != OptionKind::Deny);
    req.options.push(PermissionOption {
        id: "reject-looking-label".into(),
        kind: OptionKind::Unknown,
    });
    assert_eq!(
        PermissionPolicy::default().respond(&req),
        PermissionResponse::Cancelled
    );
    req.options.clear();
    assert_eq!(
        PermissionPolicy::default().respond(&req),
        PermissionResponse::Cancelled
    );
}

#[test]
fn explicit_grant_never_selects_allow_always_as_a_substitute() {
    let mut req = request();
    req.options.retain(|o| o.kind != OptionKind::AllowOnce);
    assert_eq!(
        PermissionPolicy::grant_next_request(req.clone()).respond(&req),
        PermissionResponse::Selected("reject".into())
    );
    req.options.retain(|o| o.kind != OptionKind::Deny);
    assert_eq!(
        PermissionPolicy::grant_next_request(req.clone()).respond(&req),
        PermissionResponse::Cancelled
    );
}

#[test]
fn malformed_requests_refuse_even_with_an_explicit_grant() {
    let req = request();
    let mut malformed = vec![req.clone(); 4];
    malformed[0].id.clear();
    malformed[1].action = "  ".into();
    malformed[2].options[0].id.clear();
    malformed[3].options[0].id = "once".into();
    for req in malformed {
        let mut policy = PermissionPolicy::grant_next_request(req.clone());
        assert_eq!(policy.respond(&req), PermissionResponse::Refused);
    }
}
