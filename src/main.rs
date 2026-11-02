use std::process::ExitCode;

fn main() -> ExitCode {
    match awesomejt_agent_harness::response(std::env::args_os().skip(1)) {
        Ok(output) => {
            print!("{output}");
            ExitCode::SUCCESS
        }
        Err(message) => {
            eprintln!("ah: {message}");
            ExitCode::from(2)
        }
    }
}
