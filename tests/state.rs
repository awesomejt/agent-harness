#![cfg(unix)]
//! P5.3 durable sequence records, lock and resume planning (D044).
use awesomejt_agent_harness::config::Exit;
use awesomejt_agent_harness::sequence::{Choice, Step, plan};
use awesomejt_agent_harness::state::{
    Attempt, Backend, Reason, Record, RunStatus, Status, StepRecord, Store, parse, root,
};
use std::ffi::OsString;
use std::os::unix::fs::PermissionsExt;
use std::path::{Path, PathBuf};

const RUN: &str = "s20261104T120000Z-0a1b2c3d";

fn temp(name: &str) -> PathBuf {
    let dir = std::env::temp_dir().join(format!("ah-state-{name}-{}", std::process::id()));
    let _ = std::fs::remove_dir_all(&dir);
    std::fs::create_dir_all(&dir).unwrap();
    dir.canonicalize().unwrap()
}

fn steps(texts: &[(&str, &str)]) -> Vec<Step> {
    texts
        .iter()
        .map(|(name, text)| Step::parse(name, text).unwrap())
        .collect()
}

fn attempt(reason: Reason, status: Status, submitted: bool) -> Attempt {
    Attempt {
        number: 1,
        reason,
        status,
        started: "2026-11-04T12:00:00Z".into(),
        ended: None,
        input_sha256: "0".repeat(64),
        agent_sha256: None,
        check: None,
        route: "local-only".into(),
        model: "ah-litellm/fixture".into(),
        fallback: None,
        permissions: "deny".into(),
        timeout_secs: 60,
        agent_outcome: None,
        exit: None,
        verification: None,
        backends: vec![Backend {
            attempt: 1,
            launched: submitted,
            prompt_submitted: submitted,
            backend_stop: None,
            cleanup_confirmed: Some(true),
            grants: Some(0),
            tool_events: Some(0),
        }],
    }
}

fn record(snapshot: &[Step], statuses: &[(Status, Vec<Attempt>)]) -> Record {
    Record {
        v: 1,
        run: RUN.into(),
        created: "2026-11-04T12:00:00Z".into(),
        updated: "2026-11-04T12:00:00Z".into(),
        project: "/project".into(),
        folder: "/project/prompts".into(),
        config: "/project/ah.json".into(),
        status: RunStatus::Stopped,
        steps: snapshot
            .iter()
            .zip(statuses)
            .map(|(step, (status, attempts))| StepRecord {
                name: step.name.clone(),
                sha256: step.sha256.clone(),
                agent: None,
                check: None,
                status: *status,
                attempts: attempts.clone(),
            })
            .collect(),
    }
}

fn three() -> Vec<Step> {
    steps(&[
        ("1-a.md", "One.\n"),
        ("2-b.md", "Two.\n"),
        ("3-c.md", "Three.\n"),
    ])
}

#[test]
fn resume_plan_requires_a_choice_whenever_effects_are_possible() {
    let snapshot = three();
    let done = (
        Status::Succeeded,
        vec![attempt(Reason::Initial, Status::Succeeded, true)],
    );
    let at = |status, attempt| record(&snapshot, &[done.clone(), (status, vec![attempt])]);
    // Never submitted: rejected, failed or cancelled before the prompt.
    for status in [Status::Rejected, Status::Failed, Status::Cancelled] {
        let r = at(status, attempt(Reason::Initial, status, false));
        assert_eq!(
            plan(&r, &snapshot, Choice::None),
            Ok(Some((1, Reason::Resume)))
        );
        assert_eq!(
            plan(&r, &snapshot, Choice::Retry),
            Ok(Some((1, Reason::Retry)))
        );
    }
    // Submitted, uncertain, interrupted, or a failed accept: refuse without a
    // choice; either choice proceeds.
    for (status, reason, submitted) in [
        (Status::Failed, Reason::Initial, true),
        (Status::Cancelled, Reason::Initial, true),
        (Status::Uncertain, Reason::Initial, false),
        (Status::Interrupted, Reason::Initial, false),
        (Status::Failed, Reason::Accept, false),
        (Status::Failed, Reason::Retry, true),
    ] {
        let r = at(status, attempt(reason, status, submitted));
        let (step, error) = plan(&r, &snapshot, Choice::None).unwrap_err();
        assert_eq!(step, "2-b.md");
        assert!(error.0.contains("may have had effects"), "{}", error.0);
        assert_eq!(
            plan(&r, &snapshot, Choice::Retry),
            Ok(Some((1, Reason::Retry)))
        );
        assert_eq!(
            plan(&r, &snapshot, Choice::Accept),
            Ok(Some((1, Reason::Accept)))
        );
    }
    // A step never attempted (signal between steps) runs without a choice.
    let r = record(&snapshot, &[done.clone(), (Status::Pending, vec![])]);
    assert_eq!(
        plan(&r, &snapshot, Choice::None),
        Ok(Some((1, Reason::Resume)))
    );
    // Everything complete: nothing to do, unless steps were appended.
    let all = record(&snapshot[..2], &[done.clone(), done.clone()]);
    assert_eq!(plan(&all, &snapshot[..2], Choice::None), Ok(None));
    assert_eq!(
        plan(&all, &snapshot, Choice::None),
        Ok(Some((2, Reason::Resume)))
    );
}

