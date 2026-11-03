# P3.5 — Dual-route use gate

Date: 2026-11-03. Entry: `ea9a5f4` (merged P3.7 / PR #30). Task branch: `feature/03/p3-5-dual-route-use`. [Card](../../tasks/03-routing.md#p3-5). This record prepares Phase 3 exit evidence for the P3.6 holistic review; it does not close the phase.

## Setup

- **Platform:** macOS 27.0.1 arm64 and Rust 1.88.0. The harness was a release build of source `ea9a5f4` (it reports `ah 0.1.0-alpha.1`, the unchanged package version), running on OpenCode `v2.2.5` (Homebrew).
- **Local route:** the user's LiteLLM proxy at `http://litellm:4000/v1`, existing alias **`flash`**. The user reports it serves Qwen 3.8 Flash Next on their AI server. The proxy server version was not reported.
- **Native route:** OpenCode's built-in `opencode` provider, model **`opencode/deepseek-v4.1-flash-free`**. A free catalog model was chosen so the gate spends nothing; ACP reported `session_cost=0 USD` on every native run.
- **Credentials:** the user's existing `LITELLM_API_KEY` and `OPENCODE_API_KEY`, loaded from `.zshrc`. Values were never printed or recorded, and each run checked both key values against its stdout and stderr: no match.
- **Project:** a disposable Git project with `calc.py` (`add` returns `a - b`) and `test_calc.py`. Every run used the same prompt with `--permissions trusted --timeout-secs 300`. Before each run, `calc.py` was reset and `verified` removed. After each run, the test was re-run independently.
- **Ambient environment:** the user's shell also exports `OPENCODE_CONFIG_DIR`, `OPENROUTER_API_KEY` and `LITELLM_MASTER_KEY`, and `~/.config/opencode` is configured. None of these may participate.

## Live results

| Run | Mode / endpoint | Route taken | Exit | Time | Grants | Edit + `verified` | Independent test | Context used |
|---|---|---|---|---|---|---|---|---|
| Local | `local-only` | LiteLLM `ah-litellm/flash` | 0 | 17 s | 5/5 | Yes | Pass | 3166 tokens |
| Native | `cloud-only` | native `opencode/deepseek-v4.1-flash-free` | 0 | 10 s | 3/3 | Yes | Pass | 3080 tokens |
| Local-first, reachable | `local-first`, `litellm:4000` | attempt 1 LiteLLM only | 0 | 13 s | 4/4 | Yes | Pass | 3093 tokens |
| Local-first, fallback | `local-first`, closed `127.0.0.1` port | attempt 1 check → attempt 2 native | 0 | 9 s | 4/4 | Yes | Pass | 2918 tokens |

**Route explanations.** `--preview` output for each mode is read-only and network-free:

- **local-only:** `route: LiteLLM only; fallback: disabled`, model `ah-litellm/flash`, and proxy handoff `direct proxy model group "flash" … existence unverified`.
- **cloud-only:** `route: native OpenCode built-in opencode API-key provider; fallback: disabled`, model `opencode/deepseek-v4.1-flash-free`, and proxy handoff `not applicable (native route)`.
- **local-first:** `route: LiteLLM primary; configured native OpenCode fallback`, which names the native fallback model.

The live run output matched these explanations:

- The **reachable** local-first run reported `LiteLLM endpoint reachable; later failures stop without fallback`, then a single local attempt.
- The **fallback** run reported `LiteLLM endpoint unreachable before submission; no runtime launched; no project changes`. The next line was `attempt=2 fallback from attempt=1; fresh runtime state and grants; shared deadline`, and the native attempt completed the task. The final line reported `fallback=attempt 2 (native) after pre-submission LiteLLM transport failure; no further retry`.

**Native-config isolation**
- The local run wrote the managed `opencode.json` and receipt. Their SHA-1 hashes were identical before and after the native run.
- A clean re-check took a fresh marker, ran one local-only and one cloud-only run (both exit 0, both verified), and then searched for changes. It found **0 modified entries** in each of `~/.config/opencode`, the `OPENCODE_CONFIG_DIR` profile, `~/.local/share/opencode`, `~/.local/state/opencode` and `~/.cache/opencode`. The user's background service stayed `stopped`.
- After all runs, no `ah-runtime-*` private state and no `opencode serve` process remained.
- An earlier, broader check had shown changes under `~/.local/share/opencode`. Their timestamps matched direct `opencode` invocations made during this session with the user's real HOME (`--version` during setup and `service status`), not harness runs. That is why the clean re-check was done.

**Recovery limits (live)**

| Check | Result |
|---|---|
| Native route with a bogus key (`cloud-only`) | The provider rejected the run after prompt submission: exit 4 (uncertain), 0 grants, no edit, and the bogus value was not echoed. This shows the free model does check the key, so the successful native runs prove that the real `OPENCODE_API_KEY` authenticates on 2.2.5. |
| `local-first`, reachable LiteLLM, nonexistent alias (`--model ah-no-such-alias`) | The local attempt failed after submission: exit 4, with `fallback not eligible after the reachability check` and `no automatic retry`. No native attempt ran and there was no edit (D031/D034). |

## Findings and friction

1. **Provider failure after submission reports exit 4 even with no tool activity** (bogus key; unknown alias). In both cases the runs record 0 grants, and under the 2.2.5 profile every tool needs a grant or has been removed. So no project side effect was possible, yet the outcome is "uncertain" and tells the user to inspect project effects. This is conservative and consistent with D031, but noisy for the commonest setup mistakes. **Candidate:** classify "prompt submitted, terminal error, zero grants and zero completed tool calls" as a known failure (exit 1), still without fallback. Recorded for P3.6 or later backlog ordering; this use gate does not change policy.
2. **Free native models** keep the gate at zero cost. Their terms may differ from paid models (for example, data use). Operators should pick `native.model` deliberately; the harness does not rank or price models.
3. **OpenRouter** (the user's ambient `OPENROUTER_API_KEY`) is not a native target under D032; it belongs behind LiteLLM. Adding it as a LiteLLM alias gives the local route OpenRouter models with no harness change.
4. **No direct OpenCode comparison** was run for this gate; the card does not require one. P2.6 recorded the first-slice comparison.

## Limits

- Each route ran one representative edit/test task with one model. Larger tasks, paid native models, rate limiting and proxy-group outages were not exercised.
- Reachability is still the only fallback evidence: a reachable proxy whose deployment is down fails locally (D034).
- The published `v0.1.0-alpha.1` binary still requires OpenCode 1.18.30. These results come from source `ea9a5f4`, and a new release is needed for binary users.
