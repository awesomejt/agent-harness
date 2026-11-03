#!/usr/bin/env python3
"""P4.2 OpenCode 2.2.5 emission/collision probe. No ACP/model prompt or key.

Loads the exact golden files emitted by `ah` (tests/fixtures/opencode-agents)
from a disposable project's `.opencode/agents/`, and confirms every project
source the collision check refuses really defines a same-named agent. This
checks parsing/destinations only; enforcement belongs to P4.3/P4.4.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
GOLDEN = ROOT / 'tests' / 'fixtures' / 'opencode-agents'
BUILT_IN = {'build', 'plan', 'general', 'explore', 'compaction', 'title', 'summary'}


def agents(runtime, setup):
    with tempfile.TemporaryDirectory(prefix='ah-agent-emission-') as d:
        base = Path(d)
        project = base / 'project'
        project.mkdir()
        home = base / 'home'
        home.mkdir(mode=0o700)
        setup(project)
        env = dict(PATH=os.environ['PATH'], HOME=str(home),
                   XDG_CONFIG_HOME=str(home/'CONFIG'), XDG_DATA_HOME=str(home/'DATA'),
                   XDG_STATE_HOME=str(home/'STATE'), XDG_CACHE_HOME=str(home/'CACHE'),
                   OPENCODE_DISABLE_MODELS_FETCH='1', OPENCODE_DISABLE_AUTOUPDATE='1',
                   OPENCODE_CONFIG_CONTENT=json.dumps(dict(
                       update='disable', share='disabled', providers={}, plugins=[], mcp={})))
        result = subprocess.run([runtime, 'debug', 'agents', '--standalone'], cwd=project,
                                env=env, capture_output=True, text=True, timeout=30)
        assert result.returncode == 0, 'debug agents failed'
        return {a['id']: a for a in json.loads(result.stdout) if a['id'] not in BUILT_IN}


def write(project, path, text):
    target = project / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text)


def main():
    runtime = shutil.which('opencode')
    assert runtime, 'OpenCode 2.2.5 required'
    version = subprocess.run([runtime, '--version'], capture_output=True, text=True, timeout=10)
    assert version.returncode == 0 and version.stdout.strip() == 'opencode v2.2.5'

    golden = sorted(GOLDEN.glob('*.md'))
    assert [g.stem for g in golden] == ['coder', 'reviewer']
    loaded = agents(runtime, lambda p: [write(p, '.opencode/agents/' + g.name, g.read_text())
                                        for g in golden])
    assert sorted(loaded) == ['coder', 'reviewer']
    for g in golden:
        _, header, body = g.read_text().split('---\n', 2)
        header = json.loads(header)
        actual = loaded[g.stem]
        assert actual['mode'] == header['mode']
        assert actual['description'] == header['description']
        assert actual['system'] == body.strip()
        assert actual['model'] == dict(providerID='ah-litellm', id='proxy')
        rules = header['permissions']
        assert all(r['effect'] != 'allow' for r in rules)
        effective = actual['permissions']
        starts = [i for i in range(len(effective)-len(rules)+1)
                  if effective[i:i+len(rules)] == rules]
        assert starts and all(r['effect'] == 'deny' for r in effective[starts[-1]+len(rules):])
        assert actual['request'] == dict(settings={}, headers={}, body={})

    # Each source the planner refuses defines an agent OpenCode would load.
    item = lambda key: json.dumps({key: {'reviewer': {'description': key, 'prompt': 'x'}}})
    sources = {
        'legacy .opencode/agent/': lambda p: write(p, '.opencode/agent/reviewer.md',
                                                   '---\n{"description":"legacy"}\n---\nx\n'),
        'case variant': lambda p: write(p, '.opencode/agents/Reviewer.md',
                                        '---\n{"description":"case"}\n---\nx\n'),
        'opencode.json agent': lambda p: write(p, 'opencode.json', item('agent')),
        'opencode.json agents': lambda p: write(p, 'opencode.json', item('agents')),
        '.opencode/opencode.json agent': lambda p: write(p, '.opencode/opencode.json', item('agent')),
    }
    for label, setup in sources.items():
        found = agents(runtime, setup)
        assert [k for k in found if k.lower() == 'reviewer'], label
    # Canonical project sources are not an OpenCode agent source.
    assert agents(runtime, lambda p: write(p, 'agents/reviewer.md',
                                           (ROOT/'agents'/'reviewer.md').read_text())) == {}
    print('PASS OpenCode 2.2.5: emitted coder/reviewer load with mode, description, system, '
          'model and ask/deny ceiling rules; 5 collision sources define agents; '
          'project agents/ not loaded; 8 probes; 0 model prompts')


if __name__ == '__main__':
    main()
