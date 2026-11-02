use std::io::{self, Write};
use std::process::ExitCode;

fn main() -> ExitCode {
    match awesomejt_agent_harness::response(std::env::args_os().skip(1)) {
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
