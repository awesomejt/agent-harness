# P8.2 evidence — Pi named agents

Task: [P8.2](../../tasks/08-pi.md#p8-2). Decision: [D082](../../DECISIONS.md#2026-11-12--d082-pi-named-roles-and-intersected-tools). Date: 2026-11-12. Platform: macOS, Pi **1.5.0** via `fake_pi.py`, branch `feature/08/p8-2-agents`.

Adds `--agent` for `litellm.runtime: pi`: canonical role body and optional project `AGENTS.md` compose the RPC prompt; tool allowlist intersects with invocation permissions through existing `grantable` mapping (e.g. reviewer → `find,grep,read`). Non-default effort refuses before launch. No live model turn.

## Reproduction

```text
cargo build --bin ah
python3 -B scripts/tests/pi.py
```

## Limits

- P8.3 installed live acceptance remains open.
- Sequence/Ralph parity unchanged (P8.4).

## Grok review

Pending PR.
