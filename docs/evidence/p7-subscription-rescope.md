# Phase 7 evidence — re-scoping around the operator's subscriptions

2026-11-08. Entry: `6b5dd12`. Decision: [D067](../../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage). Terms sources: [provider terms check](p7-native-terms-check.md). Related: [D066](../../DECISIONS.md#2026-11-08--d066-block-antigravity-on-consumer-plan-terms).

This record collects what the operator and this session established on 2026-11-08 about spend, subscriptions and fallback. It separates **settled constraints** from **open design questions**, so later work can re-explore the open parts without re-deriving the settled ones. Provider prices and limits below are a dated snapshot; re-read the sources before relying on them.

## Operator constraints (settled)

1. **No metered API spend** unless the usage is covered by an allowance or credit included in a subscription. Unpredictable API bills are the problem to avoid.
2. **A hard stop beats overage.** A "usage limit reached" error is acceptable; an unexpected bill is not. Overage switches stay off: OpenAI's "Allow other apps to use credits after reaching your usage limit" and OpenCode Go's **Extra Usage**.
3. **Subscription routes are for runs the operator starts on their own account.** Nothing that lets other people trigger runs on a subscription login, such as a Hermes bot that others can prompt. Every provider's terms bar making the account available to others.
4. **Gemini is a hard pass for now.** The consumer Google login is blocked by D066. Google AI Pro's $10/month Google Cloud credit ([Developer Program FAQ](https://developers.google.com/profile/help/benefits)) sits on a normal Cloud billing account, and no hard spend cap was confirmed. The operator also wants to protect a Google account that holds a lot of their other data.

## Subscription inventory

| Subscription | Included usage | How the harness may use it | Status |
|---|---|---|---|
| Claude (Pro/Max) | Plan limits; no API credits | Official `claude` CLI only (P7.2, D047) | Accepted adapter. Operator accepts the terms position in D067, with a re-check date. |
| ChatGPT (Plus/Pro) | Codex/ChatGPT plan limits | OpenCode or Pi via [Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt), which officially lists both | Preferred OpenAI path. Harness support is not built: OpenCode `cloud-only` accepts only an API key today, and D060 excluded Pi subscription clients. The `codex` adapter (P7.3) stays paused. |
| OpenCode Go ($10/month individual) | Per-model monthly allowances (below) | OpenCode or Pi as native clients; possibly LiteLLM (open question) | Not wired. Placement is open. |
| SuperGrok | One weekly pool across Grok products ([Grok FAQ](https://docs.x.ai/grok/faq)) | None from the harness for now. First-party Grok Build and Grok Bot PR review only | P7.4 stays paused (D058). xAI has no statement either way on third-party ACP clients. |
| Google AI Pro | Consumer limits plus $10/month Cloud credit | None | Blocked (D066); Gemini excluded by constraint 4. |
| Local models | No provider limit | LiteLLM (D002) | Working today. |

## OpenCode Go snapshot (2026-11-08)

Source: [OpenCode Go docs](https://opencode.ai/docs/console/go/).

- **How allowances work.** Each model has a monthly dollar allowance at its listed per-token prices: $15, $20, $30, $60 or $100 depending on the model. The page does not state a single pooled total for the $10 plan; it reads as a separate allowance per model, but that is an interpretation. Each model also has a 5-hour window (20% of the monthly allowance) and a weekly window (50%). The 5-hour window is usually the first one hit.
- **Usage reporting.** Each response reports what it counted as `opencode.allowance`, so the harness could record real usage per attempt.
- **Request estimates** assume agent-style calls of about 1,000 fresh input tokens plus 55,000 cached tokens. A coding task usually makes many requests, so the numbers below are calls, not tasks.
- **At the limit:** requests stop, and free models stay available. Paid overage happens only with Extra Usage enabled.

Representative models, with approximate requests per 5-hour window:

| Tier | Examples |
|---|---|
| Heavy (a few tasks per window) | Kimi K3 (~110), Kimi K3.1 Pro (~147), Qwen3.8 Max (~160), GLM-5.3 (~220) |
| Mid-weight ("smarter local" candidates) | GLM-5.2 (~880), DeepSeek V4 Pro (~1,050), Kimi K2.7 Code (~1,350), MiniMax M3 (~3,200), Qwen3.7 Plus (~4,300) |
| Cheap/flash | GLM-5.3-Flash (~6,300), MiMo-V2.6-Flash (~30,000), DeepSeek V4.1 Flash (~43,000) |
| Free, limited time | Crouton Alpha Free and Beam Free (regional restrictions); Iceman Contributor Free (prompts and completions used for training, so unsuitable for private code) |
| Closed models | Claude Haiku 5.5 (~3,850), GPT 6 Luna (~4,230), GPT 5.6 Luna (~2,050), Grok 4.7 (~169), Gemini 4 Argon (~440, 50% off until 2026-11-30) |

Gemini 4 Argon would be a capped way to use Gemini without touching the Google account. Constraint 4 excludes Gemini for now; this is recorded only in case it is reconsidered.

## What the harness does today

- `local-first` tries LiteLLM, then makes **one** configured native attempt, and only when the LiteLLM endpoint is unreachable **before launch** (D034).
- Uncertain work is never replayed (D031/D034). A run that may have changed files is not retried on another route.
- Route labels are not physical locality: `local-only` means "LiteLLM only" and may include OpenRouter or other hosted models (D002, routing contract).
- Each harness attempt is a separate runtime process with a fresh context.
- The harness avoids silent model changes inside a run. For example, Claude's `--fallback-model` is never passed (D046).

## Open design questions (not decided)

### Where Go is called

- **OpenCode/Pi provider (current lean).** These are Go's native or validated clients and meet its client conditions without extra work. OpenCode would need a config form that selects the `opencode-go` provider and never the pay-as-you-go `opencode` (Zen) provider by accident. Pi's D060 scope would need revisiting.
- **LiteLLM route.** This fits D002 as written, since Go is an open-weight subscription, and it puts Go into the existing model-alias and `group:` mechanics. It must keep the `x-opencode-session` header and send an acceptable user agent. LiteLLM's per-call router fallbacks would switch models **inside** one coding run. That conflicts with the no-silent-model-change stance unless it is limited or reported. Harness-level fallback between attempts gets a fresh process and a recorded route change anyway, so per-call fallback adds less than it seems.
- Decide together with the fallback design below.

### Fallback chain

The operator's working idea is local, then a cloud subscription, then Go. Needed before it can work:

1. **More than one fallback step.** D034 allows a single native attempt. An ordered chain is new design work.
2. **Allowance exhaustion as a trigger.** Today only "endpoint unreachable before launch" triggers fallback. A subscription "limit reached" error may arrive mid-run, after edits. Candidate rule: fall back only when the limit error arrives before any tool call or file change; otherwise stop and report.
3. **How Go rejects over-limit requests** is unknown: status code, error shape, and whether it arrives before the first token. Test this with a deliberately exhausted cheap-model window before designing around it.

### Local, then Go with a similar model

- When the local models are unavailable, map to the same or a similar open-weight model on Go.
- This needs an **explicit "private" setting** that guarantees physically local execution and refuses any hosted endpoint, because the current `local-only` label does not mean that.
- **Free models are risky** to depend on: quality is untested, they are limited-time and may become paid, two are region-restricted, and one trains on your prompts.

### Mid-weight models as a "smarter local"

Candidates are listed in the snapshot table. Whether any is worth it over the local models needs a small evaluation on real project tasks before any default changes.

### Go's closed models as a cloud fallback

Use Go's Claude Haiku, GPT Luna or Grok models when the matching subscription is exhausted. Go's allowances are small, so the operator's idea is to finish the current task or prompt on Go, then record a **known problem** for follow-up. That needs:

- a durable record type or log entry for "finished on a fallback model";
- a decision about whether a smaller sibling model counts as "the same" model for constrained roles;
- the same over-limit behaviour test as above.

### Phase 7 portfolio

P7.6/P7.7 are defined over four native targets. Antigravity is blocked (D066). Codex and Grok are paused, and OpenAI now has a preferred non-`codex` path. Phase 7 cannot close as written. Redefine the portfolio in a separate decision once the routing and fallback design above is settled.

## Related: GitHub-native workflow

The operator's current workflow runs first-party agents through GitHub: Claude or Codex do the work and open a PR, and Grok Bot reviews it. Claude and Codex also accept tasks remotely from their mobile apps. Every step stays inside each provider's own product, on subscription allowances, so it raises none of the third-party-client questions above. It complements the harness: GitHub-native agents for unattended or away-from-desk work, and `ah` for local, repeatable project loops with enforced permissions and local fallback. This is an observation, not a feature commitment.

## Validation

Sources read on 2026-11-08 as linked. Relative links and whitespace checked. Documentation only; no CLI was run against any provider.
