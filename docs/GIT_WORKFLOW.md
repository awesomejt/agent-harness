# Git Workflow

Multi-agent Git workflow for **agent-harness**. All agents (and humans) must follow this process.

Grok acts as the automated Pull Request reviewer. The existing Grok bot uses the source branch name to distinguish normal PRs from phase reviews. Feature PRs are reviewed automatically on open. Phase-review and patch branches skip automatic review on open; patch PRs require an explicit `/grok review` request.

## Core rules

- **No direct commits to `main`.** All work happens on a task branch using the naming patterns below.
- **One task per branch / PR** when practical.
- **Grok reviews feature PRs automatically on open.** `patch/` PRs require an explicit `/grok review` comment after opening. `review/` branches bypass the normal PR review process; the holistic phase-review requirements still apply.
- **One open PR at a time.** Sequence work, including phase-review remediation, so that open PRs cannot conflict.
- **Maximum 3 Grok reviews per PR.** After the third review, further automated review stops and a human must take over.
- On feature and patch PRs, agents must wait for Grok review to finish before addressing its findings.

## Workflow steps

### 1. Pick a task and create a branch

Use these branch patterns going forward:

| Work | Pattern | Example |
|---|---|---|
| Normal features and planned tasks | `feature/<phase>/<task>-description` | `feature/02/p2-1-config-contract` |
| Holistic phase reviews | `review/<phase>-description` | `review/02-first-slice` |
| Standalone fixes or patches outside the feature/task process, including follow-up remediation | `patch/<task>` | `patch/branch-naming` |

Use lowercase, hyphen-separated descriptions; the examples use two-digit phase numbers and the existing P task ID where applicable. Branch names are operational inputs to Grok's routing. Do not use `review/` for ordinary features or standalone fixes. Historical branch names in accepted evidence remain unchanged.

```bash
git checkout main
git pull
git checkout -b feature/02/p2-1-config-contract
```

Work only on this branch. Commit as needed with clear messages.

### 2. Implement and open a Pull Request

When the task is complete:

```bash
git push -u origin HEAD
```

Open a PR targeting `main`. For `feature/` source branches, the existing Grok bot starts its normal automated review. For `patch/` source branches, post `/grok review` after opening the PR; automatic review on open is skipped, so do not wait for it. For `review/` source branches, complete the holistic review/report and findings verification under [PHASE_REVIEW.md](PHASE_REVIEW.md); do not wait for or request a normal Grok PR review as a phase-review prerequisite.

### 3. Grok review (feature and patch PRs)

Grok posts findings as comments on the PR (inline or summary, depending on the bot’s configuration).

Agents must:

- Watch the PR until the review completes.
- Read all comments and the review summary.

### 4. Address findings

For Grok findings on feature and patch PRs:

| Finding severity | Action |
|------------------|--------|
| Critical or high | Fix on the same branch, push, then explicitly request another review with a `/grok review` comment. |
| Minor or nitpick | Fix if straightforward; **no re-review required**. |
| No findings of note | Proceed to merge approval. |

Fix findings within an active feature/task PR on the **same branch**. Standalone remediation outside that process uses `patch/<task>` and its own PR, with links to the originating finding. A phase-review PR records findings and the remediation plan; it does not carry the fixes (D042). Put every correction found during a phase review, documentation or code, in a linked `patch/<task>` PR and explicitly request Grok review there. All required fixes must be verified and merged before phase acceptance.

### 5. Re-review limits

- Grok may review a PR at most **3 times**.
- Count includes the initial automatic review (feature PRs) and all `/grok review` requests, including the first request on a patch PR.
- After the third review, if critical/high issues remain or another review seems necessary:
  - Leave a clear comment on the PR stating that the automated review limit has been reached and human review is required.
  - Note the same condition in the agent’s session output.
  - Stop and wait for a human. Do not request further Grok reviews.

### 6. Approval, merge, and cleanup

For feature and patch PRs, proceed when the latest Grok review has no critical/high findings (or only minor/nitpicks that do not require re-review). For phase-review PRs, proceed when every finding has been considered and recorded in the canonical report with a disposition and remediation plan (D042); normal Grok PR review is bypassed. Merging a review PR with open findings does not pass the phase: the patch PR that resolves the last finding records verification and proposes the pass.

1. Merge the PR into `main` (squash or merge commit — follow any repo preference; default is fine).
2. Delete the remote task branch.
3. Clean up locally so the repo is ready for the next task:

```bash
git checkout main
git pull --prune
git branch -d <branch>
```

(`--prune` removes remote-tracking references for deleted branches.)

The local repository is now on an up-to-date `main` and ready for the next agent or prompt.

## Requesting a review manually

For feature and patch PRs (within the 3-review limit) an agent or human may comment on the PR:

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
- [ ] Work committed only on the correctly named task branch
- [ ] PR opened to `main` (feature: automatic Grok review; patch: request `/grok review`; review: holistic phase-review process)
- [ ] Required review completed (Grok for feature/patch; holistic report for review)
- [ ] Critical/high Grok findings fixed and re-review requested (if any, and under limit); holistic phase-review findings recorded with a plan (review PR) and resolved/verified through patch PRs before phase acceptance
- [ ] Minor/nitpick findings handled without mandatory re-review
- [ ] ≤ 3 Grok reviews total
- [ ] If limit reached with remaining issues → human handoff comment + session note
- [ ] On clean approval: merge, delete remote branch, `git checkout main && git pull --prune && git branch -d <branch>`

## Related

- [AGENTS.md](../AGENTS.md) — general agent instructions
- [PROJECT.md](../PROJECT.md) — task list
- [DECISIONS.md](../DECISIONS.md) — design decisions
