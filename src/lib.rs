//! CLI information and first-slice single-run boundaries.

use std::ffi::OsString;

#[cfg(target_os = "macos")]
mod acp;
pub mod config;
pub mod permission;
#[cfg(target_os = "macos")]
mod process;
mod progress;
pub mod project_config;
#[cfg(target_os = "macos")]
mod runtime;
pub mod single;

const HELP: &str = "agent-harness (ah)\n\nUsage: ah [--help | --version]\n       ah single PROMPT [OPTIONS]\n       ah single --prompt-file PATH|- [OPTIONS]\n\nOptions:\n  -h, --help     Show this help\n  -V, --version  Show package version\n\nSingle options: --project PATH --config PATH --mode local-only --model ALIAS\n                --permissions deny|trusted --timeout-secs N --no-sync\nTrusted permits file and shell access with host privileges. Default: deny.\nCoding runs: macOS with OpenCode 1.18.30. Preview is not yet supported.\n";

/// Resolve informational arguments without launching a runtime.
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
