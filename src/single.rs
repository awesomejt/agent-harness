//! First-slice orchestration; input validation always precedes project writes.
use crate::{
    config::{Config, Exit, Invocation},
    project_config::Plan,
};
use std::ffi::OsString;

pub fn run(args: Vec<OsString>) -> Exit {
    let cwd = match std::env::current_dir() {
        Ok(cwd) => cwd,
        Err(_) => return Exit::Invalid,
    };
    let resolved = (|| {
        let invocation = Invocation::parse(args, &cwd)?;
        let config = Config::open(&invocation.config_path())?;
        invocation.resolve(
            config,
            |name| std::env::var_os(name),
            std::io::stdin().lock(),
        )
    })();
    let request = match resolved {
        Ok(request) => request,
        Err(error) => {
            eprintln!("ah: {}; use --help", error.0);
            return Exit::Invalid;
        }
    };
    if request.preview {
        eprintln!("ah: preview is not yet supported");
        return Exit::Invalid;
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = request;
        eprintln!("ah: coding runs currently support tested macOS only");
        Exit::Invalid
    }
    #[cfg(target_os = "macos")]
    {
        let plan = match Plan::prepare(&request) {
            Ok(plan) => plan,
            Err(error) => {
                eprintln!("ah: {}", error.0);
                return Exit::Invalid;
            }
        };
        let runtime = match tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
        {
            Ok(runtime) => runtime,
            Err(_) => return Exit::Failed,
        };
        runtime.block_on(async {
            let adapter = match crate::runtime::Runtime::new(&request, &plan) { Ok(adapter) => adapter, Err(exit) => return exit };
            // Preflight consumes an isolated routing snapshot; no project code or
            // plugins execute. Only then persist the already validated plan.
            if let Err(exit) = adapter.preflight(&request, &plan).await { eprintln!("ah: OpenCode preflight failed (requires 1.18.30 and exact isolated routing/permissions)"); return exit; }
            if tokio::time::Instant::now() >= adapter.deadline { return Exit::Cancelled; }
            if let Err(error) = plan.apply() { eprintln!("ah: {}", error.0); return Exit::Invalid; }
            tokio::task::yield_now().await;
            if adapter.cancelled.is_cancelled() || tokio::time::Instant::now() >= adapter.deadline { return Exit::Cancelled; }
            eprintln!("ah: local-only via OpenCode 1.18.30; model ah-litellm/{}; permissions {:?}", request.model, request.permissions);
            crate::acp::run(&adapter, &request).await
        })
    }
}
