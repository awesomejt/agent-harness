# P8.3 — Pi single-run live acceptance

Date: 2026-11-12. Task: [P8.3](../../tasks/08-pi.md#p8-3). Consolidates installed Pi **1.5.0** adapter slices D080–D082 with live primary/specialized use. **P8.3 checkboxes stay open** until two passing `pi_live.py` runs on the operator proxy; sequence/Ralph parity stays P8.4. The [capability matrix](../FRAMEWORKS.md#p83-pi-capability-matrix) and [setup](../OPERATIONS.md#pi-local-only-p83) describe the supported surface.

## Accepted surface and evidence

| P8.3 requirement | Accepted implementation / evidence |
|---|---|
| Local-only Pi route with LiteLLM | D080, D060, [deny launch](p8-2-pi-deny-launch.md) |
| Trusted grants and deny profile | D081, [trusted](p8-2-pi-trusted.md), `pi.py` |
| Named coder/reviewer roles | D082, [agents](p8-2-pi-agents.md), `pi.py` |
| Live project tasks on real LiteLLM | `scripts/tests/pi_live.py`, observations below |
| Documented capability limits | D083, capability matrix |

Reviewed starting baseline: `main` after merged P8.2 named agents ([PR #98](https://github.com/awesomejt/agent-harness/pull/98)). This increment adds the opt-in live driver, acceptance record, docs, and installed Pi runtime fixes (argv, preflight, prompt disposition, session response text).

## Fresh live acceptance

Platform: Apple Silicon `arm64`, macOS **27.0.x**. Toolchain: Rust **1.88.0**. Runtime: Pi **1.5.0**. LiteLLM: operator proxy (`api_base` and model alias from the driver defaults or flags). Authentication is the configured `litellm.api_key_env` only; the driver forwards through a loopback recorder and never prints key material.

Command: `cargo build --locked`, export `LITELLM_API_KEY`, then `python3 scripts/tests/pi_live.py` (optional `--endpoint`, `--model`, `--binary`). Each run makes two real model turns in a disposable git project with sample `reviewer` and `coder` roles, trusted permissions, outside config, dirty `sentinel.txt`, and `AGENTS.md` marker `AH-P83-INSTRUCTIONS`. The reviewer is asked to read an outside file and write `REVIEW.md`; the coder must fix `calc.py` and run `python3 -B test_calc.py` via bash without changing tests, roles, instructions or sentinel content.

| Role | Seconds | Host prompts / grants | Tool events | Observed effects |
|---|---:|---:|---:|---|
| reviewer | — | — | — | **Blocked on this host (2026-11-12):** Pi reached `agent_settled` with no assistant text ~0.2 s after `disposition: started`; exit 1 after adapter fix. `single_runtime.py --live` on the same alias timed out uncertain (≈92 s). Operator must re-run `pi_live.py` when LiteLLM and the Pi `ah-litellm` provider return a non-empty completion. |
| coder | — | — | — | Not attempted after reviewer failure. |

Every successful attempt must report Pi 1.5.0, `pi/MODEL`, the selected role, `agent_settled`, success, no protocol violation and confirmed cleanup. The coder row must change only `calc.py` and pass independent arithmetic tests. The reviewer row must leave the project unchanged (no `REVIEW.md`) and reference `calc.py` in the response. Timings and grant counts are observations, not performance claims.

## Checks and limitations

Offline: `python3 -B scripts/tests/pi.py` (34 cases), full `offline.py` suite, `cargo test --locked`, fmt/clippy as in prior P8.2 slices. Live inference remains excluded from `offline.py`.

Supported scope is `local-only` with `litellm.runtime: pi` only. Read-only role ceilings intersect tools but may still grant some extension UI prompts (unlike Claude D050); grant counts are recorded explicitly. No sequences, Ralph, `local-first`, subscription Pi clients or non-default effort. P8.4 workflow parity and P8.5 holistic review remain gated.

## Next boundary

On merge of this PR, record the driver and adapter fixes; mark **P8.3 complete** in PROJECT.md only after sanitized live table rows pass. P8.2 holistic lifecycle may still be tracked separately. Next selected work is **P8.4** sequence/Ralph parity after **P6.5**, or other gated tasks. No development-platform switch is required.

## PR review closeout

Feature [PR #100](https://github.com/awesomejt/agent-harness/pull/100) merged after Grok review (first pass and follow-up addressed). Live run table remains pending two passing operator runs. P8.3 PROJECT checkbox stays open until the table is filled per [GIT_WORKFLOW](../GIT_WORKFLOW.md).
