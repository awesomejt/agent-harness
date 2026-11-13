# P8.4 — Pi sequence and Ralph workflow parity

Date: 2026-11-12. Task: [P8.4](../../tasks/08-pi.md#p8-4). Decision: [D084](../../DECISIONS.md#2026-11-12--d084-pi-sequences-and-ralph-through-fresh-single-runs). Builds on [P8.3 live acceptance](p8-3-pi-acceptance.md) and the Phase 5/6 workflow contracts (D044/D045).

## Change

`ah sequence` and `ah ralph` already route each step or iteration through `single::launch`; Pi uses the same path as OpenCode and Claude with no new refusal gate. This increment adds fixture evidence that Pi records name `pi/MODEL`, use `agent_settled`, and honor retry/resume boundaries.

- Extended `scripts/tests/fake_pi.py` with per-launch `cases` selection (`launches.jsonl`), Ralph `claim`, `trusted-write`, and `eof-after-submit` behaviors.
- Added seven workflow cases to `scripts/tests/pi.py`: deny sequence, trusted stop/retry, uncertain step, preview, Ralph completion, Ralph cancel/resume, and `local-first` refusal.

## Fixture results

- `cargo fmt --check`, `cargo clippy --locked`, `cargo test --locked` pass.
- `python3 -B scripts/tests/pi.py`: **41** cases (34 single-run + 7 workflow).
- `node --test scripts/tests/pi_policy_boundary.mjs`: 8 cases.
- `python3 -B scripts/tests/offline.py`: **36/36** suites (includes `pi.py` and `pi_policy_boundary.mjs`; no live model).

## Limits

- Live sequence/Ralph on real LiteLLM remains operator opt-in; this task closes on fixtures plus documented capability updates.
- `local-first`, `cloud-only`, non-default effort and subscription Pi clients stay refused.
- Trusted `bash` path policy remains best-effort ([P8.3](p8-3-pi-acceptance.md)); workflow runs should pass `--permissions trusted` on every resume when tools are required.

## Next boundary

Phase 8 holistic review ([P8.5](../../tasks/08-pi.md#p8-5)) follows this evidence. Optional live workflow runs may be added to this file without changing production code.
