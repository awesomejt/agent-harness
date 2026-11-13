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
    fn({ root, outside: outsideReal, project, base });
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

test('Pi ~ path escapes are blocked; @ is stripped then checked', () => {
  withProject(({ root, project }) => {
    assert.equal(boundaryBlocked(root, 'read', { path: '~/.ssh/id_rsa' }), true);
    assert.equal(boundaryBlocked(root, 'read', { path: '@/etc/passwd' }), true);
    fs.mkdirSync(path.join(project, 'src'), { recursive: true });
    fs.writeFileSync(path.join(project, 'src', 'x.txt'), 'ok\n');
    assert.equal(boundaryBlocked(root, 'read', { path: '@src/x.txt' }), false);
  });
});

test('in-project symlink to outside is blocked', () => {
  withProject(({ root, outside, project }) => {
    const link = path.join(project, 'leak.txt');
    fs.symlinkSync(outside, link);
    assert.equal(boundaryBlocked(root, 'read', { path: 'leak.txt' }), true);
  });
});

test('non-canonical absolute path to inside file is allowed on macOS layout', () => {
  withProject(({ root, project }) => {
    const inside = path.join(project, 'inside.txt');
    const maybeVar = inside.replace('/private', '');
    if (maybeVar !== inside && fs.existsSync(maybeVar)) {
      assert.equal(boundaryBlocked(root, 'read', { path: maybeVar }), false);
    } else {
      assert.equal(boundaryBlocked(root, 'read', { path: inside }), false);
    }
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
      boundaryBlocked(root, 'bash', { command: 'cd .. && cat outside.txt' }),
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
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'python3 -B test_calc.py 2>/dev/null' }),
      false,
    );
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'curl -s https://example.com/x' }),
      false,
    );
  });
});

test('missing root does not block', () => {
  assert.equal(boundaryBlocked('', 'read', { path: '/etc/passwd' }), false);
});

test('file URL and home paths are blocked', () => {
  withProject(({ root }) => {
    assert.equal(
      boundaryBlocked(root, 'read', { path: 'file:///etc/passwd' }),
      true,
    );
    assert.equal(boundaryBlocked(root, 'read', { path: '@~/.zshrc' }), true);
  });
});

test('device nodes other than /dev/null are blocked', () => {
  withProject(({ root }) => {
    assert.equal(boundaryBlocked(root, 'write', { path: '/dev/stdout' }), true);
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'cat > /dev/stderr' }),
      true,
    );
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'python3 test.py 2>/dev/null' }),
      false,
    );
  });
});

test('dangling symlink write escapes are blocked', () => {
  withProject(({ root, project, base }) => {
    const outside = path.join(base, 'outside-created.txt');
    const link = path.join(project, 'link.txt');
    fs.symlinkSync(path.relative(project, outside), link);
    assert.equal(boundaryBlocked(root, 'write', { path: 'link.txt' }), true);
  });
});

test('curly-quote read fallbacks stay inside the root', () => {
  withProject(({ root, outside, project }) => {
    const curly = path.join(project, 'curly\u2019name');
    fs.symlinkSync(outside, curly);
    assert.equal(
      boundaryBlocked(root, 'read', { path: "curly'name" }),
      true,
    );
  });
});

test('bash double-slash absolute paths are blocked', () => {
  withProject(({ root }) => {
    assert.equal(
      boundaryBlocked(root, 'bash', { command: 'cat //etc/passwd' }),
      true,
    );
  });
});
