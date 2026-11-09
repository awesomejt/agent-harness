# Phase 7 evidence — provider terms for harness-driven native CLIs

2026-11-08. Entry: `6b5dd12` (merged PR #79). Tasks: [P7.2](../../tasks/07-native-adapters.md#p7-2), [P7.3](../../tasks/07-native-adapters.md#p7-3), [P7.4](../../tasks/07-native-adapters.md#p7-4), [P7.5](../../tasks/07-native-adapters.md#p7-5). Decisions: [D066](../../DECISIONS.md#2026-11-08--d066-block-antigravity-on-consumer-plan-terms), [D067](../../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage). Subscription re-scope findings: [p7-subscription-rescope.md](p7-subscription-rescope.md).

## Question and method

For each committed native adapter, plus the operator's OpenCode Go subscription (added later the same day), what does the provider's current official wording say about **driving its official CLI, signed in with a consumer or subscription login, from a third-party orchestrator or protocol client** such as `ah`? The harness launches the unmodified official CLI as a local subprocess for the operator's own use, and the CLI owns login (D001/D047).

Every source below was read on 2026-11-08 from the provider's own domain, except the one forum thread, which is labelled as such. Quotations are short excerpts, not the whole text. **This record quotes and compares sources. It makes no legal conclusion and no account-specific entitlement claim.** Provider pages change without notice; re-read them before relying on this record.

No CLI was run, no login, session or inference occurred, and no credential was read for this check.

## Summary

| Adapter | Login form in scope | Most specific official statement found | Looks like Antigravity's FAQ? |
|---|---|---|---|
| Antigravity (P7.5) | Google AI Pro consumer login | FAQ: wrapping `agy` in third-party agents or applications "is not supported under consumer plans"; third-party access can lead to suspension | **Yes — this is the source case.** Blocked by D066. |
| Claude Code (P7.2) | Claude Pro/Max/Ultra login | Legal page: OAuth is for "ordinary use of Claude Code"; developers of products and Agent SDK users "should use API key authentication"; it does not "prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription" | **Partly.** No "not supported" statement for wrapping, but automated-access and Agent SDK wording leaves the harness case unaddressed. No block; D067 records the operator's acceptance with a re-check date. |
| Codex / OpenAI (P7.3) | ChatGPT Plus/Pro login | [Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt): in supported apps, Plus and Pro subscribers "can also choose to use their ChatGPT plan for AI requests"; the page lists OpenClaw, OpenCode and Pi. Auth docs still recommend API keys "as the recommended default for automation" | **No.** OpenAI officially allows plan use in listed third-party apps. A third-party orchestrator driving the `codex` CLI itself is still not addressed. |
| OpenCode Go (not a P7 adapter) | Go subscription API key | [Go docs](https://opencode.ai/docs/console/go/): "designed for OpenCode and other coding agents that produce similar types of requests"; lists validated clients including Pi, Hermes, Claude Code and Codex | **No.** Use in other coding agents is documented, with client conditions. |
| Grok (P7.4) | SuperGrok / X Premium login | Build docs describe ACP "in other apps" and headless "integration into other apps"; terms bar credential sharing; AUP bars "using bots to access" | **No explicit statement either way** on subscription login under a third-party ACP client. Open question; already paused by D058. |

Only Antigravity has an official statement that names this setup and says it is unsupported on consumer plans. OpenAI and OpenCode Go are the only ones with official statements allowing subscription use in third-party coding tools.

## Antigravity (Google)

**[Antigravity FAQ](https://antigravity.google/docs/faq/)** (no page date shown; read 2026-11-08). Under "Can I use Antigravity CLI headless mode in third-party coding agents or automate account switching?":

- "Antigravity CLI headless mode (`agy -p`) is intended for direct scripting and CI workflows."
- "Wrapping `agy` inside third-party coding agents or applications, or automating account rotation, is not supported under consumer plans."

Under "Why can't I use third-party software (such as Claude Code, OpenClaw, or OpenCode) with my Antigravity login?":

- "Using third-party software, tools, or services to access Antigravity is a violation of our Terms of Service"
- "Such actions can result in suspension or termination of your account."
- "To use a third-party coding agent with Gemini, we recommend using a Gemini Enterprise or Google AI Studio API key."

The FAQ text is the same as the wording the operator's session recorded earlier on 2026-11-08.

**How this applies to the harness.** `ah` is a third-party orchestrating application. P7.5 planned to launch `agy acp` (or headless `agy -p`) as a subprocess under the operator's consumer Google AI Pro login (D061/D062). The FAQ describes this case as unsupported under consumer plans. The same FAQ calls headless mode "intended for direct scripting", which is the operator running `agy` from their own scripts, not `ah` wrapping it. The documented ACP surface ([ACP quickstart](https://antigravity.google/docs/cli/acp/), [editor/client guide](https://antigravity.google/docs/ide/extensions/acp)) shows that the protocol exists. It does not override the FAQ's consumer-plan statement.

**Earlier record.** The [P7.1 readiness assessment](p7-1-antigravity-readiness.md) cited only the general [Antigravity terms](https://antigravity.google/terms). It missed the FAQ statement above, so it treated the documented ACP interface as enough to proceed.

**Community forum (not an official source).** [Thread 181088](https://discuss.ai.google.dev/t/is-orchestrating-the-official-antigravity-cli-from-a-local-multi-agent-coding-application-allowed/181088), posted 2026-09-07, asks about this exact setup: a personal local app that launches the official `agy` CLI as a subprocess and lets the CLI handle Google sign-in. It asks for confirmation from a Google or Antigravity team member. As of 2026-11-08 it has one reply, from a user the page does not identify as Google staff, saying "Yes" to each question. **No Google staff answer is present.** A community reply does not change the FAQ statement, and it does not meet D066's resume condition.

## Claude Code (Anthropic)

**[Claude Code legal and compliance](https://code.claude.com/docs/en/legal-and-compliance)** (no page date; read 2026-11-08):

- Consumer use is subject to the [Consumer Terms](https://www.anthropic.com/legal/consumer-terms) "for Free, Pro, Max, and Ultra users".
- "Advertised usage limits for Pro, Max, and Ultra plans assume ordinary, individual usage of Claude Code and the Agent SDK."
- OAuth "is designed to support ordinary use of Claude Code and other native Anthropic applications."
- Developers building products, "including those using the Agent SDK, should use API key authentication".
- "Anthropic does not permit third-party developers to offer Claude.ai login into their own applications, or to route requests through Free, Pro, Max, or Ultra plan credentials on behalf of their users."
- Developers "may not collect, store, or intermediate Claude.ai credentials or session tokens".
- The restriction does not "prevent an end user from signing in to the unmodified Claude Code binary with their own Claude subscription", including where a platform hosts Claude Code.

**[Consumer Terms](https://www.anthropic.com/legal/consumer-terms)** (read 2026-11-08) prohibit, "Except when you are accessing our Services via an Anthropic API Key or where we otherwise explicitly permit it", accessing the Services "through automated or non-human means, whether through a bot, script, or otherwise". They also prohibit sharing login information or credentials.

**[Run Claude Code programmatically](https://code.claude.com/docs/en/headless)** describes `claude -p` as using "the Agent SDK via the CLI" for "scripts and CI/CD". Its `--bare` example says to set an API key "because bare mode doesn't use your subscription login".

**Comparison.** The legal page explicitly allows the end user to sign in to the unmodified binary with their own subscription, and it forbids intermediating credentials. The harness does neither of the forbidden things: P7.2 runs the unmodified `claude` binary for the operator alone, and the CLI owns login. The legal page also says ordinary usage of "Claude Code and the Agent SDK" is assumed, which mentions programmatic use alongside plan limits. Still, the sources leave a gap. They do not say whether `claude -p` under a plan login, launched by a personal orchestrator, counts as "ordinary, individual usage" or as automated access the provider "explicitly permit[s]". There is no statement like Antigravity's saying wrapping is unsupported. **Flag: partly similar.** P7.2 is an accepted adapter running on a plan login today, so the gap is not hypothetical. [D067](../../DECISIONS.md#2026-11-08--d067-re-scope-around-included-subscription-usage) records the operator's explicit choice: accept the P7.2 plan-login use for runs the operator starts on their own account, never triggered by other people, with a dated re-check. This check does not change the accepted P7.2 status. The [P7.1 Claude selection](p7-1-claude-selection.md) (2026-11-05) recorded the same plan-login boundary.

## Codex (OpenAI)

**[Codex authentication](https://learn.chatgpt.com/docs/auth)** (formerly `developers.openai.com/codex/auth`; read 2026-11-08):

- Codex supports "Sign in with ChatGPT for subscription access" and "Sign in with an API key for usage-based access".
- "Use API key authentication for programmatic Codex CLI workflows, such as CI/CD jobs."
- "API keys are still the recommended default for automation."
- Workspace access tokens "are intended for trusted scripts, schedulers, and private CI runners" (ChatGPT workspace plans).
- Treat `~/.codex/auth.json` "like a password", and "Don't expose Codex execution in untrusted or public environments."

**[Codex app-server](https://learn.chatgpt.com/docs/app-server)** (read 2026-11-08) is "the interface Codex uses to power rich clients (for example, the Codex VS Code extension)", and the page says to "Use it when you want a deep integration inside your own product". For automation and CI it points to the Codex SDK. The page does not say which login forms third-party app-server clients may use.

**[OpenAI Terms of Use](https://openai.com/policies/terms-of-use/)** (effective January 1, 2026) prohibit you to "Automatically or programmatically extract data or Output" and to "circumvent any rate limits or restrictions". They prohibit sharing account credentials or making the account available to others, and allow suspension or termination for breach.

**[Sign in with ChatGPT](https://learn.chatgpt.com/docs/sign-in-with-chatgpt)** (no page date; read 2026-11-08, after the first version of this record):

- "In supported apps, eligible ChatGPT Plus and Pro subscribers can also choose to use their ChatGPT plan for AI requests."
- "App usage counts toward your existing plan limits." The plan "uses your Codex / ChatGPT work usage included in your plan."
- The page lists open-source integrations including OpenClaw, OpenCode and Pi.
- A setting, "Allow other apps to use credits after reaching your usage limit", lets apps spend credits beyond the plan limit. D067 keeps it off.
- The page lists no personal-use, automation or resale restrictions.

**Comparison.** *Corrected 2026-11-08.* The first version of this record missed the Sign in with ChatGPT page and called OpenAI "partly similar". OpenAI officially lets listed third-party coding tools, including OpenCode and Pi, use a ChatGPT plan. That is the opposite of Google's consumer-plan position. OpenAI still recommends API keys for automation, and its sources do not directly address a third-party orchestrator driving the `codex` CLI on a plan login. The Terms of Use clause on programmatic Output extraction is general, and none of these sources apply it to Codex. **Flag: not like Antigravity.** D067 makes OpenCode/Pi on the ChatGPT plan the preferred OpenAI path. P7.3 stays paused under D055.

## Grok (xAI / SpaceXSI)

**[Grok Build overview](https://docs.x.ai/build/overview)** (read 2026-11-08): "Use it via an interactive TUI, headlessly in scripts or bots, or through the Agent Client Protocol (ACP) in other apps." "Headless usage is ideal for scripts, automations, or integration into other apps." The page names no subscription tiers and has no permitted-use section.

**[Headless and scripting](https://docs.x.ai/build/cli/headless-scripting)** (read 2026-11-08): "Use ACP when you want IDE or tool integration rather than a terminal session." Its ACP example "assumes `grok` is already authenticated locally, or `XAI_API_KEY` is set", so it accepts either a cached login or an API key. It has no terms or unsupported-use statements.

**[Consumer Terms of Service](https://x.ai/legal/terms-of-service)** (last updated October 27, 2026; the page names the provider "SpaceX Super Intelligence LLC (“SpaceXSI”)", which is the current operator of Grok, not a typo; read 2026-11-08 in a browser because the plain fetch returned 403): "You may not share your account credentials or make your account available to anyone else". The terms cover "Agentic Actions" such as code execution and modifying files, and they make the user responsible for them. They allow suspension or termination at xAI's discretion for breach of the Terms or the Acceptable Use Policy. They say nothing specific about third-party clients or Grok Build.

**[Acceptable Use Policy](https://x.ai/legal/acceptable-use-policy)** (read 2026-11-08) lists "using bots to access" the Service among examples of detrimentally affecting it. The list also includes copying, reselling and reverse engineering. It says not to "circumvent safeguards".

**Comparison.** xAI's own Build docs describe ACP use "in other apps" and headless "integration into other apps", and do not limit this to API-key accounts. The general AUP wording on "using bots to access" is not applied to Grok Build in any source found. No official statement says subscription login is unsupported under a third-party ACP client. **Flag: no Antigravity-like statement found. Open question.** Third-party GitHub and community pages disagree about how the terms apply; none is an official source, and none is relied on here. P7.4 is already paused under D058 for control reasons.

## OpenCode Go (OpenCode)

Not a Phase 7 native adapter. It is the operator's metered-but-capped subscription for hosted open-weight (and some closed) models. It is included here because D067 inventories every current subscription.

**[OpenCode Go docs](https://opencode.ai/docs/console/go/)** (no terms-of-service link on the page; read 2026-11-08):

- Go is "designed for OpenCode and other coding agents that produce similar types of requests." The page has setup guides for Claude Code, Codex, Hermes, Pi and Raycast.
- **Validated clients:** Hermes, Claude Code, Codex, ZCode, Pi, jcode and Kilo Code CLI. Most need a minimum version; future compatibility is not guaranteed.
- **Known problematic clients:** DeepSeek Harness, GitHub Copilot Chat, Kimi Code and MiMo Code, because of missing or incomplete session support.
- **Client conditions:** send typical coding-agent traffic; identify with the client's own user agent, "not a generic SDK or HTTP-library name"; send a stable session ID in `x-opencode-session`. Proxies should preserve that header. "Traffic is monitored for abuse that degrades the experience for other users."
- **Limits:** per-model monthly dollar allowances at the listed prices, with 5-hour (20%), weekly (50%) and monthly (100%) windows. At the limit, requests stop unless **Extra Usage** (pay-as-you-go from a credit balance) is turned on. It is off by default except on Go Teams.

**Comparison.** Use from other coding agents is explicitly documented. **Flag: not like Antigravity.** The client conditions matter for routing: OpenCode and Pi are native clients, and a LiteLLM route would have to keep the session header and send an acceptable user agent (see [re-scope findings](p7-subscription-rescope.md)).

## Consequences

- **Antigravity:** D066 blocks P7.5 on consumer-plan terms as well as the D063 control gate.
- **Claude:** D067 records the operator's acceptance of P7.2's plan-login use, limited to operator-started runs, with a dated re-check.
- **OpenAI:** officially allows plan use in listed third-party tools (OpenCode, Pi). D067 prefers that path over the `codex` adapter.
- **Grok:** no official statement either way. Subscription use stays first-party (Grok Build, Grok Bot) under D067. Re-read the sources before resuming P7.4.
- **OpenCode Go:** use in other coding agents is documented, subject to the client conditions above.
- Where the operator wants certainty, ask the provider in writing.
- No adapter's sources permit sharing, copying or intermediating credentials. D047 already forbids all three.

## Validation

Official sources read on 2026-11-08 as listed above. Relative Markdown links and whitespace checked. Documentation only: no Rust, dependency, configuration or probe change, and no CLI run against any provider.
