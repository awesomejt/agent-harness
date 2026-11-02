//! Transport-independent Phase 1 permission experiment, not a wire schema.
//!
//! No prompting or I/O occurs here. A future adapter must validate and normalize
//! requests, enforce restrictions before tools execute, and deliver responses.

/// Meaning supplied by a verified adapter, never inferred from an option label.
#[derive(Clone, Debug, PartialEq, Eq)]
pub enum OptionKind {
    AllowOnce,
    AllowAlways,
    Deny,
    Unknown,
}

#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PermissionOption {
    pub id: String,
    pub kind: OptionKind,
}

/// The complete action description must include tool arguments and scope.
/// Request identity must be unique within the attempt that owns this policy.
#[derive(Clone, Debug, PartialEq, Eq)]
pub struct PermissionRequest {
    pub id: String,
    pub action: String,
    pub options: Vec<PermissionOption>,
}

#[derive(Debug, PartialEq, Eq)]
pub enum PermissionResponse {
    Selected(String),
    /// Map to protocol cancellation; if unavailable, stop the attempt.
    Cancelled,
    /// Malformed requests require attempt failure, never an invented option ID.
    Refused,
}

/// Intentionally at most one grant per policy instance for this experiment.
/// The driver owns attempt isolation; it must not move instances across attempts.
/// An explicit grant is trusted caller input, never model text.
/// Grants bind the entire request and are consumed on the next request, even on
/// mismatch. No persistent, category, wildcard, or allow-always grant exists.
#[derive(Default)]
pub struct PermissionPolicy {
    grant: Option<PermissionRequest>,
}

impl PermissionPolicy {
    pub fn grant_next_request(request: PermissionRequest) -> Self {
        Self {
            grant: Some(request),
        }
    }

    pub fn respond(&mut self, request: &PermissionRequest) -> PermissionResponse {
        let grant = self.grant.take();
        if request.id.trim().is_empty()
            || request.action.trim().is_empty()
            || request.options.iter().enumerate().any(|(index, option)| {
                option.id.trim().is_empty()
                    || request.options[..index]
                        .iter()
                        .any(|prior| prior.id == option.id)
            })
        {
            return PermissionResponse::Refused;
        }

        if grant.as_ref() == Some(request) {
            if let Some(option) = request
                .options
                .iter()
                .find(|o| o.kind == OptionKind::AllowOnce)
            {
                return PermissionResponse::Selected(option.id.clone());
            }
        }
        match request.options.iter().find(|o| o.kind == OptionKind::Deny) {
            Some(option) => PermissionResponse::Selected(option.id.clone()),
            None => PermissionResponse::Cancelled,
        }
    }
}
