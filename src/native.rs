//! Built-in OpenCode API-key route. No project configuration or login-store I/O.
use crate::config::{Invalid, Resolved};
use serde_json::{Value, json};

pub(crate) fn routing(request: &Resolved) -> Value {
    json!({
        "provider": {},
        "enabled_providers": ["opencode"],
        "model": request.runtime_model(),
        "small_model": request.runtime_model(),
    })
}

pub(crate) fn validate_effective(request: &Resolved, effective: &Value) -> Result<(), Invalid> {
    let desired = routing(request);
    for field in ["provider", "enabled_providers", "model", "small_model"] {
        if effective[field] != desired[field] {
            return Err(Invalid(
                "native effective routing differs from selected built-in target",
            ));
        }
    }
    // A provider denylist is not part of this route; it can disable the target.
    if effective
        .get("disabled_providers")
        .is_some_and(|v| v != &json!([]))
    {
        return Err(Invalid("native effective provider restrictions differ"));
    }
    Ok(())
}
