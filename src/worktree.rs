//! Advisory, bounded baseline observation. Never modify or recover project files.
use crate::{config::Exit, process::OwnedChild};
use std::{path::Path, time::Duration};
use tokio::{io::AsyncReadExt, process::Command};

const LIMIT: usize = 1_048_576;

#[derive(Default, Debug, PartialEq)]
struct Counts {
    staged: usize,
    unstaged: usize,
    untracked: usize,
}

fn counts(bytes: &[u8]) -> Option<Counts> {
    let mut result = Counts::default();
    let mut records = bytes.split_inclusive(|b| *b == 0);
    while let Some(record) = records.next() {
        if record.len() < 5 || record[2] != b' ' || record.last() != Some(&0) {
            return None;
        }
        let (index, worktree) = (record[0], record[1]);
        if index == b'?' && worktree == b'?' {
            result.untracked += 1;
        } else {
            result.staged += usize::from(index != b' ');
            result.unstaged += usize::from(worktree != b' ');
            if index == b'R' || index == b'C' || worktree == b'R' || worktree == b'C' {
                // -z rename/copy records carry a second NUL-terminated pathname.
                let source = records.next()?;
                if source.len() < 2 || source.last() != Some(&0) {
                    return None;
                }
            }
        }
    }
    Some(result)
}

async fn observe(
    project: &Path,
    args: &[&str],
    bound: tokio::time::Instant,
    progress: &crate::progress::Progress,
) -> Result<Option<(std::process::ExitStatus, Vec<u8>)>, Exit> {
    if tokio::time::Instant::now() >= bound {
        return Ok(None);
    }
    // Fixed system Git, cleared routing/config environment, no optional index
    // locks or fsmonitor hook. Never echo filenames or raw Git diagnostics.
    let mut command = Command::new("/usr/bin/git");
    command
        .env_clear()
        .env("GIT_CONFIG_NOSYSTEM", "1")
        .env("GIT_CONFIG_GLOBAL", "/dev/null")
        .env("GIT_TERMINAL_PROMPT", "0")
        .env("LC_ALL", "C")
        .current_dir(project)
        .args([
            "--no-optional-locks",
            "-c",
            "core.fsmonitor=false",
            "-c",
            "core.untrackedCache=false",
        ])
        .args(args);
    let Ok(mut child) = OwnedChild::spawn(&mut command) else {
        return Ok(None);
    };
    let observed = tokio::time::timeout_at(bound, async {
        let mut bytes = Vec::new();
        child
            .child
            .stdout
            .take()?
            .take((LIMIT + 1) as u64)
            .read_to_end(&mut bytes)
            .await
            .ok()?;
        if bytes.len() > LIMIT {
            return None;
        }
        Some((child.child.wait().await.ok()?, bytes))
    })
    .await
    .ok()
    .flatten();
    if !child.cleanup().await {
        progress.event("project baseline: Git cleanup unconfirmed; refusing runtime launch");
        return Err(Exit::Uncertain);
    }
    Ok(observed)
}

pub(crate) async fn report(
    project: &Path,
    deadline: tokio::time::Instant,
    progress: &crate::progress::Progress,
) -> Result<(), Exit> {
    progress.event("project preservation: no automatic stash/reset/clean/commit/rollback; authorized runtime edits may change existing files; attribution unknown");
    let bound = deadline.min(tokio::time::Instant::now() + Duration::from_secs(2));
    // Status can run clean/process filters while comparing stat-dirty files.
    // Inspect effective config (including includes and worktree config) first;
    // any driver configuration makes status unsafe for this observation.
    let filters = observe(
        project,
        &[
            "config",
            "--includes",
            "--null",
            "--name-only",
            "--get-regexp",
            "^filter\\.",
        ],
        bound,
        progress,
    )
    .await?;
    if !matches!(filters, Some((status, ref bytes)) if status.code() == Some(1) && bytes.is_empty())
    {
        progress.event("project baseline: unavailable (system Git missing, filter configuration present, or config inspection incomplete; requires macOS Command Line Tools Git); status skipped to avoid filter execution");
        return Ok(());
    }
    let observed = observe(
        project,
        &[
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--ignore-submodules=all",
        ],
        bound,
        progress,
    )
    .await?;
    let observed = observed.and_then(|(status, bytes)| {
        if status.success() {
            counts(&bytes)
        } else {
            None
        }
    });
    match observed {
        Some(c) => progress.event(format!(
            "project baseline: {}; staged={} unstaged={} untracked={}; repository-wide counts; submodule contents excluded; paths omitted",
            if c == Counts::default() { "clean" } else { "dirty" },
            c.staged, c.unstaged, c.untracked,
        )),
        None => progress.event("project baseline: unavailable (not a Git worktree, Git error, or bounded status incomplete; requires macOS Command Line Tools Git); preservation policy still applies"),
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn nul_records_handle_renames_non_utf8_and_control_characters() {
        assert_eq!(counts(b""), Some(Counts::default()));
        assert_eq!(
            counts(b"MM both\0R  new\nname\0old\xff\0?? unknown\n\xff\0 D gone\0"),
            Some(Counts {
                staged: 2,
                unstaged: 2,
                untracked: 1
            })
        );
        assert_eq!(counts(b"R  target\0"), None);
        assert_eq!(counts(b"?? truncated"), None);
    }
}
