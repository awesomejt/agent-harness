import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';

/** Path-shaped fields per tool; content and patterns are intentionally excluded. */
const PATH_FIELDS = {
  read: ['path', 'filePath'],
  write: ['path', 'filePath'],
  edit: ['path', 'filePath'],
  find: ['path', 'cwd', 'directory'],
  grep: ['path', 'cwd'],
  ls: ['path', 'directory'],
};

function realRoot(root) {
  if (!root) return '';
  try {
    return fs.realpathSync.native(root);
  } catch {
    return path.resolve(root);
  }
}

/** Fail closed on paths Pi would reinterpret (~, @, home env interpolation). */
function pathUsesPiEscapeHatch(value) {
  if (typeof value !== 'string' || !value) return false;
  const v = value.trim().normalize('NFC');
  return (
    v.startsWith('@') ||
    v.startsWith('~') ||
    v.includes('$HOME') ||
    v.includes('${HOME')
  );
}

function relativeInside(rootReal, target) {
  if (!rootReal || typeof target !== 'string' || !target) return true;
  if (pathUsesPiEscapeHatch(target)) return false;
  const abs = path.isAbsolute(target)
    ? path.normalize(target)
    : path.resolve(rootReal, target);
  let resolved = abs;
  try {
    if (fs.existsSync(abs)) {
      resolved = fs.realpathSync.native(abs);
    } else {
      let probe = abs;
      while (!fs.existsSync(probe)) {
        const parent = path.dirname(probe);
        if (parent === probe) break;
        probe = parent;
      }
      if (fs.existsSync(probe)) {
        const realParent = fs.realpathSync.native(probe);
        resolved = path.join(realParent, path.relative(probe, abs));
      }
    }
  } catch {
    return false;
  }
  const rel = path.relative(rootReal, resolved);
  return (
    rel === '' ||
    (rel !== '..' && !rel.startsWith(`..${path.sep}`) && !path.isAbsolute(rel))
  );
}

function absolutePathTokens(text) {
  const paths = [];
  for (const m of text.matchAll(/(?:^|[\s"'=<>:])(\/[^\s;|&]+)/g)) paths.push(m[1]);
  for (const m of text.matchAll(/(?:^|[\s"'=])(~\/[^\s;|&]+)/g)) {
    paths.push(path.join(os.homedir(), m[1].slice(2)));
  }
  return paths;
}

function bashEscapes(rootReal, command) {
  if (typeof command !== 'string' || !command) return false;
  if (pathUsesPiEscapeHatch(command) || /\$\{HOME/.test(command)) return true;
  if (/(^|[\s"'=:/])\.\.(?=$|[\s"'/;|&])/.test(command)) return true;
  if (/\/\.\.(\/|$)/.test(command)) return true;
  return absolutePathTokens(command).some((p) => !relativeInside(rootReal, p));
}

/** Exported for offline boundary tests (`node --test`). */
export function boundaryBlocked(root, toolName, input) {
  if (!root) return false;
  const rootReal = realRoot(root);
  if (!rootReal) return true;
  const fields = PATH_FIELDS[toolName];
  if (fields && input && typeof input === 'object') {
    for (const key of fields) {
      const value = input[key];
      if (typeof value === 'string' && !relativeInside(rootReal, value)) return true;
    }
  }
  if (toolName === 'bash' && bashEscapes(rootReal, input?.command)) return true;
  return false;
}

export default function (pi) {
  const grantable = new Set(
    (process.env.AH_PI_GRANTABLE || '').split(',').filter(Boolean),
  );
  const root = process.env.AH_PI_PROJECT_ROOT || '';
  const kindOf = (name) =>
    ({
      read: 'read',
      find: 'search',
      grep: 'search',
      ls: 'search',
      edit: 'edit',
      write: 'edit',
      bash: 'execute',
    })[name];
  pi.on('tool_call', async (event, ctx) => {
    const kind = kindOf(event.toolName);
    if (!kind || !grantable.has(kind)) {
      return { block: true, reason: 'Harness policy' };
    }
    if (boundaryBlocked(root, event.toolName, event.input)) {
      return { block: true, reason: 'outside project root' };
    }
    const msg = JSON.stringify({
      toolName: event.toolName,
      toolCallId: event.toolCallId,
      input: event.input,
    });
    const ok = await ctx.ui.confirm('ah-permission', msg);
    if (!ok) return { block: true, reason: 'denied by agent-harness policy' };
  });
}
