# P8.2 evidence — Pi trusted extension UI grants

Task: [P8.2](../../tasks/08-pi.md#p8-2). Decision: [D081](../../DECISIONS.md#2026-11-11--d081-pi-trusted-grants-through-rpc-extension-ui). Date: 2026-11-11. Platform: macOS, Pi **1.5.0** via `fake_pi.py`, `ah` on branch `feature/08/p8-2-trusted`.

Adds `--permissions trusted` for `litellm.runtime: pi` (`local-only`): `--tools` allowlist, harness-owned policy extension with Pi RPC `extension_ui_request` / `extension_ui_response` confirm bridge and shared `PermissionPolicy` allow-once per call. Named agents remain refused. No live model turn.

## Reproduction

```text
env -u CARGO_TARGET_DIR cargo build --bin ah
python3 -B scripts/tests/pi.py
```

## Limits

- Full trusted tool set only; named-role narrowing is a later slice.
- P8.3 installed live acceptance still open.

## Grok review

Pending PR.
