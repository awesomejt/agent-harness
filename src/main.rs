use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    let args: Vec<_> = std::env::args_os().skip(1).collect();
    if args.first().is_some_and(|arg| arg == "single") {
        let exit = awesomejt_agent_harness::single::run(args);
        return ExitCode::from(exit as u8);
    }
    if args.first().is_some_and(|arg| arg == "sequence") {
        let exit = awesomejt_agent_harness::sequence::run(args);
        return ExitCode::from(exit as u8);
    }
    if args.first().is_some_and(|arg| arg == "ralph") {
        let exit = awesomejt_agent_harness::ralph::run(args);
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
