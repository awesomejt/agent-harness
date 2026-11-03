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

/// Submission evidence must be affirmative; an absent acknowledgement is unknown.
#[derive(Clone, Copy, Debug, Default, PartialEq, Eq)]
pub enum Submission {
    #[default]
    Unknown,
    Attempted,
    NotAttempted,
}

/// Conservative facts established by the supervisor.
#[derive(Clone, Copy, Debug)]
pub struct Evidence {
    pub mode: Mode,
    pub failure: Failure,
    pub submission: Submission,
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
#[must_use]
pub fn decide(e: &Evidence) -> Decision {
    if e.mode == Mode::LocalFirst
        && matches!(
            e.failure,
            Failure::Unavailable | Failure::RateLimit | Failure::Transport
        )
        && e.submission == Submission::NotAttempted
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
