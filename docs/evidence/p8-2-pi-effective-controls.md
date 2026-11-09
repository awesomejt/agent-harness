# P8.2 evidence — Pi settings and synthetic credential controls

2026-11-08 (America/Denver). Entry: merged PR #78, `93879dc` (verify full entry identity in Git history). Task: [P8.2](../../tasks/08-pi.md#p8-2). Consumes D060/D064; disposition: D065.

## Result and scope

This focused effective-control increment proves project-settings exclusion and synthetic credential precedence in the pinned installed Pi 1.5.0 runtime. It extends the [discovery probe](p8-2-pi-feasibility.md), retaining its exact runtime-tree/Node fingerprints, disposable state, environment allowlist, network/home-read/outside-write containment, bounded capture and process-group cleanup. No prompt, HTTP request, real credential/config read, production Rust change, dependency or installation occurs.

The broad P8.2 card remains open. Complete provider/resource coverage, trapped HTTP route fidelity and adversarial tool denial precede production/model work; this PR closes only the settings/credential substep. A callable credential resolver and idle state do not establish which headers a future HTTP client sends. OS containment remains an experiment fence, not a production policy.

## Installed observations

1. **Project settings and SYSTEM require a separate exclusion.** Seed `.pi/settings.json` with conflicting enabled retry/compaction, seven provider retries, an inert default-model marker and idle cache warming. Private settings disable retries/compaction/provider retries/cache warming and use a distinct default-model marker. With `--no-approve`, the startup observer's `pi.getSettings()` reports only the private values, and the existing no-tool/MCP/skill/template/context checks pass. The explicit CLI provider/model remains exact. The project settings file remains unchanged.
2. **A positive control proves detection.** Change only `--no-approve` to `--approve`, still under network denial and with no model turn. The startup observer now sees the project retry/compaction/provider-retry/default-model values and exactly the seeded `.pi/SYSTEM.md` sentinel (all other named context sentinels remain absent), despite `--no-context-files`. After correlated `set_auto_compaction(false)`, `get_state` still reports compaction enabled because the project layer overrides the private write. The safe validator rejects this state; a fixture-specific positive-control expectation accepts it. The discovery flags alone must not be promoted into production isolation.
3. **Cache warming has a distinct accessor.** A separate contained Node process imports `SettingsManager` from the fingerprinted copied installed package, creates it with project trust enabled, and checks both merged settings and `getCacheWarmingMode()`. Merged settings report `idle`; the actual accessor reports `off`, from private/global settings. This is an installed component check, not an observation of background request behavior. The extension's merged view alone is insufficient to assert effective warming.
4. **Synthetic stored auth overrides the configured environment key.** The startup observer resolves the explicit synthetic model through `ctx.modelRegistry.getApiKeyAndHeaders()`. It emits only `authOk`, a key-source enum (missing/empty keys classify as `unset`) and whether headers/base-URL overrides appear, never key bytes. Initially the private `models.json` interpolation resolves to the allowlisted synthetic environment key, with no auth override headers/base URL. Seed a private `auth.json` entry for the same provider with a different synthetic key: the resolver chooses the stored key. Delete that synthetic auth file and the resolver again chooses the environment key. Each process reports the single expected available model and unchanged explicit idle model route. The normal safe settings/credential validator rejects the stored-key case; only its explicit positive-control expectation accepts it.

Consequences: the eventual adapter needs `--no-approve`, exclusive private-state ownership and rejection of unexpected auth material/effective settings before submission. Do not copy user auth or treat the environment interpolation as an override of stored credentials. `getAvailable()` describes authenticated chat-model availability, **not** the full provider/resource inventory, custom non-chat models, extension registration sources or actual HTTP routing.

## Source and reproduction

The installed package was already matched against the published distribution in discovery. The unchanged tree pin includes the sources used here. Matching release references: [CLI controls](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/docs/cli.md), [settings manager](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/src/core/settings-manager.ts), [provider composer](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/src/core/provider-composer.ts), [model registry](https://github.com/earendil-works/pi/blob/f9a26365568127461c47a07a37dcb42c140a3ac5/packages/coding-agent/src/core/model-registry.ts). Read the installed JS/types for the extension API and getter behavior; verify the pinned CLI reference online. No moving-source assumption or package installation is required.

```sh
python3 -B scripts/experiments/pi_feasibility.py \
  --release /Users/jason/.pi/agent/install/releases/1.5.0 \
  --node /Users/jason/.nvm/versions/node/v24.14.0/bin/node \
  --effective-controls
python3 -B scripts/tests/pi_feasibility_cases.py
python3 -B scripts/tests/doclinks.py
git diff --check
```

The default discovery mode remains available. Both modes use only the fixed disable-compaction, disable-retry and get-state RPC records. The new mode adds no caller-controlled RPC method, model turn or network allowance. Offline cases cover missing/malformed control reports, enabled settings, non-integer provider retries, wrong setting/key source, auth failure/overrides and unexpected available models, alongside the existing protocol/output/deadline/cleanup cases. The installed trust and auth positive controls prove the observations can detect the specific unsafe states.

## Next boundary

Continue on this host with a focused complete resource/provider-source inventory assessment and a trapped synthetic HTTP/adversarial-deny experiment once its prerequisites are proven. Do not use operator credentials or a real inference endpoint to bridge the gate. Exact trusted grants, adapter/terminal/lifecycle implementation and P8.3 live acceptance remain separate. P7.6/P7.7 and P8.5 review gates are not ready. No development-platform switch is required; continuing context is efficient for the remaining closely related Pi feasibility work.

Grok PR #79 review of `ac7b40b` (posted as `awesomejt`): 0 blockers, 1 concern, 1 nit. The concern identified that an aggregate context marker could not prove SYSTEM attribution; the corrected observer reports each named sentinel and requires exactly SYSTEM for the trusted positive control, and none otherwise. The nit identified an undefined-key equality edge case; missing/empty keys now classify as unset before source comparison. Installed controls and offline absent/wrong/additional sentinel and unset/unexpected key-source refusal cases pass, as do links/whitespace. No critical/high fixes or re-review required.
