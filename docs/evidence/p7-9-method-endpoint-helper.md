# P7.9 — Method, endpoint and helper proof (retained login)

Date: 2026-11-13. Branch: `feature/07/p7-9-method-endpoint-helper`. Depends on
[login preflight](p7-9-login-preflight.md) (D085) and pinned
[feasibility selection](p7-9-chatgpt-feasibility.md) (D069).

## Plan recorded before launch

On a retained root that passes login-mode preflight, prove without network that the active
`openai` integration exposes the pinned `chatgpt-token-sharing` OAuth method, the ChatGPT
plugin endpoint (`baseURL`) matches the pinned resource constant, the provider package is
`opencode.provider.chatgpt`, and explicit helper selection (`openai` / `gpt-6.1-sol`) surfaces
through `model.default`. No credential fields are read or printed.

**Result:** see **Validation** below. Unauthenticated roots are refused; authenticated installed
proof needs the operator session from D085.

## Reproduction

On the accepted Apple Silicon macOS host with hash-pinned OpenCode 2.2.5 and a login preflight
root:

```sh
python3 -B scripts/experiments/chatgpt_method_endpoint_helper.py \
  --root <prepared-work> \
  --source <v2.2.5 checkout>
```

Offline regression:

```sh
python3 -B scripts/tests/chatgpt_method_endpoint_helper_cases.py
```

## Boundary

- Reuses D076 composed profile, D085 root attach rules and login-mode invariants before route
  reads.
- Network fully denied; no session or model turn.
- Provider responses are redacted to `baseURL`, `encoding` and `transport` only.
- No production route, dependency or D034 change.

## Validation

- **Offline:** `chatgpt_method_endpoint_helper_cases.py` decodes pinned `chatgpt.ts` constants
  and covers provider redaction plus helper config merge; it joins `offline.py`.
- **Unauthenticated installed:** Exits 1 when `openai-connection` is absent (same gate as D085).
- **Authenticated installed:** Pending operator OAuth into the dedicated root; record redacted
  JSON summary here after one passing run.

## Limits

- Proof uses HTTP metadata routes only; deny/trusted grants, account credits-off and D034 remain
  separate gates. Full P7.9/P7.10 remain unchecked and P7.11/P7.12 blocked.
- `model.default` confirms the explicit helper selection merged into `OPENCODE_CONFIG_CONTENT`
  for this boot; it does not prove ChatGPT catalog fetch or live model availability.

## Next boundary

After this increment passes on an authenticated root, P7.9 continues with
deny/trusted permission proofs under retained login. P7.10 and Pi remain independent.