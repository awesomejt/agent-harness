# P7.9 — Operator-login retained-root preflight

Date: 2026-11-13. Branch: `feature/07/p7-9-login-preflight`. Prior
[retained-state experiment](p7-9-retained-state-experiment.md), D078;
[exclusive-state decision](p7-9-exclusive-state-decision.md), D077.

## Plan recorded before launch

After D078's no-auth retained-state proofs, run the bounded login increment: the operator
personally completes D077's official `auth login` into a fresh harness-owned root; then run a
no-inference preflight under the D076 composed profile with network denied and
`login=True` invariants. The harness prints the login command and never runs, wraps or
observes the OAuth exchange (D047/D067).

**Result:** see **Validation** below. An unauthenticated root is refused with
`openai-connection` only. Installed login-mode success requires the operator session
described under **Reproduction**.

## Reproduction

On the accepted Apple Silicon macOS host with hash-pinned OpenCode 2.2.5
(`4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`):

1. Obtain the public v2.2.5 checkout (`9bbb8ce18c80f099e0e448775f59d965ead40a21`) with the
   D071 procedure.
2. Prepare a root and print the operator login command:

```sh
python3 -B scripts/experiments/chatgpt_login_preflight.py \
  --prepare /tmp/ah-chatgpt-login-evidence
```

3. In your own shell (not the harness), run the printed `cd … && env -i … auth login …`
   command. Complete the browser OAuth personally.
4. Run the contained preflight:

```sh
python3 -B scripts/experiments/chatgpt_login_preflight.py \
  --root /tmp/ah-chatgpt-login-evidence/work \
  --source <v2.2.5 checkout>
```

5. Offline regression:

```sh
python3 -B scripts/tests/chatgpt_login_preflight_cases.py
```

The helper copies and hash-checks the installed executable beside the prepared parent
directory. It reuses the D077 boot, lock, integration-redaction and login invariants from
`chatgpt_retained_state.py`.

## Boundary

- **Operator login** runs outside containment (D077). The harness never invokes it.
- **Preflight boots** use the D076 composed profile with network fully denied, the same
  integration/resource invariants as D078, and `login=True` on `openai` (exactly one
  `credential`/`oauth` connection, no `needs_auth`).
- **Credentials** are never read, copied, exported or printed. Connection metadata is hashed
  in memory only.
- No session, model turn, production route, dependency or D034 change.

## Validation

- **Offline:** `chatgpt_login_preflight_cases.py` covers the D077 login-command shape, prepare
  byte-drift refusal and attach marker/executable refusals; it joins `offline.py`.
- **Unauthenticated installed:** On a prepared root before login, the preflight exits 1 with
  withheld diagnostics; bound controls still print their PASS lines.
- **Authenticated installed:** Pending operator OAuth into a dedicated root on this host;
  record redacted JSON summary and three consecutive passing runs here before PR merge.

## Limits

- One dedicated root per operator account (D067). A second login from an existing global
  OpenCode install does not substitute for this evidence.
- KV rows, session history and exact OAuth method IDs remain outside `integration.list`
  invariants.
- Method, endpoint, helper, deny/trusted, account credits-off and D034 remain separate gates.
  Full P7.9/P7.10 remain unchecked and P7.11/P7.12 blocked.

## Next boundary

After installed login-mode preflight passes, the next P7.9 increment is method/endpoint/helper
proof under retained login state. P7.10 and independent Pi work remain unchanged.