#[test]
fn resume_plan_refuses_changed_completed_steps_and_a_lost_next_step() {
    let snapshot = three();
    let done = (
        Status::Succeeded,
        vec![attempt(Reason::Initial, Status::Succeeded, true)],
    );
    let failed = (
        Status::Failed,
        vec![attempt(Reason::Initial, Status::Failed, true)],
    );
    let r = record(&snapshot, &[done.clone(), failed.clone()]);
    // Completed step edited, renamed or removed.
    for changed in [
        steps(&[("1-a.md", "Edited.\n"), ("2-b.md", "Two.\n")]),
        steps(&[("1-z.md", "One.\n"), ("2-b.md", "Two.\n")]),
        vec![],
    ] {
        let (step, error) = plan(&r, &changed, Choice::Retry).unwrap_err();
        assert_eq!(step, "1-a.md");
        assert!(error.0.contains("completed step changed"), "{}", error.0);
    }
    // The attempted step must stay next; its body may change.
    let moved = steps(&[
        ("1-a.md", "One.\n"),
        ("2-new.md", "New.\n"),
        ("3-b.md", "Two.\n"),
    ]);
    let (step, error) = plan(&r, &moved, Choice::Retry).unwrap_err();
    assert_eq!(step, "2-b.md");
    assert!(error.0.contains("must remain the next step"));
    let edited = steps(&[
        ("1-a.md", "One.\n"),
        ("2-b.md", "Fixed.\n"),
        ("9-z.md", "Z.\n"),
    ]);
    assert_eq!(
        plan(&r, &edited, Choice::Retry),
        Ok(Some((1, Reason::Retry)))
    );
    // 32 attempts is the bound.
    let mut full = r.clone();
    full.steps[1].attempts = (0..32)
        .map(|_| attempt(Reason::Retry, Status::Failed, true))
        .collect();
    assert!(
        plan(&full, &snapshot, Choice::Retry)
            .unwrap_err()
            .1
            .0
            .contains("32 attempts")
    );
    // Attempts after the first incomplete step are inconsistent.
    let mut stray = r.clone();
    stray.steps.push(StepRecord {
        status: Status::Failed,
        attempts: vec![attempt(Reason::Initial, Status::Failed, true)],
        ..stray.steps[1].clone()
    });
    assert!(
        plan(&stray, &snapshot, Choice::Retry)
            .unwrap_err()
            .1
            .0
            .contains("inconsistent")
    );
}

#[test]
fn records_are_private_atomic_strict_and_versioned() {
    let base = temp("store");
    let project = base.join("project");
    std::fs::create_dir(&project).unwrap();
    let store = Store::create(base.join("state/agent-harness"), &project).unwrap();
    for dir in ["", "sequences", "locks"] {
        let mode = std::fs::metadata(base.join("state/agent-harness").join(dir))
            .unwrap()
            .permissions()
            .mode();
        assert_eq!(mode & 0o777, 0o700, "{dir}");
    }
    let snapshot = three();
    let mut r = record(&snapshot, &vec![(Status::Pending, vec![]); 3]);
    store.write(&r).unwrap();
    let path = store.record_path(RUN);
    assert_eq!(
        std::fs::metadata(&path).unwrap().permissions().mode() & 0o777,
        0o600
    );
    assert_eq!(store.read(RUN).unwrap(), r);
    r.steps[0].status = Status::Active;
    store.write(&r).unwrap();
    assert_eq!(store.read(RUN).unwrap(), r);
    // No temporary file survives a write.
    let names: Vec<_> = std::fs::read_dir(path.parent().unwrap())
        .unwrap()
        .map(|e| e.unwrap().file_name())
        .collect();
    assert_eq!(names, vec![OsString::from(format!("{RUN}.json"))]);
    // Version first, then strict fields, then the filed run ID.
    let text = std::fs::read_to_string(&path).unwrap();
    let refuse = |bytes: &str, run: &str| parse(bytes.as_bytes(), run).unwrap_err().reason;
    assert!(refuse(&text.replacen("\"v\": 1", "\"v\": 2", 1), RUN).contains("version"));
    assert!(refuse(&text.replacen("\"v\": 1", "\"v\": \"1\"", 1), RUN).contains("version"));
    assert!(refuse(&text.replacen("{", "{\"extra\": 0,", 1), RUN).contains("schema v1"));
    assert!(refuse(&text, "s20261104T120000Z-ffffffff").contains("schema v1"));
    assert!(refuse("[", RUN).contains("unparsable"));
    // An invalid run ID never forms a path.
    assert_eq!(store.read("../x").unwrap_err().exit, Exit::Invalid);
    assert!(
        store
            .read("s20261104T120000Z-00000000")
            .unwrap_err()
            .reason
            .contains("no sequence record")
    );
    // A symlinked record is refused, not followed.
    std::fs::rename(&path, base.join("moved.json")).unwrap();
    std::os::unix::fs::symlink(base.join("moved.json"), &path).unwrap();
    assert!(store.read(RUN).unwrap_err().reason.contains("cannot open"));
    std::fs::remove_dir_all(&base).unwrap();
}

