#!/usr/bin/env python3
"""Synthetic macOS source-read boundary proof; never launches OpenCode."""
import json
from pathlib import Path
import sys
import tempfile

from antigravity_feasibility import capture, check
from chatgpt_contained import contained_profile, PYTHON

MACHINE_ROOTS = ('/Library/Application Support/opencode', '/Library/Managed Preferences')


def source_profile(root, operator_home, denied_roots):
    # Keep this experiment separate from accepted diagnostics and production.
    check(bool(denied_roots))
    value = contained_profile(root, operator_home)
    for path in denied_roots:
        check(isinstance(path, Path) and path.is_absolute() and str(path) != '/')
        value += '(deny file-read* (subpath ' + json.dumps(str(path)) + '))'
    return value


WORKER = r'''
import json,os,subprocess,sys
from pathlib import Path
root=Path(sys.argv[1]); deny=sys.argv[2]=='deny'; phase=sys.argv[3]
system=root/'machine support'; mdm=root/'managed'
def blocked(action):
 try: action()
 except PermissionError:
  assert deny
 else: assert not deny
for path in [system/'opencode.json', mdm/'user'/'ai.opencode.managed.plist',
             mdm/'ai.opencode.managed.plist', root/'alias-in'/'opencode.json',
             system/'alias-out']:
 blocked(lambda: path.read_bytes())
 blocked(lambda: path.stat())
for path in [system,mdm]: blocked(lambda: list(path.iterdir()))
assert (root/'allowed'/'canary').read_text()=='AH_ALLOWED'
# An already running child must not gain access when a source appears/replaces
# an entry after launch. Writes are allowed inside disposable root only.
(system/'late.json').write_text('AH_LATE')
(system/'replacement').write_text('AH_REPLACED')
os.replace(system/'replacement',system/'opencode.json')
if phase=='parent': (root/'future').mkdir()
(root/'future'/'opencode.json').write_text('AH_FUTURE_ROOT')
for path in [system/'late.json',system/'opencode.json',root/'future'/'opencode.json']:
 blocked(lambda: path.read_bytes())
 blocked(lambda: path.stat())
if phase=='parent':
 subprocess.run([sys.executable,'-B',__file__,str(root),sys.argv[2],'child'],check=True)
print('AH_SOURCE_'+phase.upper()+'_PASS')
'''


def main():
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    # Independent roots keep late-file creation genuine in both modes.
    for deny in (False, True):
        with tempfile.TemporaryDirectory(prefix='ah-source-boundary-') as directory:
            root = Path(directory).resolve()
            for path in (root / 'machine support', root / 'managed' / 'user', root / 'allowed'):
                path.mkdir(parents=True)
            files = {'machine support/opencode.json': 'AH_SYSTEM',
                     'managed/user/ai.opencode.managed.plist': 'AH_USER_MDM',
                     'managed/ai.opencode.managed.plist': 'AH_MACHINE_MDM',
                     'allowed/canary': 'AH_ALLOWED'}
            for name, content in files.items():
                (root / name).write_text(content)
            check(not (root / 'machine support' / 'late.json').exists())
            check(not (root / 'future').exists())
            (root / 'alias-in').symlink_to(root / 'machine support', target_is_directory=True)
            (root / 'machine support' / 'alias-out').symlink_to(root / 'allowed' / 'canary')
            worker = root / 'worker.py'
            worker.write_text(WORKER)
            env = {'HOME': str(root / 'home'), 'TMPDIR': str(root), 'PATH': '/usr/bin:/bin'}
            # Real machine paths are denied without stat/list/read probes against
            # them. Equivalent disposable roots supply paired semantic controls.
            roots = tuple(Path(path) for path in MACHINE_ROOTS)
            if deny:
                roots += (root / 'machine support', root / 'managed', root / 'future')
            policy = source_profile(root, Path.home(), roots)
            out, err = capture(['/usr/bin/sandbox-exec', '-p', policy, PYTHON, '-B',
                                str(worker), str(root), 'deny' if deny else 'allow', 'parent'], root, env)
            check(not err and out.splitlines() == [b'AH_SOURCE_CHILD_PASS', b'AH_SOURCE_PARENT_PASS'])
    print('PASS: paired synthetic data/metadata/listing, symlink, late-create/replace and inherited-child controls')
    print('LIMIT: no OpenCode startup, real machine-source access, persistent state, login or model proof')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('Synthetic source boundary failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
