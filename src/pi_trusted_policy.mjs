import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** Path-shaped fields per tool; content and patterns are intentionally excluded. */
const PATH_FIELDS = {
  read: ['path', 'filePath'],
  write: ['path', 'filePath'],
  edit: ['path', 'filePath'],
  find: ['path', 'cwd', 'directory'],
  grep: ['path', 'cwd'],
  ls: ['path', 'directory'],
};

const UNICODE_SPACES = /[\u00A0\u2000-\u200A\u202F\u205F\u3000]/g;
const NARROW_NO_BREAK_SPACE = '\u202F';
const BLOCKED_DEVICES = new Set(['/dev/stdout', '/dev/stderr']);

function realRoot(root) {
  if (!root) return '';
  try {
    return fs.realpathSync.native(root);
  } catch {
    return path.resolve(root);
  }
}

function fileExists(filePath) {
  try {
    fs.accessSync(filePath);
    return true;
  } catch {
    return false;
  }
}

/** Match Pi 1.5.0 `normalizePath` before `resolvePath` (paths.js). */
export function normalizePiPath(input, { homeDir = os.homedir() } = {}) {
  if (typeof input !== 'string' || !input) return '';
  let normalized = input.trim().replace(UNICODE_SPACES, ' ').normalize('NFC');
  if (normalized.startsWith('@')) {
    normalized = normalized.slice(1);
  }
  if (/^file:\/\//i.test(normalized)) {
    try {
      return fileURLToPath(normalized);
    } catch {
      return normalized;
    }
  }
  if (normalized.includes('$HOME') || normalized.includes('${HOME')) {
    return null;
  }
  if (normalized === '~') return homeDir;
  if (
    normalized.startsWith('~/') ||
    (process.platform === 'win32' && normalized.startsWith('~\\'))
  ) {
    return path.join(homeDir, normalized.slice(2));
  }
  if (/(^|[\s"'=])~(?=$|[\s;&|/])/.test(input.trim())) {
    return null;
  }
  return normalized;
}

export function resolvePiCwd(filePath, cwd) {
  const normalized = normalizePiPath(filePath);
  if (normalized === null) return null;
  if (path.isAbsolute(normalized)) {
    return path.normalize(normalized);
  }
  return path.resolve(cwd, normalized);
}

function tryMacOSScreenshotPath(filePath) {
  return filePath.replace(/ (AM|PM)\./gi, `${NARROW_NO_BREAK_SPACE}$1.`);
}

function tryNFDVariant(filePath) {
  return filePath.normalize('NFD');
}

function tryCurlyQuoteVariant(filePath) {
  return filePath.replace(/'/g, '\u2019');
}

/** Candidates Pi read may open (path-utils resolveReadPathAsync). */
export function readPathCandidates(filePath, cwd) {
  const resolved = resolvePiCwd(filePath, cwd);
  if (resolved === null) return [null];
  const candidates = [resolved];
  if (!fileExists(resolved)) {
    candidates.push(
      tryMacOSScreenshotPath(resolved),
      tryNFDVariant(resolved),
      tryCurlyQuoteVariant(resolved),
      tryCurlyQuoteVariant(tryNFDVariant(resolved)),
    );
  }
  return [...new Set(candidates)];
}

function isSafeNullDevice(absPath) {
  return path.normalize(absPath) === '/dev/null';
}

function walkPathInside(rootReal, absPath) {
  let abs = absPath;
  let root = rootReal;
  try {
    abs = fs.realpathSync.native(absPath);
  } catch {
    abs = path.normalize(absPath);
  }
  try {
    root = fs.realpathSync.native(rootReal);
  } catch {
    root = rootReal;
  }
  const norm = path.normalize(abs);
  if (BLOCKED_DEVICES.has(norm)) return false;
  if (isSafeNullDevice(norm)) return true;
  const rel = path.relative(root, norm);
  if (rel === '') return true;
  if (rel.startsWith('..') || path.isAbsolute(rel)) return false;
  let current = root;
  for (const part of rel.split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    let st;
    try {
      st = fs.lstatSync(current);
    } catch {
      return true;
    }
    if (st.isSymbolicLink()) {
      let target;
      try {
        target = fs.readlinkSync(current);
      } catch {
        return false;
      }
      const resolved = path.resolve(path.dirname(current), target);
      if (!walkPathInside(root, resolved)) return false;
      try {
        current = fs.realpathSync.native(current);
      } catch {
        return false;
      }
    }
  }
  return true;
}

function pathInsideProject(rootReal, userPath, toolName) {
  const candidates =
    toolName === 'read'
      ? readPathCandidates(userPath, rootReal)
      : [resolvePiCwd(userPath, rootReal)];
  for (const abs of candidates) {
    if (abs === null) return false;
    if (!walkPathInside(rootReal, abs)) return false;
  }
  return true;
}

function normalizeAbsoluteToken(token) {
  if (token.startsWith('//') && !token.startsWith('///')) {
    return `/${token.slice(2)}`;
  }
  return token;
}

function absolutePathTokens(text) {
  const paths = [];
  for (const m of text.matchAll(/(?:^|[\s"'=<>])(\/[^\s;|&]+)/g)) {
    paths.push(normalizeAbsoluteToken(m[1]));
  }
  for (const m of text.matchAll(/(?:^|[\s"'=])(~\/[^\s;|&]+)/g)) {
    paths.push(path.join(os.homedir(), m[1].slice(2)));
  }
  return paths;
}

function bashEscapes(rootReal, command) {
  if (typeof command !== 'string' || !command) return false;
  const v = command.trim().normalize('NFC');
  if (v.startsWith('~') || v.includes('$HOME') || v.includes('${HOME')) return true;
  if (/(^|[\s"'=])~(?=$|[\s;&|/])/.test(command)) return true;
  if (/(^|[\s"'=:/])\.\.(?=$|[\s"'/;|&])/.test(command)) return true;
  if (/\/\.\.(\/|$)/.test(command)) return true;
  return absolutePathTokens(command).some((p) => !walkPathInside(rootReal, p));
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
      if (typeof value === 'string' && !pathInsideProject(rootReal, value, toolName)) {
        return true;
      }
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
