import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../..');
const policyUrl = pathToFileURL(path.join(ROOT, 'src/pi_trusted_policy.mjs')).href;
const { boundaryBlocked } = await import(policyUrl);

function withProject(fn) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'ah-pi-boundary-'));
  const project = path.join(base, 'project');
  fs.mkdirSync(project);
  fs.writeFileSync(path.join(project, 'inside.txt'), 'ok\n');
  const outside = path.join(base, 'outside.txt');
  fs.writeFileSync(outside, 'secret\n');
  const root = fs.realpathSync.native(project);
  const outsideReal = fs.realpathSync.native(outside);
  try {
    fn({ root, outside: outsideReal, project });
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
}

test('read outside absolute path is blocked', () => {
  withProject(({ root, outside }) => {
    assert.equal(boundaryBlocked(root, 'read', { path: outside }), true);
    assert.equal(boundaryBlocked(root, 'read', { path: 'inside.txt' }), false);
  });
});

test('read parent traversal is blocked', () => {
  withProject(({ root }) => {
    assert.equal(boundaryBlocked(root, 'read', { path: '../outside.txt' }), true);
  });
});

test('edit content with slashes or URLs is allowed', () => {
  withProject(({ root }) => {
    assert.equal(
      boundaryBlocked(root, 'edit', {
        path: 'calc.py',
        content: 'return a/b\nhttps://example.com/x\n',
      }),
      false,
    );
    assert.equal(
      boundaryBlocked(root, 'grep', { path: '.', pattern: 'foo/bar' }),
      false,
    );
  });
});

test('bash blocks parent traversal and absolute outside paths', () => {
  withProject(({ root, outside }) => {
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'cat ../outside.txt' }),
      true,
    );
    assert.equal(
      boundaryBlocked(root, 'bash', { command: `cat ${outside}` }),
      true,
    );
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'python3 -B test_calc.py' }),
      false,
    );
  });
});

test('missing root does not block', () => {
  assert.equal(boundaryBlocked('', 'read', { path: '/etc/passwd' }), false);
});
