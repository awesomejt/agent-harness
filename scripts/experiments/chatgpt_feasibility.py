#!/usr/bin/env python3
"""Opt-in macOS OpenCode 2.2.5 no-login diagnostic observations, not a gate pass."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile

from antigravity_feasibility import capture, check, containment_checks, profile

SHA256 = '4ecfcc961e52d7c89011db860df1cafcb3ed180a2902fbd5fb99fffc923bb1b5'
COMMANDS = {('--version',)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--opencode', default='opencode')
    args = parser.parse_args()
    check(sys.platform == 'darwin' and Path('/usr/bin/sandbox-exec').is_file())
    installed = shutil.which(args.opencode)
    check(installed is not None)
    with tempfile.TemporaryDirectory(prefix='ah-chatgpt-feasibility-') as directory:
        root = Path(directory).resolve()
        executable = root / 'opencode-cli'
        shutil.copy2(installed, executable)
        check(hashlib.sha256(executable.read_bytes()).hexdigest() == SHA256)
        home, project = root / 'home', root / 'repo' / 'project'
        for path in (home, project, root / 'repo' / '.git'):
            path.mkdir(parents=True, exist_ok=True)
        env = {'HOME': str(home), 'TMPDIR': str(root),
               'PATH': '/usr/bin:/bin:/usr/sbin:/sbin', 'NO_COLOR': '1', 'TERM': 'dumb',
               'OPENCODE_DISABLE_MODELS_FETCH': 'true',
               'OPENCODE_DISABLE_AUTOUPDATE': 'true',
               'OPENCODE_DISABLE_PROJECT_CONFIG': 'true'}
        for kind in ('CONFIG', 'DATA', 'CACHE', 'STATE'):
            env['XDG_' + kind + '_HOME'] = str(root / kind)
        model = {'providerID': 'openai', 'model': 'gpt-6.1-sol'}
        rules = [{'action': '*', 'resource': '*', 'effect': 'deny'},
                 {'action': 'external_directory', 'resource': '*', 'effect': 'deny'}]
        config = {'model': model, 'update': 'disable', 'share': 'disabled',
                  'permissions': rules, 'policies': [
                      {'action': 'provider.use', 'resource': '*', 'effect': 'deny'},
                      {'action': 'provider.use', 'resource': 'openai', 'effect': 'allow'}],
                  'agents': {'title': {'model': model}}, 'instructions': [],
                  'mcp': {}, 'plugins': [], 'providers': {}}
        env['OPENCODE_CONFIG_CONTENT'] = json.dumps(config)
        sandbox = ['/usr/bin/sandbox-exec', '-p', profile(root, Path.home())]
        with tempfile.TemporaryDirectory(prefix='.ah-chatgpt-read-', dir=Path.home()) as protected:
            read_target = Path(protected) / 'sentinel'
            read_target.write_text('AH_READ_DENIAL_SENTINEL')
            with tempfile.TemporaryDirectory(prefix='ah-chatgpt-fence-') as fence:
                capture([*sandbox, '/usr/bin/python3', '-B', '-c',
                         containment_checks(read_target, Path(fence) / 'write')], project, env)
        print('PASS: network bind, operator-home data read and outside write denied', flush=True)

        def run(command):
            check(tuple(command) in COMMANDS)
            out, _ = capture([*sandbox, str(executable), *command, '--standalone'], project, env)
            return out.decode()

        check(run(['--version']).strip() == 'opencode v2.2.5')
        # Standalone debug starts a child server. Preserve its exact exit status
        # inside the bounded group capture; the wrapper itself always exits zero.
        wrapper = '"$@"; status=$?; printf "\\nAH_EXIT=%s\\n" "$status"'
        out, err = capture([*sandbox, '/bin/sh', '-c', wrapper, 'ah-diagnostic',
                            str(executable), 'debug', 'config', '--standalone'], project, env)
        check(out.endswith(b'\nAH_EXIT=1\n') and b'EPERM' in err and b'posix_spawn' in err)
        print('BLOCK: standalone debug config exits 1 with EPERM at child posix_spawn', flush=True)
        print('LIMIT: sources/agents positive controls not reached; no login/session/model or permission proof')


if __name__ == '__main__':
    try:
        main()
    except Exception:
        print('OpenCode ChatGPT diagnostic observation failed; raw diagnostics withheld', file=sys.stderr)
        sys.exit(1)
