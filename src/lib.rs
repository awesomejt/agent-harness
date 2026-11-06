//! CLI information and first-slice single-run boundaries.

use std::ffi::OsString;

#[cfg(target_os = "macos")]
mod acp;
pub mod agents;
#[cfg_attr(not(target_os = "macos"), allow(dead_code))]
mod claude;
pub mod config;
#[cfg_attr(not(target_os = "macos"), allow(dead_code))]
mod opencode;
pub mod permission;
mod preview;
#[cfg(target_os = "macos")]
mod probe;
#[cfg(target_os = "macos")]
mod process;
mod progress;
pub mod project_config;
pub mod ralph;
pub mod recovery;
#[cfg(target_os = "macos")]
mod runtime;
pub mod sequence;
pub mod single;
pub mod state;
mod verify;
#[cfg(target_os = "macos")]
mod worktree;

const HELP: &str = "agent-harness (ah)\n\nUsage: ah [--help | --version]\n       ah single PROMPT [OPTIONS]\n       ah single --prompt-file PATH|- [OPTIONS]\n       ah sequence run DIR [OPTIONS]\n       ah sequence resume RUN_ID [--retry|--accept] [OPTIONS]\n       ah sequence show [RUN_ID | --project PATH]\n       ah ralph run FILE --verify CHECK [--max-iterations N] [--max-runtime-secs S] [OPTIONS]\n       ah ralph resume RUN_ID [--retry|--accept] --verify CHECK [--max-iterations N] [--max-runtime-secs S] [OPTIONS]\n       ah ralph show [RUN_ID | --project PATH]\n\nOptions:\n  -h, --help     Show this help\n  -V, --version  Show package version\n\nSingle options: --project PATH --config PATH --mode local-only|cloud-only|local-first\n                --model MODEL|group:NAME --agent NAME --permissions deny|trusted\n                --timeout-secs N --no-sync --preview --output human|jsonl --verify CHECK\nTrusted permits file and shell access with host privileges. Default: deny.\n--agent runs PROJECT/agents/NAME.md as the session agent within its ceiling.\n--output jsonl writes version-1 records to stdout ending in one result record;\nhuman diagnostics stay on stderr. Not combinable with --preview.\n--verify runs config checks.CHECK after backend success; its result decides the exit.\nsequence run executes DIR/N-slug.md steps in numeric order, each a fresh single run\nwith the same options (no prompt sources or jsonl); it stops at the first step that\ndoes not complete. Step frontmatter may set agent: NAME and, under --verify, verify: CHECK.\nEach sequence keeps a private record under $XDG_STATE_HOME/agent-harness (else\n~/.local/state/agent-harness) and holds a per-project lock. show inspects records\nwithout a model; resume continues a stopped run after its completed steps (no\n--project/--config/--preview). A step that may have had effects needs --retry (new\nagent attempt) or --accept (no agent turn; a gated step reruns its check).\nralph run repeats FILE as fresh single runs (same options; no other prompt sources\nor jsonl) behind a fixed harness header; at most --max-iterations per run (1-100,\ndefault 10) and --max-runtime-secs per invocation (1-86400, default 3600). It completes\nonly when a response ends with the line AH-RALPH-COMPLETE and CHECK then passes; a\nclaim whose check fails or times out continues to a repair iteration. Any other\nnon-success stops the run. It shares the sequence lock and keeps a private record that\nralph show inspects. ralph resume re-reads FILE (no --project/--config/--preview);\nafter a stop that may have had effects it needs --retry or --accept (no agent turn;\nthe check alone decides), and a reached iteration bound needs a larger --max-iterations.\nLocal-first falls back once to configured native only if LiteLLM is unreachable before launch.\nCoding runs: macOS with OpenCode 2.2.5, or Claude Code 2.1.314 for native.target claude\n(cloud-only single runs, deny or trusted, --agent with effort, existing official CLI\nlogin). Preview: read-only local plan; no child launch or network checks.\n";

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