#[test]
fn the_project_lock_is_exclusive_and_names_its_holder() {
    let base = temp("lock");
    let project = base.join("project");
    std::fs::create_dir(&project).unwrap();
    let store = Store::create(base.join("state"), &project).unwrap();
    assert!(!store.holds(&project, RUN));
    let lock = store.lock(&project, RUN).unwrap();
    let error = store
        .lock(&project, "s20261104T120000Z-ffffffff")
        .err()
        .unwrap();
    assert_eq!(error.exit, Exit::Invalid);
    assert!(error.reason.contains("another sequence holds"));
    assert!(store.holds(&project, RUN));
    assert!(!store.holds(&project, "s20261104T120000Z-ffffffff"));
    // Another project is independent.
    let other = base.join("other");
    std::fs::create_dir(&other).unwrap();
    drop(store.lock(&other, RUN).unwrap());
    // Released on drop; the stale holder name no longer reads as active.
    drop(lock);
    assert!(!store.holds(&project, RUN));
    let lock = store.lock(&project, "s20261104T120000Z-ffffffff").unwrap();
    assert!(!store.holds(&project, RUN));
    drop(lock);
    std::fs::remove_dir_all(&base).unwrap();
}

#[test]
fn state_lives_outside_the_project_in_real_directories() {
    let env = |pairs: &'static [(&'static str, &'static str)]| {
        move |name: &str| {
            pairs
                .iter()
                .find(|(k, _)| *k == name)
                .map(|(_, v)| OsString::from(v))
        }
    };
    assert_eq!(
        root(env(&[("XDG_STATE_HOME", "/x"), ("HOME", "/h")])).unwrap(),
        Path::new("/x/agent-harness")
    );
    assert_eq!(
        root(env(&[("XDG_STATE_HOME", "rel"), ("HOME", "/h")])).unwrap(),
        Path::new("/h/.local/state/agent-harness")
    );
    for pairs in [&[("XDG_STATE_HOME", "rel")][..], &[("HOME", "rel")], &[]] {
        assert_eq!(root(env(pairs)).unwrap_err().exit, Exit::Invalid);
    }
    let base = temp("location");
    let project = base.join("project");
    std::fs::create_dir(&project).unwrap();
    // Inside the project, directly or through a symlinked ancestor.
    for inside in [project.join("state"), project.join("a/b")] {
        let error = Store::create(inside, &project).err().unwrap();
        assert!(error.reason.contains("outside the project"));
    }
    std::os::unix::fs::symlink(&project, base.join("link")).unwrap();
    let error = Store::create(base.join("link/state"), &project)
        .err()
        .unwrap();
    assert!(error.reason.contains("outside the project"));
    assert!(!project.join("state").exists() && !project.join("a").exists());
    // A symlinked harness directory is refused for writes and reads.
    std::fs::create_dir(base.join("target")).unwrap();
    std::os::unix::fs::symlink(base.join("target"), base.join("ah")).unwrap();
    assert!(
        Store::create(base.join("ah"), &project)
            .err()
            .unwrap()
            .reason
            .contains("not symlinks")
    );
    assert!(Store::existing(base.join("ah")).is_err());
    assert!(Store::existing(base.join("absent")).unwrap().is_none());
    std::fs::remove_dir_all(&base).unwrap();
}
