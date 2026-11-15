# P7.9 — Post-login integration inventory refusal

Recorded: 2026-11-14, America/Denver (UTC−07:00). Baseline: `216c91ff6b16af5aa36beafe73275b602242a846`.
Branch: `feature/07/p7-9-authenticated-evidence`.
[Task](../../tasks/07-native-adapters.md#p7-9), [D085](p7-9-login-preflight.md),
[closeout boundary](p7-9-feasibility-closeout.md).

## Outcome

**Preflight refused; P7.9 remains unpassed and P7.11 remains blocked.** The operator
personally ran the printed official login command and reported “Connected to OpenAI”.
The harness did not run, wrap or observe OAuth. A subsequent contained preflight did
not reach login-mode validation: its integration-ID inventory differed from the fixed
D077/D085 baseline. Successful operator login is not a passing D085 result.

No D086, D087 or D088 installed continuation ran. No account-setting assertion was
obtained, session created or model turn submitted. No production code, runtime pin,
inventory expectation or source/network boundary changed. The dedicated root is
retained for investigation; no login-store contents were inspected or copied.

## Runtime and source

The default installed executable resolved to Homebrew OpenCode 2.3.0 and failed the
prepare helper's SHA-256 gate before creating a root. Preparation then explicitly
selected a retained 2.2.5 executable with the required hash, and copied that executable
beside the fresh dedicated root using the existing helper.

- OpenCode executable SHA-256: `4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`.
- Public v2.2.5 source checkout: `9bbb8ce18c80f099e0e448775f59d965ead40a21`, clean worktree.
- Opaque same-root evidence label: `p79-login-20261114-a`.
- Host: macOS arm64; existing D076 containment and retained-root helpers.

## Sanitized observation

The initial contained invocation exited 1 with raw diagnostics withheld. A diagnostic
repeat emitted only exception type and source frame locations: `RuntimeError` at
`chatgpt_login_preflight.py`'s integration-digest equality check in `run_preflight`.
A further bounded repeat, starting at **2026-11-14 21:26:57−07:00**, wrapped `boot`
to print only boot number, phase, integration count and integration-ID digest before
returning each unchanged record to the existing validator. It did not bypass checks
or print integration metadata, connection identities, logs or credentials.

| Observation | Expected | Observed |
|---|---|---|
| Integration count | 236 | 336 |
| Sorted integration-ID SHA-256 | `2cd1b632219bbd635a2f7a5911d6c0e36d7205d75cc4c85d751cb90081de73af` | `e762516c54aee5ba05b35eb0061e07beb1b1c6ffe0625c0ba0e77ef57f595311` |
| Two contained boots, before/after inventory | Fixed baseline | All four observed counts/digests identical, but different from baseline |
| Boundary probe | Existing D076 controls | PASS: owned TCP echo; other TCP/binds, external TCP, UDP, Unix and filesystem denials |
| Login-mode preflight | Must pass after inventory checks | Not reached |

The repeat exited 1 at the unchanged preflight gate. Stable counts and ID digests do
not establish stable connection metadata, trusted integrations or accepted feasibility.
The cause of the inventory difference has **not** been established.

## Next bounded task

Investigate the public integration-inventory construction and the post-login retained
catalog behavior against the pinned source, using synthetic state where possible.
Separate fixed built-in definitions from any runtime-owned cached catalog before
proposing a control change. Preserve D071/D077/D089: do not simply replace the expected
hash/count, delete retained login state, inspect credentials, widen source/network
access or advance to D086–D088 to make the failure disappear. Any revised control plan
needs separately reviewed evidence before another authenticated expansion.

After that gate is resolved, revalidate the same-root D085 chain, then D086/D087 and
D088 with a fresh operator credits-off attestation. A runtime/login/root change requires
revalidation rather than transfer of this attempted result. P7.10 remains separate.

## Validation

Documentation links/anchors, anchor fixtures and whitespace checks cover this record.
The installed result above is a failed gate, not mocked acceptance or a live coding run.
