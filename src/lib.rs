//! Minimal CLI boundary; runtime integration is introduced in later tasks.

use std::ffi::OsString;

const HELP: &str = "agent-harness (ah)\n\nUsage: ah [--help | --version]\n\nOptions:\n  -h, --help     Show this help\n  -V, --version  Show package version\n\nScaffold only; coding runs are not implemented yet.\n";

/// Resolve the scaffold's informational arguments without launching a runtime.
pub fn response(args: impl IntoIterator<Item = OsString>) -> Result<String, &'static str> {
    let mut args = args.into_iter();
    let first = args.next();
    if args.next().is_some() {
        return Err("expected at most one option; use --help");
    }

    match first.as_deref().and_then(|arg| arg.to_str()) {
        None if first.is_none() => Ok(HELP.to_owned()),
        Some("--help" | "-h") => Ok(HELP.to_owned()),
        Some("--version" | "-V") => Ok(format!("ah {}\n", env!("CARGO_PKG_VERSION"))),
        _ => Err("unsupported argument; use --help"),
    }
}
