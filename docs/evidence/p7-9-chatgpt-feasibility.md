# P7.9 — OpenCode ChatGPT-plan feasibility

Date: 2026-11-09. Entry: `10be0e6` (merged P7.8 / PR #82).
[Task](../../tasks/07-native-adapters.md#p7-9). D068 and D067 apply.

## Control plan recorded before installed checks

Select the existing installed OpenCode 2.2.5 candidate, caller-owned ACP for any
eventual coding loop. Do not upgrade the accepted production pin in this task.
Fresh provider documentation describes both Sign in with ChatGPT and legacy
Codex login; select the first-party built-in `opencode.provider.chatgpt` method
`chatgpt-token-sharing` on provider `openai` as the assessment candidate. This
does not select legacy Codex OAuth or an API key as a substitute.

The installed experiment may run only version and standalone debug paths,
config and agents commands. No ACP, authentication, credential-list, session,
model-list network fetch or prompt command. Copy only the executable into a
disposable root; clear environment; use private HOME, XDG roots and TMPDIR.
Verify network denial, operator-home data-read denial and outside-write denial
with synthetic sentinels before starting OpenCode. Reuse the bounded capture
and containment helpers from the Antigravity experiment (10 seconds, two MiB,
process-group cleanup); no real auth/config/store is read or copied.

Use inert project config sentinels and a positive control with project discovery
enabled. Inspect exact provider policy, helper model and deny permissions with
project discovery disabled. Compare two disposable XDG data roots while keeping
config private; this observes path separation, not login preservation. Stop at
an unproven boundary. No startup plugins, MCP or hooks are seeded.

## Results and disposition

The contained version check passes; standalone config inspection is blocked at
child spawn. The full observations and unpassed disposition are below.

## Official sources and selected candidate

Re-read on 2026-11-09:

- [OpenAI Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt)
  lists OpenCode among open-source integrations. Plan consumption requires a
  separate permission; app usage shares the existing plan allowance. Settings >
  Usage exposes app limits and the post-limit credits control. This supports
  the integration candidate, not this account's entitlement or a harness cap.
- [OpenCode providers](https://opencode.ai/docs/providers/) documents ChatGPT
  plan use through OpenAI and distinguishes the new sign-in from legacy Codex
  methods. A zero displayed model cost is not spend enforcement.
- [OpenCode configuration](https://opencode.ai/docs/config/) documents merged
  global/project/system sources and macOS managed preferences. Private HOME
  alone is not proof that every source is excluded.
- [OpenCode permissions](https://opencode.ai/docs/permissions/) documents ordered
  action/resource/effect rules and last-match semantics. Config syntax is not
  evidence of effective tool behavior.
- [OpenCode CLI](https://opencode.ai/docs/cli/) documents shared-server defaults
  and private `--standalone` execution. The [current ACP page](https://opencode.ai/docs/cli/acp/)
  is the documentation entry for the prospective stdio client; no ACP runs here.

Pinned official source: tag `v2.2.5`, commit
`9bbb8ce18c80f099e0e448775f59d965ead40a21` in
[anomalyco/opencode](https://github.com/anomalyco/opencode/tree/9bbb8ce18c80f099e0e448775f59d965ead40a21).
Downloaded to disposable `/tmp` for source inspection only; no package install,
update or build. This is upstream tagged source, not verified build provenance
for the Homebrew executable. Moving documentation and tagged source are distinct.

| Source path within the pin | SHA-256 |
|---|---|
| `packages/core/src/plugin/provider/chatgpt.ts` | `cbb119fa3f231f5b79b588916ad23afc1f6fa71529332bcae8f7fadaa98e8bd2` |
| `packages/util/src/global-roots.ts` | `6cdc234ac155e308dadeb62682c687468ba656fd463482d00fce025c9dc819b6` |
| `packages/cli/src/database-path.ts` | `921368eee69db647d2973d7dc529e86a8942027ee0032d3acb112d6a55e6b9d7` |
| `packages/core/src/config.ts` | `df2d83dff70a6cb3ef3e3a1d735bd397facc96ccf15794c6eb1a3646cef17390` |

The pinned `chatgpt.ts` selects OAuth method `chatgpt-token-sharing` on `openai`,
requires the sharing scope, and sets the provider resource to
`https://api.openai.com/v1`. The distinct `plugin/provider/openai.ts` legacy
methods select the Codex backend. Therefore an `api.openai.com` URL alone cannot
identify API-key billing versus plan use; the active runtime connection/method
must be verified without exposing secrets. Neither legacy OAuth nor API-key
fallback is selected. Source has a finite model allowlist and non-retryable
sharing-limit codes, but neither proves account access or harness retry behavior.
The diagnostic configuration names `openai/gpt-6.1-sol` only as an inert explicit
selection; no availability, effort mapping or support claim follows.

`credential.ts` uses the runtime database; `database-path.ts` and
`util/global-roots.ts` place it beneath the XDG data root by default and allow a
database-path override. The legacy migration reads `auth.json` from that root.
Private XDG data intentionally does not reuse the operator's normal login.
Reusing the normal data/database may also retain integration configuration and
other state: `core/src/config.ts` loads integration/well-known documents, and
`config/discovery.ts` discovers system/managed sources separately. A database
path override is consequently a lead, not accepted credential-only isolation.
No normal database, auth file or account metadata was inspected.

## Installed results

Host: Apple Silicon macOS. Installed symlink resolves to Homebrew
`/opt/homebrew/Cellar/opencode/2.2.5/bin/opencode`; copied executable SHA-256:
`4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`.

Reproduce from the repository root:

```sh
python3 -B scripts/experiments/chatgpt_feasibility.py
```

The script refuses missing executables, other platforms and byte drift. It never
invokes auth, credential inspection, ACP, sessions or prompts. Its exit 0 means
these observations reproduced, **not that feasibility passed**.

- Synthetic containment checks pass: loopback bind, operator-home sentinel read
  and outside-root write each receive a permission denial.
- `--version --standalone` reports `opencode v2.2.5`.
- `debug config --standalone` exits 1, with `EPERM` at child `posix_spawn`.
  `debug paths --standalone` was also attempted during investigation and failed
  at the same capture boundary; it is not needed in the final reproducer.
- Pinned `cli/src/services/standalone.ts` starts a caller-owned `serve --stdio
  --port 0` subprocess. The observed spawn failure is an experimental containment
  blocker; its underlying cause is not established. Do not infer that ChatGPT
  integration or OpenCode production operation is impossible.
- Effective config/agents, positive source canaries and data-root comparisons
  were **not reached**. No tool inventory, login preservation or endpoint
  selection was observed. The inert config document is an input, not a result.
- An initial scratch executable named `opencode` collided with OpenCode's
  `TMPDIR/opencode` directory; the final probe uses `opencode-cli`. No containment
  permission was relaxed to fix this experiment error.

The experiment clears environment and holds no real credentials; the sandbox
checks only the stated filesystem/network boundaries. It is not a production
sandbox or a complete keychain/IPC isolation proof. No inference or metered
request, provider login, global config edit, Rust/dependency change or direct-tool
coding comparison occurred. Disposable roots and captured child groups are
cleaned through the reused bounded helper.

## Account controls and next bounded follow-up

Before any eventual live gate, have the operator verify the selected account's
app permission and plan eligibility, and that **Allow other apps to use credits
after reaching your usage limit** is off in ChatGPT Settings > Usage. Record only
the dated assertion and selected account/workspace label, never tokens or account
screenshots containing secrets. An app's percentage limit is optional narrowing,
not an independent allowance. This task did not inspect or change the account;
its controls remain unverified. Any later credential resolution/refresh or login
must be done by unmodified OpenCode and separately authorized; never parse,
copy, symlink, export or supply its OAuth tokens from the harness.

**Disposition: P7.9 feasibility not passed; P7.11 blocked.** This bounded
selection/assessment increment can close on review/merge while P7.9 stays
unchecked. It establishes neither a production route nor a provider terms block.

Select the following separate P7.9 no-inference continuation before production:

1. Establish a containment/control plan permitting only the private server's
   required local transport while continuing to deny external networking,
   operator-home data reads and outside writes. Explain and reproduce the spawn
   failure with a synthetic child control before changing any sandbox rule.
   Validate all permitted/denied transport paths and cleanup; do not merely
   remove network denial or attach to the operator's shared service.
2. Once contained diagnostics work, prove project/parent/global/managed source
   exclusion with positive and negative inert canaries; verify exact provider,
   helpers, request overrides and deny rules. Cover skills/plugins/MCP/hooks and
   indirect/delegated tools before treating deny as effective enforcement.
3. Assess a **new, exclusively owned persistent OpenCode state** candidate with
   synthetic data only, retaining private configuration and excluding stale
   integration sources. Record a separate D047 isolation decision and a bounded
   runtime-owned operator login/connection check if the remaining proof requires
   leaving this task's no-auth boundary. The existing login is not imported.
4. Require effective connection/method, provider/model/helper/endpoint evidence,
   exact one-use grants for advertised trusted roles, sanitized output and
   pre-submission refusal/no-uncertain-replay before accepting feasibility or
   consuming P7.11. A model turn cannot substitute for these checks.

P7.10 remains separately ready from P7.8, but its installed experiment should
consume a proven containment approach rather than repeat this failure. Pi is
independent; no alternative or platform switch is selected. P7.13/P7.6/P7.7
remain later gates. Continuing this context is efficient for the related
containment investigation; a fresh context is appropriate after that boundary
or for the independent Go assessment.

## Validation

The installed reproducer passes with the explicit blocked observation above;
missing-executable and byte-drift cases refuse with sanitized diagnostics before
CLI execution. Python syntax, tracked Markdown relative links/anchors and Git
whitespace checks pass. Rust tests are not applicable: production sources and
Cargo files are unchanged. Required PR review and any corrections are recorded
in PROJECT.md at closeout.
