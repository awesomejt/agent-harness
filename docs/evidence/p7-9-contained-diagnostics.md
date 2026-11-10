# P7.9 — Contained diagnostic continuation

Date: 2026-11-09. Entry: `1c9d5f6` (PR #83).
[Prior assessment](p7-9-chatgpt-feasibility.md), D069.

## Plan recorded before the continuation experiment

Keep the pinned executable, private HOME/XDG/TMPDIR, cleared environment,
operator-home data-read denial and outside-write denial. First run synthetic
Python child/pipe/socketpair controls under the unchanged network-deny profile.
Then use Bun's documented `BUN_BE_BUN=1` compiled-executable mode only for an
explicit synthetic JavaScript child-spawn fixture, bypassing the OpenCode entry
point entirely. Compare piped/inherited/ignored stdio and detached/non-detached
children. The fixture may spawn only system echo/true or itself in synthetic
mode; it may not invoke OpenCode authentication, sessions or model calls.

Change containment only after reproducing the failing primitive. Any proposed
local transport exception must be tested with positive/negative synthetic
controls, including external/loopback TCP, UDP, named Unix sockets outside the
owned root, filesystem boundaries and child inheritance. No live remote
connection, credentials or normal OpenCode service is used. Do not infer that
socketpair success establishes arbitrary local service isolation.

Once that gate is proven, allow only standalone version/config/agents/paths
diagnostics with inert source canaries and private empty runtime state. No ACP,
login, credential inspection, auth/session RPC or inference in this increment.
Production pin/code/config/dependencies remain unchanged. Any remaining
login/permission gate stays explicit.

### Primitive result and narrowed transport proposal

The original profile permits Python pipe/socketpair/child controls. Embedded Bun
1.4.4 synthetic spawning succeeds for piped/inherited stdio and fails with EPERM
for ignored stdio, for both detached states. Direct `/dev/null` read opens work;
write/read-write opens fail. Adding only `(allow file-write-data (literal
"/dev/null"))` makes every synthetic Bun spawn case pass. The pinned OpenCode
spawner ignores server stderr. This explains the observed spawn blocker without
changing network permissions.

Pinned `cli/src/services/standalone.ts` always launches `serve --stdio --port 0`;
`server/src/process.ts` binds TCP on the requested hostname/port. Rather than
allow all loopback ports for an unknown ephemeral listener, test an explicitly
owned `serve --stdio --hostname 127.0.0.1 --port <selected>` child and diagnostic
clients with explicit `--server` plus a private generated server password.
Allow only TCP bind/inbound at that one loopback port and TCP outbound to it,
plus the literal `/dev/null` data-write exception. The port is selected from a
parent-owned temporary socket; release/start can race, so require our child's
readiness and generated password before any diagnostic, refuse bind conflict,
and never discover/attach to a shared service. Provider authentication remains
forbidden. This transport decision is experimental, not a production change.

## Implemented experiment and observations

Reproduce on the accepted Apple Silicon macOS host from the repository root:

```sh
python3 -B scripts/experiments/chatgpt_contained.py
python3 -B scripts/tests/chatgpt_contained_cases.py
```

The installed executable is still OpenCode 2.2.5, SHA-256
`4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5`.
The probe refuses missing binaries, byte drift and unsupported platforms; it
copies only the executable, not operator configuration or credentials. Embedded
Bun reports 1.4.4 in synthetic mode. Bun documents this mode in its official
[single-file executable guide](https://bun.sh/docs/compiler/executables).
`BUN_BE_BUN` is present only in synthetic child controls, never in an OpenCode
server or diagnostic environment. System Command Line Tools Python is used
directly, avoiding the `/usr/bin/python3` launcher's outside-root cache attempt.

The initial Python pipe/socketpair/spawn controls were ad-hoc observations under
the original profile; the committed reproducer uses the stronger paired Bun
matrix and direct null-device controls below. No Bun executable installation,
recompilation or modification is needed.

| Control | Installed observation |
|---|---|
| Direct `/dev/null` open | Original profile permits read only; write/read-write get EPERM. Literal data-write exception permits all three. |
| Embedded Bun child spawn | Six combinations (ignore/inherit/pipe × detached false/true): original fails only ignored stdio; corrected profile passes all six. |
| Inherited sandbox | A sandboxed Python parent launches a Python child running the entire TCP/filesystem positive/negative matrix. |
| Exact selected TCP port | A synthetic echo listener/client works on `127.0.0.1:<port>`. |
| Negative networking | Other loopback port, ephemeral bind, wildcard bind on a different port, external TCP to documentation-only `192.0.2.1:443`, UDP on the allowed numeric port, IPv6 on another port and named Unix socket bind all get permission denials. |
| Filesystem boundary | Operator-home synthetic sentinel read and outside-root write are denied; `/dev/null` data writes are permitted. |
| Occupied server port | Our server fails before readiness; it makes no connection to the conflicting synthetic listener. No diagnostic is submitted. |
| Private server access | Clients with no password or an incorrect password exit 1 with the expected password rejection; the generated-password client succeeds. |
| Isolated sources | Exact result: private `CONFIG/opencode` directory plus the supplied document; inert project and parent config/agents are absent. |
| Discovery positive control | Restarting our private server with project discovery enabled loads both project and parent documents and their sentinel agents. |
| Agent/helper controls | Every reported model is unset or the exact selected `openai/gpt-6.1-sol`; request settings/headers/body are empty; the selected deny rules occur with only deny tails. |
| Data paths | `debug paths` with no server flags shows separate synthetic XDG data/database roots while private configuration stays fixed. This proves path selection only. |

The policy is the original network/home-data/outside-write denial plus only:

```scheme
(allow file-write-data (literal "/dev/null"))
(allow network-bind network-inbound (local tcp "localhost:<port>"))
(allow network-outbound (remote tcp "localhost:<port>"))
```

Here `<port>` is a validated integer substituted by the probe. macOS's SBPL
`tcp` address grammar accepts `localhost`, not a numeric `127.0.0.1` host. The
actual server's explicit hostname and all successful connections use
`127.0.0.1`; the rule names the localhost namespace, which can include IPv6.
Do not claim that it prohibits every wildcard bind on the allowed numeric port.
It prohibits the tested other-port bind and remote/UDP/Unix paths. This is a
bounded diagnostic transport, not a general untrusted-code network sandbox.
No remote provider request is allowed. The external-address negative test
requires an immediate permission denial, not a timeout or refusal from a peer.

The negative transport matrix validates the rule construction on a disposable
control port. The private server then uses a fresh selected port with the same
rule construction, avoiding the echo connection's TIME_WAIT. The selection/start
race is not eliminated by port reservation: our child's exact readiness and
successful private-password connection are required, and occupied-port refusal
is separately observed. No shared-service discovery occurs. The generated
server password is an experimental local transport secret, not a provider
credential or provider authentication operation; it is neither logged nor saved.

Each client/control capture retains the existing ten-second/two-MiB combined
output limit and process-group cleanup. Server stdout/stderr are drained for its
entire lifetime with a combined two-MiB cap; readiness is bounded to ten seconds.
Clients run sequentially with fixed command allowlists. Server shutdown closes
the owned stdin lease, waits at most three seconds, then kills/reaps its group
and joins pipe readers. There is no single whole-probe deadline; the finite
control/diagnostic sequence has per-command and cleanup bounds.

The offline suite needs macOS sandbox-exec and Command Line Tools Python, but no
OpenCode, Bun install, provider account or network service. It verifies command
rejection before spawn; agent-model/request/permission widening refusals; malformed
and missing readiness; early exit; output overflow; normal lease shutdown; and
cleanup of a descendant left in the owned group. All six lifecycle scenarios
pass. It is included in `offline.py`.

## Source basis and correction to the previous report

Pinned upstream source remains commit
`9bbb8ce18c80f099e0e448775f59d965ead40a21`; source is distinct from verified
installed build provenance. These files explain the transport observations:

| File within the pin | SHA-256 |
|---|---|
| `packages/util/src/cross-spawn-spawner.ts` | `6c1a6b3121f518ea0ad78b71e4d718b9b1698ca3de92c29f5c40bba50877199b` |
| `packages/cli/src/services/standalone.ts` | `dc8197da471d3d213acf51ef809bb1c05a7cf697bce1f0795e49fdd4c0165cf9` |
| `packages/server/src/process.ts` | `33048eff5aeaa894bf511f4167389039b7d483e0dfb9d9429ce617ff1c160492` |

The first two files show detached spawns, ignored server stderr and ephemeral
standalone ports. The third binds TCP. The copied-runtime synthetic matrix and
direct null-device controls establish the local EPERM cause without asserting a
universal Bun defect. The old blocked reproducer is retained as historical
regression evidence against its unchanged original profile.

A prior exploratory `debug paths --standalone` failure did **not** establish a
spawn failure: installed `debug paths` rejects `--standalone` and `--server`.
Calling it without either flag works under containment. Config/agents commands
use our explicit server. This corrects the earlier report's implication that all
failed diagnostic invocations reached the same runtime stage.

## Disposition and remaining gate

This focused contained-diagnostic increment closes on required review/merge.
**P7.9 remains unchecked; P7.11 remains blocked.** D070 accepts this experiment's
transport only. No production Rust/config/CLI/dependency, provider login,
auth-store access/copy, session, model turn or billed request occurred.

The private-source assertion covers the exact sources on this host, plus the
seeded project/parent configuration canaries. It does not prove global,
compatibility (`.claude`/`.agents`), system/MDM, skill/plugin/MCP/hook or persistent
integration-source exclusion when those sources exist. Reported deny rules are
not complete effective tool enforcement. An empty synthetic data root and data
path selection are not login preservation or connection/method proof.

Next is a separate P7.9 no-inference resource/source and persistent-state control
assessment using this transport, with positive/negative synthetic canaries.
Resolve supported global/managed exclusions and runtime-owned persistent state
before any later D047 login/connection decision or live gate. Account eligibility,
post-limit credits-off verification, effective auth method/provider endpoint,
complete tool denial and exact trusted grants remain required. Do not read/import
the normal database or copy/symlink auth. P7.10 remains independently ready and
can reuse this tested transport. P7.13/P7.6/P7.7 remain later gates; Pi remains
independent. No platform switch is needed. A fresh context is efficient at this
source/state-control boundary because reproduction and remaining gates are now
recorded here.

## Validation and independent review

Installed reproducer, missing-executable/byte-drift refusals, offline lifecycle/
narrowing suite, Python syntax, Markdown links/anchors and Git whitespace checks
pass. No production tests are required for unchanged Rust sources/dependencies.
An independent read-only security review prompted explicit absent/wrong-password
refusals, parent canaries, reproducible primitive/inheritance controls and
process-group descendant coverage. Re-review found no critical/high or remaining
correctness defect. Source-scope and state/endpoint/tool limitations above remain
explicit. Grok PR review and closeout are recorded in PROJECT.md.
