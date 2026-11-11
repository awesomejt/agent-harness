# P7.9 — Installed no-auth retained-state experiment

Date: 2026-11-10. Entry: `fa4b6bb` (PR #91 merged). Prior
[exclusive-state decision](p7-9-exclusive-state-decision.md), D077;
[installed observer](p7-9-installed-observer.md), D076;
[observer/refusal design](p7-9-observer-refusal-design.md), D075;
[contained diagnostics](p7-9-contained-diagnostics.md), D070.

## Plan recorded before launch

Run the experiment that D077 selected, against the installed, hash-pinned OpenCode 2.2.5,
under the D076 composed profile. The experiment has five parts:

- Fix the expected integration set from fresh roots, and cross-check it against the pinned
  checkout.
- Run the reused-root pair with a concurrent-lock refusal.
- Run the retained well-known pair, seeded through the official `integration.wellknown.add`
  route from a harness-written origin on one extra owned loopback port.
- Run the connected Console pair, seeded with a synthetic non-secret key through the official
  `integration.connect.key` route.
- Check the name-only root-shape refusals before any launch.

Add `integration.list` to the observer and nothing else. A separate seeder may use only the
two seeding routes, each with one synthetic payload. The experiment stops on any unexpected
integration, connection, resource or warning, any spawn other than `git rev-parse`, or any
write outside the owned root. It does not log in, start sessions, call models, read real
configuration, state or credentials, or change production code, the runtime pin, interfaces
or D034.

**Result:** every row has installed paired evidence. The D077 preflight passes on fresh and
reused unauthenticated roots, and it refuses each seeded retained state for exactly the
expected reason. With the login invariant switched on, it refuses every no-auth root for
`openai-connection` alone, so nothing apart from the login blocks it. Three consecutive full
runs of the final helper passed with identical redacted summaries. **Full P7.9 and P7.10
remain unchecked, and P7.11 and P7.12 remain blocked.** The next step needs an operator
login, which this task does not authorise.

## Reproduction

On the accepted Apple Silicon macOS host, obtain the public v2.2.5 checkout with the D071
procedure. From the repository root:

```sh
python3 -B scripts/experiments/chatgpt_retained_state.py --source <checkout>
python3 -B scripts/tests/chatgpt_retained_cases.py
```

The helper reuses the D076 checks: a clean worktree at
`9bbb8ce18c80f099e0e448775f59d965ead40a21`, the D076 fingerprints plus those below, and
installed executable SHA-256
`4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`. A missing executable,
a byte-drifted copy and a wrong checkout each exit 1 with raw diagnostics withheld. Each case
uses its own temporary parent, discarded on exit. The helper prints only PASS lines and a
redacted JSON summary.

## Boundary

Each boot uses the D076 composed profile: D070 transport, D073 machine-root denials and the
ancestor discovery-name denials. The owned root holds HOME, the XDG roots, the project and the
copied executable. Writes are allowed beneath it, as D077 allows for a retained root. Two
controls run before any OpenCode process:

| Control | Observation |
|---|---|
| D070 matrix under the composed profile | Owned echo works. Other TCP ports, binds, external TCP, UDP, IPv6, Unix sockets, operator-home reads and outside writes are denied. |
| Extra origin port, paired | Both controls use the same composition as each boot, including the ancestor denials. The origin port has live listeners on `127.0.0.1` and `::1`. Without the allowance, connecting to either is denied. With it, only outbound connections to that port work, and they work on both loopback addresses: SBPL `localhost` covers IPv4 and IPv6 loopback, and SBPL accepts only `localhost` or `*` as the host. Binding the port and connecting to a second live loopback listener stay denied. Neither origin listener received a request. |

The allowance is added only to the boot that serves the synthetic origin (boot A of the two
well-known cases). Every later boot runs without it.

## Owned root and preflight as implemented

- **Root.** `mkdir` with mode `0700` fails if the directory exists. The ownership marker is
  created with `O_CREAT | O_EXCL | O_NOFOLLOW` and mode `0600`, and holds a random token.
  Nothing is copied, linked or imported into the root apart from the hash-checked executable
  and the D076 synthetic fixtures. `OPENCODE_DB` is never set.
- **Root shape.** Before every boot, three name-only checks run, then `debug paths`. The
  checks are: the marker is a regular file holding the token; `DATA/opencode/auth.json` does
  not exist (by `lexists`, so a dangling symlink also counts); and `XDG_DATA_HOME` is the
  owned data root with no `OPENCODE_DB`. `debug paths` must report the owned default database.
- **Lock.** The run holds an exclusive non-blocking `flock` on `.ah-lock` in the root. A
  separate process probes the same lock.
- **Integration read.** `integration.list` is decoded with a strict schema. Unknown fields,
  method types or method keys fail the run, and so does a connection status other than
  `needs_auth`. The record keeps each integration ID, its method signatures as type and
  method ID, and each connection's type, method and status. Connection IDs and labels are
  reduced to a SHA-256 that is compared in memory and never recorded or printed.
- **Invariants.** `integration-set`, `openai-connection`, `console-connection`,
  `other-connection`, `resources` (the D076 case 1 exact sets and 92 active built-ins) and
  `config-documents` (only the owned global document). The no-auth variant requires `openai`
  to have no connection. The login variant requires exactly one `credential` connection with
  method `oauth` and no status.
- **Seeder.** The seeder allows two exact POST routes and two payloads. The well-known payload
  is `{"url": <origin>}`, and the origin must match `http://127.0.0.1:<port>`. The Console
  payload is `{"key": "AH_SYNTHETIC_NON_SECRET_CONSOLE_MARKER", "label": "ah-synthetic"}`.
  Each POST must return 204 with an empty body.
- **Synthetic origin.** The origin serves only
  `{"auth": {"command": [<absent path in the write-denied bin>], "env": "AH_SYNTHETIC_TOKEN"}}`
  at `/.well-known/opencode`. It has no `config` or `remote_config`, and it counts every
  request.

The D076 log gates apply to each boot's log lines. The log is appended across boots, so only
the lines a boot adds are checked. The machine-parent watch must start, no watcher may fail,
and spawns are limited to `git rev-parse`. Neither `node_modules` nor an entry in the
write-denied bin may appear. The WARN/ERROR set must equal the boot's expected set exactly.

## Expected integration set

Four fresh roots listed the same set before any seeding: **236 integrations**, SHA-256 of the
sorted newline-joined IDs
`2cd1b632219bbd635a2f7a5911d6c0e36d7205d75cc4c85d751cb90081de73af`. Fresh roots have no
connection on any integration, no metadata and no `command` method.

The cross-check is exact. The set equals the union of two sources:

- **The pinned models.dev snapshot.** All 230 providers in `core/src/models-dev/snapshot.txt`
  list environment names, and `plugin/models-dev.ts` registers an integration for each one.
- **The 19 IDs that the 91 fingerprinted built-in plugin files name.** The helper reads them
  from string literals, `Provider.ID` constants and `<Module>.ID` aliases, in each plugin file
  and its one-hop relative imports. `claude-agent` is registered in such an import. Six of
  these IDs are plugin-only: `claude-agent`, `exa`, `firecrawl`, `parallel`, `tavily` and
  `tinyfish`.

Release builds may bundle a live catalog in place of the source snapshot (`models-dev.ts`).
For this pin, the installed binary's catalog matched the snapshot. A pin change therefore
re-derives the set. The source scan also finds that the well-known plugin is the only
built-in that registers a `command` method, so an extra `command` integration can only come
from a retained well-known source.

## Paired installed cases

| Case | Boot A | Boot B (same root) | Preflight (no-auth / login) |
|---|---|---|---|
| Reused root | Fresh, under the held lock | Identical integrations, resources, config documents and connection digests | `[]` / `openai-connection`, both boots |
| Well-known control | Origin up and allowed, not seeded; 0 origin requests | Origin down, no allowance; same as boot A | `[]` both boots; no warnings |
| Well-known seeded | Seeded; exactly 1 manifest request; one extra integration, the origin, with one `command`/`login` method | Origin down (listener closed) and no allowance; the origin integration is retained. From OpenCode's side, a refused and a denied connection look the same, and the paired boundary control proves the denial separately. | `integration-set`, both boots |
| Console seeded | Seeded; `opencode` has one `credential`/`key` connection, the only connection anywhere | Same connection digest retained | `console-connection`, both boots; with login: `console-connection`, `openai-connection` |

The reused-root case is also the unseeded Console control. Its lock probe from a second
process was refused before boot A and between the boots. After release, the probe acquired
the lock. An in-process second acquire also returned no lock.

**Expected warnings.** The source explains every warning, and each is gated as an exact set:

- Well-known seeded boot A logs `failed to load wellknown config`. Without a credential,
  `core/src/config.ts` fails the config resolve and keeps the cached config. Here the cached
  config is empty.
- Well-known seeded boot B adds `failed to load wellknown manifest`. The origin is unreachable,
  so `core/src/wellknown.ts` falls back to the stored manifest. That fallback is the retained
  state under test.
- Both Console boots log `failed to load OpenCode provider config`. The Console plugin
  fetches remote configuration as soon as a connection exists, at connect time and at every
  boot. The profile denies the fetch, so the plugin keeps its last config, which is empty here.

Unseeded boots log no warnings. In both seeded cases the resources and config documents stay
exactly as in the fresh state, and the well-known auth command never runs: the bin stays
empty and the only spawn is `git rev-parse`.

**Static refusals before launch.** Three fresh roots each fail one root-shape check: a
zero-byte `auth.json`, a mismatched marker and an `OPENCODE_DB` override. Each is refused
for exactly that reason, before any OpenCode process starts.

## Findings

1. **A retained Console connection contacts the Console on every boot.** The fetch starts at
   connect time and at each boot, and repeats every minute while connected. A network failure
   is not a well-formed Console error, so the connection keeps no status and looks healthy.
   The preflight must therefore run with the network denied, as D077 requires, and must refuse
   any `opencode` connection, whatever its method or status. The installed case confirms both.
2. **A retained well-known source survives an unreachable origin.** The integration stays
   listed from the stored manifest, and the only signal is a warning. The exact integration-set
   invariant catches it. Without a credential, no well-known config document is applied.
3. **Both D077 discovery flags gate the same roots.** `cli/src/server-process.ts` treats
   `OPENCODE_DISABLE_CLAUDE_CODE` and `OPENCODE_DISABLE_CLAUDE_CODE_SKILLS` alike, so `.claude`
   is read only for skills. D077's login command uses the first flag, and the D076 and D077
   experiments use the second. Their effect on discovery is the same.

## Row dispositions

| Row | Disposition after this increment |
|---|---|
| Reused data root | **Pass (no-auth).** Two boots are identical, and a concurrent lock is refused while held. |
| Retained well-known cache | **Pass: refused.** The seeded origin integration is retained across an unreachable origin and refused by `integration-set`. The unseeded control passes. |
| Connected Console | **Pass: refused.** The synthetic key connection is retained, its fetch is denied and logged, and it is refused by `console-connection`. The reused-root control passes. |
| Root shape | **Pass.** The legacy auth file, marker and database override are refused by name before launch. |
| Login invariant | **Not exercised installed.** No login exists. The full preflight refuses no-auth roots for `openai-connection` only. Offline cases cover the healthy single OAuth connection and its refusals. |

## Limits

- **No login.** The `openai` positive case and an OAuth grant's retained behaviour are
  untested on the installed runtime. The operator's login boot runs outside containment (D077).
- **Synthetic seeds only.** The Console seed is a key credential stored through the official
  route. The OAuth device flow was not run. The invariant refuses any Console connection, so
  the method does not change the outcome. The well-known manifest is auth-only, so the
  remote-config path was not exercised.
- **Unobservable state.** Arbitrary KV rows and session history are still outside the
  invariants (D077).
- **Lock and location.** The lock is advisory and was tested only between harness processes.
  The root is a temporary directory, not the harness state directory. The production location
  and lock contract belong to P7.11.
- **Pin-specific set.** The 236-ID set and its digest hold for this pin and installed binary.
- **Platform.** The evidence is for this experimental macOS host only. The helper is opt-in
  tooling, not production code.

## Next boundary

The no-auth evidence that D077 required is now complete. The next focused task is the bounded
login. The operator runs D077's official `opencode auth login openai --method
chatgpt-token-sharing --standalone` command into a fresh dedicated root. A no-inference
preflight then checks that root with this helper's invariants, with login mode on. That task
needs explicit operator authorisation under D067, and the operator must perform the login
personally. The harness never runs it, and an agent cannot do it on the operator's behalf.

Method, endpoint and helper proof, deny and trusted grants, the account credits-off check and
D034 remain separate gates. Full P7.9/P7.10 remain unchecked and P7.11/P7.12 blocked.
Independent P8.2 Pi remains available, and no platform switch is needed.

## Fingerprints

The helper verifies these pinned files beyond the D076 table, and re-verifies the D077 files
it consumes. Paths are under `packages/`.

| Pinned path | SHA-256 |
|---|---|
| `core/src/wellknown/plugin.ts` | `dd71fc144c5c99303f61cfd7d61ffd516c418f5bac3ebcac6433d4f1ab014bed` |
| `core/src/plugin/models-dev.ts` | `5b456026359976407f2be11456d1974ee795ce3cc2a6ec41b0d0d0ac6a96ef74` |
| `core/src/models-dev/snapshot.txt` | `5d5740c70071aa628d1efe317f6885faf1f20b32a9fcb502553f57cce15cf9f1` |
| `core/src/console-access.ts` | `7ae41c74078b9c5a3887bec4908e9ee0ab00e632d3ce1f5eaf37d9da23c0eec5` |
| `core/src/config.ts` | `df2d83dff70a6cb3ef3e3a1d735bd397facc96ccf15794c6eb1a3646cef17390` |
| `cli/src/server-process.ts` | `37e89b2eed32bc9324f4cdf0a639387dfe6fc0ef8e6f37fc33c43987869b4bc2` |
| `schema/src/provider.ts` | `e06382adea1a5823aea72024461064319647117c8b08abad72490efd6191a404` |
| `core/src/plugin/provider/claude-agent/integration.ts` | `e4b31a6ef179823f1520f88914d260734d28b70d66cc6ef691657815eda1e1c3` |
| `core/src/plugin/provider/claude-agent/provider.ts` | `b7cb78d7962c1f871cb54a5b1c299a3dd34b62dc6c6ce668fd85a8c3954433e3` |

Re-verified from D077: `wellknown.ts`, `plugin/provider/opencode.ts`, `integration.ts`,
`server/src/handlers/integration.ts`, `protocol/src/groups/integration.ts`,
`schema/src/integration.ts`, `schema/src/connection.ts`, `global-roots.ts` and
`database-path.ts`. The built-in plugin files' combined digest matches D076
(`68e17ecb…`).

## Validation

- **Installed experiment.** The first full run stopped on the then-unexpected
  `failed to load wellknown config` warning. After the source check above, it was added to the
  expected set for seeded boots. Two runs then passed. The exact integration cross-check and
  the pre-launch boundary controls were added next, and three consecutive runs of the final helper passed with identical redacted
  summaries. After review, the boundary controls were aligned with the boot composition and
  given an IPv6 probe, and two further full runs passed with identical summaries. The missing-executable, byte-drift and wrong-checkout refusals pass.
- **D076 regression.** The observer's route allowlist became a class attribute so this helper
  can add one route. The D076 installed probe and `chatgpt_observer_cases.py` pass unchanged.
  The D076 observer still refuses `/api/integration`.
- **Offline suite.** `chatgpt_retained_cases.py` joins `offline.py`, and all 33 entries pass.
  It covers:
  - route refusal before connecting, including credential, connect and well-known routes;
  - seeder route, payload, origin-shape and response refusals;
  - strict integration redaction, with no label or connection-ID leak;
  - every preflight invariant in both variants, including `needs_auth`, key, duplicate and
    env connections on `openai`;
  - exclusive root creation and modes, name-only and dangling `auth.json`, a symlinked marker
    and database overrides;
  - the in-process and cross-process lock;
  - the literal, constant and alias cross-check with its refusals;
  - the synthetic origin;
  - settle and timeout.
- **Other checks.** Python syntax, documentation links and whitespace pass. Rust sources and
  dependencies are unchanged.

## Review

Grok reviewed the first revision in [PR #92](https://github.com/awesomejt/agent-harness/pull/92)
and found 0 blockers, 0 concerns and 3 nits. All three are addressed:

- **Nit:** the boundary controls used the D076 profile without the ancestor denials. They now
  use the boot's exact composition, and the origin probe adds a live `::1` listener. The
  allowance admits the origin port on IPv6 loopback as well, and the helper pins and records
  that result.
- **Nit:** the well-known boot B row now says the origin is down with no allowance, rather
  than claiming a denial that this case cannot observe.
- **Nit:** the status line links the PR.

Two full installed runs, the offline cases, links and whitespace pass again. No critical or
high finding, so no re-review was requested.
