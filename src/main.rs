use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.first().is_some_and(|arg| arg == "single") {
        let exit = awesomejt_agent_harness::single::run(args);
        if exit == awesomejt_agent_harness::config::Exit::Uncertain {
            eprintln!(
                "ah: uncertain completion or cleanup; inspect project effects before retrying"
            );
        } else if exit != awesomejt_agent_harness::config::Exit::Success {
            eprintln!("ah: run stopped ({exit:?}); no automatic retry or fallback");
        }
        return ExitCode::from(exit as u8);
    }
    match awesomejt_agent_harness::response(args) {
        Ok(output) => match io::stdout().lock().write_all(output.as_bytes()) {
            Ok(()) => ExitCode::SUCCESS,
            Err(_) => ExitCode::FAILURE,
        },
        Err(message) => {
            let _ = writeln!(io::stderr().lock(), "ah: {message}");
            ExitCode::from(2)
        }
    }
}
