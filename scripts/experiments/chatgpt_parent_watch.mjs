// D097 inert primitive only. No OpenCode imports, services, child processes or network.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import { pathToFileURL } from 'node:url';

// Mirrors nativeLayer's filename filter: eventType is deliberately ignored.
export function matches(filename, candidate) {
  return filename == null || filename === candidate;
}

export function run(parent, denied, nonce) {
  let watcher, input, timer, phase = 0, armed = false, observed = false, stopped = false, pendingArm = false;
  const candidate = 'opencode.jsonc';
  const target = path.join(parent, candidate);
  const names = new Set(['.agents', '.opencode', 'opencode.json', candidate]);
  const emit = (label) => process.stdout.write(`${nonce} ${label}\n`);
  const stop = (label) => {
    if (stopped) return;
    stopped = true;
    clearTimeout(timer);
    // A failed close must still terminate the protocol, and never as a success label.
    try { watcher?.close(); } catch { label = 'FAIL'; }
    try { input?.close(); } catch { label = 'FAIL'; }
    process.stdin.pause();
    emit(label);
  };
  const code = (error) => {
    const value = error?.code;
    return ['EPERM', 'EACCES', 'ENOENT'].includes(value) ? value : 'UNKNOWN';
  };
  const state = () => {
    const stat = fs.lstatSync(parent);
    if (!stat.isDirectory() || stat.isSymbolicLink()) throw Error();
    if (phase === 3) return !fs.existsSync(target);
    const item = fs.lstatSync(target);
    return item.isFile() && !item.isSymbolicLink() && item.nlink === 1 &&
      fs.readFileSync(target, 'utf8') === (phase === 1 ? 'AH_CREATE' : 'AH_UPDATE');
  };
  process.on('uncaughtException', () => stop('FAIL'));
  process.on('unhandledRejection', () => stop('FAIL'));
  try {
    if (!/^[a-f0-9]{32}$/.test(nonce) || !['allow', 'deny'].includes(denied)) return stop('FAIL');
    let listing;
    try { listing = fs.readdirSync(parent).sort(); }
    catch (error) {
      if (denied !== 'deny' || !['EPERM', 'EACCES'].includes(code(error))) return stop('PROBE_FAIL');
      listing = null;
    }
    if ((denied === 'deny') !== (listing === null)) return stop('PROBE_FAIL');
    if (listing && JSON.stringify(listing) !== JSON.stringify(['opencode.json', 'project'])) return stop('PROBE_FAIL');
    const parentStat = fs.lstatSync(parent);
    if (!parentStat.isDirectory() || parentStat.isSymbolicLink()) return stop('PROBE_FAIL');
    // Discovery probes all five names even when Claude resource loading is off.
    for (const name of ['.claude', '.agents', '.opencode', 'opencode.json', candidate]) {
      const probe = path.join(parent, name);
      if (name === 'opencode.json') {
        const st = fs.lstatSync(probe);
        if (!st.isFile() || st.isSymbolicLink() || st.nlink !== 1 ||
            fs.realpathSync(probe) !== probe || fs.readFileSync(probe, 'utf8') !== 'AH_DIRECT')
          return stop('PROBE_FAIL');
      } else {
        for (const operation of [fs.lstatSync, fs.realpathSync]) {
          try { operation(probe); return stop('PROBE_FAIL'); }
          catch (error) { if (code(error) !== 'ENOENT') return stop('PROBE_FAIL'); }
        }
      }
    }
    emit('PROBES_OK');
    try {
      watcher = fs.watch(parent, { recursive: false }, (_event, file) => {
        if (file && !names.has(file)) return;
        if (!armed || observed) return; // duplicates between phases do not count
        if (!matches(file, candidate)) return;
        try {
          if (!state()) return stop('PREMATURE');
          observed = true;
          emit(`EVENT_${phase}`);
        } catch { stop('STATE_FAIL'); }
      });
    } catch (error) { return stop(`SYNC_${code(error)}`); }
    watcher.on('error', (error) => stop(`ASYNC_${code(error)}`));
    input = readline.createInterface({ input: process.stdin });
    input.on('line', (line) => {
      if (stopped) return;
      if (line === `${nonce} CLOSE` && phase === 3 && observed) return stop('CLOSED');
      if (pendingArm || line !== `${nonce} ARM_${phase + 1}` || phase === 3 || (phase > 0 && !observed)) return stop('PROTOCOL_FAIL');
      armed = false;
      pendingArm = true;
      // Drain duplicate/coalesced callbacks before arming the next mutation.
      // This bounded quiet interval does not prove kernel-event causality.
      setTimeout(() => {
        if (stopped) return;
        phase++;
        pendingArm = false;
        observed = false;
        armed = true;
        emit(`ARMED_${phase}`);
      }, 150);
    });
    input.on('close', () => { if (!stopped) stop('PROTOCOL_FAIL'); });
    timer = setTimeout(() => stop('TIMEOUT'), 8000);
    emit('READY');
  } catch { stop('FAIL'); }
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  run(...process.argv.slice(2));
}
