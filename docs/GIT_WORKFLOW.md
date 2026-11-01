# Git Workflow

Multi-agent Git workflow for **agent-harness**. All agents (and humans) must follow this process.

Grok acts as the automated Pull Request reviewer. An existing Grok bot already listens for new PRs and for explicit `/grok review` comments; it only needs to be pointed at this repository.

## Core rules

- **No direct commits to `main`.** All work happens on a feature branch.
- **One task per branch / PR** when practical.
- **Grok reviews every PR** (automatically on open, and on demand via comment).
- **Maximum 3 Grok reviews per PR.** After the third review, further automated review stops and a human must take over.
- Agents must wait for the review to finish before addressing findings.

## Workflow steps

### 1. Pick a task and create a feature branch

```bash
git checkout main
git pull
git checkout -b feature/<short-task-name>
```

Work only on this branch. Commit as needed with clear messages.

### 2. Implement and open a Pull Request

When the task is complete:

```bash
git push -u origin feature/<short-task-name>
```

Open a PR targeting `main`. The existing Grok bot will automatically start a review when it sees the new PR (once the repo is added to the bot’s watch list).

### 3. Grok review

Grok posts findings as comments on the PR (inline or summary, depending on the bot’s configuration).

Agents must:

- Watch the PR until the review completes.
- Read all comments and the review summary.

### 4. Address findings

| Finding severity | Action |
|------------------|--------|
| Critical or high | Fix on the same branch, push, then explicitly request another review with a `/grok review` comment. |
| Minor or nitpick | Fix if straightforward; **no re-review required**. |
| No findings of note | Proceed to merge approval. |

Push fixes to the **same branch**. Do not open a new PR for review fixes.

### 5. Re-review limits

- Grok may review a PR at most **3 times**.
- Count includes the initial automatic review plus any `/grok review` requests.
- After the third review, if critical/high issues remain or another review seems necessary:
  - Leave a clear comment on the PR stating that the automated review limit has been reached and human review is required.
  - Note the same condition in the agent’s session output.
  - Stop and wait for a human. Do not request further Grok reviews.

### 6. Approval, merge, and cleanup

If the latest review has no critical/high findings (or only minor/nitpicks that do not require re-review):

1. Merge the PR into `main` (squash or merge commit — follow any repo preference; default is fine).
2. Delete the remote feature branch.
3. Clean up locally so the repo is ready for the next task:

```bash
git checkout main
git pull --prune
git branch -d feature/<short-task-name>
```

(`--prune` removes remote-tracking references for deleted branches.)

The local repository is now on an up-to-date `main` and ready for the next agent or prompt.

## Requesting a review manually

At any time (within the 3-review limit) an agent or human may comment on the PR:

```
/grok review
```

The Grok bot will perform another review and post findings.

## Human handoff

When the 3-review limit is reached and further review is still needed:

- Comment on the PR:  
  `Automated Grok review limit (3) reached. Human review required before further changes or merge.`
- Record the same note in the agent session output.
- Do not merge until a human approves or gives explicit direction.

## Summary checklist for agents

- [ ] Branch created from up-to-date `main`
- [ ] Work committed only on the feature branch
- [ ] PR opened to `main` (triggers automatic Grok review)
- [ ] Waited for review to finish
- [ ] Critical/high findings fixed and re-review requested (if any, and under limit)
- [ ] Minor/nitpick findings handled without mandatory re-review
- [ ] ≤ 3 Grok reviews total
- [ ] If limit reached with remaining issues → human handoff comment + session note
- [ ] On clean approval: merge, delete remote branch, `git checkout main && git pull --prune && git branch -d <branch>`

## Related

- [AGENTS.md](../AGENTS.md) — general agent instructions
- [PROJECT.md](../PROJECT.md) — task list
- [DECISIONS.md](../DECISIONS.md) — design decisions
