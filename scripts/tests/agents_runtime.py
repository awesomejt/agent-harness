#!/usr/bin/env python3
"""P4.1 OpenCode 2.2.5 destination/schema probe. No ACP/model prompt or key.

Candidate documents here prove destinations only; production emission belongs
in P4.2 and constraint enforcement/live role use belongs in P4.3/P4.4.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile


def main():
    runtime = shutil.which('opencode')
    assert runtime, 'OpenCode 2.2.5 required'
    version = subprocess.run([runtime, '--version'], capture_output=True, text=True, timeout=10)
    assert version.returncode == 0 and version.stdout.strip() == 'opencode v2.2.5'
    rules = [dict(action='*', resource='*', effect='deny'),
             dict(action='external_directory', resource='*', effect='deny')]
    with tempfile.TemporaryDirectory(prefix='ah-agent-destination-') as d:
        base = Path(d)
        for destination in ['document', 'project-markdown']:
            for mode in ['primary', 'subagent', 'all']:
                case = base / (destination + '-' + mode)
                project = case / 'project'
                project.mkdir(parents=True)
                home = case / 'home'
                home.mkdir(mode=0o700)
                env = dict(PATH=os.environ['PATH'], HOME=str(home),
                           XDG_CONFIG_HOME=str(home/'CONFIG'), XDG_DATA_HOME=str(home/'DATA'),
                           XDG_STATE_HOME=str(home/'STATE'), XDG_CACHE_HOME=str(home/'CACHE'),
                           OPENCODE_DISABLE_MODELS_FETCH='1', OPENCODE_DISABLE_AUTOUPDATE='1')
                body = 'P4.1 destination sentinel: review the supplied change.'
                item = dict(description='P4.1 probe', system=body, mode=mode,
                            permissions=rules, model=dict(providerID='ah-litellm', model='fixture'))
                config = dict(update='disable', share='disabled', permissions=rules,
                              providers={}, plugins=[], mcp={})
                if destination == 'document':
                    config['agents'] = {'reviewer': item}
                    env['OPENCODE_DISABLE_PROJECT_CONFIG'] = '1'
                else:
                    agents = project / '.opencode' / 'agents'
                    agents.mkdir(parents=True)
                    header = {k: v for k, v in item.items() if k != 'system'}
                    # JSON flow mapping is valid YAML frontmatter; body supplies system.
                    (agents/'reviewer.md').write_text('---\n'+json.dumps(header)+'\n---\n'+body+'\n')
                env['OPENCODE_CONFIG_CONTENT'] = json.dumps(config)
                result = subprocess.run([runtime, 'debug', 'agents', '--standalone'], cwd=project,
                                        env=env, capture_output=True, text=True, timeout=30)
                assert result.returncode == 0, 'debug agents failed'
                agents = json.loads(result.stdout)
                named = [a for a in agents if a['id'] == 'reviewer']
                assert len(named) == 1
                actual = named[0]
                assert actual['mode'] == mode and actual['system'] == body
                assert actual['description'] == item['description']
                assert actual['model'] == dict(providerID='ah-litellm', id='fixture')
                effective = actual['permissions']
                starts = [i for i in range(len(effective)-len(rules)+1) if effective[i:i+len(rules)] == rules]
                assert starts and all(r['effect'] == 'deny' for r in effective[starts[-1]+len(rules):])
                assert actual['request'] == dict(settings={}, headers={}, body={})
    print('PASS OpenCode 2.2.5: native agents.NAME and project .opencode/agents/NAME.md; '
          'primary/subagent/all, system, description, model and deny rules; 6 probes; 0 model prompts')


if __name__ == '__main__':
    main()
