# P7.9 — Account credits-off assertion (retained login)

Date: 2026-11-14. Branch: `feature/07/p7-9-credits-off-assertion`. Depends on
[permission proof](p7-9-permission-proof.md) (D087) and
[login preflight](p7-9-login-preflight.md) (D085).

## Plan recorded before launch

On a retained root that passes D085–D087, record a bounded operator attestation that ChatGPT
Settings → Usage keeps **Allow other apps to use credits after reaching your usage limit** off
(D067), and prove without network that pinned `experimental.usage.limits` returns `null` on
ChatGPT-only login (Console/Go scope only in source). No credential fields are read or printed.

**Result:** see **Validation** below. Unauthenticated roots are refused; authenticated installed
proof needs the operator session from D085.

## Reproduction

On the accepted Apple Silicon macOS host with hash-pinned OpenCode 2.2.5 and a login preflight
root:

```sh
python3 -B scripts/experiments/chatgpt_credits_off.py --print-checklist
# Operator writes attestation JSON (label + timestamp only; no secrets).

python3 -B scripts/experiments/chatgpt_credits_off.py \
  --root <prepared-work> \
  --source <v2.2.5 checkout> \
  --attestation /path/to/attestation.json
```

Offline regression:

```sh
python3 -B scripts/tests/chatgpt_credits_off_cases.py
```

## Boundary

- Reuses D076 composed profile, D085 root attach rules and login-mode invariants before the
  usage route read.
- Network fully denied; no session or model turn.
- Attestation is point-in-time operator evidence; the harness does not scrape ChatGPT Settings.
- Pinned source shows `usage.limits` resolves OpenCode Console budgets/Go only, not post-limit
  app credits.
- No production route, dependency or D034 change.

## Validation

- **Offline:** `chatgpt_credits_off_cases.py` covers attestation schema and usage inventory;
  it joins `offline.py`.
- **Unauthenticated installed:** Exits 1 when `openai-connection` is absent (same gate as D085).
- **Authenticated installed:** Pending operator OAuth into the dedicated root and attestation;
  record redacted JSON summary here after one passing run.

## Limits

- Null `usage.limits` does not prove the ChatGPT toggle is off; operator attestation carries that
  gate. Continuous enforcement remains out of scope until a supported programmatic read exists.
- D034 remains a separate gate. Full P7.9/P7.10 remain unchecked and P7.11/P7.12 blocked.

## Next boundary

After this increment passes on an authenticated root, P7.9 feasibility closure and P7.11 design
remain gated on the remaining D034 and live acceptance boundaries. P7.10 and Pi remain independent.