# P7.9 — Deny and trusted permission proof (retained login)

Date: 2026-11-13. Branch: `feature/07/p7-9-deny-trusted-permission`. Depends on
[method/endpoint/helper](p7-9-method-endpoint-helper.md) (D086) and
[login preflight](p7-9-login-preflight.md) (D085).

## Plan recorded before launch

On a retained root that has passed D085 login preflight (and typically D086 on the same root),
prove
without network that merged global deny rules and a named trusted agent (`trusted-coder`) surface
through `debug agents` on a contained boot. Require deny-default tails on every default agent and
an exact harness trusted ask profile on the named agent. No credential fields are read or printed.

**Result:** see **Validation** below. Unauthenticated roots are refused; authenticated installed
proof needs the operator session from D085.

## Reproduction

On the accepted Apple Silicon macOS host with hash-pinned OpenCode 2.2.5 and a login preflight
root:

```sh
python3 -B scripts/experiments/chatgpt_permission_proof.py \
  --root <prepared-work> \
  --source <v2.2.5 checkout>
```

Offline regression:

```sh
python3 -B scripts/tests/chatgpt_permission_proof_cases.py
```

## Boundary

- Reuses D076 composed profile, D085 root attach rules and login-mode invariants before
  `debug agents`.
- Network fully denied; no session or model turn.
- Uses the same deny and trusted permission shapes as harness agent fixtures
  (`agents_exec.py`).
- No production route, dependency or D034 change.

## Validation

- **Offline:** `chatgpt_permission_proof_cases.py` covers trusted validation and config merge; it
  joins `offline.py`.
- **Unauthenticated installed:** Exits 1 when `openai-connection` is absent (same gate as D085).
- **Authenticated installed:** Pending operator OAuth into the dedicated root; record redacted
  JSON summary here after one passing run.

## Limits

- Proof uses `debug agents` metadata only; it does not exercise tool invocation or live trusted
  grants. Account credits-off and D034 remain separate gates. Full P7.9/P7.10 remain unchecked
  and P7.11/P7.12 blocked.

## Next boundary

After this increment passes on an authenticated root, P7.9 continues with the account
credits-off / usage-limit assertion gate. P7.10 and Pi remain independent.