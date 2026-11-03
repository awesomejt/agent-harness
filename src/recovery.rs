//! Phase 3 recovery decision; this does not launch or retry an attempt.

/// Classification requires trusted, adapter-specific evidence, never error text.
#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Failure {
    InvalidInput,
    UnsupportedConstraint,
    Authentication,
    RateLimit,
    Unavailable,
    Transport,
    Runtime,
    Cancelled,
    Deadline,
    Unknown,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Mode {
    LocalOnly,
    CloudOnly,
    LocalFirst,
}

/// Conservative facts established by the supervisor. `prompt_not_sent` means
/// submission was never attempted, not merely that an acknowledgement is absent.
pub struct Evidence {
    pub mode: Mode,
    pub failure: Failure,
    pub prompt_not_sent: bool,
    pub cleanup_confirmed: bool,
    pub cancelled_or_expired: bool,
    pub configured_target_validated: bool,
    pub constraints_preserved: bool,
    pub prior_fallbacks: u32,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
pub enum Decision {
    Stop,
    Fallback,
}

/// One configured native fallback at most; no same-route automatic retry.
pub fn decide(e: &Evidence) -> Decision {
    if e.mode == Mode::LocalFirst
        && matches!(
            e.failure,
            Failure::Unavailable | Failure::RateLimit | Failure::Transport
        )
        && e.prompt_not_sent
        && e.cleanup_confirmed
        && !e.cancelled_or_expired
        && e.configured_target_validated
        && e.constraints_preserved
        && e.prior_fallbacks == 0
    {
        Decision::Fallback
    } else {
        Decision::Stop
    }
}
