# P7.9 — Exclusive-state login decision

Date: 2026-11-10. Entry: `aade007` (PR #90 merged). Prior
[installed observer](p7-9-installed-observer.md), D076;
[observer/refusal design](p7-9-observer-refusal-design.md), D075;
[source/state controls](p7-9-source-state-controls.md), D071;
[bounded assessment](p7-9-chatgpt-feasibility.md), D069.

## Plan and result

Follow D076's next step. Decide how D047's login prerequisite applies to the OpenCode
ChatGPT route, given that a login has to live in persistent OpenCode state. Resolve the
three retained-state rows that D075 left blocked: the retained well-known cache, the
connected Console integration and the reused data root. Inspect only public pinned source.
Do not launch OpenCode, log in, read real configuration, state or credentials, seed machine
roots, or change production code, the runtime pin, interfaces or D034. Stop rather than
select a design for any row whose safety cannot be stated as a checkable invariant.

**Result:** select a **dedicated, harness-owned data root** that the operator logs into
with the unmodified official CLI. Every run checks it with a **retained-state preflight**
before it creates any session. All three rows now have a checkable invariant and a planned
paired proof, so this decision unblocks the next experiment. It does not authorise a login.
Four source findings drive the selection:

1. **A login cannot use a fresh root per run.** The ChatGPT plugin stores the OAuth grant in
   the runtime database, persists refreshed tokens there, and keeps a stable
   `chatgpt-agent-host-id` in plugin storage that it sends with every sign-in. D075's
   "fresh per run, never reused" rule is therefore incompatible with any login. Reuse is
   required, and it reopens the three blocked rows.
2. **The default login path does not target a private root.** `opencode auth login`
   attaches to the managed background service unless `--standalone` or `--server` is given.
   That service may already be serving the operator's ordinary data root. `--standalone`
   spawns a private `serve --stdio --port 0` child that inherits the caller's environment and
   ends its lease on stdin EOF.
3. **Some login forms write retained well-known state.** A URL target runs
   `integration.wellknown.add`, which fetches the origin and persists `wellknown:sources`.
   An integration ID target (`openai`) does not.
4. **Connection metadata is observable without secrets.** `integration.list` waits for
   plugin activation and returns each integration's `connections` as `Connection.Info`:
   `id`, `label`, `method` (`key`, `oauth` or `external`) and an optional `status`. The
   schema has no secret field. The label can be personal, for example an account name.

## Source findings

All paths are relative to `packages/` in the official v2.2.5 checkout at
`9bbb8ce18c80f099e0e448775f59d965ead40a21`. Fingerprints are at the end.

- **Root selection.** `util/src/global-roots.ts` derives the data, cache, config and state
  roots from `XDG_*_HOME`, falling back to `os.homedir()`. `cli/src/database-path.ts` puts
  the database under the data root unless `OPENCODE_DB` overrides it. A dedicated root is
  therefore selected by environment alone, with no auth-path flag.
- **Credential storage and refresh.** `core/src/plugin/provider/chatgpt.ts` registers the
  `chatgpt-token-sharing` OAuth method as a PKCE browser flow with a loopback callback on
  `127.0.0.1`. It refreshes against `https://auth.openai.com` and accepts only an `oauth`
  credential whose `methodID` matches. A separate path migrates `chatgpt-browser` grants.
  A run on the logged-in root must be able to write to it, because a refresh rotates the
  stored grant.
- **Legacy import.** Migration `20260805200742_import_legacy_credentials` reads
  `auth.json` from the data root and imports its credentials and well-known origins. A
  harness-created root never contains that file.
- **Console connection.** `core/src/plugin/provider/opencode.ts` loads Console remote
  configuration at boot whenever `integration.connection.active("opencode")` returns a
  connection. When that load fails, the last config is kept. `integration.connection.key`
  in `core/src/integration.ts` stores a key credential without any network call, so a
  synthetic Console connection can be created offline through the official route.
- **Well-known cache.** `core/src/wellknown.ts` keeps sources, manifests and configs in KV
  and falls back to the cached copy when a refresh fails (D075). Upstream ships a synthetic
  origin fixture, `core/script/wellknown-server.ts`. It is cited for shape only and is
  never run.
- **Login client.** `cli/src/commands/handlers/auth/shared.ts` calls `model.default` before
  `integration.list`. A login therefore boots the full location graph in its working
  directory, which activates plugins and reads every configuration source the environment
  reaches.

## Selected design

For the OpenCode ChatGPT route only. Experimental until its own installed proof passes.

| Element | Selection |
|---|---|
| Root | A harness-owned directory created exclusively (`O_EXCL`, mode `0700`) with an ownership marker, under the harness's own state directory. It holds an owned HOME, owned XDG roots and an empty owned project. It is never the ordinary `~/.local/share/opencode`, and nothing is copied, linked or imported into it. `OPENCODE_DB` must be unset. |
| Login | The operator runs the unmodified official CLI against that root: `opencode auth login openai --method chatgpt-token-sharing --standalone`, with HOME and XDG pointed at the owned roots, project discovery off, and the empty owned project as the working directory. The harness may print this command in setup docs and diagnostics. It does not run, wrap or prompt for it, and it never observes the browser exchange (D047). A URL target and the managed service are refused. |
| Ownership | One root serves one operator account and only operator-started runs (D067). An advisory exclusive lock is held for the whole run. The operator must not use the root by hand while a run is active. |
| Preflight | Before any session, under the D076 composed profile with network fully denied, the observer adds `integration.list` to its allowlist and requires all of the invariants below. Any failure is a pre-submission setup error with no fallback (D031/D034). |
| Run | The run boot repeats the same invariants before the first session is created. Data writes are allowed only beneath the owned root. Route, endpoint, method and permission controls are separate gates (P7.11). |
| Repair | The harness never edits, filters or deletes rows. On a failed invariant, it tells the operator to run the official `opencode auth logout`, or to discard the root and log in again. |

**Preflight invariants:**

- **Root shape.** The ownership marker matches, no `auth.json` exists (checked by name
  only, never read), and the database path is the owned default.
- **Integration set.** The integration IDs equal the pinned built-in set exactly. Any extra
  ID means retained well-known or other registered state, and the run is refused.
- **Connections.** `openai` has exactly one connection, with method `oauth` and no
  `needs_auth` status. `opencode` (Console) and every other integration have none. Env
  connections are impossible because the environment is cleared. Labels and IDs are
  hashed in memory and never stored or printed.
- **Resources.** The D076 exact sets still hold on the retained root: plugins, commands,
  skills, MCP, config and agents.

`integration.list` is the only new route. It returns connection metadata, not credentials,
and it is decoded with a strict schema that rejects unknown fields. Credential list, export
and import routes stay refused. Whether the stored grant uses the exact
`chatgpt-token-sharing` method is not visible from this metadata. That proof stays with the
route gate.

## Row dispositions

| Row | Invariant | Planned paired proof (next experiment, no login) |
|---|---|---|
| Reused data root | Two runs against one root see identical invariants. A second run cannot start while the lock is held. | Run twice on one exclusively created root, with writes allowed beneath it, and compare redacted inventories. Pair with a concurrent-lock refusal. |
| Retained well-known cache | No extra integration ID and no well-known config entry. | Seed through the official `integration.wellknown.add` against a harness-written synthetic origin on a second owned loopback port, then require refusal. The control case omits the seeding. |
| Connected Console | `opencode` has zero connections. | Seed through the official `integration.connect.key` with a synthetic, non-secret marker. Record the denied Console fetch, then require refusal. The control case omits the seeding. |

For the experiment only, this decision authorises one extra owned loopback port that serves
the synthetic origin, and a synthetic marker stored through the official key route. Neither
is a real credential, and no request leaves the host. D070's other denials stay in place.

## Limits

- The login itself runs outside harness containment. Machine sources that D073 denies, such
  as `/Library/Application Support/opencode`, are reachable during the operator's login
  boot. The preflight detects changes to integrations, connections and resources. It cannot
  detect arbitrary KV rows or session history that leave no observable effect.
- Session history accumulates in the retained database. The harness never continues or
  exports an earlier session, but the history is retained by OpenCode, not the harness.
- The advisory lock does not stop an operator who ignores it. A race between the preflight
  and the run boot remains possible, and the repeated run-boot check narrows that race.
- Path denials and a fresh login do not establish that post-limit credits are off. Account
  controls are still verified by the operator (D067).
- This is a second login of the same account into a new root, not reuse of an existing
  login. D069's statement that a new root is not a preserved login still holds. D047 is
  refined for this route, as recorded in D077.

## Next boundary

The next focused task is the installed no-auth retained-state experiment in the table
above, run under the D076 composed profile. It stops on any unexpected integration,
connection or resource, any network attempt beyond the owned ports, or any write outside
the owned root. A bounded operator-authorised login into the dedicated root, followed by a
no-inference preflight, is a separate later task with its own explicit authorisation.
Exact method, endpoint and helper proof, deny and trusted grants, the account credits-off
check and D034 remain separate gates. Full P7.9/P7.10 remain unchecked and P7.11/P7.12
blocked. Independent P8.2 Pi remains available, and no platform switch is needed.

## Reproduction and fingerprints

Use the D071 clone procedure to obtain a public v2.2.5 checkout. Nothing is installed or run.

| File (`packages/`) | SHA-256 |
|---|---|
| `util/src/global-roots.ts` | `6cdc234ac155e308dadeb62682c687468ba656fd463482d00fce025c9dc819b6` |
| `cli/src/database-path.ts` | `921368eee69db647d2973d7dc529e86a8942027ee0032d3acb112d6a55e6b9d7` |
| `cli/src/services/server-connection.ts` | `161524ef2525a04bedea305dbfc9df61bd951c69b55a13bc0dca6445f16880b3` |
| `cli/src/services/standalone.ts` | `dc8197da471d3d213acf51ef809bb1c05a7cf697bce1f0795e49fdd4c0165cf9` |
| `cli/src/commands/handlers/auth/login.ts` | `d38a229c7db598d499fa51602f3086a75c64b7f5de64f6e1de51ba5612c47f30` |
| `cli/src/commands/handlers/auth/shared.ts` | `77179fe4706f3d62dc6aa00871ee10ccf93f1e6c2b3257d33263d82cbb7035e6` |
| `schema/src/connection.ts` | `b8bec346b315e6ef36174945c6b62ac467465c2777d0666e103c90b9e55adbf8` |
| `schema/src/integration.ts` | `2cf903a147260a405fa87504a07e05e3a5536ae62d351ddbacb3142af3274c82` |
| `protocol/src/groups/integration.ts` | `3f3010e8b66f378b9a862b789bfc079369f5ce7c9a9b424ab2cfbf8623aceeb1` |
| `server/src/handlers/integration.ts` | `f2f69342bfaa56706466b547f237433c8135ecc87c2639942544d44a7fccbe78` |
| `core/src/integration.ts` | `ec5f1299df972928baf457b277ecb2146acd1b429870b9e61f96eb96a3f82ebe` |
| `core/src/plugin/provider/chatgpt.ts` | `cbb119fa3f231f5b79b588916ad23afc1f6fa71529332bcae8f7fadaa98e8bd2` |
| `core/src/plugin/provider/opencode.ts` | `1a757ab84e8dc2d96de1ebe75b64cbe4b8b1e82bcea07bf9ead681977d63f4ed` |
| `core/src/database/migration/20260805200742_import_legacy_credentials.ts` | `6942179c17f7a756a85d9b708fbe482eca60f5b855d75a6dfb886989647af97c` |
| `core/src/wellknown.ts` | `1983793d5ce0fbc2abec598d8f95b70b0ba118430b2ff9cce2205c4d0938c52b` |
| `core/script/wellknown-server.ts` | `6e1996cba926453363e35e0726680c6c100680fd68fb3c9fddc2b9d1eba25c30` |

The `database-path.ts`, `chatgpt.ts` and `wellknown.ts` fingerprints match earlier P7.9
reports.
