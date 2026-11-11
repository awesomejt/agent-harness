# P8.2 evidence — Pi resource inventory, HTTP trap, adversarial deny

2026-11-10 (America/Denver). Task: [P8.2](../../tasks/08-pi.md#p8-2). Consumes D060/D064/D065; disposition: D079.

## Result and boundary

Installed pinned Pi 1.5.0 under disposable macOS containment completes a third P8.2 feasibility increment: full registry snapshot (`getRegisteredProviderIds`, `getAll`/`getAvailable` counts, `getModelsOfType` for chat/image/classifier, redacted `getAllTools` sourceInfo, `getMcpServers`), adversarial `prompt`/`bash` RPC refusal before an owned-root marker appears (paired with a permissive-extension positive control that can create the same marker), and a trapped OpenAI-compatible `GET /v1/models` capture when `ModelRuntime.refresh` runs with explicit `allowNetwork` on one owned loopback port through a synthetic `refreshModels` hook. No operator credentials, no production Rust change, no real HTTP beyond the owned trap, and no successful model turn occur.

This increment may close on required PR review/merge. P8.2 remains unchecked for adapter/production acceptance; exact trusted grants and lifecycle proofs stay gated. OS containment remains an experiment fence.

## Installed fingerprints and reproduction

Runtime fingerprints match [discovery](p8-2-pi-feasibility.md) (`TREE_HASH`, `CLI_HASH`, `NODE_HASH`). On this host:

```sh
python3 -B scripts/experiments/pi_resource_route.py \
  --release /Users/jason/.pi/agent/install/releases/1.5.0 \
  --node /Users/jason/.nvm/versions/node/v24.14.0/bin/node
python3 -B scripts/tests/pi_resource_route_cases.py
python3 -B scripts/tests/pi_feasibility_cases.py
python3 -B scripts/tests/doclinks.py
git diff --check
```

The probe copies runtime into scratch, clears managed-install inheritance, uses private `PI_CODING_AGENT_DIR`, and keeps default network denial except during the isolated refresh subprocess bound to one reserved localhost TCP port. Inventory RPCs remain allowlisted (`set_auto_compaction`, `set_auto_retry`, `get_state`). The observer extension blocks `tool_call`, throws on `before_agent_start`/`before_provider_request`/`user_bash`, and emits one `ah_resource_route` JSON record on stderr at `session_start`. Adversarial stdin adds fixed `prompt` and `bash` records targeting a marker under the writable root; validation requires bash failure, stdout/stderr containing the harness error strings, zero pending messages, and an absent marker, with a second run using an observer without the bash/prompt guards that writes the same marker at `session_start`, proving the blocking hooks change the outcome under the same sandbox. The refresh sidecar imports `ModelRuntime` from the **copied** tree, registers a synthetic `refreshModels` hook for `ah-feasibility`, calls `refresh({ allowNetwork: true, providers: ['ah-feasibility'] })`, and records trap header **names** plus an `authorizationSynthetic` flag.

## Limits and next boundary

`getRegisteredProviderIds()` lists extension-registered providers only; configured provider IDs are reported separately from `getAll()`. Builtin catalog counts are large offline bundles, not a harness authorization set. Prompt RPC may return `success: true` with `disposition: started` while extensions block before provider HTTP; the harness requires the specific `Harness blocked …` error strings plus `messageCount == 0`, not RPC-level `success: false` alone. Trap capture exercises refresh-hook network gating through a synthetic `refreshModels` implementation, not Pi RPC's built-in provider listing path. Adapter mapping, trusted grants, P8.3 live acceptance, P8.4 workflows and P8.5 holistic review remain open.

## Grok review

<!-- Placeholder: record PR review id, commit, blocker/concern/nit counts and remediation after merge. -->
