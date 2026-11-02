//! Minimal CLI boundary; runtime integration is introduced in later tasks.

use std::ffi::OsString;

pub mod config;
pub mod permission;

const HELP: &str = "agent-harness (ah)\n\nUsage: ah [--help | --version]\n\nOptions:\n  -h, --help     Show this help\n  -V, --version  Show package version\n\nScaffold only; coding runs are not implemented yet.\n";

/// Resolve the scaffold's informational arguments without launching a runtime.
pub fn response(args: impl IntoIterator<Item = OsString>) -> Result<String, &'static str> {
    let mut args = args.into_iter();
    let first = args.next();
    if args.next().is_some() {
        return Err("expected at most one option; use --help");
    }

    let Some(first) = first else {
        return Ok(HELP.to_owned());
    };
    match first.to_str() {
        Some("--help" | "-h") => Ok(HELP.to_owned()),
        Some("--version" | "-V") => Ok(format!("ah {}\n", env!("CARGO_PKG_VERSION"))),
        _ => Err("unsupported argument; use --help"),
    }
}

#[cfg(all(test, unix))]
mod tests {
    use super::response;
    use std::ffi::OsString;
    use std::os::unix::ffi::OsStringExt;

    #[test]
    fn non_utf8_argument_is_rejected() {
        assert!(response([OsString::from_vec(vec![0xff])]).is_err());
    }
}
