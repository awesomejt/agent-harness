# P8.2 evidence — Pi deny-profile launch (first production slice)

Task: [P8.2](../../tasks/08-pi.md#p8-2). Decision: [D080](../../DECISIONS.md#2026-11-10--d080-optional-litellmruntime-selects-opencode-or-pi-locally). Date: 2026-11-10. Platform: macOS arm64, Pi **1.5.0** via fake RPC child, `ah` built on branch `feature/08/p8-2-deny-launch`.

This increment wires `litellm.runtime: "pi"` for `local-only` deny runs: private `PI_CODING_AGENT_DIR`, synthetic `ah-litellm` provider (`models.json` `apiKey` uses Pi 1.5.0 `${ENV}` interpolation per D064/D079 probes), RPC preflight (`set_auto_compaction`, `set_auto_retry`, `get_state` with required `piVersion` and empty tool arrays), prompt submission, `agent_settled` terminal mapping and cancellation. Trusted, `--agent`, `local-first`, `cloud-only` pi runtime and missing runtime refuse before launch. No live model turn.

## Reproduction

```text
cargo build
python3 -B scripts/tests/pi.py   # 21 cases including cancel-stall, models-key, cloud-only-pi
python3 scripts/tests/offline.py   # includes pi.py
```

## Limits

- Deny only; trusted grants and named roles refuse (later P8.2 slices).
- No sequence/Ralph parity claims in this PR; deny single-run path only.
- Installed Pi live acceptance remains P8.3.

## Grok review

Pending PR review.
