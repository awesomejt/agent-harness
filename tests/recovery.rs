use awesomejt_agent_harness::recovery::{Decision, Evidence, Failure, Mode, decide};

fn eligible() -> Evidence {
    Evidence {
        mode: Mode::LocalFirst,
        failure: Failure::Unavailable,
        prompt_not_sent: true,
        cleanup_confirmed: true,
        cancelled_or_expired: false,
        configured_target_validated: true,
        constraints_preserved: true,
        prior_fallbacks: 0,
    }
}

#[test]
fn only_proven_pre_submission_availability_failures_are_eligible() {
    for failure in [Failure::Unavailable, Failure::RateLimit, Failure::Transport] {
        assert_eq!(
            decide(&Evidence {
                failure,
                ..eligible()
            }),
            Decision::Fallback
        );
        assert_eq!(
            decide(&Evidence {
                failure,
                prompt_not_sent: false,
                ..eligible()
            }),
            Decision::Stop
        );
    }
    for failure in [
        Failure::InvalidInput,
        Failure::UnsupportedConstraint,
        Failure::Authentication,
        Failure::Runtime,
        Failure::Cancelled,
        Failure::Deadline,
        Failure::Unknown,
    ] {
        assert_eq!(
            decide(&Evidence {
                failure,
                ..eligible()
            }),
            Decision::Stop
        );
    }
}

#[test]
fn every_route_and_recovery_guard_is_required() {
    for mode in [Mode::LocalOnly, Mode::CloudOnly] {
        assert_eq!(decide(&Evidence { mode, ..eligible() }), Decision::Stop);
    }
    for evidence in [
        Evidence {
            cleanup_confirmed: false,
            ..eligible()
        },
        Evidence {
            cancelled_or_expired: true,
            ..eligible()
        },
        Evidence {
            configured_target_validated: false,
            ..eligible()
        },
        Evidence {
            constraints_preserved: false,
            ..eligible()
        },
        Evidence {
            prior_fallbacks: 1,
            ..eligible()
        },
        Evidence {
            prior_fallbacks: u32::MAX,
            ..eligible()
        },
    ] {
        assert_eq!(decide(&evidence), Decision::Stop);
    }
}
