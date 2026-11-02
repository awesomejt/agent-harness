//! First-slice orchestration; input validation always precedes project writes.
use crate::{
    config::{Config, Exit, Invocation},
    project_config::Plan,
};
use std::ffi::OsString;

pub fn run(args: Vec<OsString>) -> Exit {
    let progress = crate::progress::Progress::new();
    let exit = execute(args, &progress);
    progress.finish(exit)
}

fn execute(args: Vec<OsString>, progress: &crate::progress::Progress) -> Exit {
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
            progress.event(format!("{}; use --help", error.0));
            return Exit::Invalid;
        }
    };
    if request.preview {
        progress.event("preview is not yet supported");
        return Exit::Invalid;
    }
    #[cfg(not(target_os = "macos"))]
    {
        let _ = request;
        progress.event("coding runs currently support tested macOS only");
        Exit::Invalid
    }
    #[cfg(target_os = "macos")]
    {
        let deadline =
            tokio::time::Instant::now() + std::time::Duration::from_secs(request.timeout_secs);
        let plan = match Plan::prepare(&request) {
            Ok(plan) => plan,
            Err(error) => {
                progress.event(error.0);
                return Exit::Invalid;
            }
        };
        if tokio::time::Instant::now() >= deadline {
            return Exit::Cancelled;
        }
        let runtime = match tokio::runtime::Builder::new_current_thread()
            .enable_all()
            .build()
        {
            Ok(runtime) => runtime,
            Err(_) => return Exit::Failed,
        };
        runtime.block_on(async {
            let adapter = match crate::runtime::Runtime::new(&request, &plan, deadline, progress.clone()) { Ok(adapter) => adapter, Err(exit) => return exit };
            // Preflight consumes an isolated routing snapshot; no project code or
            // plugins execute. Only then persist the already validated plan.
            if let Err(exit) = adapter.preflight(&request, &plan).await { progress.event("preflight failed (requires OpenCode 1.18.30 and exact isolated routing/permissions)"); return exit; }
            if tokio::time::Instant::now() >= adapter.deadline { return Exit::Cancelled; }
            if let Err(error) = plan.apply() { progress.event(error.0); return Exit::Invalid; }
            tokio::task::yield_now().await;
            if adapter.cancelled.is_cancelled() || tokio::time::Instant::now() >= adapter.deadline { return Exit::Cancelled; }
            progress.event(format!("attempt=1 local-only via OpenCode 1.18.30; model ah-litellm/{}; permissions {:?}", request.model, request.permissions));
            crate::acp::run(&adapter, &request).await
        })
    }
}
